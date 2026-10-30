import SwiftUI

struct CourseworkAssignment: Codable, Identifiable, Equatable, Sendable {
    let id: String
    let title: String
    var details: String = ""
    var classId: String? = nil
    var className: String? = nil
    var dueAt: String? = nil
    var done: Bool = false
    var notebookId: String? = nil

    var deadline: Date? {
        guard let dueAt else { return nil }
        let parser = ISO8601DateFormatter()
        parser.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return parser.date(from: dueAt) ?? ISO8601DateFormatter().date(from: dueAt)
    }
}

struct CourseworkClass: Decodable, Identifiable, Equatable, Sendable {
    let id: String
    let name: String
}

struct AssignmentDraft: Encodable, Equatable, Sendable {
    var title: String
    var classId: String? = nil
    var notebookId: String? = nil
    var dueAt: String? = nil
}

protocol CourseworkServing: Sendable {
    func listAssignments() async throws -> [CourseworkAssignment]
    func listClasses() async throws -> [CourseworkClass]
    func createAssignment(_ draft: AssignmentDraft) async throws -> CourseworkAssignment
    func completeAssignment(id: String, done: Bool) async throws -> CourseworkAssignment
}

extension NotaeoAPI: CourseworkServing {
    func listAssignments() async throws -> [CourseworkAssignment] {
        let response = try await send(path: "api/assignments", method: "GET")
        return try decode([CourseworkAssignment].self, from: response.data)
    }
    func listClasses() async throws -> [CourseworkClass] {
        let response = try await send(path: "api/classes", method: "GET")
        return try decode([CourseworkClass].self, from: response.data)
    }
    func createAssignment(_ draft: AssignmentDraft) async throws -> CourseworkAssignment {
        let response = try await send(path: "api/assignments", method: "POST", json: draft)
        return try decode(CourseworkAssignment.self, from: response.data)
    }
    func completeAssignment(id: String, done: Bool) async throws -> CourseworkAssignment {
        struct Body: Encodable { let done: Bool }
        let response = try await send(path: "api/assignments/\(id)", method: "PATCH", json: Body(done: done))
        return try decode(CourseworkAssignment.self, from: response.data)
    }
}

struct TodaySections {
    var overdue: [CourseworkAssignment] = []
    var today: [CourseworkAssignment] = []
    var upcoming: [CourseworkAssignment] = []
    var undated: [CourseworkAssignment] = []

    init(_ assignments: [CourseworkAssignment], now: Date, calendar: Calendar) {
        let pending = assignments.filter { !$0.done }.sorted {
            let left = $0.deadline ?? .distantFuture, right = $1.deadline ?? .distantFuture
            if left != right { return left < right }
            return ($0.title, $0.id) < ($1.title, $1.id)
        }
        for assignment in pending {
            guard let deadline = assignment.deadline else { undated.append(assignment); continue }
            if deadline < now { overdue.append(assignment) }
            else if calendar.isDate(deadline, inSameDayAs: now) { today.append(assignment) }
            else { upcoming.append(assignment) }
        }
    }
}

@MainActor
final class TodayController: ObservableObject {
    @Published private(set) var assignments: [CourseworkAssignment] = []
    @Published private(set) var classes: [CourseworkClass] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isWriting = false
    @Published private(set) var notice: String?

    private var account: String?
    private var generation = 0

    func bind(accountToken: String?) {
        let next = accountToken.flatMap { $0.isEmpty ? nil : $0 }
        guard account != next else { return }
        generation += 1; account = next
        assignments = []; classes = []; notice = nil; isLoading = false; isWriting = false
    }

    func load(using service: any CourseworkServing) async {
        guard account != nil, !Task.isCancelled, !isLoading, !isWriting else { return }
        let current = generation
        isLoading = true; notice = nil
        defer { if current == generation { isLoading = false } }
        do {
            async let work = service.listAssignments()
            async let courses = service.listClasses()
            let result = try await (work, courses)
            guard current == generation, !Task.isCancelled else { return }
            assignments = result.0; classes = result.1
        } catch {
            guard current == generation, !Task.isCancelled else { return }
            notice = error.localizedDescription
        }
    }

    func add(_ draft: AssignmentDraft, using service: any CourseworkServing) async -> Bool {
        var submitted = draft
        submitted.title = draft.title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !submitted.title.isEmpty else { return false }
        return await write(using: { try await service.createAssignment(submitted) })
    }

    func setDone(_ assignment: CourseworkAssignment, done: Bool, using service: any CourseworkServing) async {
        guard assignments.contains(where: { $0.id == assignment.id }) else { return }
        _ = await write(using: { try await service.completeAssignment(id: assignment.id, done: done) })
    }

    private func write(using operation: () async throws -> CourseworkAssignment) async -> Bool {
        guard account != nil, !Task.isCancelled, !isWriting, !isLoading else { return false }
        let current = generation
        isWriting = true; notice = nil
        defer { if current == generation { isWriting = false } }
        do {
            let saved = try await operation()
            guard current == generation, !Task.isCancelled else { return false }
            if let index = assignments.firstIndex(where: { $0.id == saved.id }) { assignments[index] = saved }
            else { assignments.append(saved) }
            return true
        } catch {
            guard current == generation, !Task.isCancelled else { return false }
            notice = error.localizedDescription
            return false
        }
    }
}
