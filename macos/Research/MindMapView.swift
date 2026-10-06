import AppKit
import SwiftUI
import UniformTypeIdentifiers

/// Keyless course mind map: notebook → source branches → concept leaves.
///
/// Built on-device from the notebook's own sources (term-frequency mapping,
/// no provider key). Every branch/leaf cites its source; tapping a citation
/// opens the source via `onOpenSource(sourceId, page)`.
struct MindMapView: View {
    @EnvironmentObject private var appState: AppState
    let notebook: Notebook
    let onOpenSource: (String, Int?) -> Void

    @State private var root: NativeMindmapNode?
    @State private var collapsed: Set<String> = []
    @State private var mode: Mode = .map
    @State private var zoom: CGFloat = 1.0
    @GestureState private var magnification: CGFloat = 1.0
    @State private var graphHeight: CGFloat = 460
    @State private var refreshTask: Task<Void, Never>?
    @State private var exportTask: Task<Void, Never>?
    @State private var isLoading = false
    @State private var isExporting = false
    @State private var error: String?
    @State private var notice: String?
    @State private var generation = 0

    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @AppStorage("notaeo.native.reduceMotion") private var appReduceMotion = false
    private var motion: NativeMotionPolicy {
        NativeMotionPolicy(systemReduceMotion: systemReduceMotion, appReduceMotion: appReduceMotion)
    }

    enum Mode: String, CaseIterable { case map = "Map", outline = "Outline" }

    init(notebook: Notebook, onOpenSource: @escaping (String, Int?) -> Void) {
        self.notebook = notebook
        self.onOpenSource = onOpenSource
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header
                if let error {
                    NativeCard(title: "Mind map couldn't load", systemImage: "exclamationmark.circle") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(error).font(NativeType.body).textSelection(.enabled)
                            Button("Try again") { refresh() }
                        }
                    }
                    .transition(motion.transition)
                }
                if isLoading && root == nil {
                    NativeAIActivity(label: "Mapping your sources…")
                        .transition(motion.transition)
                } else if let root {
                    Picker("Mind map view", selection: $mode) {
                        ForEach(Mode.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 200)
                    .accessibilityLabel("Mind map view")
                    if mode == .map {
                        mapCard(root)
                            .transition(motion.transition)
                    } else {
                        outlineCard(root)
                            .transition(motion.transition)
                    }
                } else if !isLoading {
                    ContentUnavailableView(
                        "Map your course at a glance",
                        systemImage: "map",
                        description: Text("Add course material, then refresh to see each source and its key concepts.")
                    )
                }
                if let notice {
                    Text(notice).font(NativeType.caption).foregroundStyle(.secondary)
                        .transition(motion.transition)
                }
            }
            .padding(24)
            .frame(maxWidth: 1_100, alignment: .leading)
            .frame(maxWidth: .infinity)
            .animation(motion.animation, value: isLoading)
            .animation(motion.animation, value: mode)
        }
        .background(NativePalette.canvas)
        .task(id: notebook.id) { await load() }
        .onDisappear {
            generation += 1
            refreshTask?.cancel()
            exportTask?.cancel()
        }
    }

    // MARK: - Header

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Course mind map").font(NativeType.display)
            Text("Each source branches into its key concepts. Open any citation to read it in context.")
                .font(NativeType.body).foregroundStyle(.secondary)
                .lineSpacing(2)
            Text("Built from your course material. No AI key needed.")
                .font(NativeType.caption).foregroundStyle(.secondary)
            HStack(spacing: 12) {
                Button { refresh() } label: { Label("Refresh map", systemImage: "arrow.clockwise") }
                    .disabled(isLoading || isExporting)
                Button { exportTask = Task { await exportMap() } } label: { Label("Export Markdown…", systemImage: "square.and.arrow.up") }
                    .disabled(isLoading || isExporting || root == nil)
                if isLoading {
                    Button("Cancel") { generation += 1; refreshTask?.cancel(); isLoading = false }
                }
                if isExporting {
                    ProgressView().controlSize(.small).accessibilityLabel("Exporting mind map")
                }
            }
            .padding(.top, 8)
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: [NativePalette.accent.opacity(0.16), NativePalette.surface],
                startPoint: .topLeading, endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 16)
        )
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(NativePalette.border))
        .padding(.top, 4)
    }

    // MARK: - Branching visual

    private func mapCard(_ root: NativeMindmapNode) -> some View {
        let graphWidth = max(320, CGFloat(root.children.count) * 220 + CGFloat(max(0, root.children.count - 1)) * 18) + 24
        let displayZoom = min(1.6, max(0.6, zoom * magnification))
        return NativeCard(title: root.name, systemImage: "map") {
            VStack(alignment: .leading, spacing: 10) {
                mapToolbar(root)
                ScrollView([.horizontal, .vertical]) {
                    VStack(spacing: 0) {
                        rootPill(root)
                        if !root.children.isEmpty {
                            connectorVertical(height: 22)
                            HStack(alignment: .top, spacing: 18) {
                                ForEach(root.children) { branch in
                                    branchColumn(branch)
                                }
                            }
                            .overlay(alignment: .top) {
                                Rectangle().fill(NativePalette.accent.opacity(0.45))
                                    .frame(width: CGFloat(max(0, root.children.count - 1)) * 238, height: 2)
                                    .accessibilityHidden(true)
                            }
                        }
                    }
                    .padding(12)
                    .frame(width: graphWidth)
                    .background(GeometryReader { geometry in
                        Color.clear.preference(key: MindMapHeightKey.self, value: geometry.size.height)
                    })
                    .scaleEffect(displayZoom, anchor: .topLeading)
                    .frame(width: graphWidth * displayZoom, height: graphHeight * displayZoom, alignment: .topLeading)
                    .onPreferenceChange(MindMapHeightKey.self) { graphHeight = $0 }
                }
                .frame(height: 440)
                .gesture(MagnificationGesture()
                    .updating($magnification) { value, state, _ in state = value }
                    .onEnded { value in zoom = min(1.6, max(0.6, zoom * value)) })
                Text("Scroll to explore. Use Outline for a compact reading view.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
                    .accessibilityHidden(true)
            }
        }
    }

    private func mapToolbar(_ root: NativeMindmapNode) -> some View {
        HStack(spacing: 12) {
            Text("\(root.children.count) source\(root.children.count == 1 ? "" : "s") · \(root.children.reduce(0) { $0 + $1.children.count }) concepts")
                .font(NativeType.caption).foregroundStyle(.secondary)
            Spacer()
            Button("Collapse all") { collapsed = Set(root.children.map { $0.id }) }
                .disabled(root.children.isEmpty)
            Button("Expand all") { collapsed.removeAll() }
                .disabled(collapsed.isEmpty)
            HStack(spacing: 6) {
                Button { zoom = max(0.6, zoom - 0.15) } label: { Image(systemName: "minus.magnifyingglass") }
                    .disabled(zoom <= 0.6).help("Zoom out")
                Text("\(Int(zoom * 100))%").font(NativeType.caption).frame(minWidth: 44)
                    .accessibilityLabel("Zoom \(Int(zoom * 100)) percent")
                Button { zoom = min(1.6, zoom + 0.15) } label: { Image(systemName: "plus.magnifyingglass") }
                    .disabled(zoom >= 1.6).help("Zoom in")
            }
            .accessibilityElement(children: .contain)
            .accessibilityLabel("Map zoom")
        }
    }

    private func rootPill(_ root: NativeMindmapNode) -> some View {
        Text(root.name)
            .font(NativeType.heading)
            .lineLimit(3)
            .multilineTextAlignment(.center)
            .padding(.horizontal, 18).padding(.vertical, 12)
            .frame(maxWidth: 320)
            .background(
                LinearGradient(colors: [NativePalette.accent.opacity(0.28), NativePalette.surface],
                               startPoint: .topLeading, endPoint: .bottomTrailing),
                in: RoundedRectangle(cornerRadius: 14)
            )
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(NativePalette.accent.opacity(0.5)))
    }

    private func branchColumn(_ branch: NativeMindmapNode) -> some View {
        VStack(spacing: 0) {
            connectorVertical(height: 10)
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 8) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(branch.name)
                            .font(NativeType.heading)
                            .lineLimit(3)
                        if !branch.pages.isEmpty {
                            Text("p. \(branch.pages.map(String.init).joined(separator: ", "))")
                                .font(NativeType.caption).foregroundStyle(.secondary)
                        }
                    }
                    Spacer(minLength: 4)
                    Button {
                        if collapsed.contains(branch.id) { collapsed.remove(branch.id) }
                        else { collapsed.insert(branch.id) }
                    } label: {
                        Image(systemName: collapsed.contains(branch.id) ? "chevron.right" : "chevron.down")
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(collapsed.contains(branch.id) ? "Expand \(branch.name)" : "Collapse \(branch.name)")
                }
                if let sourceId = branch.sourceId {
                    Button { onOpenSource(sourceId, branch.pages.first) } label: {
                        Label("Open source", systemImage: "arrow.up.right")
                    }
                    .buttonStyle(.link).font(NativeType.caption)
                    .accessibilityLabel("Open source \(branch.name)")
                }
                if !collapsed.contains(branch.id) {
                    Divider()
                    if branch.children.isEmpty {
                        Text("No key concepts yet.")
                            .font(NativeType.caption).foregroundStyle(.secondary)
                    } else {
                        VStack(alignment: .leading, spacing: 6) {
                            ForEach(branch.children) { leaf in
                                leafRow(leaf)
                            }
                        }
                    }
                }
            }
            .padding(12)
            .frame(width: 220, alignment: .leading)
            .background(NativePalette.surface, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(NativePalette.border))
        }
    }

    private func leafRow(_ leaf: NativeMindmapNode) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Rectangle().fill(NativePalette.accent.opacity(0.6)).frame(width: 2, height: 28)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 2) {
                Text(leaf.name).font(NativeType.body).lineLimit(3)
                if !leaf.pages.isEmpty {
                    Text("p. \(leaf.pages.map(String.init).joined(separator: ", "))")
                        .font(NativeType.caption).foregroundStyle(.secondary)
                }
            }
            Spacer(minLength: 2)
            if let sourceId = leaf.sourceId {
                Button { onOpenSource(sourceId, leaf.pages.first) } label: {
                    Image(systemName: "arrow.up.right.circle")
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open \(leaf.name) in source")
            }
        }
    }

    private func connectorVertical(height: CGFloat) -> some View {
        Rectangle().fill(NativePalette.accent.opacity(0.45))
            .frame(width: 2, height: height)
            .accessibilityHidden(true)
    }

    // MARK: - Readable outline alternative

    private func outlineCard(_ root: NativeMindmapNode) -> some View {
        NativeCard(title: "Outline", systemImage: "list.bullet") {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(root.children) { branch in
                    DisclosureGroup {
                        VStack(alignment: .leading, spacing: 6) {
                            if let sourceId = branch.sourceId {
                                Button("Open source\(branch.pages.isEmpty ? "" : " · p. \(branch.pages.map(String.init).joined(separator: ", "))")") {
                                    onOpenSource(sourceId, branch.pages.first)
                                }
                                .buttonStyle(.link).font(NativeType.body)
                            }
                            ForEach(branch.children) { leaf in
                                HStack {
                                    Text(leaf.name).font(NativeType.body).textSelection(.enabled)
                                    Spacer()
                                    if !leaf.pages.isEmpty {
                                        Text("p. \(leaf.pages.map(String.init).joined(separator: ", "))")
                                            .font(NativeType.caption).foregroundStyle(.secondary)
                                    }
                                    if let sourceId = leaf.sourceId {
                                        Button("Open") { onOpenSource(sourceId, leaf.pages.first) }
                                            .buttonStyle(.link).font(NativeType.body)
                                    }
                                }
                            }
                        }
                        .padding(.leading, 4)
                    } label: {
                        Text("\(branch.name) · \(branch.children.count) concept\(branch.children.count == 1 ? "" : "s")")
                            .font(NativeType.heading)
                    }
                    Divider()
                }
            }
        }
    }

    // MARK: - Loading + export

    private func api() -> NotaeoAPI? { appState.makeAPI() }

    private func refresh() {
        refreshTask?.cancel()
        refreshTask = Task { await load() }
    }

    private func load() async {
        guard let api = api() else {
            error = "Backend is not ready yet."
            return
        }
        generation += 1
        let current = generation
        isLoading = true; error = nil; notice = nil
        defer { if current == generation { isLoading = false } }
        do {
            let tree = try await api.getMindmap(notebookId: notebook.id)
            guard !Task.isCancelled, current == generation else { return }
            root = tree
            collapsed.removeAll()
        } catch {
            guard !Task.isCancelled, current == generation else { return }
            self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func exportMap() async {
        guard !isExporting, let api = api() else { return }
        isExporting = true; notice = nil
        let current = generation
        defer { isExporting = false }
        do {
            let result = try await api.exportMindmap(notebookId: notebook.id)
            guard !Task.isCancelled, current == generation else { return }
            let panel = NSSavePanel()
            panel.allowedContentTypes = [UTType(filenameExtension: "md") ?? .plainText]
            panel.nameFieldStringValue = DownloadHandler.sanitizedExportFilename(
                result.filename, fallback: "mindmap.md")
            guard await panel.begin() == .OK, let url = panel.url else { return }
            guard !Task.isCancelled, current == generation else { return }
            try result.data.write(to: url, options: .atomic)
            notice = "Mind map exported."
        } catch {
            guard !Task.isCancelled, current == generation else { return }
            notice = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct MindMapHeightKey: PreferenceKey {
    static let defaultValue: CGFloat = 460
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
