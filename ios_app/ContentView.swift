import SwiftUI

struct ContentView: View {
    @EnvironmentObject var store: StoreManager
    @EnvironmentObject var history: ScanHistory
    @State private var selectedTab: Tab = .scan

    enum Tab { case scan, history, generate, settings }

    var body: some View {
        TabView(selection: $selectedTab) {
            ScannerView()
                .tabItem { Label("Scan", systemImage: "qrcode.viewfinder") }
                .tag(Tab.scan)

            HistoryView()
                .tabItem { Label("History", systemImage: "clock.fill") }
                .tag(Tab.history)

            GeneratorView()
                .tabItem { Label("Generate", systemImage: "qrcode") }
                .tag(Tab.generate)

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape.fill") }
                .tag(Tab.settings)
        }
        .accentColor(.blue)
    }
}
