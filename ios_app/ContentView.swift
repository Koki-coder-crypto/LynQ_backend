import SwiftUI

struct ContentView: View {
    @EnvironmentObject var store: StoreManager
    @EnvironmentObject var history: ScanHistory
    @State private var selectedTab: Tab = .scan

    enum Tab: Int, CaseIterable {
        case scan, history, generate, settings

        var icon: String {
            switch self {
            case .scan:     return "qrcode.viewfinder"
            case .history:  return "clock.fill"
            case .generate: return "qrcode"
            case .settings: return "gearshape.fill"
            }
        }

        var label: String {
            switch self {
            case .scan:     return "Scan"
            case .history:  return "History"
            case .generate: return "Create"
            case .settings: return "Settings"
            }
        }

        var tint: Color {
            switch self {
            case .scan:     return Color(hex: "4F8EF7")
            case .history:  return Color(hex: "A78BFA")
            case .generate: return Color(hex: "34D399")
            case .settings: return Color(hex: "8B9CB6")
            }
        }
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            Color.lynqBG.ignoresSafeArea()

            Group {
                switch selectedTab {
                case .scan:
                    ScannerView()
                case .history:
                    HistoryView()
                        .safeAreaInset(edge: .bottom) { Color.clear.frame(height: 82) }
                case .generate:
                    GeneratorView()
                        .safeAreaInset(edge: .bottom) { Color.clear.frame(height: 82) }
                case .settings:
                    SettingsView()
                        .safeAreaInset(edge: .bottom) { Color.clear.frame(height: 82) }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            customTabBar
        }
        .ignoresSafeArea(edges: .bottom)
        .preferredColorScheme(.dark)
    }

    // MARK: - Custom Tab Bar

    private var customTabBar: some View {
        HStack(spacing: 0) {
            ForEach(Tab.allCases, id: \.self) { tab in
                tabItem(tab)
            }
        }
        .padding(.top, 10)
        .padding(.bottom, 28)
        .background(
            ZStack {
                Rectangle()
                    .fill(.ultraThinMaterial)
                Rectangle()
                    .fill(
                        LinearGradient(
                            colors: [Color.white.opacity(0.05), Color.clear],
                            startPoint: .top, endPoint: .bottom
                        )
                    )
                Rectangle()
                    .frame(height: 0.5)
                    .foregroundStyle(Color.white.opacity(0.1))
                    .frame(maxHeight: .infinity, alignment: .top)
            }
        )
        .ignoresSafeArea(edges: .bottom)
    }

    private func tabItem(_ tab: Tab) -> some View {
        Button {
            if selectedTab != tab {
                Haptics.impact(.light)
                withAnimation(.spring(response: 0.35, dampingFraction: 0.75)) {
                    selectedTab = tab
                }
            }
        } label: {
            VStack(spacing: 4) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(tab.tint.opacity(selectedTab == tab ? 0.15 : 0))
                        .frame(width: 52, height: 34)
                    Image(systemName: tab.icon)
                        .font(.system(size: 20, weight: selectedTab == tab ? .semibold : .regular))
                        .foregroundStyle(selectedTab == tab ? tab.tint : Color.lynqMuted)
                        .scaleEffect(selectedTab == tab ? 1.08 : 1.0)
                }
                .frame(width: 52, height: 34)
                .animation(.spring(response: 0.35, dampingFraction: 0.75), value: selectedTab)

                Text(tab.label)
                    .font(.system(size: 10, weight: selectedTab == tab ? .semibold : .regular))
                    .foregroundStyle(selectedTab == tab ? tab.tint : Color.lynqMuted)
            }
        }
        .frame(maxWidth: .infinity)
        .buttonStyle(.plain)
    }
}
