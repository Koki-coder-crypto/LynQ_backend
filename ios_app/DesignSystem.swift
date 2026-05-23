import SwiftUI

// MARK: - Color Tokens

extension Color {
    static let lynqBG          = Color(hex: "0A0E1A")
    static let lynqSurface     = Color(hex: "131929")
    static let lynqSurfaceHigh = Color(hex: "1A2235")
    static let lynqAccent      = Color(hex: "4F8EF7")
    static let lynqSecondary   = Color(hex: "818CF8")
    static let lynqMuted       = Color(hex: "8B9CB6")
    static let lynqBorder      = Color.white.opacity(0.06)

    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:  (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:  (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:  (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default: (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(.sRGB,
                  red:   Double(r) / 255,
                  green: Double(g) / 255,
                  blue:  Double(b) / 255,
                  opacity: Double(a) / 255)
    }
}

extension QRScanResult.SafetyLevel {
    var gradientColors: [Color] {
        switch self {
        case .safe:    return [Color(hex: "2ECC71"), Color(hex: "059669")]
        case .caution: return [Color(hex: "F39C12"), Color(hex: "D97706")]
        case .danger:  return [Color(hex: "E74C3C"), Color(hex: "DC2626")]
        }
    }
}

// MARK: - Haptics

enum Haptics {
    static func impact(_ style: UIImpactFeedbackGenerator.FeedbackStyle = .medium) {
        UIImpactFeedbackGenerator(style: style).impactOccurred()
    }
    static func notification(_ type: UINotificationFeedbackGenerator.FeedbackType) {
        UINotificationFeedbackGenerator().notificationOccurred(type)
    }
    static func selection() {
        UISelectionFeedbackGenerator().selectionChanged()
    }
}

// MARK: - Gradient Button Style

struct GradientButtonStyle: ButtonStyle {
    var colors: [Color] = [Color(hex: "4F8EF7"), Color(hex: "2563EB")]
    var cornerRadius: CGFloat = 16

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.spring(response: 0.2, dampingFraction: 0.7), value: configuration.isPressed)
            .background(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .fill(LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing))
                    .shadow(color: colors.first?.opacity(configuration.isPressed ? 0.2 : 0.45) ?? .clear,
                            radius: configuration.isPressed ? 4 : 14,
                            y: configuration.isPressed ? 2 : 7)
            )
    }
}

// MARK: - Glass Card

struct GlassSurface: ViewModifier {
    var cornerRadius: CGFloat = 20
    var borderOpacity: Double = 0.06

    func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .fill(Color.lynqSurface)
                    .overlay(
                        RoundedRectangle(cornerRadius: cornerRadius)
                            .stroke(Color.white.opacity(borderOpacity), lineWidth: 1)
                    )
            )
    }
}

extension View {
    func glassSurface(cornerRadius: CGFloat = 20, borderOpacity: Double = 0.06) -> some View {
        modifier(GlassSurface(cornerRadius: cornerRadius, borderOpacity: borderOpacity))
    }
}

// MARK: - Corner Bracket Viewfinder (Canvas)

struct CornerBrackets: View {
    let size: CGFloat
    var isActive: Bool = false
    var activeColors: [Color] = [Color(hex: "4F8EF7"), Color(hex: "2ECC71")]

    var body: some View {
        Canvas { ctx, canvasSize in
            let L: CGFloat = 32
            let W: CGFloat = 3
            let h = W / 2
            let shading = GraphicsContext.Shading.color(isActive ? activeColors[0] : .white)
            let style = StrokeStyle(lineWidth: W, lineCap: .round, lineJoin: .round)

            func drawBracket(_ points: [CGPoint]) {
                var path = Path()
                path.addLines(points)
                ctx.stroke(path, with: shading, style: style)
            }

            // top-left
            drawBracket([.init(x: L, y: h), .init(x: h, y: h), .init(x: h, y: L)])
            // top-right
            drawBracket([.init(x: canvasSize.width - L, y: h),
                         .init(x: canvasSize.width - h, y: h),
                         .init(x: canvasSize.width - h, y: L)])
            // bottom-left
            drawBracket([.init(x: h, y: canvasSize.height - L),
                         .init(x: h, y: canvasSize.height - h),
                         .init(x: L, y: canvasSize.height - h)])
            // bottom-right
            drawBracket([.init(x: canvasSize.width - h, y: canvasSize.height - L),
                         .init(x: canvasSize.width - h, y: canvasSize.height - h),
                         .init(x: canvasSize.width - L, y: canvasSize.height - h)])
        }
        .frame(width: size, height: size)
    }
}
