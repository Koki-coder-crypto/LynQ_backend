import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var store: StoreManager
    @State private var showPaywall = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.lynqBG.ignoresSafeArea()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 14) {
                        subscriptionCard
                        aboutCard
                        supportCard
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 16)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(Color.lynqBG, for: .navigationBar)
            .sheet(isPresented: $showPaywall) { PaywallView() }
        }
    }

    // MARK: - Subscription Card

    private var subscriptionCard: some View {
        VStack(spacing: 0) {
            sectionHeader("Subscription", icon: "crown.fill", iconColor: Color(hex: "F59E0B"))
            Divider().background(Color.white.opacity(0.05))
            if store.isPro {
                settingsRow(icon: "checkmark.shield.fill", iconBG: Color(hex: "2ECC71").opacity(0.15),
                            iconColor: Color(hex: "2ECC71"),
                            title: "LynQ Pro — Active", subtitle: "All features unlocked")
            } else {
                Button { showPaywall = true } label: {
                    settingsRow(icon: "arrow.up.circle.fill", iconBG: Color.lynqAccent.opacity(0.15),
                                iconColor: Color.lynqAccent,
                                title: "Upgrade to Pro", subtitle: "Unlimited AI scans & more",
                                trailing: {
                                    AnyView(
                                        Text("View Plans")
                                            .font(.system(size: 13, weight: .semibold))
                                            .foregroundStyle(Color.lynqAccent)
                                    )
                                })
                }
                .buttonStyle(.plain)
                Divider().background(Color.white.opacity(0.05)).padding(.leading, 62)
                Button { Task { await store.restorePurchases() } } label: {
                    settingsRow(icon: "arrow.clockwise.circle.fill", iconBG: Color.lynqMuted.opacity(0.15),
                                iconColor: Color.lynqMuted,
                                title: "Restore Purchases", subtitle: nil)
                }
                .buttonStyle(.plain)
            }
        }
        .glassSurface(cornerRadius: 20)
    }

    // MARK: - About Card

    private var aboutCard: some View {
        VStack(spacing: 0) {
            sectionHeader("About", icon: "info.circle.fill", iconColor: Color.lynqAccent)
            Divider().background(Color.white.opacity(0.05))

            settingsRow(icon: "tag.fill", iconBG: Color.lynqSecondary.opacity(0.15),
                        iconColor: Color.lynqSecondary,
                        title: "Version",
                        subtitle: nil,
                        trailing: {
                            AnyView(
                                Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                                    .font(.system(size: 14))
                                    .foregroundStyle(Color.lynqMuted)
                            )
                        })

            Divider().background(Color.white.opacity(0.05)).padding(.leading, 62)

            Link(destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/privacy_policy.html")!) {
                settingsRow(icon: "hand.raised.fill", iconBG: Color(hex: "34D399").opacity(0.15),
                            iconColor: Color(hex: "34D399"),
                            title: "Privacy Policy", subtitle: nil,
                            trailing: { AnyView(chevron) })
            }
            .buttonStyle(.plain)

            Divider().background(Color.white.opacity(0.05)).padding(.leading, 62)

            Link(destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/blob/master/app_store/terms_of_service.html")!) {
                settingsRow(icon: "doc.text.fill", iconBG: Color(hex: "A78BFA").opacity(0.15),
                            iconColor: Color(hex: "A78BFA"),
                            title: "Terms of Service", subtitle: nil,
                            trailing: { AnyView(chevron) })
            }
            .buttonStyle(.plain)
        }
        .glassSurface(cornerRadius: 20)
    }

    // MARK: - Support Card

    private var supportCard: some View {
        VStack(spacing: 0) {
            sectionHeader("Support", icon: "bubble.left.fill", iconColor: Color(hex: "38BDF8"))
            Divider().background(Color.white.opacity(0.05))

            Link(destination: URL(string: "https://github.com/Koki-coder-crypto/LynQ_backend/issues")!) {
                settingsRow(icon: "questionmark.circle.fill", iconBG: Color(hex: "38BDF8").opacity(0.15),
                            iconColor: Color(hex: "38BDF8"),
                            title: "Get Help", subtitle: "Report a bug or ask a question",
                            trailing: { AnyView(chevron) })
            }
            .buttonStyle(.plain)
        }
        .glassSurface(cornerRadius: 20)
    }

    // MARK: - Helpers

    private func sectionHeader(_ title: String, icon: String, iconColor: Color) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(iconColor)
            Text(title)
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.lynqMuted)
                .textCase(.uppercase)
                .tracking(0.5)
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func settingsRow(icon: String,
                              iconBG: Color,
                              iconColor: Color,
                              title: String,
                              subtitle: String?,
                              trailing: (() -> AnyView)? = nil) -> some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 9)
                    .fill(iconBG)
                    .frame(width: 36, height: 36)
                Image(systemName: icon)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(iconColor)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(.white)
                if let sub = subtitle {
                    Text(sub)
                        .font(.system(size: 12))
                        .foregroundStyle(Color.lynqMuted)
                }
            }
            Spacer()
            trailing?()
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .contentShape(Rectangle())
    }

    private var chevron: some View {
        Image(systemName: "chevron.right")
            .font(.system(size: 12, weight: .medium))
            .foregroundStyle(Color.lynqMuted.opacity(0.4))
    }
}
