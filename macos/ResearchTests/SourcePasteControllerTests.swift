import XCTest
@testable import Notaeo

private actor PasteStub: NotebookPasting {
    struct Request: Equatable, Sendable {
        let notebook: String
        let title: String
        let text: String
        let force: Bool
    }
    private var requests: [Request] = []
    private var replies: [PasteResult]
    private var failure: APIError?
    private var held: CheckedContinuation<PasteResult, Error>?
    private let suspend: Bool

    init(_ replies: [PasteResult] = [], failure: APIError? = nil, suspend: Bool = false) {
        self.replies = replies; self.failure = failure; self.suspend = suspend
    }
    func pasteSource(notebookId: String, title: String, text: String, force: Bool) async throws -> PasteResult {
        requests.append(Request(notebook: notebookId, title: title, text: text, force: force))
        if let failure { throw failure }
        if suspend {
            return try await withCheckedThrowingContinuation { held = $0 }
        }
        guard !replies.isEmpty else { throw APIError.network("Unexpected request") }
        return replies.removeFirst()
    }
    func calls() -> [Request] { requests }
    func release(_ reply: PasteResult) { held?.resume(returning: reply); held = nil }
}

@MainActor
final class SourcePasteControllerTests: XCTestCase {
    private let duplicate = PasteResult(saved: false, duplicateOf: DuplicateRef(id: "source", title: "Existing lecture"), summary: nil)
    private let saved = PasteResult(saved: true, duplicateOf: nil, summary: nil)

    private func controller() -> NativePasteController {
        let controller = NativePasteController()
        controller.bind(accountToken: "account-a", notebookId: "course-a")
        return controller
    }

    private func waitForRequest(_ service: PasteStub) async throws {
        for _ in 0..<100 {
            if !(await service.calls()).isEmpty { return }
            try await Task.sleep(for: .milliseconds(5))
        }
        throw APIError.network("Test request never started")
    }

    func testDuplicateRequiresAnExplicitDecisionAndCancelSendsNothing() async {
        let controller = controller()
        let service = PasteStub([duplicate])
        let result = await controller.save(title: "Lecture", text: "Course text", using: service)
        XCTAssertNil(result)
        XCTAssertEqual(controller.pendingDuplicate, duplicate.duplicateOf)
        XCTAssertFalse(controller.isSaving)
        let calls = await service.calls()
        XCTAssertEqual(calls.count, 1)
        XCTAssertFalse(calls[0].force)
        controller.cancelDuplicate()
        XCTAssertNil(controller.pendingDuplicate)
        XCTAssertNil(controller.confirmCopy(using: service))
        let afterCancel = await service.calls()
        XCTAssertEqual(afterCancel.count, 1)
    }

    func testConfirmReplaysTheExactSubmittedSnapshotAndDismissDoesNotLoseApproval() async throws {
        let controller = controller()
        let text = "Cells 雪\n\"DNA\" & RNA 👩🏽‍🔬"
        let service = PasteStub([duplicate, saved])
        _ = await controller.save(title: "  Lecture 雪\n", text: text, using: service)
        let operation = try XCTUnwrap(controller.confirmCopy(using: service))
        controller.cancelDuplicate() // SwiftUI dismisses the dialog after the explicit action.
        XCTAssertNil(controller.confirmCopy(using: service), "Repeated confirmation cannot issue a third write")
        let result = await operation.value
        XCTAssertNotNil(result)
        XCTAssertTrue(result?.matchesDraft(title: "  Lecture 雪\n", text: text) == true)
        XCTAssertFalse(result?.matchesDraft(title: "New draft", text: text) == true)
        XCTAssertFalse(result?.matchesDraft(title: "  Lecture 雪\n", text: "Edited") == true)
        let calls = await service.calls()
        XCTAssertEqual(calls.count, 2)
        XCTAssertEqual(calls[0].title, "Lecture 雪")
        XCTAssertEqual(calls[0].title, calls[1].title)
        XCTAssertEqual(calls[0].text, calls[1].text)
        XCTAssertEqual(calls[1].notebook, "course-a")
        XCTAssertTrue(calls[1].force)
    }

    func testNormalSaveWhitespaceTitleAndEmptyText() async {
        let controller = controller()
        let service = PasteStub([saved])
        let empty = await controller.save(title: "", text: " \n\t", using: service)
        XCTAssertNil(empty)
        let result = await controller.save(title: " \n", text: "Fresh note", using: service)
        XCTAssertNotNil(result)
        XCTAssertNil(controller.pendingDuplicate)
        XCTAssertEqual(controller.notice, "Paste saved.")
        let calls = await service.calls()
        XCTAssertEqual(calls.count, 1)
        XCTAssertEqual(calls[0].title, "Pasted note")
    }

    func testChangingEitherAccountOrNotebookInvalidatesConsent() async {
        for scope in [("account-b", "course-a"), ("account-a", "course-b")] {
            let controller = controller()
            let service = PasteStub([duplicate])
            _ = await controller.save(title: "Lecture", text: "Same notes", using: service)
            controller.bind(accountToken: scope.0, notebookId: scope.1)
            XCTAssertNil(controller.pendingDuplicate)
            XCTAssertNil(controller.confirmCopy(using: service))
            let calls = await service.calls()
            XCTAssertEqual(calls.count, 1)
        }
    }

    func testSignedOutOrDisappearedControllerCannotSubmitOrConfirm() async {
        let controller = controller()
        let service = PasteStub([duplicate])
        controller.bind(accountToken: nil, notebookId: "course-a")
        let signedOut = await controller.save(title: "Lecture", text: "Notes", using: service)
        XCTAssertNil(signedOut)
        controller.bind(accountToken: "account-a", notebookId: "course-a")
        _ = await controller.save(title: "Lecture", text: "Notes", using: service)
        controller.clear()
        XCTAssertNil(controller.confirmCopy(using: service))
        let calls = await service.calls()
        XCTAssertEqual(calls.count, 1)
    }

    func testRepeatedSaveIsIgnoredAndLateResultCannotCrossScope() async throws {
        let controller = controller()
        let service = PasteStub(suspend: true)
        let request = Task { await controller.save(title: "Lecture", text: "Notes", using: service) }
        try await waitForRequest(service)
        XCTAssertTrue(controller.isSaving)
        let repeated = await controller.save(title: "Repeated", text: "Notes", using: service)
        XCTAssertNil(repeated)
        controller.bind(accountToken: "account-b", notebookId: "course-b")
        await service.release(duplicate)
        let result = await request.value
        XCTAssertNil(result)
        XCTAssertNil(controller.pendingDuplicate)
        XCTAssertNil(controller.notice)
        XCTAssertFalse(controller.isSaving)
        let calls = await service.calls()
        XCTAssertEqual(calls.count, 1)
    }

    func testNetworkFailureAndMalformedReplyDoNotForceOrPretendSuccess() async {
        let controller = controller()
        let service = PasteStub(failure: .network("Synthetic offline"))
        let offline = await controller.save(title: "Lecture", text: "Keep draft", using: service)
        XCTAssertNil(offline)
        XCTAssertEqual(controller.notice, "Synthetic offline")
        XCTAssertFalse(controller.isSaving)
        let malformed = PasteStub([PasteResult(saved: false, duplicateOf: nil, summary: nil)])
        let notSaved = await controller.save(title: "Lecture", text: "Keep draft", using: malformed)
        XCTAssertNil(notSaved)
        XCTAssertEqual(controller.notice, "The paste was not saved. Try again.")
        XCTAssertNil(controller.pendingDuplicate)
    }

    func testConfirmFailurePreservesRecoverableDraftAndDoesNotRetry() async throws {
        let controller = controller()
        let initial = PasteStub([duplicate])
        _ = await controller.save(title: "Lecture", text: "Keep draft", using: initial)
        let failed = PasteStub(failure: .notFound("Notebook no longer available"))
        let request = try XCTUnwrap(controller.confirmCopy(using: failed))
        let result = await request.value
        XCTAssertNil(result)
        XCTAssertFalse(controller.isSaving)
        XCTAssertNil(controller.pendingDuplicate)
        XCTAssertEqual(controller.notice, "Notebook no longer available")
        let calls = await failed.calls()
        XCTAssertEqual(calls.count, 1)
        XCTAssertTrue(calls[0].force)
    }

    func testRebindingTheSameScopeRetainsConsentButNewSaveReplacesIt() async {
        let controller = controller()
        let service = PasteStub([duplicate, saved])
        _ = await controller.save(title: "Old", text: "Old draft", using: service)
        controller.bind(accountToken: "account-a", notebookId: "course-a")
        XCTAssertNotNil(controller.pendingDuplicate)
        let result = await controller.save(title: "New", text: "New draft", using: service)
        XCTAssertNotNil(result)
        XCTAssertNil(controller.pendingDuplicate)
        XCTAssertNil(controller.confirmCopy(using: service))
    }

    func testCancelledSaveAndCancelledApprovalDoNotPublishOrIssueAnotherRequest() async throws {
        let controller = controller()
        let service = PasteStub(suspend: true)
        let request = Task { await controller.save(title: "Lecture", text: "Notes", using: service) }
        try await waitForRequest(service)
        request.cancel()
        await service.release(saved)
        let cancelled = await request.value
        XCTAssertNil(cancelled)
        XCTAssertNil(controller.notice)
        XCTAssertFalse(controller.isSaving)

        let warning = PasteStub([duplicate])
        _ = await controller.save(title: "Lecture", text: "Notes", using: warning)
        let copyService = PasteStub([saved])
        let approval = try XCTUnwrap(controller.confirmCopy(using: copyService))
        controller.clear() // Changes/disappearance before the scheduled task starts.
        let result = await approval.value
        XCTAssertNil(result)
        let calls = await copyService.calls()
        XCTAssertTrue(calls.isEmpty)
    }

    func testOldRequestCannotStopNewScopesLoadingState() async throws {
        let controller = controller()
        let oldService = PasteStub(suspend: true)
        let old = Task { await controller.save(title: "Old", text: "Old notes", using: oldService) }
        try await waitForRequest(oldService)
        controller.bind(accountToken: "account-b", notebookId: "course-b")
        let newService = PasteStub(suspend: true)
        let new = Task { await controller.save(title: "New", text: "New notes", using: newService) }
        try await waitForRequest(newService)
        await oldService.release(saved)
        let oldResult = await old.value
        XCTAssertNil(oldResult)
        XCTAssertTrue(controller.isSaving)
        await newService.release(saved)
        let newResult = await new.value
        XCTAssertNotNil(newResult)
        XCTAssertFalse(controller.isSaving)
    }

    func testLargeSnapshotSurvivesBlankContextAndFreshRebinding() async {
        let controller = controller()
        let service = PasteStub([duplicate, saved])
        controller.bind(accountToken: "", notebookId: "course-a")
        let denied = await controller.save(title: "Lecture", text: "Notes", using: service)
        XCTAssertNil(denied)
        controller.bind(accountToken: "account-a", notebookId: "")
        XCTAssertNil(controller.confirmCopy(using: service))
        controller.bind(accountToken: "account-a", notebookId: "course-a")
        let text = String(repeating: "Snow 雪\nDNA 🧬\n", count: 5000)
        _ = await controller.save(title: "Large lecture", text: text, using: service)
        let operation = controller.confirmCopy(using: service)
        let result = await operation?.value
        XCTAssertTrue(result?.matchesDraft(title: "Large lecture", text: text) == true)
        let calls = await service.calls()
        XCTAssertEqual(calls.count, 2)
        XCTAssertEqual(calls[1].text, text)
    }
}
