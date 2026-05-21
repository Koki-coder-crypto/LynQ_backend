import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var history: ScanHistory
    @EnvironmentObject var store: StoreManager
    @State private var selectedResult: QRScanResult?
    @State private var searchText = ""

    var filtered: [QRScanResult] {
        let base = store.isPro ? history.scans : history.scans.filter {
            Calendar.current.dateComponents([.day], from: $0.scannedAt, to: Date()).day ?? 0 < 7
        }
        guard !searchText.isEmpty else { return base }
        return base.filter { $0.content.localizedCaseInsensitiveContains(searchText) }
    }

    var body: some View {
        NavigationStack {
            Group {
                if filtered.isEmpty {
                    ContentUnavailableView("No Scans Yet", systemImage: "qrcode.viewfinder",
                        description: Text("Scanned QR codes will appear here."))
                } else {
                    List {
                        ForEach(filtered) { result in
                            HistoryRow(result: result)
                                .contentShape(Rectangle())
                                .onTapGesture { selectedResult = result }
                        }
                        .onDelete { history.delete(at: $0) }
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .navigationTitle("History")
            .searchable(text: $searchText, prompt: "Search scans")
            .toolbar {
                if !history.scans.isEmpty {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Clear All", role: .destructive) { history.clearAll() }
                    }
                }
            }
            .sheet(item: $selectedResult) { ScanResultView(result: $0) }
        }
    }
}

struct HistoryRow: View {
    let result: QRScanResult

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: result.safety.icon)
                .foregroundStyle(result.safety.color)
                .font(.title2)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 2) {
                Text(result.content)
                    .lineLimit(1)
                    .font(.subheadline)
                Text(result.scannedAt, style: .relative)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Image(systemName: result.category.icon)
                .foregroundStyle(.tertiary)
                .font(.caption)
        }
        .padding(.vertical, 4)
    }
}
