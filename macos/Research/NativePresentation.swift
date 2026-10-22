import AppKit
import SwiftUI

enum NativeWindowPlacement {
    static func frame(in visibleFrame: CGRect) -> CGRect {
        let width = min(1200, max(1, visibleFrame.width - 48))
        let height = min(800, max(1, visibleFrame.height - 48))
        return CGRect(x: visibleFrame.midX - width / 2, y: visibleFrame.midY - height / 2,
                      width: width, height: height)
    }
}

@MainActor
final class MainWindowPresentation {
    private weak var placedWindow: NSWindow?

    static func configureLaunchPreferences(_ preferences: UserDefaults) {
        // The owner wants a fresh windowed launch, even after quitting fullscreen.
        // This is the app's domain, not the system-wide preferences domain.
        preferences.set(false, forKey: "NSQuitAlwaysKeepsWindows")
    }

    @discardableResult
    func apply(to window: NSWindow, visibleFrame: CGRect) -> Bool {
        guard placedWindow !== window else { return false }
        placedWindow = window
        window.isRestorable = false
        window.setFrame(NativeWindowPlacement.frame(in: visibleFrame), display: false)
        return true
    }
}

/// Attached only to the main scene. Settings and later view updates never move it.
struct MainWindowPlacement: NSViewRepresentable {
    final class Anchor: NSView {
        let placement = MainWindowPresentation()

        override func viewDidMoveToWindow() {
            super.viewDidMoveToWindow()
            guard let window, let screen = window.screen ?? NSScreen.main else { return }
            placement.apply(to: window, visibleFrame: screen.visibleFrame)
        }
    }

    func makeNSView(context: Context) -> Anchor { Anchor() }
    func updateNSView(_ nsView: Anchor, context: Context) {}
}

extension NativeMotionPolicy {
    func folioLift(time: Double) -> Double {
        guard !reducesMotion else { return 0 }
        return 2 * sin(time.truncatingRemainder(dividingBy: 4) / 4 * 2 * .pi)
    }
}

/// An original folded-paper N; the app icon generator uses the same coordinates.
struct NotaeoMark: View {
    var body: some View {
        GeometryReader { geometry in
            let side = min(geometry.size.width, geometry.size.height)
            ZStack {
                RoundedRectangle(cornerRadius: side * 0.24)
                    .fill(LinearGradient(colors: [Color(red: 0.12, green: 0.34, blue: 0.30),
                                                   Color(red: 0.05, green: 0.20, blue: 0.18)],
                                         startPoint: .topLeading, endPoint: .bottomTrailing))
                FolioRibbon().fill(Color(red: 0.97, green: 0.94, blue: 0.85))
                Path { path in
                    path.move(to: CGPoint(x: side * 0.28, y: side * 0.24))
                    path.addLine(to: CGPoint(x: side * 0.72, y: side * 0.76))
                }.stroke(Color.black.opacity(0.10), lineWidth: side * 0.025)
                Circle().fill(Color(red: 0.83, green: 0.68, blue: 0.38))
                    .frame(width: side * 0.075, height: side * 0.075)
                    .offset(x: side * 0.28, y: -side * 0.30)
            }
            .frame(width: side, height: side)
        }
        .accessibilityHidden(true)
    }
}

private struct FolioRibbon: Shape {
    func path(in rect: CGRect) -> Path {
        let points: [CGPoint] = [(0.22, 0.76), (0.22, 0.24), (0.36, 0.24),
                                 (0.64, 0.59), (0.64, 0.24), (0.78, 0.24),
                                 (0.78, 0.76), (0.64, 0.76), (0.36, 0.41),
                                 (0.36, 0.76)].map { CGPoint(x: rect.minX + $0.0 * rect.width,
                                                            y: rect.minY + $0.1 * rect.height) }
        return Path { path in path.addLines(points); path.closeSubpath() }
    }
}

enum CozyChime {
    static let sampleRate = 44_100
    static let samples: [Float] = {
        let count = Int(Double(sampleRate) * 0.52)
        var result = [Float](repeating: 0, count: count)
        func note(_ time: Double, frequency: Double, start: Double, length: Double) -> Double {
            let local = time - start
            guard local > 0, local < length else { return 0 }
            let attack = min(1, local / 0.022)
            let release = min(1, (length - local) / 0.060)
            let envelope = attack * attack * (3 - 2 * attack)
                * release * release * (3 - 2 * release) * exp(-7 * local)
            let phase = 2 * Double.pi * frequency * local
            return envelope * (sin(phase) + 0.12 * sin(2 * phase))
        }
        for index in 1..<(count - 1) {
            let time = Double(index) / Double(sampleRate)
            result[index] = Float(0.10 * note(time, frequency: 261.626, start: 0, length: 0.39)
                                 + 0.085 * note(time, frequency: 329.628, start: 0.09, length: 0.43))
        }
        return result
    }()

    static let waveData: Data = {
        var data = Data()
        func append<T: FixedWidthInteger>(_ value: T) {
            var littleEndian = value.littleEndian
            withUnsafeBytes(of: &littleEndian) { data.append(contentsOf: $0) }
        }
        let size = UInt32(samples.count * 2)
        data.append(contentsOf: "RIFF".utf8); append(UInt32(36) + size)
        data.append(contentsOf: "WAVEfmt ".utf8); append(UInt32(16))
        append(UInt16(1)); append(UInt16(1)); append(UInt32(sampleRate))
        append(UInt32(sampleRate * 2)); append(UInt16(2)); append(UInt16(16))
        data.append(contentsOf: "data".utf8); append(size)
        for sample in samples { append(Int16((sample * Float(Int16.max)).rounded())) }
        return data
    }()
}

@MainActor
final class NativeFeedback {
    static let preferenceKey = "notaeo.native.soundEnabled"
    static let shared = NativeFeedback()

    private let preferences: UserDefaults
    private let isTestHost: Bool
    private let playback: ((Data) -> Void)?
    private var sound: NSSound?

    init(preferences: UserDefaults = .standard, isTestHost: Bool = AppState.isTestHost(),
         playback: ((Data) -> Void)? = nil) {
        self.preferences = preferences
        self.isTestHost = isTestHost
        self.playback = playback
    }

    func success() { play(explicitPreview: false) }
    func preview() { play(explicitPreview: true) }

    func saveExport(_ data: Data, to url: URL) throws {
        try data.write(to: url, options: .atomic)
        success()
    }

    func stop() {
        sound?.stop()
        sound = nil
    }

    private func play(explicitPreview: Bool) {
        guard !isTestHost, explicitPreview || preferences.bool(forKey: Self.preferenceKey) else { return }
        stop()
        if let playback {
            playback(CozyChime.waveData)
        } else {
            sound = NSSound(data: CozyChime.waveData)
            sound?.volume = 0.6
            sound?.play()
        }
    }
}
