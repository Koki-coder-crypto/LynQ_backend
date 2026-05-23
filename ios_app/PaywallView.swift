import SwiftUI
import StoreKit

struct PaywallView: View {
    @EnvironmentObject var store: StoreManager
    @Environment(\.dismiss) private var dismiss
    @State private var selectedPlan: String = "com.lynq.app.pro.annual"
    @State private var isPurchasing = false
    @State private var errorMessage: String?
    @State private var appeared = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.lynqBG.ignoresSafeArea()
                heroGlow

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 0) {
                        heroSection.padding(.bottom, 28)
                        featureList.padding(.horizontal, 20).padding(.bottom, 18)
                        planPicker.padding(.horizontal, 20).padding(.bottom, 20)
                        purchaseSection.padding(.horizontal, 20).padding(.bottom, 14)
                        legalSection.padding(.bottom, 40)
                    }
                }
            }
            .toolbarBackground(.clear, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 22))
                            .foregroundStyle(Color.lynqMuted)
                            .symbolRenderingMode(.hierarchical)
                    }
                }
            }
        }
        .onAppear {
            withAnimation(.spring(response: 0.6, dampingFraction: 0.8)) { appeared = true }
        }
    }

    // MARK: - Background Glow

    private var heroGlow: some View {
        ZStack {
            Ellipse()
                .fill(Color.lynqAccent.opacity(0.1))
                .frame(width: 300, height: 220)
                .blur(radius: 64)
                .offset(x: -50, y: -240)
            Ellipse()
                .fill(Color.lynqSecondary.opacity(0.07))
                .frame(width: 220, height: 180)
                .blur(radius: 50)
                .offset(x: 110, y: -180)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .ignoresSafeArea()
        .allowsHitTesting(false)
    }

    // MARK: - Hero

    private var heroSection: some View {
        VStack(spacing: 18) {
            ZStack {
                Circle().fill(Color.lynqAccent.opacity(0.12)).frame(width: 104, height: 104)
                Circle().stroke(Color.lynqAccent.opacity(0.3), lineWidth: 1.5).frame(width: 104, height: 104)
                Image(systemName: "shield.checkered")
                    .font(.system(size: 44, weight: .semibold))
                    .foregroundStyle(
                        LinearGradient(colors: [Color.lynqAccent, Color.lynqSecondary],
                                       startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
            }
            .scaleEffect(appeared ? 1.0 : 0.5)
            .animation(.spring(response: 0.5, dampingFraction: 0.65).delay(0.05), value: appeared)

            VStack(spacing: 8) {
                Text("LynQ Pro")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundStyle(
                        LinearGradient(colors: [.white, Color(hex: "B0BDD4")],
                                       startPoint: .top, endPoint: .bottom)
                    )
                Text("Unlimited AI Protection")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Color.lynqMuted)
            }
            .opacity(appeared ? 1 : 0)
            .offset(y: appeared ? 0 : 10)
            .animation(.easeOut(duration: 0.4).delay(0.2), value: appeared)
        }
        .padding(.top, 28)
    }

    // MARK: - Feature List

    private let features: [(icon: String, color: Color, title: String, detail: String)] = [
        ("infinity",    Color(hex: "4F8EF7"), "Unlimited AI scans",        "No daily limits"),
        ("shield.fill", Color(hex: "2ECC71"), "Priority threat detection", "Phishing & quishing"),
        ("qrcode",      Color(hex: "A78BFA"), "Custom QR generation",      "Colors, logos, styles"),
        ("clock.fill",  Color(hex: "F39C12"), "1-year scan history",       "vs. 7 days on free"),
        ("icloud.fill", Color(hex: "38BDF8"), "iCloud sync",               "All Apple devices"),
        ("nosign",      Color(hex: "E74C3C"), "Zero ads",                  "Always clean"),
    ]

    private var featureList: some View {
        VStack(spacing: 12) {
            ForEach(Array(features.enumerated()), id: \.offset) { i, feat in
                ProFeatureRow(icon: feat.icon, color: feat.color, title: feat.title, detail: feat.detail)
                    .opacity(appeared ? 1 : 0)
                    .offset(x: appeared ? 0 : -18)
                    .animation(.easeOut(duration: 0.35).delay(0.1 + Double(i) * 0.055), value: appeared)
            }
        }
        .padding(18)
        .glassSurface(cornerRadius: 24)
    }

    // MARK: - Plan Picker

    private var planPicker: some View {
        VStack(spacing: 10) {
            if let p = store.proAnnual {
                ProPlanCard(
                    title: "Annual", displayPrice: p.displayPrice, period: "/ year",
                    badge: "Best Value · Save 42%", badgeColor: Color(hex: "2ECC71"),
                    trialNote: "7-day free trial",
                    selected: selectedPlan == p.id
                ) { Haptics.selection(); withAnimation(.spring(response: 0.3)) { selectedPlan = p.id } }
            }
            if let p = store.proMonthly {
                ProPlanCard(
                    title: "Monthly", displayPrice: p.displayPrice, period: "/ month",
                    badge: nil, badgeColor: .clear, trialNote: nil,
                    selected: selectedPlan == p.id
                ) { Haptics.selection(); withAnimation(.spring(response: 0.3)) { selectedPlan = p.id } }
            }
            if let p = store.lifetime {
                ProPlanCard(
                    title: "Lifetime", displayPrice: p.displayPrice, period: "one-time",
                    badge: "Pay Once, Keep Forever", badgeColor: Color(hex: "F59E0B"),
                    trialNote: nil,
                    selected: selectedPlan == p.id
                ) { Haptics.selection(); withAnimation(.spring(response: 0.3)) { selectedPlan = p.id } }
            }
        }
    }

    // MARK: - Purchase

    private var purchaseSection: some View {
        VStack(spacing: 14) {
            Button { Task { await startPurchase() } } label: {
                ZStack {
                    if isPurchasing {
                        ProgressView().tint(.white)
                    } else {
                        HStack(spacing: 8) {
                            Text(selectedPlan.contains("annual") ? "Start Free Trial" : "Get LynQ Pro")
                                .font(.system(size: 17, weight: .bold))
                            Image(systemName: "arrow.right")
                                .font(.system(size: 14, weight: .semibold))
                        }
                        .foregroundStyle(.white)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 18)
            }
            .buttonStyle(GradientButtonStyle())
            .disabled(isPurchasing)

            if let err = errorMessage {
                Text(err)
                    .font(.system(size: 13))
                    .foregroundStyle(Color(hex: "E74C3C"))
                    .multilineTextAlignment(.center)
            }

            Button("Restore Purchases") { Task { await store.restorePurchases() } }
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(Color.lynqMuted)
        }
    }

    private var legalSection: some View {
        VStack(spacing: 8) {
            Text("Subscriptions auto-renew. Cancel anytime in Apple ID settings.")
                .font(.system(size: 11))
                .foregroundStyle(Color.lynqMuted.opacity(0.5))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            HStack(spacing: 20) {
                Link("Privacy Policy",
                     destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/privacy_policy.html")!)
                Link("Terms of Use",
                     destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/terms_of_service.html")!)
            }
            .font(.system(size: 12, weight: .medium))
            .foregroundStyle(Color.lynqAccent.opacity(0.65))
        }
    }

    // MARK: - Purchase Logic

    private func startPurchase() async {
        guard let product = store.products.first(where: { $0.id == selectedPlan }) else { return }
        isPurchasing = true
        errorMessage = nil
        Haptics.impact(.medium)
        do {
            try await store.purchase(product)
            Haptics.notification(.success)
            dismiss()
        } catch {
            Haptics.notification(.error)
            errorMessage = "Purchase failed. Please try again."
        }
        isPurchasing = false
    }
}

// MARK: - Subviews

struct ProFeatureRow: View {
    let icon: String
    let color: Color
    let title: String
    let detail: String

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(color.opacity(0.15))
                    .frame(width: 40, height: 40)
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(color)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.white)
                Text(detail)
                    .font(.system(size: 12))
                    .foregroundStyle(Color.lynqMuted)
            }
            Spacer()
            Image(systemName: "checkmark")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(color)
        }
    }
}

struct ProPlanCard: View {
    let title: String
    let displayPrice: String
    let period: String
    let badge: String?
    let badgeColor: Color
    let trialNote: String?
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 8) {
                        Text(title)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.white)
                        if let badge {
                            Text(badge)
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(badgeColor)
                                .padding(.horizontal, 8).padding(.vertical, 3)
                                .background(badgeColor.opacity(0.12), in: Capsule())
                        }
                    }
                    HStack(alignment: .lastTextBaseline, spacing: 4) {
                        Text(displayPrice)
                            .font(.system(size: 22, weight: .bold, design: .rounded))
                            .foregroundStyle(selected ? Color.lynqAccent : .white)
                        Text(period)
                            .font(.system(size: 13))
                            .foregroundStyle(Color.lynqMuted)
                    }
                    if let note = trialNote {
                        Text(note)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color(hex: "2ECC71"))
                    }
                }
                Spacer()
                ZStack {
                    Circle()
                        .stroke(selected ? Color.lynqAccent : Color.white.opacity(0.2), lineWidth: 2)
                        .frame(width: 22, height: 22)
                    if selected {
                        Circle()
                            .fill(Color.lynqAccent)
                            .frame(width: 12, height: 12)
                    }
                }
            }
            .padding(18)
            .background(
                RoundedRectangle(cornerRadius: 18)
                    .fill(selected ? Color.lynqAccent.opacity(0.07) : Color.lynqSurface)
                    .overlay(
                        RoundedRectangle(cornerRadius: 18)
                            .stroke(
                                selected ? Color.lynqAccent.opacity(0.5) : Color.white.opacity(0.06),
                                lineWidth: selected ? 1.5 : 1
                            )
                    )
            )
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.3, dampingFraction: 0.75), value: selected)
    }
}
