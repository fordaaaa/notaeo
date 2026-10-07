import AppKit
import SwiftUI

// MARK: - Service protocol

/// Public-web discovery service. Search is explicit only; import wraps URL ingest.
protocol WebDiscovering: Sendable {
    func discoverWeb(request: WebDiscoveryRequest) async throws -> WebDiscoveryPage
    func importWebSource(notebookId: String, url: String) async throws -> PasteResult
}

extension NotaeoAPI: WebDiscovering {}

// MARK: - Google link helper

/// Builds a deliberate "Open in Google" link from the submitted query plus the
/// validated site/type filters only. Academic, recency and region never travel.
enum GoogleDiscoveryLink {
    static func normalizedDomain(_ raw: String) -> String? {
        guard isValidDomain(raw) else { return nil }
        let input = raw.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return URL(string: "https://" + input)?.host?.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
    }

    static func isValidDomain(_ raw: String) -> Bool {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return false }
        if trimmed.contains(" ") || trimmed.contains("\t") || trimmed.contains("\n") { return false }
        if trimmed.contains("://") || trimmed.contains("/") || trimmed.contains("?")
            || trimmed.contains("#") || trimmed.contains("@") || trimmed.contains(":") { return false }
        if trimmed.contains("\"") || trimmed.contains("'") { return false }
        guard var host = URL(string: "https://" + trimmed)?.host?.lowercased() else { return false }
        if host.hasSuffix(".") { host = String(host.dropLast()) }
        guard !host.isEmpty, host.count <= 253 else { return false }
        guard host != "localhost" else { return false }
        if host.contains("..") { return false }
        let labels = host.split(separator: ".", omittingEmptySubsequences: false)
        guard labels.count >= 2 else { return false }
        // Reject IPv4 literals (backend also excludes private/reserved IPs).
        if labels.count == 4, labels.allSatisfy({ !$0.isEmpty && $0.allSatisfy(\.isNumber) && $0.count <= 3 }) {
            return false
        }
        for label in labels {
            guard label.count >= 1, label.count <= 63 else { return false }
            guard label.first != "-", label.last != "-" else { return false }
            for ch in label {
                let ok = (ch >= "a" && ch <= "z") || (ch >= "0" && ch <= "9") || ch == "-"
                if !ok { return false }
            }
        }
        return true
    }

    /// Encoded Google URL for the submitted query plus validated site/type only.
    static func url(query: String, domain: String?, fileType: WebDiscoveryFileType) -> URL? {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        var q = trimmed
        if let domain {
            if let normalized = normalizedDomain(domain) {
                q += " site:\(normalized)"
            }
        }
        switch fileType {
        case .pdf: q += " filetype:pdf"
        case .html: q += " -filetype:pdf"
        case .all: break
        }
        var comps = URLComponents(string: "https://www.google.com/search")
        comps?.queryItems = [URLQueryItem(name: "q", value: q)]
        return comps?.url
    }

    /// Only explicit, credential-free http(s) URLs may open in a browser.
    static func canOpenWebsite(_ url: URL) -> Bool {
        guard let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else { return false }
        guard let host = url.host, !host.isEmpty else { return false }
        if url.user != nil || url.password != nil { return false }
        return true
    }

    static func canOpenWebsite(string: String) -> Bool {
        guard let url = URL(string: string) else { return false }
        return canOpenWebsite(url)
    }

    static func isHTTPS(string: String) -> Bool {
        URL(string: string)?.scheme?.lowercased() == "https"
    }
}

// MARK: - Controller

/// Discovery state with generation guards: late search/import responses can
/// never replace newer results, and clear/cancel/task-cancel stops spinners.
@MainActor
final class NativeDiscoveryController: ObservableObject {
    @Published private(set) var page: WebDiscoveryPage?
    @Published private(set) var isLoading = false
    @Published private(set) var error: String?
    @Published private(set) var lastRequest: WebDiscoveryRequest?
    @Published private(set) var importingURL: String?
    @Published private(set) var importNotice: String?
    @Published private(set) var lastImportedSourceId: String?
    @Published private(set) var lastDuplicate: DuplicateRef?
    private(set) var notebookId: String?
    private var searchGeneration = 0
    private var importGeneration = 0
    private var boundAccountToken: String?

    var googleURL: URL? {
        guard let request = lastRequest else { return nil }
        return GoogleDiscoveryLink.url(query: request.query, domain: request.domain, fileType: request.fileType)
    }

    func bindAccount(_ token: String?) {
        guard boundAccountToken != token else { return }
        boundAccountToken = token
        clear()
    }

    func clear() {
        searchGeneration += 1
        importGeneration += 1
        page = nil; error = nil; lastRequest = nil; notebookId = nil; isLoading = false
        importingURL = nil; importNotice = nil; lastImportedSourceId = nil; lastDuplicate = nil
    }

    func cancel() {
        searchGeneration += 1
        importGeneration += 1
        isLoading = false
        importingURL = nil
    }

    func search(notebookId: String, request: WebDiscoveryRequest, using service: any WebDiscovering) async {
        guard !Task.isCancelled else { return }
        searchGeneration += 1
        let current = searchGeneration
        isLoading = true; error = nil; page = nil; lastRequest = request
        self.notebookId = notebookId
        defer { if searchGeneration == current { isLoading = false } }
        do {
            let result = try await service.discoverWeb(request: request)
            guard !Task.isCancelled, searchGeneration == current else { return }
            page = result
        } catch {
            guard !Task.isCancelled, searchGeneration == current else { return }
            self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func importSource(notebookId: String, url: String, using service: any WebDiscovering) async {
        guard !Task.isCancelled else { return }
        importGeneration += 1
        let current = importGeneration
        importingURL = url; importNotice = nil; lastImportedSourceId = nil; lastDuplicate = nil
        do {
            let res = try await service.importWebSource(notebookId: notebookId, url: url)
            guard !Task.isCancelled, importGeneration == current else { return }
            importingURL = nil
            if res.saved {
                importNotice = "Imported. Find it in Sources."
                lastImportedSourceId = res.summary?.id
            } else if let dup = res.duplicateOf {
                importNotice = "Already saved as “\(dup.title)”."
                lastDuplicate = dup
            } else {
                importNotice = "Already saved."
            }
        } catch {
            guard !Task.isCancelled, importGeneration == current else { return }
            importingURL = nil
            importNotice = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }
}

// MARK: - View

/// Native public-web discovery: explicit query + filters, typed results with
/// domain/snippet, HTTPS-HTML import via the existing URL API, deliberate
/// browser actions only. Never searches on tab/filter changes.
struct DiscoveryView: View {
    @EnvironmentObject private var appState: AppState
    let notebook: Notebook
    let onOpenSource: (String) -> Void
    @ObservedObject private var controller: NativeDiscoveryController
    @State private var query = ""
    @State private var engine: WebDiscoveryEngine = .auto
    @State private var domain = ""
    @State private var fileType: WebDiscoveryFileType = .all
    @State private var academic = false
    @State private var recency: WebDiscoveryRecency = .any
    @State private var region: WebDiscoveryRegion = .usEN
    @State private var pendingRequest: WebDiscoveryRequest?
    @State private var importTask: Task<Void, Never>?
    @State private var searchVersion = 0
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @AppStorage("notaeo.native.reduceMotion") private var reduceMotion = false

    private var motion: NativeMotionPolicy {
        NativeMotionPolicy(systemReduceMotion: systemReduceMotion, appReduceMotion: reduceMotion)
    }

    init(notebook: Notebook, controller: NativeDiscoveryController, onOpenSource: @escaping (String) -> Void) {
        self.notebook = notebook
        self.controller = controller
        self.onOpenSource = onOpenSource
        if controller.notebookId == notebook.id, let saved = controller.lastRequest {
            _query = State(initialValue: saved.query)
            _engine = State(initialValue: saved.engine)
            _domain = State(initialValue: saved.domain ?? "")
            _fileType = State(initialValue: saved.fileType)
            _academic = State(initialValue: saved.academic)
            _recency = State(initialValue: saved.recency)
            _region = State(initialValue: saved.region)
        }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Discover the public web").font(NativeType.title)
                    Text("Find useful course material on the web or in your indexed sites, then import an article.")
                        .font(NativeType.body).foregroundStyle(.secondary)
                }
                searchCard
                if let link = controller.googleURL {
                    Button { openURL(link) } label: { Label("Open in Google", systemImage: "arrow.up.right") }
                        .help("Opens Google with your submitted query, site and page type only.")
                        .accessibilityLabel("Open in Google")
                }
                if controller.isLoading {
                    HStack {
                        NativeAIActivity(label: controller.lastRequest?.engine == .index ? "Searching indexed pages…" : "Searching the public web…")
                        Spacer()
                        Button("Cancel") { cancelSearch() }
                            .accessibilityLabel("Cancel web search")
                    }.transition(motion.transition)
                } else if let error = controller.error {
                    NativeCard(title: "Web search couldn't finish", systemImage: "exclamationmark.circle") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(error).font(NativeType.body).textSelection(.enabled)
                            Button("Try again") { submit() }
                        }
                    }
                } else if let page = controller.page {
                    results(page)
                } else {
                    ContentUnavailableView("Research starts with a question", systemImage: "globe",
                        description: Text("Ask about your course, then import one HTTPS article. PDF links open for download."))
                }
                if let notice = controller.importNotice {
                    importNoticeCard(notice)
                }
            }
            .padding(24).frame(maxWidth: 900, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .background(NativePalette.canvas)
        .task(id: searchVersion) {
            guard let request = pendingRequest, let api = appState.makeAPI() else { return }
            await controller.search(notebookId: notebook.id, request: request, using: api)
        }
        .onDisappear { importTask?.cancel(); importTask = nil; controller.cancel() }
        .onAppear { controller.bindAccount(appState.accountToken) }
        .onChange(of: appState.accountToken) { _, token in
            importTask?.cancel()
            importTask = nil
            pendingRequest = nil
            searchVersion += 1
            query = ""
            domain = ""
            controller.bindAccount(token)
        }
        .onChange(of: engine) { _, value in if value == .index { recency = .any } }
    }

    private var searchCard: some View {
        NativeCard(title: "Find course sources", systemImage: "globe") {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 12) {
                    TextField("Topic, question, or exact phrase", text: $query)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel("Search the public web")
                        .onSubmit { submit() }
                    Button("Search") { submit() }
                        .buttonStyle(.borderedProminent)
                        .disabled(query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || query.trimmingCharacters(in: .whitespacesAndNewlines).count > 500)
                        .accessibilityLabel("Search the web")
                }
                HStack(spacing: 16) {
                    Picker("Search engine", selection: $engine) {
                        Text("Automatic").tag(WebDiscoveryEngine.auto)
                        Text("Google").tag(WebDiscoveryEngine.google)
                        Text("DuckDuckGo").tag(WebDiscoveryEngine.duckduckgo)
                        Text("Brave").tag(WebDiscoveryEngine.brave)
                        Text("Mojeek").tag(WebDiscoveryEngine.mojeek)
                        Text("Indexed sites").tag(WebDiscoveryEngine.index)
                    }.frame(maxWidth: 220).accessibilityLabel("Search engine")
                    Picker("Page type", selection: $fileType) {
                        Text("All pages").tag(WebDiscoveryFileType.all)
                        Text("PDF links").tag(WebDiscoveryFileType.pdf)
                        Text("Web pages").tag(WebDiscoveryFileType.html)
                    }.frame(maxWidth: 200).accessibilityLabel("Page type")
                }
                TextField("Site, for example example.edu (optional)", text: $domain)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Limit to site")
                HStack(spacing: 16) {
                    Toggle("Academic sites only", isOn: $academic)
                        .accessibilityLabel("Academic sites only")
                    Picker("Recent period", selection: $recency) {
                        Text("Any time").tag(WebDiscoveryRecency.any)
                        Text("Past day").tag(WebDiscoveryRecency.day)
                        Text("Past week").tag(WebDiscoveryRecency.week)
                        Text("Past month").tag(WebDiscoveryRecency.month)
                        Text("Past year").tag(WebDiscoveryRecency.year)
                    }.disabled(engine == .index).frame(maxWidth: 180).accessibilityLabel("Recent period")
                    Picker("Region", selection: $region) {
                        Text("US (English)").tag(WebDiscoveryRegion.usEN)
                        Text("Canada (English)").tag(WebDiscoveryRegion.caEN)
                        Text("UK (English)").tag(WebDiscoveryRegion.ukEN)
                        Text("Australia (English)").tag(WebDiscoveryRegion.auEN)
                    }.frame(maxWidth: 200).accessibilityLabel("Region")
                }
                Text("Academic limits results to educational sites (.edu, .ac.uk, arXiv, NCBI, OpenStax, Khan Academy, MIT OpenCourseWare, Coursera).")
                    .font(NativeType.caption).foregroundStyle(.secondary)
                Text("Search runs only when you press Search. Open in Google uses your query, site and page type only.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
                if query.count > 500 {
                    Text("Use 500 characters or fewer.").font(NativeType.caption).foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    private func results(_ page: WebDiscoveryPage) -> some View {
        HStack {
            Text("\(page.results.count) result\(page.results.count == 1 ? "" : "s")")
                .font(NativeType.heading)
                .accessibilityLabel("\(page.results.count) web results")
            Spacer()

        }
        Text("Results for “\(page.query)”").font(NativeType.caption).foregroundStyle(.secondary)
        if page.results.isEmpty {
            ContentUnavailableView("No public results", systemImage: "globe",
                description: Text("Try fewer words, another site, or a different page type."))
        } else {
            ForEach(Array(page.results.enumerated()), id: \.offset) { _, result in
                resultCard(result)
            }
        }
    }

    private func resultCard(_ result: WebDiscoveryResult) -> some View {
        NativeCard(title: result.title, systemImage: result.isPDF ? "doc.richtext" : "globe") {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    Text(result.domain).font(NativeType.caption).foregroundStyle(.secondary)
                    Text("·").font(NativeType.caption).foregroundStyle(.secondary)
                    Text(result.typeLabel).font(NativeType.caption).foregroundStyle(.secondary)
                }
                Text(result.snippet).font(NativeType.body).lineSpacing(4).textSelection(.enabled)
                resultActions(result)
            }
        }
    }

    @ViewBuilder
    private func resultActions(_ result: WebDiscoveryResult) -> some View {
        let safe = GoogleDiscoveryLink.canOpenWebsite(string: result.url)
        let https = GoogleDiscoveryLink.isHTTPS(string: result.url)
        HStack(spacing: 12) {
            if safe, let url = URL(string: result.url) {
                Button { openURL(url) } label: { Label("Open website", systemImage: "arrow.up.right") }
                    .accessibilityLabel("Open website \(result.domain)")
            }
            if result.isPDF {
                Text("Download the PDF, then upload it in Sources.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
            } else if !https {
                Text("Import needs an HTTPS address.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
            } else {
                if controller.importingURL == result.url {
                    NativeAIActivity(label: "Importing article…")
                    Button("Cancel") { importTask?.cancel(); importTask = nil; controller.cancel() }
                } else {
                    Button("Import") { importResult(result) }
                        .disabled(controller.importingURL != nil)
                        .accessibilityLabel("Import \(result.domain) article")
                }
            }
            Spacer()
        }
    }

    private func importNoticeCard(_ notice: String) -> some View {
        NativeCard(title: "Web import", systemImage: "tray.and.arrow.down") {
            VStack(alignment: .leading, spacing: 8) {
                Text(notice).font(NativeType.body)
                if let id = controller.lastImportedSourceId ?? controller.lastDuplicate?.id {
                    Button { onOpenSource(id) } label: { Label("Open source", systemImage: "arrow.up.right") }
                        .accessibilityLabel("Open imported source")
                }
            }
        }
    }

    private func submit() {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed.count <= 500 else { return }
        let site = domain.trimmingCharacters(in: .whitespacesAndNewlines)
        pendingRequest = WebDiscoveryRequest(
            query: trimmed,
            limit: 20,
            engine: engine,
            domain: site.isEmpty ? nil : site,
            fileType: fileType,
            academic: academic,
            recency: engine == .index ? .any : recency,
            region: region
        )
        searchVersion += 1
    }

    private func cancelSearch() {
        pendingRequest = nil
        searchVersion += 1
        controller.cancel()
    }

    private func importResult(_ result: WebDiscoveryResult) {
        guard let api = appState.makeAPI() else { return }
        let notebookId = notebook.id
        let url = result.url
        importTask?.cancel()
        importTask = Task {
            guard !Task.isCancelled else { return }
            await controller.importSource(notebookId: notebookId, url: url, using: api)
        }
    }

    private func openURL(_ url: URL) {
        guard GoogleDiscoveryLink.canOpenWebsite(url) else { return }
        NSWorkspace.shared.open(url)
    }
}
