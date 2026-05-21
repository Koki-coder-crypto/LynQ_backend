import SwiftUI
import StoreKit

@main
struct LynQApp: App {
    @StateObject private var store = StoreManager()
    @StateObject private var history = ScanHistory()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .environmentObject(history)
                .preferredColorScheme(.none)
        }
    }
}
