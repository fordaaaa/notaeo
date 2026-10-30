import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var controller = TodayController()
    let notebooks: [Notebook]
    let openNotebook: (Notebook, Bool) -> Void
    @State private var title = ""
    @State private var classId = ""
    @State private var notebookId = ""
    @State private var hasDeadline = false
    @State private var deadline = Date()
    @State private var showCompleted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Today").font(NativeType.title)
                    Text("Your coursework and the material you need next.")
                        .font(NativeType.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Refresh", systemImage: "arrow.clockwise") { Task { await reload() } }
                    .disabled(controller.isLoading || controller.isWriting)
            }
            if controller.isLoading { ProgressView("Loading coursework…") }
            if let notice = controller.notice {
                HStack {
                    Text(notice).foregroundStyle(.secondary)
                    Button("Try again") { Task { await reload() } }
                }
            }
            addAssignment.disabled(controller.isWriting || controller.isLoading)
            Divider()
            TimelineView(.periodic(from: .now, by: 60)) { context in
                let sections = TodaySections(controller.assignments, now: context.date, calendar: .current)
                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        if controller.assignments.isEmpty && !controller.isLoading && controller.notice == nil {
                            ContentUnavailableView("Make a plan for your coursework", systemImage: "checklist",
                                description: Text("Add an assignment above. Link a notebook to keep its readings and study tools within reach."))
                        }
                        section("Overdue", assignments: sections.overdue)
                        section("Due today", assignments: sections.today)
                        section("Upcoming", assignments: sections.upcoming)
                        section("No deadline", assignments: sections.undated)
                        if !controller.assignments.isEmpty && controller.assignments.allSatisfy(\.done) {
                            Text("All saved work is complete.").foregroundStyle(.secondary)
                        }
                        DisclosureGroup("Completed work", isExpanded: $showCompleted) {
                            section("", assignments: controller.assignments.filter(\.done))
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .padding(24)
        .background(NativePalette.canvas)
        .task(id: appState.accountToken) {
            controller.bind(accountToken: appState.accountToken)
            await reload()
        }
        .onDisappear { controller.bind(accountToken: nil) }
    }

    private var addAssignment: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Add coursework").font(NativeType.heading)
            TextField("Assignment or reading", text: $title).textFieldStyle(.roundedBorder)
            HStack {
                Picker("Course", selection: $classId) {
                    Text("No course").tag("")
                    ForEach(controller.classes) { Text($0.name).tag($0.id) }
                }
                Picker("Material", selection: $notebookId) {
                    Text("No linked notebook").tag("")
                    ForEach(notebooks) { Text($0.name).tag($0.id) }
                }
            }
            HStack {
                Toggle("Deadline", isOn: $hasDeadline).toggleStyle(.checkbox)
                if hasDeadline { DatePicker("Due", selection: $deadline).labelsHidden() }
                Spacer()
                Button("Add assignment") { Task { await save() } }
                    .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || controller.isWriting || controller.isLoading)
            }
        }
    }

    @ViewBuilder
    private func section(_ heading: String, assignments: [CourseworkAssignment]) -> some View {
        if !assignments.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                if !heading.isEmpty { Text(heading).font(NativeType.heading) }
                ForEach(assignments) { assignment in
                    HStack(alignment: .top, spacing: 12) {
                        Button {
                            guard let api = appState.makeAPI() else { return }
                            Task { await controller.setDone(assignment, done: !assignment.done, using: api) }
                        } label: {
                            Image(systemName: assignment.done ? "checkmark.circle.fill" : "circle")
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(assignment.done ? "Reopen \(assignment.title)" : "Complete \(assignment.title)")
                        .disabled(controller.isWriting || controller.isLoading)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(assignment.title).font(.headline)
                            if let name = assignment.className { Text(name).foregroundStyle(.secondary) }
                            if let due = assignment.deadline {
                                Text(due, format: .dateTime.month().day().hour().minute()).font(NativeType.caption)
                            }
                            if !assignment.details.isEmpty { Text(assignment.details).lineLimit(3).foregroundStyle(.secondary) }
                        }
                        Spacer()
                        if let notebook = notebooks.first(where: { $0.id == assignment.notebookId }) {
                            Button("Read material") { openNotebook(notebook, false) }
                            Button("Study") { openNotebook(notebook, true) }
                        }
                    }.padding(12).background(NativePalette.surface, in: RoundedRectangle(cornerRadius: 10))
                }
            }
        }
    }

    private func reload() async {
        guard let api = appState.makeAPI() else { return }
        await controller.load(using: api)
    }

    private func save() async {
        guard let api = appState.makeAPI() else { return }
        let draft = AssignmentDraft(title: title, classId: classId.isEmpty ? nil : classId,
            notebookId: notebookId.isEmpty ? nil : notebookId,
            dueAt: hasDeadline ? ISO8601DateFormatter().string(from: deadline) : nil)
        if await controller.add(draft, using: api), title == draft.title { title = "" }
    }
}
