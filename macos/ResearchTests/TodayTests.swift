import XCTest
@testable import Notaeo

private actor CourseworkStub: CourseworkServing {
    var rows: [CourseworkAssignment]
    let holdsLoad: Bool
    let holdsWrite: Bool
    let fails: Bool
    var loads = 0
    var writes = 0
    var heldLoad: CheckedContinuation<[CourseworkAssignment], Error>?
    var heldWrite: CheckedContinuation<CourseworkAssignment, Error>?

    init(_ rows: [CourseworkAssignment] = [], holdsLoad: Bool = false, holdsWrite: Bool = false, fails: Bool = false) {
        self.rows = rows; self.holdsLoad = holdsLoad; self.holdsWrite = holdsWrite; self.fails = fails
    }
    func listAssignments() async throws -> [CourseworkAssignment] {
        loads += 1
        if fails { throw APIError.network("Offline") }
        if holdsLoad { return try await withCheckedThrowingContinuation { heldLoad = $0 } }
        return rows
    }
    func listClasses() async throws -> [CourseworkClass] { [] }
    func createAssignment(_ draft: AssignmentDraft) async throws -> CourseworkAssignment {
        writes += 1
        if fails { throw APIError.network("Offline") }
        if holdsWrite { return try await withCheckedThrowingContinuation { heldWrite = $0 } }
        return CourseworkAssignment(id: "created", title: draft.title, dueAt: draft.dueAt, notebookId: draft.notebookId)
    }
    func completeAssignment(id: String, done: Bool) async throws -> CourseworkAssignment {
        writes += 1
        if fails { throw APIError.network("Offline") }
        return CourseworkAssignment(id: id, title: "Essay", done: done)
    }
    func loadStarted() -> Bool { loads > 0 }
    func writeStarted() -> Bool { writes > 0 }
    func writeCount() -> Int { writes }
    func releaseLoad() { heldLoad?.resume(returning: rows); heldLoad = nil }
    func releaseWrite() { heldWrite?.resume(returning: CourseworkAssignment(id: "late", title: "Late task")); heldWrite = nil }
}

@MainActor
final class TodayTests: XCTestCase {
    private func waitUntil(_ predicate: () async -> Bool) async throws {
        for _ in 0..<100 {
            if await predicate() { return }
            try await Task.sleep(for: .milliseconds(5))
        }
        throw APIError.network("Test operation did not start")
    }

    func testDeviceDayBucketsIncludeOverdueAndUndatedAndExcludeCompleted() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/Toronto")!
        let now = ISO8601DateFormatter().date(from: "2026-10-30T03:30:00Z")!
        let sections = TodaySections([
            CourseworkAssignment(id: "next", title: "Next day", dueAt: "2026-10-30T04:15:00Z"),
            CourseworkAssignment(id: "done", title: "Done", dueAt: "2026-10-29T12:00:00Z", done: true),
            CourseworkAssignment(id: "none", title: "Reading"),
            CourseworkAssignment(id: "today", title: "Tonight", dueAt: "2026-10-30T03:45:00.000Z"),
            CourseworkAssignment(id: "late", title: "Late", dueAt: "2026-10-30T03:00:00Z"),
        ], now: now, calendar: calendar)
        XCTAssertEqual(sections.overdue.map(\.id), ["late"])
        XCTAssertEqual(sections.today.map(\.id), ["today"])
        XCTAssertEqual(sections.upcoming.map(\.id), ["next"])
        XCTAssertEqual(sections.undated.map(\.id), ["none"])
    }

    func testLoadCompletionAndReloadUseTheSameSavedAssignments() async {
        let task = CourseworkAssignment(id: "essay", title: "Essay")
        let service = CourseworkStub([task])
        let state = TodayController(); state.bind(accountToken: "a")
        await state.load(using: service)
        XCTAssertEqual(state.assignments, [task])
        await state.setDone(task, done: true, using: service)
        XCTAssertTrue(state.assignments.first?.done == true)
        XCTAssertNil(state.notice)
    }

    func testAccountChangeClearsDataAndRejectsLateLoad() async throws {
        let service = CourseworkStub([CourseworkAssignment(id: "private", title: "Private")], holdsLoad: true)
        let state = TodayController(); state.bind(accountToken: "a")
        let loading = Task { await state.load(using: service) }
        try await waitUntil { await service.loadStarted() }
        state.bind(accountToken: "b")
        await service.releaseLoad(); await loading.value
        XCTAssertTrue(state.assignments.isEmpty)
        XCTAssertFalse(state.isLoading)
        XCTAssertNil(state.notice)
    }

    func testDuplicateSaveAndLateWriteAfterSignOutAreIgnored() async throws {
        let service = CourseworkStub(holdsWrite: true)
        let state = TodayController(); state.bind(accountToken: "a")
        let draft = AssignmentDraft(title: "Essay")
        let saving = Task { await state.add(draft, using: service) }
        try await waitUntil { await service.writeStarted() }
        let duplicate = await state.add(draft, using: service)
        XCTAssertFalse(duplicate)
        state.bind(accountToken: nil)
        await service.releaseWrite()
        let saved = await saving.value
        XCTAssertFalse(saved)
        XCTAssertTrue(state.assignments.isEmpty)
        let count = await service.writeCount()
        XCTAssertEqual(count, 1)
        XCTAssertFalse(state.isWriting)
    }

    func testFailureCanRetryAndBlankDraftDoesNotWrite() async {
        let state = TodayController(); state.bind(accountToken: "a")
        let bad = CourseworkStub(fails: true)
        await state.load(using: bad)
        XCTAssertEqual(state.notice, "Offline")
        XCTAssertFalse(state.isLoading)
        let good = CourseworkStub()
        await state.load(using: good)
        XCTAssertNil(state.notice)
        let saved = await state.add(AssignmentDraft(title: " \n"), using: good)
        XCTAssertFalse(saved)
        let count = await good.writeCount()
        XCTAssertEqual(count, 0)
    }
}
