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
}
