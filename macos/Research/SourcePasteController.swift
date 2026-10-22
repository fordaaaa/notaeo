import SwiftUI

protocol NotebookPasting: Sendable {
    func pasteSource(notebookId: String, title: String, text: String, force: Bool) async throws -> PasteResult
}

extension NotaeoAPI: NotebookPasting {}

struct NativePasteSnapshot: Equatable, Sendable {
    let rawTitle: String
    let text: String

    var title: String {
        let trimmed = rawTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "Pasted note" : trimmed
    }

    func matchesDraft(title: String, text: String) -> Bool { rawTitle == title && self.text == text }
}

@MainActor
final class NativePasteController: ObservableObject {
    private struct Scope: Equatable {
        let account: String
        let notebook: String
    }
    private struct Pending {
        let snapshot: NativePasteSnapshot
        let scope: Scope
    }

    @Published private(set) var pendingDuplicate: DuplicateRef?
    @Published private(set) var isSaving = false
    @Published private(set) var notice: String?
    private var scope: Scope?
    private var pending: Pending?
    private var generation = 0
    private var confirmationTask: Task<NativePasteSnapshot?, Never>?

    func bind(accountToken: String?, notebookId: String?) {
        guard let accountToken, !accountToken.isEmpty, let notebookId, !notebookId.isEmpty else {
            clear()
            return
        }
        let next = Scope(account: accountToken, notebook: notebookId)
        guard next != scope else { return }
        clear()
        scope = next
    }

    func clear() {
        generation += 1
        confirmationTask?.cancel()
        confirmationTask = nil
        scope = nil; pending = nil; pendingDuplicate = nil; notice = nil; isSaving = false
    }

    func cancelDuplicate() {
        // A dialog dismissal after approval must not cancel an approved save.
        guard pending != nil else { return }
        pending = nil; pendingDuplicate = nil; notice = nil
    }

    func save(title: String, text: String, using service: any NotebookPasting) async -> NativePasteSnapshot? {
        guard !Task.isCancelled, !isSaving, let scope else { return nil }
        pending = nil; pendingDuplicate = nil
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            notice = "Paste some course material first."
            return nil
        }
        generation += 1
        isSaving = true; notice = nil
        return await perform(NativePasteSnapshot(rawTitle: title, text: text), force: false,
                             scope: scope, generation: generation, using: service)
    }

    /// Consume the reviewed snapshot synchronously, before SwiftUI dismisses its dialog.
    func confirmCopy(using service: any NotebookPasting) -> Task<NativePasteSnapshot?, Never>? {
        guard !Task.isCancelled, !isSaving, let pending, pending.scope == scope else { return nil }
        self.pending = nil; pendingDuplicate = nil
        generation += 1
        let current = generation
        isSaving = true; notice = nil
        let operation = Task {
            await perform(pending.snapshot, force: true, scope: pending.scope, generation: current, using: service)
        }
        confirmationTask = operation
        return operation
    }

    private func perform(_ snapshot: NativePasteSnapshot, force: Bool, scope: Scope,
                         generation current: Int, using service: any NotebookPasting) async -> NativePasteSnapshot? {
        defer {
            if generation == current { isSaving = false; confirmationTask = nil }
        }
        guard !Task.isCancelled, generation == current, self.scope == scope else { return nil }
        do {
            let result = try await service.pasteSource(notebookId: scope.notebook,
                title: snapshot.title, text: snapshot.text, force: force)
            guard !Task.isCancelled, generation == current, self.scope == scope else { return nil }
            if result.saved {
                notice = force ? "Duplicate saved as a copy." : "Paste saved."
                return snapshot
            }
            if !force, let duplicate = result.duplicateOf {
                pending = Pending(snapshot: snapshot, scope: scope)
                pendingDuplicate = duplicate
                notice = "Already saved as “\(duplicate.title)”."
            } else {
                notice = "The paste was not saved. Try again."
            }
        } catch {
            guard !Task.isCancelled, generation == current, self.scope == scope else { return nil }
            notice = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
        return nil
    }
}
