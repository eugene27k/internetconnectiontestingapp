import Foundation

final class SessionStore: ObservableObject {
    @Published private(set) var sessions: [SessionLog] = []
    private let decoder = JSONDecoder()
    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }()

    private let folderURL: URL

    init(folderURL: URL? = nil) {
        if let folderURL {
            self.folderURL = folderURL
        } else {
            self.folderURL = Self.defaultSessionsDirectory()
        }

        try? FileManager.default.createDirectory(at: self.folderURL, withIntermediateDirectories: true)
        loadSessions()
    }

    private static func defaultSessionsDirectory() -> URL {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
        let baseDirectory = appSupport ?? FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let appFolderName = Bundle.main.bundleIdentifier ?? "InternetConnectionTestingApp"
        return baseDirectory
            .appendingPathComponent(appFolderName, isDirectory: true)
            .appendingPathComponent("Sessions", isDirectory: true)
    }

    func loadSessions() {
        let files = (try? FileManager.default.contentsOfDirectory(at: folderURL, includingPropertiesForKeys: nil)) ?? []
        let logs = files.compactMap { url -> SessionLog? in
            guard url.pathExtension == "json" else { return nil }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? decoder.decode(SessionLog.self, from: data)
        }
        DispatchQueue.main.async {
            self.sessions = logs.sorted(by: { $0.startedAt > $1.startedAt })
        }
    }

    func save(_ log: SessionLog) {
        let url = folderURL.appendingPathComponent(log.filename)
        guard let data = try? encoder.encode(log) else { return }
        try? data.write(to: url, options: .atomic)
        loadSessions()
    }
}
