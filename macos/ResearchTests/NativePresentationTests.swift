import AppKit
import SwiftUI
import XCTest
@testable import Notaeo

final class NativePresentationTests: XCTestCase {
    func testLaunchFrameIsCenteredOnTheVisibleScreenIncludingNegativeOrigins() {
        for screen in [CGRect(x: 0, y: 24, width: 1728, height: 1050),
                       CGRect(x: -1440, y: 100, width: 1440, height: 820),
                       CGRect(x: 320, y: -900, width: 1024, height: 700)] {
            let frame = NativeWindowPlacement.frame(in: screen)
            XCTAssertTrue(screen.contains(frame))
            XCTAssertEqual(frame.midX, screen.midX, accuracy: 0.001)
            XCTAssertEqual(frame.midY, screen.midY, accuracy: 0.001)
            XCTAssertLessThanOrEqual(frame.width, 1200)
            XCTAssertLessThanOrEqual(frame.height, 800)
        }
    }

    @MainActor
    func testLaunchOptsOutOfRestoredWindowsWithoutChangingAppearance() {
        let name = "notaeo.presentation.\(UUID().uuidString)"
        let preferences = UserDefaults(suiteName: name)!
        defer { preferences.removePersistentDomain(forName: name) }
        preferences.set(true, forKey: "NSQuitAlwaysKeepsWindows")
        preferences.set("dark", forKey: "notaeo.native.appearance")
        MainWindowPresentation.configureLaunchPreferences(preferences)
        XCTAssertFalse(preferences.bool(forKey: "NSQuitAlwaysKeepsWindows"))
        XCTAssertEqual(preferences.string(forKey: "notaeo.native.appearance"), "dark")
    }

    @MainActor
    func testMainSceneActuallyLaunchesCenteredAndWindowed() throws {
        let window = try XCTUnwrap(NSApplication.shared.windows.first { $0.title == "Notaeo" })
        let visible = try XCTUnwrap(window.screen).visibleFrame
        XCTAssertFalse(window.styleMask.contains(.fullScreen))
        XCTAssertFalse(window.isRestorable)
        XCTAssertTrue(visible.contains(window.frame))
        XCTAssertEqual(window.frame.midX, visible.midX, accuracy: 1)
        XCTAssertEqual(window.frame.midY, visible.midY, accuracy: 1)
    }

    @MainActor
    func testPlacementAppliesOnceAndPreservesUserMovementAndWindowedStyle() {
        let window = NSWindow(contentRect: CGRect(x: 10, y: 10, width: 600, height: 500),
                              styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: true)
        let policy = MainWindowPresentation()
        let screen = CGRect(x: -1400, y: 20, width: 1400, height: 900)
        XCTAssertTrue(policy.apply(to: window, visibleFrame: screen))
        XCTAssertFalse(window.isRestorable)
        XCTAssertFalse(window.styleMask.contains(.fullScreen))
        XCTAssertEqual(window.frame.midX, screen.midX, accuracy: 1)
        XCTAssertEqual(window.frame.midY, screen.midY, accuracy: 1)
        window.setFrameOrigin(CGPoint(x: -1200, y: 70))
        let movedFrame = window.frame
        XCTAssertFalse(policy.apply(to: window, visibleFrame: screen))
        XCTAssertEqual(window.frame, movedFrame)
    }

    func testStartupFolioStopsForEitherReducedMotionPreference() {
        for (system, app) in [(true, false), (false, true), (true, true)] {
            let motion = NativeMotionPolicy(systemReduceMotion: system, appReduceMotion: app)
            XCTAssertEqual(motion.folioLift(time: 0), motion.folioLift(time: 2))
        }
        let motion = NativeMotionPolicy(systemReduceMotion: false, appReduceMotion: false)
        XCTAssertNotEqual(motion.folioLift(time: 0), motion.folioLift(time: 1))
        for time in stride(from: 0.0, through: 8.0, by: 0.1) {
            XCTAssertTrue((-3...3).contains(motion.folioLift(time: time)))
            XCTAssertEqual(motion.folioLift(time: time), motion.folioLift(time: time + 4), accuracy: 0.0001)
        }
    }

    @MainActor
    func testStartupCanRenderOfflineWithReducedMotion() throws {
        let name = "notaeo.startup-preview.\(UUID().uuidString)"
        let preferences = UserDefaults(suiteName: name)!
        defer { preferences.removePersistentDomain(forName: name) }
        preferences.set(true, forKey: "notaeo.native.reduceMotion")
        let renderer = ImageRenderer(content: StartupView(preferences: preferences).frame(width: 960, height: 640))
        let image = try XCTUnwrap(renderer.nsImage)
        let data = try XCTUnwrap(image.tiffRepresentation)
        let bitmap = try XCTUnwrap(NSBitmapImageRep(data: data))
        XCTAssertEqual(bitmap.pixelsWide, 960)
        XCTAssertEqual(bitmap.pixelsHigh, 640)
        let png = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
        try png.write(to: URL(fileURLWithPath: "/tmp/notaeo-startup-preview.png"))
    }

    @MainActor
    func testPackagedIconMatchesTheStartupMark() throws {
        let iconURL = try XCTUnwrap(Bundle.main.url(forResource: "AppIcon", withExtension: "icns"))
        let icon = try XCTUnwrap(NSImage(contentsOf: iconURL))
        let mark = try XCTUnwrap(ImageRenderer(content: NotaeoMark().frame(width: 512, height: 512)).nsImage)
        func bitmap(_ image: NSImage) throws -> NSBitmapImageRep {
            var rect = CGRect(x: 0, y: 0, width: 512, height: 512)
            return NSBitmapImageRep(cgImage: try XCTUnwrap(image.cgImage(forProposedRect: &rect, context: nil, hints: nil)))
        }
        let actual = try bitmap(icon)
        let expected = try bitmap(mark)
        var error = 0.0
        for y in 1..<10 {
            for x in 1..<10 {
                let a = try XCTUnwrap(actual.colorAt(x: actual.pixelsWide * x / 10, y: actual.pixelsHigh * y / 10)?.usingColorSpace(.sRGB))
                let b = try XCTUnwrap(expected.colorAt(x: expected.pixelsWide * x / 10, y: expected.pixelsHigh * y / 10)?.usingColorSpace(.sRGB))
                error += abs(a.redComponent - b.redComponent) + abs(a.greenComponent - b.greenComponent)
                    + abs(a.blueComponent - b.blueComponent) + abs(a.alphaComponent - b.alphaComponent)
            }
        }
        XCTAssertLessThan(error / (81 * 4), 0.04, "Regenerate stale icon assets from the original folio mark")
    }
}

final class NativeFeedbackTests: XCTestCase {
    @MainActor
    func testExportCueFollowsSuccessfulAtomicWriteAndNeverAFailedWrite() throws {
        let name = "notaeo.export-feedback.\(UUID().uuidString)"
        let preferences = UserDefaults(suiteName: name)!
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(name)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer {
            preferences.removePersistentDomain(forName: name)
            try? FileManager.default.removeItem(at: directory)
        }
        preferences.set(true, forKey: NativeFeedback.preferenceKey)
        var plays = 0
        let feedback = NativeFeedback(preferences: preferences, isTestHost: false) { _ in plays += 1 }
        let data = Data("synthetic exported content".utf8)
        let target = directory.appendingPathComponent("Biologie 雪.zip")
        try feedback.saveExport(data, to: target)
        XCTAssertEqual(try Data(contentsOf: target), data)
        XCTAssertEqual(plays, 1)
        XCTAssertThrowsError(try feedback.saveExport(data, to: directory))
        XCTAssertEqual(plays, 1, "A failed save must not produce a success cue")
        preferences.set(false, forKey: NativeFeedback.preferenceKey)
        try feedback.saveExport(Data(), to: target)
        XCTAssertEqual(try Data(contentsOf: target), Data())
        XCTAssertEqual(plays, 1)
    }

    func testChimeIsDeterministicBriefQuietAndHasSilentEdges() {
        let samples = CozyChime.samples
        XCTAssertEqual(samples, CozyChime.samples)
        XCTAssertEqual(samples.count, Int(Double(CozyChime.sampleRate) * 0.52))
        XCTAssertEqual(samples.first, 0)
        XCTAssertEqual(samples.last, 0)
        XCTAssertTrue(samples.allSatisfy { $0.isFinite && abs($0) <= 0.20 })
        XCTAssertGreaterThan(samples.map { abs($0) }.max() ?? 0, 0.05)
        let largestStep = zip(samples, samples.dropFirst()).map { abs($0 - $1) }.max() ?? 1
        XCTAssertLessThan(largestStep, 0.02, "No sharp waveform discontinuities")
    }

    func testChimeWavHasConsistentMonoPcmHeaderAndIsLoadableWithoutPlayback() throws {
        let data = CozyChime.waveData
        XCTAssertEqual(String(data: data.prefix(4), encoding: .ascii), "RIFF")
        XCTAssertEqual(String(data: data[8..<12], encoding: .ascii), "WAVE")
        func integer(_ offset: Int, _ count: Int) -> Int {
            (0..<count).reduce(0) { $0 | Int(data[offset + $1]) << (8 * $1) }
        }
        XCTAssertEqual(integer(4, 4), data.count - 8)
        XCTAssertEqual(integer(22, 2), 1)
        XCTAssertEqual(integer(24, 4), 44_100)
        XCTAssertEqual(integer(34, 2), 16)
        XCTAssertEqual(integer(40, 4), CozyChime.samples.count * 2)
        XCTAssertEqual(data.count, 44 + CozyChime.samples.count * 2)
        XCTAssertNotNil(NSSound(data: data), "Decode only; never play test audio")
        try data.write(to: URL(fileURLWithPath: "/tmp/notaeo-cozy-chime.wav"))
    }

    @MainActor
    func testCompletionRequiresOptInPreviewIsExplicitAndMutePersists() {
        let name = "notaeo.feedback.\(UUID().uuidString)"
        let preferences = UserDefaults(suiteName: name)!
        defer { preferences.removePersistentDomain(forName: name) }
        var plays = 0
        let feedback = NativeFeedback(preferences: preferences, isTestHost: false) { bytes in
            XCTAssertEqual(bytes, CozyChime.waveData)
            plays += 1
        }
        feedback.success()
        XCTAssertEqual(plays, 0, "Native sounds default off")
        feedback.preview()
        XCTAssertEqual(plays, 1, "An explicit preview works before opting in")
        preferences.set(true, forKey: NativeFeedback.preferenceKey)
        feedback.success()
        XCTAssertEqual(plays, 2)
        preferences.set(false, forKey: NativeFeedback.preferenceKey)
        let reopened = NativeFeedback(preferences: preferences, isTestHost: false) { _ in plays += 1 }
        reopened.success()
        XCTAssertEqual(plays, 2)
    }

    @MainActor
    func testTestHostsSuppressBothCompletionAndExplicitPreviewWithoutChangingPreferences() {
        let name = "notaeo.feedback-silent.\(UUID().uuidString)"
        let preferences = UserDefaults(suiteName: name)!
        defer { preferences.removePersistentDomain(forName: name) }
        preferences.set(true, forKey: NativeFeedback.preferenceKey)
        let feedback = NativeFeedback(preferences: preferences, isTestHost: true) { _ in
            XCTFail("A test host must never emit audio")
        }
        feedback.success()
        feedback.preview()
        feedback.stop()
        XCTAssertTrue(preferences.bool(forKey: NativeFeedback.preferenceKey))
    }
}
