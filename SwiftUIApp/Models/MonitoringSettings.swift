import Foundation

final class MonitoringSettings: ObservableObject {
    @Published var targetHost: String = "1.1.1.1"
    @Published var pingInterval: Double = 2.0
    @Published var speedInterval: Double = 60.0
    @Published var outageThreshold: Int = 3
    @Published var speedEnabled: Bool = true
}
