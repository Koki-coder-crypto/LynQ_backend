import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var store: StoreManager
    @State private var showPaywall = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if store.isPro {
                        Label("LynQ Pro — Active", systemImage: "checkmark.shield.fill")
                            .foregroundStyle(.green)
                    } else {
                        Button("Upgrade to Pro") { showPaywall = true }
                            .foregroundStyle(.blue)
                    }
                } header: { Text("Subscription") }

                Section("About") {
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                    Link("Privacy Policy", destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/privacy_policy.html")!)
                    Link("Terms of Service", destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/terms_of_service.html")!)
                    Link("Support", destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/issues")!)
                }

                Section {
                    Button("Restore Purchases") {
                        Task { await store.restorePurchases() }
                    }
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showPaywall) { PaywallView() }
        }
    }
}
