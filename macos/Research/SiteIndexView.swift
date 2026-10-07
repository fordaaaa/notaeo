import SwiftUI

// MARK: - Service protocol

/// Account-owned educational site index. Listing/adding/removing never crawls;
/// only explicit refresh crawls (bounded, up to 5 pages per pass on the server).
protocol SiteIndexManaging: Sendable {
    func listIndexSites() async throws -> [SiteIndexSite]
    func addIndexSite(url: String) async throws -> SiteIndexSite
    func refreshIndexSite(id: String) async throws -> SiteIndexSite
    func deleteIndexSite(id: String) async throws
}

extension NotaeoAPI: SiteIndexManaging {}

// MARK: - Controller

/// Site-index state with generation guards: late list/add/refresh/delete
/// responses can never replace newer results, and clear/cancel/task-cancel
/// stops spinners without leaking another account's pages.
@MainActor
final class SiteIndexController: ObservableObject {
    @Published private(set) var sites: [SiteIndexSite] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isAdding = false
    @Published private(set) var workingId: String?
    @Published private(set) var error: String?
    @Published private(set) var notice: String?
    private var generation = 0

    func clear() {
        generation += 1
        sites = []
        isLoading = false
        isAdding = false
        workingId = nil
        error = nil
        notice = nil
    }

    func cancel() {
        generation += 1
        isLoading = false
        isAdding = false
        workingId = nil
    }

    func list(using service: any SiteIndexManaging) async {
        guard !Task.isCancelled else { return }
        generation += 1
        let current = generation
        isLoading = true
        error = nil
        notice = nil
        defer { if generation == current { isLoading = false } }
        do {
            let result = try await service.listIndexSites()
            guard !Task.isCancelled, generation == current else { return }
            sites = result
        } catch {
            guard !Task.isCancelled, generation == current else { return }
            self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func add(url: String, using service: any SiteIndexManaging) async {
        guard !Task.isCancelled else { return }
        generation += 1
        let current = generation
        isAdding = true
        error = nil
        notice = nil
        defer { if generation == current { isAdding = false } }
        do {
            let site = try await service.addIndexSite(url: url)
            guard !Task.isCancelled, generation == current else { return }
            upsert(site)
            notice = "Site saved. Refresh it explicitly to cache pages."
        } catch {
            guard !Task.isCancelled, generation == current else { return }
            self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func refresh(id: String, using service: any SiteIndexManaging) async {
        guard !Task.isCancelled else { return }
        generation += 1
        let current = generation
        workingId = id
        error = nil
        notice = nil
        defer { if generation == current { workingId = nil } }
        do {
            let site = try await service.refreshIndexSite(id: id)
            guard !Task.isCancelled, generation == current else { return }
            upsert(site)
            notice = "Refresh finished."
        } catch {
            guard !Task.isCancelled, generation == current else { return }
            self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func delete(id: String, using service: any SiteIndexManaging) async {
        guard !Task.isCancelled else { return }
        generation += 1
        let current = generation
        workingId = id
        error = nil
        notice = nil
        defer { if generation == current { workingId = nil } }
        do {
            try await service.deleteIndexSite(id: id)
            guard !Task.isCancelled, generation == current else { return }
            sites.removeAll(where: { $0.id == id })
            notice = "Site removed."
        } catch {
            guard !Task.isCancelled, generation == current else { return }
            self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func upsert(_ site: SiteIndexSite) {
        if let index = sites.firstIndex(where: { $0.id == site.id }) {
            sites[index] = site
        } else {
            sites.append(site)
        }
    }
}

// MARK: - View

/// Native educational site index: per-account starting URLs, explicit refresh
/// (up to 5 pages per pass), page counts and status. Listing is local-only;
/// adding never crawls. Never opens a browser automatically.
struct SiteIndexView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var controller: SiteIndexController
    @State private var urlText = ""
    @State private var selectedId: String?
    @State private var showDeleteConfirm = false
    @State private var operationTask: Task<Void, Never>?
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @AppStorage("notaeo.native.reduceMotion") private var reduceMotion = false

    private var motion: NativeMotionPolicy {
        NativeMotionPolicy(systemReduceMotion: systemReduceMotion, appReduceMotion: reduceMotion)
    }

    init(controller: SiteIndexController = SiteIndexController()) {
        _controller = StateObject(wrappedValue: controller)
    }

    private var isWaiting: Bool {
        controller.isLoading || controller.isAdding || controller.workingId != nil
    }

    private var waitingLabel: String {
        if controller.isLoading { return "Listing indexed sites…" }
        if controller.isAdding { return "Saving site…" }
        if controller.workingId != nil { return "Updating site…" }
        return "Working…"
    }

    private var selectedSite: SiteIndexSite? {
        controller.sites.first(where: { $0.id == selectedId })
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Site index").font(NativeType.title)
                    Text("Keep your own index of selected educational sites for this account.")
                        .font(NativeType.body).foregroundStyle(.secondary)
                    Text("Choose Indexed sites in Discover for local cached passages; import fetches the live article. Adding a site never crawls; refresh explicitly caches up to 5 pages per pass.")
                        .font(NativeType.caption).foregroundStyle(.secondary)
                }
                addCard
                if isWaiting {
                    HStack {
                        NativeAIActivity(label: waitingLabel)
                        Spacer()
                        Button("Cancel") { cancelWaiting() }
                            .accessibilityLabel("Cancel site index request")
                            .help("Cancel stops waiting. The server refresh is bounded and may still finish.")
                    }.transition(motion.transition)
                    Text("Cancel stops waiting. The server refresh is bounded and may still finish.")
                        .font(NativeType.caption).foregroundStyle(.secondary)
                } else if let error = controller.error {
                    NativeCard(title: "Site index couldn't finish", systemImage: "exclamationmark.circle") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(error).font(NativeType.body).textSelection(.enabled)
                            Button("Try again") { list() }
                        }
                    }
                }
                sitesCard
                if let notice = controller.notice {
                    NativeCard(title: "Site index", systemImage: "checkmark.circle") {
                        Text(notice).font(NativeType.body)
                    }
                }
            }
            .padding(24).frame(maxWidth: 900, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .background(NativePalette.canvas)
        .task {
            if let api = appState.makeAPI() {
                await controller.list(using: api)
            } else {
                await controller.list(using: OfflineSiteIndexService())
            }
            // Report unavailable storage rather than presenting a false empty index.
        }
        .onDisappear {
            operationTask?.cancel()
            operationTask = nil
            controller.clear()
        }
        .onChange(of: appState.accountToken) { _, _ in
            operationTask?.cancel()
            operationTask = nil
            controller.clear()
            selectedId = nil
            urlText = ""
            showDeleteConfirm = false
            operationTask = Task {
                guard !Task.isCancelled else { return }
                guard let api = appState.makeAPI() else { return }
                await controller.list(using: api)
            }
        }
        .confirmationDialog(
            "Remove this site?",
            isPresented: $showDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Remove site", role: .destructive) { doDelete() }
            Button("Keep site", role: .cancel) {}
        } message: {
            Text("Removes the site and its cached pages for this account. This cannot be undone.")
        }
    }

    private var addCard: some View {
        NativeCard(title: "Add educational site", systemImage: "plus.circle") {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 12) {
                    TextField("https://example.edu/collection", text: $urlText)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel("Starting URL for an educational site")
                        .onSubmit { doAdd() }
                    Button("Add") { doAdd() }
                        .buttonStyle(.borderedProminent)
                        .disabled(urlText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isWaiting)
                        .accessibilityLabel("Add indexed site")
                }
                Text("Use an HTTPS starting URL. Educational and robots scope is enforced by the server; adding never crawls.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
            }
        }
    }

    private var sitesCard: some View {
        NativeCard(title: "Indexed sites", systemImage: "books.vertical") {
            VStack(alignment: .leading, spacing: 12) {
                if controller.sites.isEmpty && !isWaiting {
                    Text("No indexed sites yet. Add a starting URL above, then refresh it explicitly.")
                        .font(NativeType.body).foregroundStyle(.secondary)
                } else {
                    ForEach(controller.sites) { site in
                        siteRow(site)
                    }
                }
                HStack(spacing: 12) {
                    Button("Refresh selected (up to 5 pages)") { doRefresh() }
                        .disabled(selectedSite == nil || isWaiting)
                        .accessibilityLabel("Refresh selected site")
                        .help("Caches up to 5 pages per refresh pass.")
                    Button("Remove", role: .destructive) { showDeleteConfirm = true }
                        .disabled(selectedSite == nil || isWaiting)
                        .accessibilityLabel("Remove selected site")
                    Spacer()
                }
            }
        }
    }

    private func siteRow(_ site: SiteIndexSite) -> some View {
        let selected = site.id == selectedId
        return Button {
            selectedId = site.id
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(site.url).font(NativeType.body).lineLimit(2).textSelection(.enabled)
                Text(detailLine(for: site))
                    .font(NativeType.caption).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(selected ? NativePalette.accent.opacity(0.12) : NativePalette.canvas)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .strokeBorder(selected ? NativePalette.accent : NativePalette.border)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Indexed site \(site.url)")
        .accessibilityHint("\(site.pageCount) pages. \(lastIndexedLine(for: site)) \(noticeLabel(for: site)).")
    }

    private func detailLine(for site: SiteIndexSite) -> String {
        "\(site.pageCount) \(site.pageCount == 1 ? "page" : "pages") · \(lastIndexedLine(for: site)) · \(noticeLabel(for: site))"
    }

    private func noticeLabel(for site: SiteIndexSite) -> String {
        switch site.notice {
        case "complete": return "Refresh complete"
        case "page_limit": return "Five-page limit reached"
        case "time_limit": return "Refresh time limit reached"
        case "partial": return "Some pages could not be indexed"
        default: return "Not refreshed yet"
        }
    }

    private func lastIndexedLine(for site: SiteIndexSite) -> String {
        if let indexed = site.indexedAt, !indexed.isEmpty {
            return "Last indexed \(indexed)"
        }
        return "Never indexed"
    }

    private func list() {
        operationTask?.cancel()
        guard let api = appState.makeAPI() else { return }
        operationTask = Task {
            guard !Task.isCancelled else { return }
            await controller.list(using: api)
        }
    }

    private func doAdd() {
        let trimmed = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isWaiting else { return }
        guard let api = appState.makeAPI() else { return }
        operationTask?.cancel()
        operationTask = Task {
            guard !Task.isCancelled else { return }
            await controller.add(url: trimmed, using: api)
            if !Task.isCancelled { urlText = "" }
        }
    }

    private func doRefresh() {
        guard let id = selectedId, !isWaiting else { return }
        guard let api = appState.makeAPI() else { return }
        operationTask?.cancel()
        operationTask = Task {
            guard !Task.isCancelled else { return }
            await controller.refresh(id: id, using: api)
        }
    }

    private func doDelete() {
        guard let id = selectedId, !isWaiting else { return }
        guard let api = appState.makeAPI() else { return }
        operationTask?.cancel()
        operationTask = Task {
            guard !Task.isCancelled else { return }
            await controller.delete(id: id, using: api)
            if !Task.isCancelled { selectedId = nil }
        }
    }

    private func cancelWaiting() {
        operationTask?.cancel()
        operationTask = nil
        controller.cancel()
    }
}

// MARK: - Offline fallback (keeps the screen usable before the sidecar is ready)

private struct OfflineSiteIndexService: SiteIndexManaging {
    func listIndexSites() async throws -> [SiteIndexSite] { throw APIError.network("Backend is not ready yet.") }
    func addIndexSite(url: String) async throws -> SiteIndexSite {
        throw APIError.network("Backend is not ready yet.")
    }
    func refreshIndexSite(id: String) async throws -> SiteIndexSite {
        throw APIError.network("Backend is not ready yet.")
    }
    func deleteIndexSite(id: String) async throws {
        throw APIError.network("Backend is not ready yet.")
    }
}
