import Foundation

@MainActor
class ScanHistory: ObservableObject {
    @Published private(set) var scans: [QRScanResult] = []

    private let storageURL: URL = {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("lynq_history.json")
    }()

    init() { load() }

    func add(_ result: QRScanResult) {
        scans.insert(result, at: 0)
        pruneIfNeeded()
        save()
    }

    func delete(at offsets: IndexSet) {
        scans.remove(atOffsets: offsets)
        save()
    }

    func clearAll() {
        scans.removeAll()
        save()
    }

    // MARK: - Persistence

    private func load() {
        guard let data = try? Data(contentsOf: storageURL),
              let decoded = try? JSONDecoder().decode([QRScanResult].self, from: data)
        else { return }
        scans = decoded
    }

    private func save() {
        guard let data = try? JSONEncoder().encode(scans) else { return }
        try? data.write(to: storageURL, options: .atomic)
    }

    // Free tier: keep 7 days; Pro: keep 365 days (enforced via StoreManager)
    private func pruneIfNeeded(maxDays: Int = 365) {
        let cutoff = Calendar.current.date(byAdding: .day, value: -maxDays, to: Date())!
        scans = scans.filter { $0.scannedAt > cutoff }
    }
}
