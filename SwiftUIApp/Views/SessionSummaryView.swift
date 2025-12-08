import SwiftUI

struct SessionSummaryView: View {
    let log: SessionLog

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Session Summary")
                .font(.headline)
            ForEach(log.summaryLines, id: \.self) { line in
                Label(line, systemImage: "dot.radiowaves.left.and.right")
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
