import SwiftUI
import StoreKit

struct PaywallView: View {
    @EnvironmentObject var store: StoreManager
    @Environment(\.dismiss) private var dismiss
    @State private var selectedPlan: String = "com.lynq.app.pro.annual"
    @State private var isPurchasing = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    header
                    featureList
                    planPicker
                    purchaseButton
                    if let error = errorMessage {
                        Text(error).foregroundStyle(.red).font(.caption)
                    }
                    legalLinks
                }
                .padding()
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    // MARK: - Sections

    private var header: some View {
        VStack(spacing: 8) {
            Image(systemName: "shield.checkered")
                .font(.system(size: 56))
                .foregroundStyle(.blue)
            Text("LynQ Pro")
                .font(.title.bold())
            Text("Unlimited AI scans. Full protection.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top)
    }

    private var featureList: some View {
        VStack(alignment: .leading, spacing: 14) {
            FeatureRow(icon: "infinity", color: .blue, text: "Unlimited AI-powered scans per day")
            FeatureRow(icon: "shield.fill", color: .green, text: "Priority phishing & quishing detection")
            FeatureRow(icon: "qrcode", color: .purple, text: "Advanced QR customization + logo embed")
            FeatureRow(icon: "clock.fill", color: .orange, text: "1-year scan history (vs. 7 days free)")
            FeatureRow(icon: "icloud.fill", color: .cyan, text: "iCloud sync across all your Apple devices")
            FeatureRow(icon: "nosign", color: .red, text: "No ads, ever")
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(16)
    }

    private var planPicker: some View {
        VStack(spacing: 12) {
            if let annual = store.proAnnual {
                PlanCard(
                    title: "Annual",
                    price: annual.displayPrice + " / year",
                    badge: "Best Value — Save 42%",
                    selected: selectedPlan == annual.id
                ) { selectedPlan = annual.id }
            }
            if let monthly = store.proMonthly {
                PlanCard(
                    title: "Monthly",
                    price: monthly.displayPrice + " / month",
                    badge: nil,
                    selected: selectedPlan == monthly.id
                ) { selectedPlan = monthly.id }
            }
            if let lifetime = store.lifetime {
                PlanCard(
                    title: "Lifetime",
                    price: lifetime.displayPrice + " one-time",
                    badge: "Pay Once, Keep Forever",
                    selected: selectedPlan == lifetime.id
                ) { selectedPlan = lifetime.id }
            }
        }
    }

    private var purchaseButton: some View {
        VStack(spacing: 12) {
            Button {
                Task { await startPurchase() }
            } label: {
                Group {
                    if isPurchasing {
                        ProgressView().tint(.white)
                    } else {
                        Text(selectedPlan.contains("annual") ? "Try Free for 7 Days" : "Get LynQ Pro")
                            .font(.headline)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(.blue)
                .foregroundColor(.white)
                .cornerRadius(14)
            }
            .disabled(isPurchasing)

            Button("Restore Purchases") {
                Task { await store.restorePurchases() }
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
        }
    }

    private var legalLinks: some View {
        VStack(spacing: 4) {
            Text("Subscriptions auto-renew. Cancel anytime in Apple ID settings.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
            HStack(spacing: 16) {
                Link("Privacy Policy", destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/privacy_policy.html")!)
                Link("Terms of Use", destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/terms_of_service.html")!)
            }
            .font(.caption2)
        }
    }

    // MARK: - Purchase

    private func startPurchase() async {
        guard let product = store.products.first(where: { $0.id == selectedPlan }) else { return }
        isPurchasing = true
        errorMessage = nil
        do {
            try await store.purchase(product)
            dismiss()
        } catch {
            errorMessage = "Purchase failed: \(error.localizedDescription)"
        }
        isPurchasing = false
    }
}

// MARK: - Subviews

struct FeatureRow: View {
    let icon: String
    let color: Color
    let text: String

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 24)
            Text(text)
                .font(.subheadline)
        }
    }
}

struct PlanCard: View {
    let title: String
    let price: String
    let badge: String?
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.headline)
                    Text(price).font(.subheadline).foregroundStyle(.secondary)
                    if let badge {
                        Text(badge)
                            .font(.caption.bold())
                            .foregroundStyle(.green)
                    }
                }
                Spacer()
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? .blue : .secondary)
                    .font(.title3)
            }
            .padding()
            .background(selected ? Color.blue.opacity(0.08) : Color(.secondarySystemBackground))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(selected ? Color.blue : Color.clear, lineWidth: 2))
            .cornerRadius(14)
        }
        .buttonStyle(.plain)
    }
}
