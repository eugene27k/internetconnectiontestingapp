import Foundation
import Combine

final class MonitoringSessionModel: ObservableObject {
    @Published var currentPing: Double = 0
    @Published var lastSpeed: Double? = nil
    @Published var interruptions: Int = 0
    @Published var isRunning: Bool = false
    @Published var currentSession: SessionLog? = nil

    private var pingTimer: AnyCancellable?
    private var speedTimer: AnyCancellable?

    func start(with settings: MonitoringSettings) {
        guard !isRunning else { return }
        isRunning = true
        interruptions = 0
        currentSession = SessionLog(
            targetHost: settings.targetHost,
            pingInterval: settings.pingInterval,
            speedInterval: settings.speedInterval,
            outageThreshold: settings.outageThreshold,
            speedEnabled: settings.speedEnabled
        )

        startPingLoop(settings: settings)
        if settings.speedEnabled {
            startSpeedLoop(settings: settings)
        }
    }

    func stop(sessionStore: SessionStore) {
        guard isRunning else { return }
        isRunning = false
        pingTimer?.cancel()
        speedTimer?.cancel()
        pingTimer = nil
        speedTimer = nil
        if var log = currentSession {
            log.endedAt = Date()
            log.interruptions = interruptions
            sessionStore.save(log)
        }
        currentSession = nil
    }

    private func startPingLoop(settings: MonitoringSettings) {
        pingTimer = Timer.publish(every: settings.pingInterval, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                self?.recordPingSample(settings: settings)
            }
    }

    private func recordPingSample(settings: MonitoringSettings) {
        // Replace with a real ICMP probe when integrating with a transport layer.
        let simulatedPing = Double.random(in: 15...120)
        let outage = Bool.random() && Int.random(in: 0..<settings.outageThreshold + 1) == 0

        currentPing = simulatedPing
        if outage {
            interruptions += 1
        }

        let sample = StatSample(
            timestamp: Date(),
            pingMilliseconds: simulatedPing,
            speedMbps: lastSpeed,
            outageDetected: outage
        )

        if var log = currentSession {
            log.interruptions = interruptions
            log.samples.append(sample)
            currentSession = log
        }
    }

    private func startSpeedLoop(settings: MonitoringSettings) {
        speedTimer = Timer.publish(every: settings.speedInterval, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                self?.recordSpeedSample()
            }
    }

    private func recordSpeedSample() {
        // Replace with real download/upload probes when connected to backend.
        let simulatedSpeed = Double.random(in: 20...350)
        lastSpeed = simulatedSpeed

        if var log = currentSession {
            let sample = StatSample(
                timestamp: Date(),
                pingMilliseconds: currentPing,
                speedMbps: simulatedSpeed,
                outageDetected: false
            )
            log.samples.append(sample)
            currentSession = log
        }
    }
}
