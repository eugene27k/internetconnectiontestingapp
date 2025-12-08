import SwiftUI

struct SessionDetailView: View {
    let log: SessionLog
    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                SessionSummaryView(log: log)
                Divider()
                VStack(alignment: .leading, spacing: 8) {
                    Text("Raw JSON")
                        .font(.headline)
                    Text(rawJSONString)
                        .font(.system(.footnote, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            .padding()
        }
        .navigationTitle(log.startedAt, format: .dateTime.month().day().hour().minute())
    }

    private var rawJSONString: String {
        guard let data = try? encoder.encode(log),
              let string = String(data: data, encoding: .utf8) else {
            return "Could not encode session log."
        }
        return string
    }
}
