import SwiftUI

@main
struct InternetConnectionTestingApp: App {
    @StateObject private var monitor = MonitoringSessionModel()
    @StateObject private var settings = MonitoringSettings()
    @StateObject private var sessionStore = SessionStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(monitor)
                .environmentObject(settings)
                .environmentObject(sessionStore)
        }
    }
}
