import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: MonitoringSettings

    var body: some View {
        NavigationStack {
            Form {
                Section("Host") {
                    TextField("Target host", text: $settings.targetHost)
                        .textInputAutocapitalization(.never)
                        .disableAutocorrection(true)
                }

                Section("Intervals") {
                    Stepper(value: $settings.pingInterval, in: 0.5...30, step: 0.5) {
                        LabeledContent("Ping interval") {
                            Text(String(format: "%.1f s", settings.pingInterval))
                        }
                    }

                    Toggle(isOn: $settings.speedEnabled) {
                        Text("Enable speed sampling")
                    }

                    if settings.speedEnabled {
                        Stepper(value: $settings.speedInterval, in: 10...600, step: 10) {
                            LabeledContent("Speed cadence") {
                                Text(String(format: "%.0f s", settings.speedInterval))
                            }
                        }
                    }
                }

                Section("Outage detection") {
                    Stepper(value: $settings.outageThreshold, in: 1...10) {
                        LabeledContent("Failed pings to mark outage") {
                            Text("\(settings.outageThreshold)")
                        }
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
