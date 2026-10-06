import XCTest
@testable import Notaeo

final class ThinkingOrbTests: XCTestCase {
    func testReducedMotionOrbsRemainStillWhenEitherPreferenceIsEnabled() {
        for (system, app) in [(true, false), (false, true), (true, true)] {
            let policy = NativeMotionPolicy(systemReduceMotion: system, appReduceMotion: app)
            for index in 0..<3 {
                let first = policy.orbSample(time: 0, index: index)
                let later = policy.orbSample(time: 100, index: index)
                XCTAssertEqual(first.scale, later.scale)
                XCTAssertEqual(first.x, later.x)
                XCTAssertEqual(first.y, later.y)
                XCTAssertEqual(first.opacity, later.opacity)
            }
        }
    }

    func testThinkingOrbsMoveGentlyWithinTheirFrameAndRepeat() {
        let policy = NativeMotionPolicy(systemReduceMotion: false, appReduceMotion: false)
        for index in 0..<3 {
            for time in stride(from: 0.0, through: 8.0, by: 0.1) {
                let sample = policy.orbSample(time: time, index: index)
                XCTAssertTrue((0.88...1.12).contains(sample.scale))
                XCTAssertTrue((-3.0...3.0).contains(sample.x))
                XCTAssertTrue((-3.0...3.0).contains(sample.y))
                XCTAssertTrue((0.65...0.95).contains(sample.opacity))
                let repeated = policy.orbSample(time: time + 4, index: index)
                XCTAssertEqual(sample.x, repeated.x, accuracy: 0.0001)
                XCTAssertEqual(sample.scale, repeated.scale, accuracy: 0.0001)
            }
        }
        XCTAssertNotEqual(policy.orbSample(time: 0.5, index: 0).x, policy.orbSample(time: 0.5, index: 1).x)
    }
}
