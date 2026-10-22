import AppKit
import Foundation
import Darwin

private struct WorkflowFailure: Error, CustomStringConvertible {
    let description: String
}

@MainActor
private final class WorkflowCredentials: SessionCredentialStore {
    private var token: String?
    func load() -> String? { token }
    func save(_ token: String?) { self.token = token }
}

/// Reads only the fixture explicitly created and owned by the shell runner.
/// Process termination and directory removal remain with that parent supervisor.
@MainActor
private final class PackagedSidecarFixture {
    let directory: URL
    let token: String
    private let backendPID: Int32
    var isRunning: Bool { kill(backendPID, 0) == 0 }

    init(directory: URL, token: String, backendPID: Int32) throws {
        guard directory.lastPathComponent == "fixture",
              directory.deletingLastPathComponent().lastPathComponent.hasPrefix("notaeo-workflow-build."),
              !token.isEmpty, backendPID > 1,
              try directory.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true else {
            throw WorkflowFailure(description: "Run this check through sh scripts/test_macos_workflows.sh for an isolated fixture.")
        }
        self.directory = directory
        self.token = token
        self.backendPID = backendPID
    }

    func start() async throws -> URL {
        let logURL = directory.appendingPathComponent("backend.log")
        let deadline = ContinuousClock.now + .seconds(30)
        while ContinuousClock.now < deadline {
            guard isRunning else { throw WorkflowFailure(description: "Packaged backend stopped before readiness") }
            let reader = try FileHandle(forReadingFrom: logURL)
            let data: Data
            do {
                data = try reader.read(upToCount: 65_536) ?? Data()
                try reader.close()
            } catch {
                try? reader.close()
                throw error
            }
            for line in String(decoding: data, as: UTF8.self).split(separator: "\n") where line.hasPrefix("RESEARCH_READY ") {
                let raw = String(line.dropFirst("RESEARCH_READY ".count)).trimmingCharacters(in: .whitespacesAndNewlines)
                guard let url = BackendProcess.readyURL(from: raw) else {
                    throw WorkflowFailure(description: "Fixture announced an invalid/non-loopback URL")
                }
                return url
            }
            try await Task.sleep(for: .milliseconds(25))
        }
        throw WorkflowFailure(description: "Packaged backend did not announce readiness within 30 seconds")
    }
}

@main
@MainActor
struct PackagedWorkflow {
    static func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
        guard condition() else { throw WorkflowFailure(description: message) }
    }

    static func expectError(_ kind: String, _ operation: () async throws -> Void) async throws {
        do {
            try await operation()
        } catch let error as APIError {
            switch (kind, error) {
            case ("unauthorized", .unauthorized), ("forbidden", .forbidden), ("notFound", .notFound): return
            default: throw WorkflowFailure(description: "Expected \(kind), received \(error)")
            }
        }
        throw WorkflowFailure(description: "Expected \(kind), request unexpectedly succeeded")
    }

    static func main() async {
        do {
            guard CommandLine.arguments.count == 3,
                  let backendPID = Int32(CommandLine.arguments[2]),
                  let token = ProcessInfo.processInfo.environment["NOTAEO_WORKFLOW_TOKEN"] else {
                throw WorkflowFailure(description: "Run sh scripts/test_macos_workflows.sh to prepare the fixture.")
            }
            let fixture = try PackagedSidecarFixture(directory: URL(fileURLWithPath: CommandLine.arguments[1]),
                                                    token: token, backendPID: backendPID)
            let url = try await fixture.start()
            try await withThrowingTaskGroup(of: Void.self) { group in
                group.addTask { try await checkStudyWorkflow(fixture: fixture, baseURL: url) }
                group.addTask {
                    try await Task.sleep(for: .seconds(90))
                    throw WorkflowFailure(description: "Native workflow exceeded its 90-second budget")
                }
                defer { group.cancelAll() }
                _ = try await group.next()
            }
            print("PACKAGED NATIVE WORKFLOW PASS: auth, paste/upload/read/search, duplicate consent contract, basic revision, maps/export, ownership and revocation")
        } catch {
            FileHandle.standardError.write(Data("PACKAGED NATIVE WORKFLOW FAIL: \(error)\n".utf8))
            exit(1)
        }
    }

    private static func checkStudyWorkflow(fixture: PackagedSidecarFixture, baseURL: URL) async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 5
        configuration.timeoutIntervalForResource = 15
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel() }
        let anonymous = NotaeoAPI(baseURL: baseURL, desktopToken: fixture.token, session: session)
        let badLaunch = NotaeoAPI(baseURL: baseURL, desktopToken: "wrong-synthetic-launch", session: session)
        try await expectError("forbidden") { _ = try await badLaunch.listNotebooks() }
        try await expectError("unauthorized") { _ = try await anonymous.listNotebooks() }

        var suites: [String] = []
        func state() throws -> AppState {
            let name = "notaeo.workflow.\(UUID().uuidString)"
            guard let preferences = UserDefaults(suiteName: name) else {
                throw WorkflowFailure(description: "Could not create isolated preferences")
            }
            suites.append(name)
            let result = AppState(credentials: WorkflowCredentials(), preferences: preferences)
            result.configureBackend(baseURL: baseURL, desktopToken: fixture.token)
            return result
        }
        defer { for name in suites { UserDefaults(suiteName: name)?.removePersistentDomain(forName: name) } }
        let account = try state()
        let email = "native-\(UUID().uuidString.lowercased())@example.test"
        let password = "Synthetic-course-password-123"
        let registered = await account.register(email: email, password: password, session: session)
        try require(registered && account.isLoggedIn, "Native account registration failed")
        await account.signOut(session: session)
        try require(!account.isLoggedIn, "Native sign-out retained credentials")
        await account.login(email: email, password: "incorrect-synthetic-password", session: session)
        try require(!account.isLoggedIn && account.authError != nil, "Wrong password was not rejected")
        await account.login(email: email, password: password, session: session)
        guard let api = account.makeAPI(session: session), account.isLoggedIn else {
            throw WorkflowFailure(description: "Native login did not establish an account session")
        }
        let me = try await api.me()
        try require(me.email == email, "Native account identity mismatch")
        let availability = try await api.getAIStatus()
        try require(!availability.enabled && availability.model == nil, "Fixture unexpectedly enables AI")

        let notebook = try await api.createNotebook(name: "Biology 雪 — exam workflow")
        let notebooks = try await api.listNotebooks()
        try require(notebooks.contains { $0.id == notebook.id }, "Created course notebook missing")
        let text = "Photosynthesis converts sunlight into chemical energy inside chloroplasts. "
            + "Chlorophyll pigments capture photons in the thylakoid membranes. "
            + "Mitochondria release energy from glucose during cellular respiration. "
            + "Meiosis produces four haploid cells with half the chromosomes."
        let pasted = try await api.pasteSource(notebookId: notebook.id, title: "Lecture — 雪", text: text)
        guard pasted.saved, let original = pasted.summary else {
            throw WorkflowFailure(description: "Native paste response could not be read as a saved source")
        }
        let detail = try await api.getSource(id: original.id)
        try require(detail.fullText.contains("Photosynthesis"), "Reader did not receive stored source text")
        let chunks = try await api.getSourceChunks(id: original.id, limit: 1)
        try require(chunks.total > 0 && !chunks.chunks.isEmpty, "Native chunk contract failed")
        let uploaded = try await api.uploadFiles(notebookId: notebook.id, files: [
            (filename: "Genetics.txt", data: Data("DNA stores genetic information. Chromosomes carry genes. Ribosomes translate messenger RNA into proteins.".utf8), mime: "text/plain"),
        ])
        try require(uploaded.sources.count == 1 && uploaded.errors.isEmpty, "Native file import failed")
        let search = try await api.searchNotebook(notebookId: notebook.id,
            request: NativeSearchRequest(query: "photosynthesis", kind: "paste", related: false))
        try require(search.total > 0 && search.hits.contains { $0.sourceId == original.id }, "Native source search missed imported material")

        let pasteDecision = NativePasteController()
        pasteDecision.bind(accountToken: account.accountToken, notebookId: notebook.id)
        let duplicate = await pasteDecision.save(title: "Same lecture", text: text, using: api)
        try require(duplicate == nil && pasteDecision.pendingDuplicate?.id == original.id, "Duplicate did not return a decision boundary")
        let beforeConsent = try await api.listSources(notebookId: notebook.id)
        try require(beforeConsent.count == 2, "Duplicate warning persisted an unapproved source")
        pasteDecision.cancelDuplicate()
        try require(pasteDecision.confirmCopy(using: api) == nil, "Cancelled consent remained usable")
        _ = await pasteDecision.save(title: "Same lecture", text: text, using: api)
        guard let copy = pasteDecision.confirmCopy(using: api) else {
            throw WorkflowFailure(description: "Explicit copy decision was unavailable")
        }
        let approved = await copy.value
        try require(approved?.matchesDraft(title: "Same lecture", text: text) == true, "Explicit copy did not preserve its reviewed snapshot")
        let sources = try await api.listSources(notebookId: notebook.id)
        try require(sources.count == 3, "Explicit copy count is incorrect")
        let sourceIDs = Set(sources.map(\.id))

        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        let examDate = formatter.string(from: Date().addingTimeInterval(7 * 24 * 60 * 60))
        let goal = ExamGoal(title: "Biology midterm", examDate: examDate, dailyMinutes: 20, focusTopics: [])
        let savedGoal = try await api.saveExamGoal(notebookId: notebook.id, goal: goal)
        try require(savedGoal == goal, "Revision goal did not round-trip")
        let draft = try await api.buildCoachSession(notebookId: notebook.id, useAi: false)
        guard let task = draft.tasks.first else { throw WorkflowFailure(description: "Basic practice produced no questions") }
        try require(draft.generatedBy == "basic", "Basic practice unexpectedly used AI")
        try require(task.sourceId.map(sourceIDs.contains) == true, "Practice question lacks an owned source")
        let active = try await api.startCoachSession(notebookId: notebook.id, sessionId: draft.id, taskIds: [task.id])
        try require(active.status == "active" && active.tasks.count == 1, "Native question selection did not start")
        let answer = "Chloroplasts convert sunlight into chemical energy."
        let attempted = try await api.recordCoachAttempt(notebookId: notebook.id, sessionId: draft.id,
            taskId: task.id, rating: "revise", response: answer)
        try require(attempted.attempts.first?.response == answer, "Student answer did not persist")
        let explanation = try await api.explainCoachTask(notebookId: notebook.id, sessionId: draft.id, taskId: task.id, useAi: false)
        try require(explanation.generatedBy == "basic" && !explanation.answer.isEmpty, "Basic explanation failed")
        try require(!explanation.citations.isEmpty && explanation.citations.allSatisfy { sourceIDs.contains($0.sourceId) }, "Explanation references foreign/missing material")
        let finished = try await api.finishCoachSession(notebookId: notebook.id, sessionId: draft.id)
        try require(finished.status == "completed" && finished.completedAt != nil, "Revision session did not finish")
        let persisted = try await api.getCoachState(notebookId: notebook.id)
        try require(persisted.sessions.contains { $0.id == draft.id && $0.status == "completed" }, "Completed revision session was not persisted")
        let next = try await api.buildCoachSession(notebookId: notebook.id, useAi: true)
        try require(next.generatedBy == "basic" && next.notice != nil, "Unavailable AI did not preserve basic revision")

        let map = try await api.getMindmap(notebookId: notebook.id)
        try require(!map.name.isEmpty && !map.children.isEmpty, "Native mind map contract failed")
        let mapExport = try await api.exportMindmap(notebookId: notebook.id)
        try require(!mapExport.data.isEmpty && !mapExport.filename.contains("/"), "Mind map export failed")
        let exported = try await api.exportNotebook(id: notebook.id)
        try require(exported.starts(with: [0x50, 0x4b]), "Notebook export is not a ZIP archive")
        let exportURL = fixture.directory.appendingPathComponent("saved-course.zip")
        let soundPreferences = UserDefaults(suiteName: suites[0])!
        var emitted = false
        let feedback = NativeFeedback(preferences: soundPreferences, isTestHost: true) { _ in emitted = true }
        try feedback.saveExport(exported, to: exportURL)
        let savedData = try Data(contentsOf: exportURL)
        try require(savedData == exported && !emitted, "Native export write or silent-test policy failed")
        // The supervising shell verifies the archive CRC and owns that process too.
        let database = fixture.directory.appendingPathComponent("data/app.db")
        let file = try FileHandle(forReadingFrom: database)
        let header = try file.read(upToCount: 16)
        try file.close()
        try require(header == Data("SQLite format 3\0".utf8), "Workflow did not persist a real SQLite database")

        let other = try state()
        let secondRegistered = await other.register(email: "other-\(UUID().uuidString.lowercased())@example.test", password: password, session: session)
        try require(secondRegistered, "Second synthetic account registration failed")
        guard let foreign = other.makeAPI(session: session) else { throw WorkflowFailure(description: "Second client unavailable") }
        try await expectError("notFound") { _ = try await foreign.getSource(id: original.id) }
        try await expectError("notFound") { _ = try await foreign.searchNotebook(notebookId: notebook.id, request: NativeSearchRequest(query: "photosynthesis")) }
        try await expectError("notFound") { _ = try await foreign.getCoachState(notebookId: notebook.id) }
        try await expectError("notFound") { _ = try await foreign.exportNotebook(id: notebook.id) }
        await account.signOut(session: session)
        try require(!account.isLoggedIn, "Native logout did not clear the account")
        try await expectError("unauthorized") { _ = try await api.me() }
    }
}
