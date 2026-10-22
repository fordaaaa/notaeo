import AppKit
import SwiftUI

/// Terminates only the sidecar this shell started.
@MainActor
private final class AppDelegate: NSObject, NSApplicationDelegate {
    weak var backend: BackendProcess?

    func applicationWillFinishLaunching(_ notification: Notification) {
        guard !AppState.isTestHost() else { return }
        MainWindowPresentation.configureLaunchPreferences(.standard)
    }

    func applicationWillTerminate(_ notification: Notification) {
        backend?.stop()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { sender.windows.first(where: { $0.title == "Notaeo" })?.makeKeyAndOrderFront(nil) }
        return true
    }
}

@main
struct NotaeoApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var backend = BackendProcess()
    @StateObject private var appState = AppState.forApplication()
    @AppStorage("notaeo.native.appearance") private var appearance = "system"

    var body: some Scene {
        mainWindow

        // Native Settings scene: visible via app menu + Cmd+, throughout.
        Settings {
            SettingsView()
                .environmentObject(appState)
                .preferredColorScheme(appearance == "dark" ? .dark : appearance == "light" ? .light : nil)
                .tint(NativePalette.accent)
        }
    }

    private var mainWindow: some Scene {
        Window("Notaeo", id: "main") {
            ContentView()
                .background(MainWindowPlacement())
                .preferredColorScheme(appearance == "dark" ? .dark : appearance == "light" ? .light : nil)
                .environmentObject(backend)
                .environmentObject(appState)
                .onAppear {
                    appDelegate.backend = backend
                    if !AppState.isTestHost() { backend.startIfNeeded() }
                }
                .onChange(of: backend.state, initial: true) { _, state in
                    if case .ready(let url) = state {
                        appState.configureBackend(baseURL: url, desktopToken: backend.desktopToken)
                    } else {
                        appState.disconnectBackend()
                    }
                }
        }
        .defaultSize(width: 1200, height: 800)
        .defaultPosition(.center)
    }
}

private struct ContentView: View {
    @EnvironmentObject private var backend: BackendProcess
    @EnvironmentObject private var appState: AppState
    @Environment(\.openSettings) private var openSettings
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @AppStorage("notaeo.native.reduceMotion") private var reduceMotion = false

    private var motion: NativeMotionPolicy {
        NativeMotionPolicy(systemReduceMotion: systemReduceMotion, appReduceMotion: reduceMotion)
    }

    var body: some View {
        Group {
            switch backend.state {
            case .failed(let message):
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle").font(.largeTitle)
                    Text("Couldn’t start Notaeo").font(.title2)
                    Text(message).foregroundStyle(.secondary)
                    Button("Try Again") { backend.start() }
                }
            case .ready:
                if appState.isLoggedIn {
                    MainView()
                        .environmentObject(appState)
                        .transition(motion.transition)
                } else {
                    AuthView()
                        .environmentObject(appState)
                        .transition(motion.transition)
                }
            case .idle, .starting:
                StartupView()
            }
        }
        .frame(minWidth: 640, minHeight: 480)
        .font(NativeType.body)
        .tint(NativePalette.accent)
        .animation(motion.animation, value: appState.isLoggedIn)
        .transaction { transaction in
            if motion.reducesMotion {
                transaction.animation = nil
                transaction.disablesAnimations = true
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    openSettings()
                } label: {
                    Label("Settings", systemImage: "gearshape")
                }
                .help("Open Settings (⌘,)")
            }
        }
    }
}

struct StartupView: View {
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @AppStorage private var reduceMotion: Bool

    init(preferences: UserDefaults = .standard) {
        _reduceMotion = AppStorage(wrappedValue: false, "notaeo.native.reduceMotion", store: preferences)
    }

    private var motion: NativeMotionPolicy {
        NativeMotionPolicy(systemReduceMotion: systemReduceMotion, appReduceMotion: reduceMotion)
    }

    var body: some View {
        VStack(spacing: 18) {
            if motion.reducesMotion {
                NotaeoMark().frame(width: 84, height: 84)
            } else {
                TimelineView(.animation(minimumInterval: 1.0 / 30)) { context in
                    NotaeoMark().frame(width: 84, height: 84)
                        .offset(y: motion.folioLift(time: context.date.timeIntervalSinceReferenceDate))
                }
            }
            Text("Notaeo").font(NativeType.display)
            Text("Know what to study next.")
                .font(NativeType.heading).foregroundStyle(.secondary)
            HStack(spacing: 10) {
                if !motion.reducesMotion { ProgressView().controlSize(.small) }
                Text("Opening your workspace…").font(NativeType.body).foregroundStyle(.secondary)
            }
            .padding(.top, 14)
            .accessibilityElement(children: .combine)
            Text("Your sources and study tools work without AI.")
                .font(NativeType.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(NativePalette.canvas)
    }
}
