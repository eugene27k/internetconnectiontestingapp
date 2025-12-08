import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var monitor: MonitoringSessionModel
    @EnvironmentObject private var settings: MonitoringSettings
    @EnvironmentObject private var sessionStore: SessionStore

    var body: some View {
        TabView {
            NavigationStack {
                VStack(spacing: 16) {
                    sessionControls
                    liveStats
                    Spacer()
                }
                .padding()
                .navigationTitle("Connection Monitor")
            }
            .tabItem { Label("Monitor", systemImage: "wifi") }

            SessionsListView()
                .tabItem { Label("Sessions", systemImage: "tray.full") }

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
    }

    private var sessionControls: some View {
        HStack(spacing: 12) {
            Button(action: {
                monitor.start(with: settings)
            }) {
                Label("Start", systemImage: "play.fill")
                    .padding()
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
            .disabled(monitor.isRunning)

            Button(action: {
                monitor.stop(sessionStore: sessionStore)
            }) {
                Label("Stop", systemImage: "stop.fill")
                    .padding()
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .tint(.red)
            .disabled(!monitor.isRunning)
        }
    }

    private var liveStats: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Live Stats")
                .font(.headline)
            Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 10) {
                GridRow {
                    Label("Current Ping", systemImage: "timer")
                    Text("\(Int(monitor.currentPing)) ms")
                        .font(.title3)
                        .bold()
                }
                GridRow {
                    Label("Last Speed", systemImage: "gauge")
                    Text(speedText)
                        .font(.title3)
                        .bold()
                }
                GridRow {
                    Label("Interruptions", systemImage: "exclamationmark.triangle")
                    Text("\(monitor.interruptions)")
                        .font(.title3)
                        .bold()
                        .foregroundStyle(monitor.interruptions > 0 ? .orange : .secondary)
                }
            }
            if monitor.isRunning, let session = monitor.currentSession {
                SessionSummaryView(log: session)
                    .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var speedText: String {
        if let speed = monitor.lastSpeed {
            return String(format: "%.1f Mbps", speed)
        }
        return settings.speedEnabled ? "Waiting…" : "Disabled"
    }
}
