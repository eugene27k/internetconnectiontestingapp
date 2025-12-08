import Foundation

struct StatSample: Codable, Identifiable {
    let id = UUID()
    let timestamp: Date
    let pingMilliseconds: Double
    let speedMbps: Double?
    let outageDetected: Bool
}

struct SessionLog: Codable, Identifiable {
    let id: UUID
    var startedAt: Date
    var endedAt: Date?
    var targetHost: String
    var pingInterval: Double
    var speedInterval: Double
    var outageThreshold: Int
    var speedEnabled: Bool
    var interruptions: Int
    var samples: [StatSample]
    var notes: String?

    init(id: UUID = UUID(),
         startedAt: Date = Date(),
         endedAt: Date? = nil,
         targetHost: String,
         pingInterval: Double,
         speedInterval: Double,
         outageThreshold: Int,
         speedEnabled: Bool,
         interruptions: Int = 0,
         samples: [StatSample] = [],
         notes: String? = nil) {
        self.id = id
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.targetHost = targetHost
        self.pingInterval = pingInterval
        self.speedInterval = speedInterval
        self.outageThreshold = outageThreshold
        self.speedEnabled = speedEnabled
        self.interruptions = interruptions
        self.samples = samples
        self.notes = notes
    }
}

extension SessionLog {
    var filename: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions.insert(.withInternetDateTime)
        return "session_\(formatter.string(from: startedAt)).json"
    }

    var summaryLines: [String] {
        let duration: TimeInterval
        if let endedAt {
            duration = endedAt.timeIntervalSince(startedAt)
        } else {
            duration = Date().timeIntervalSince(startedAt)
        }

        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.hour, .minute, .second]
        formatter.unitsStyle = .abbreviated

        let durationText = formatter.string(from: duration) ?? "--"
        let pingText = String(format: "%.1fs", pingInterval)
        let speedText = speedEnabled ? String(format: "%.0fs", speedInterval) : "Disabled"

        return [
            "Host: \(targetHost)",
            "Duration: \(durationText)",
            "Ping interval: \(pingText)",
            "Speed cadence: \(speedText)",
            "Outage threshold: \(outageThreshold)",
            "Interruptions: \(interruptions)",
            "Samples: \(samples.count)"
        ]
    }
}
