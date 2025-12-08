import SwiftUI

struct SessionsListView: View {
    @EnvironmentObject private var sessionStore: SessionStore

    var body: some View {
        NavigationStack {
            List(sessionStore.sessions) { log in
                NavigationLink(value: log) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(log.startedAt, format: .dateTime.month().day().hour().minute())
                            .font(.headline)
                        Text(log.targetHost)
                            .foregroundStyle(.secondary)
                        Text("Samples: \(log.samples.count) · Interruptions: \(log.interruptions)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Sessions")
            .navigationDestination(for: SessionLog.self) { log in
                SessionDetailView(log: log)
            }
            .refreshable {
                sessionStore.loadSessions()
            }
        }
    }
}
