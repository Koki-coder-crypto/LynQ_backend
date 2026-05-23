import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var history: ScanHistory
    @EnvironmentObject var store: StoreManager
    @State private var selectedResult: QRScanResult?
    @State private var searchText = ""
    @State private var confirmClearAll = false

    var filtered: [QRScanResult] {
        let base = store.isPro ? history.scans : history.scans.filter {
            (Calendar.current.dateComponents([.day], from: $0.scannedAt, to: Date()).day ?? 0) < 7
        }
        guard !searchText.isEmpty else { return base }
        return base.filter { $0.content.localizedCaseInsensitiveContains(searchText) }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.lynqBG.ignoresSafeArea()

                if filtered.isEmpty {
                    emptyState
                } else {
                    listContent
                }
            }
            .navigationTitle("History")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(Color.lynqBG, for: .navigationBar)
            .searchable(text: $searchText, prompt: "Search scans")
            .toolbar {
                if !history.scans.isEmpty {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            Haptics.impact(.light)
                            confirmClearAll = true
                        } label: {
                            Text("Clear")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(Color(hex: "E74C3C"))
                        }
                    }
                }
            }
            .confirmationDialog("Clear all scan history?",
                                isPresented: $confirmClearAll,
                                titleVisibility: .visible) {
                Button("Clear All", role: .destructive) {
                    Haptics.notification(.warning)
                    withAnimation { history.clearAll() }
                }
            }
            .sheet(item: $selectedResult) { result in
                ScanResultView(result: result)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
        }
    }

    // MARK: - List

    private var listContent: some View {
        List {
            if !store.isPro && !history.scans.isEmpty {
                proHistoryBanner
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 2, trailing: 16))
                    .listRowSeparator(.hidden)
            }
            ForEach(Array(filtered.enumerated()), id: \.element.id) { idx, result in
                HistoryCard(result: result)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        Haptics.impact(.light)
                        selectedResult = result
                    }
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                    .listRowSeparator(.hidden)
                    .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                        Button(role: .destructive) {
                            if let i = history.scans.firstIndex(where: { $0.id == result.id }) {
                                withAnimation(.spring(response: 0.35)) {
                                    history.delete(at: IndexSet(integer: i))
                                }
                            }
                        } label: {
                            Label("Delete", systemImage: "trash.fill")
                        }
                    }
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Color.lynqBG)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 18) {
            ZStack {
                Circle()
                    .fill(Color.lynqAccent.opacity(0.08))
                    .frame(width: 100, height: 100)
                Image(systemName: "qrcode.viewfinder")
                    .font(.system(size: 40))
                    .foregroundStyle(Color.lynqMuted)
            }
            VStack(spacing: 8) {
                Text("No Scans Yet")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(.white)
                Text("Scanned QR codes will appear here.")
                    .font(.system(size: 15))
                    .foregroundStyle(Color.lynqMuted)
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Pro Banner

    private var proHistoryBanner: some View {
        HStack(spacing: 12) {
            Image(systemName: "lock.fill")
                .font(.system(size: 14))
                .foregroundStyle(Color(hex: "F39C12"))
            VStack(alignment: .leading, spacing: 2) {
                Text("Showing last 7 days")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.white)
                Text("Upgrade to Pro for 1-year history")
                    .font(.system(size: 12))
                    .foregroundStyle(Color.lynqMuted)
            }
            Spacer()
            Text("Pro")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.lynqAccent)
                .padding(.horizontal, 10).padding(.vertical, 5)
                .background(Color.lynqAccent.opacity(0.12), in: Capsule())
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.lynqSurface)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color(hex: "F39C12").opacity(0.2), lineWidth: 1)
                )
        )
    }
}

// MARK: - History Card

struct HistoryCard: View {
    let result: QRScanResult

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(result.safety.color.opacity(0.12))
                    .frame(width: 46, height: 46)
                Image(systemName: result.safety.icon)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(result.safety.color)
            }
            VStack(alignment: .leading, spacing: 4) {
                Text(result.content)
                    .lineLimit(1)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.white)
                HStack(spacing: 8) {
                    Image(systemName: result.category.icon)
                        .font(.system(size: 10))
                        .foregroundStyle(Color.lynqMuted)
                    Text(result.scannedAt, style: .relative)
                        .font(.system(size: 12))
                        .foregroundStyle(Color.lynqMuted)
                }
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(Color.lynqMuted.opacity(0.4))
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.lynqSurface)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.05), lineWidth: 1)
                )
        )
    }
}
