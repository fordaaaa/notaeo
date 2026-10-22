import SwiftUI

/// Native Settings: account + appearance/motion preview + read-only AI availability.
/// Available logged-out (AI section explains login is required).
struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var aiEnabled = false
    @State private var aiModel: String?
    @State private var aiLoaded = false
    @State private var busy = false
    @State private var message: String?
    @AppStorage("notaeo.native.appearance") private var appearance = "system"
    @AppStorage("notaeo.native.reduceMotion") private var appReduceMotion = false
    @AppStorage("notaeo.native.soundEnabled") private var soundEnabled = false
    @State private var previewing = false
    @State private var previewTask: Task<Void, Never>?

    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    private var motion: NativeMotionPolicy {
        NativeMotionPolicy(systemReduceMotion: systemReduceMotion, appReduceMotion: appReduceMotion)
    }

    var body: some View {
        Form {
            Section("Appearance and motion") {
                Picker("Appearance", selection: $appearance) {
                    Text("System").tag("system")
                    Text("Light").tag("light")
                    Text("Dark").tag("dark")
                }
                Toggle("Reduce motion", isOn: $appReduceMotion)
                    .accessibilityLabel("Reduce motion")
                Button("Preview AI loading") {
                    previewing = true
                    previewTask = Task { @MainActor in
                        try? await Task.sleep(for: .seconds(3))
                        guard !Task.isCancelled else { return }
                        previewing = false
                    }
                }.disabled(previewing)
                if previewing {
                    NativeAIActivity(label: "Preparing an explanation…")
                        .transition(motion.transition)
                }
                Text("The preview runs locally for three seconds.").font(NativeType.caption).foregroundStyle(.secondary)
            }
            Section("Sound") {
                Toggle("Gentle completion sounds", isOn: $soundEnabled)
                    .onChange(of: soundEnabled) { _, enabled in
                        if !enabled { NativeFeedback.shared.stop() }
                    }
                Button("Preview cozy chime") { NativeFeedback.shared.preview() }
                Text("A quiet cue after saving an export. Preview plays once, even with completion sounds off.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
            }
            Section("Account") {
                if let email = appState.userEmail, appState.isLoggedIn {
                    Text(email).font(NativeType.body).textSelection(.enabled)
                    Button("Sign out") { Task { await appState.signOut() } }
                } else {
                    Text("Sign in to access your notebooks and see AI availability.")
                        .font(NativeType.body).foregroundStyle(.secondary)
                        .lineSpacing(1)
                }
            }
            Section("Optional AI") {
                Text("Source, search, and practice work without AI.")
                    .font(NativeType.caption).foregroundStyle(.secondary)
                if !appState.isLoggedIn {
                    Text("Sign in to see AI availability.")
                        .font(NativeType.body).foregroundStyle(.secondary)
                } else if busy && !aiLoaded {
                    ProgressView("Checking AI availability…")
                        .font(NativeType.body)
                } else if aiLoaded {
                    Text(aiEnabled ? "AI is available." : "AI is not available. Source, search, and practice work without AI.")
                        .font(NativeType.body).foregroundStyle(.secondary)
                    if aiEnabled, let model = aiModel, !model.isEmpty {
                        Text("Model: \(model)").font(NativeType.caption).foregroundStyle(.tertiary)
                    }
                }
                if let message {
                    Text(message).font(NativeType.body).foregroundStyle(.secondary)
                        .transition(motion.transition)
                }
            }
        }
        .formStyle(.grouped)
        .disabled(busy)
        .frame(width: 560, height: 660)
        .transaction { transaction in
            if motion.reducesMotion {
                transaction.animation = nil
                transaction.disablesAnimations = true
            }
        }
        .animation(motion.animation, value: previewing)
        .animation(motion.animation, value: message)
        .task(id: appState.accountToken) {
            aiEnabled = false; aiModel = nil; aiLoaded = false; message = nil
            await load()
        }
        .onDisappear { previewTask?.cancel(); previewing = false }
    }

    private func api() -> NotaeoAPI? { appState.makeAPI() }

    private func load() async {
        guard appState.isLoggedIn, let api = api() else { return }
        let account = appState.accountToken
        busy = true; defer { busy = false }
        do {
            let s = try await api.getAIStatus()
            guard !Task.isCancelled, account == appState.accountToken else { return }
            aiEnabled = s.enabled
            aiModel = s.model
            aiLoaded = true
        } catch {
            guard !Task.isCancelled, account == appState.accountToken else { return }
            message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }
}
