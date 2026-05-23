import SwiftUI

// MARK: - Result Model

struct QRScanResult: Identifiable, Codable {
    let id: UUID
    let content: String
    let scannedAt: Date
    let safety: SafetyLevel
    let safetyExplanation: String
    let category: QRCategory
    let extractedData: ExtractedData?

    enum SafetyLevel: String, Codable {
        case safe, caution, danger

        var color: Color {
            switch self {
            case .safe:    return Color(hex: "2ECC71")
            case .caution: return Color(hex: "F39C12")
            case .danger:  return Color(hex: "E74C3C")
            }
        }
        var icon: String {
            switch self {
            case .safe:    return "checkmark.shield.fill"
            case .caution: return "exclamationmark.shield.fill"
            case .danger:  return "xmark.shield.fill"
            }
        }
        var label: String {
            switch self {
            case .safe:    return "Safe"
            case .caution: return "Caution"
            case .danger:  return "Danger"
            }
        }
    }

    enum QRCategory: String, Codable {
        case url, wifi, contact, email, phone, sms, calendar, text, payment, other
        var icon: String {
            switch self {
            case .url:      return "link"
            case .wifi:     return "wifi"
            case .contact:  return "person.fill"
            case .email:    return "envelope.fill"
            case .phone:    return "phone.fill"
            case .sms:      return "message.fill"
            case .calendar: return "calendar"
            case .text:     return "doc.text.fill"
            case .payment:  return "creditcard.fill"
            case .other:    return "qrcode"
            }
        }
    }

    struct ExtractedData: Codable {
        var url: String?
        var ssid: String?
        var contactName: String?
        var phoneNumber: String?
        var emailAddress: String?
        var eventTitle: String?
    }
}

// MARK: - Result Sheet

struct ScanResultView: View {
    let result: QRScanResult
    @Environment(\.dismiss) private var dismiss
    @State private var copied = false
    @State private var appeared = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.lynqBG.ignoresSafeArea()

                // Ambient glow
                Circle()
                    .fill(result.safety.color.opacity(0.07))
                    .frame(width: 320)
                    .blur(radius: 70)
                    .offset(y: -100)
                    .allowsHitTesting(false)

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 16) {
                        safetyBadge
                        contentCard
                        if let extracted = result.extractedData {
                            actionButtons(extracted)
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 10)
                    .padding(.bottom, 40)
                }
            }
            .navigationTitle("Scan Result")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(Color.lynqAccent)
                }
            }
        }
        .onAppear {
            withAnimation(.spring(response: 0.5, dampingFraction: 0.65).delay(0.05)) {
                appeared = true
            }
        }
    }

    // MARK: - Safety Badge

    private var safetyBadge: some View {
        VStack(spacing: 18) {
            ZStack {
                Circle()
                    .fill(result.safety.color.opacity(0.1))
                    .frame(width: 96, height: 96)
                Circle()
                    .stroke(result.safety.color.opacity(0.25), lineWidth: 1.5)
                    .frame(width: 96, height: 96)
                Image(systemName: result.safety.icon)
                    .font(.system(size: 38, weight: .semibold))
                    .foregroundStyle(result.safety.color)
            }
            .scaleEffect(appeared ? 1.0 : 0.4)
            .opacity(appeared ? 1.0 : 0.0)

            VStack(spacing: 6) {
                Text(result.safety.label)
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .foregroundStyle(result.safety.color)

                Text(result.safetyExplanation)
                    .font(.system(size: 15))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Color.lynqMuted)
                    .padding(.horizontal, 12)
            }
            .opacity(appeared ? 1 : 0)
            .offset(y: appeared ? 0 : 8)
            .animation(.easeOut(duration: 0.4).delay(0.15), value: appeared)
        }
        .padding(.vertical, 28)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(result.safety.color.opacity(0.06))
                .overlay(
                    RoundedRectangle(cornerRadius: 24)
                        .stroke(result.safety.color.opacity(0.18), lineWidth: 1)
                )
        )
    }

    // MARK: - Content Card

    private var contentCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label(result.category.rawValue.uppercased(), systemImage: result.category.icon)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color.lynqAccent)
                    .padding(.horizontal, 10).padding(.vertical, 5)
                    .background(Color.lynqAccent.opacity(0.12), in: Capsule())
                    .tracking(0.5)

                Spacer()

                Button {
                    UIPasteboard.general.string = result.content
                    Haptics.impact(.light)
                    withAnimation(.spring(response: 0.3)) { copied = true }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                        withAnimation { copied = false }
                    }
                } label: {
                    HStack(spacing: 5) {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                            .font(.system(size: 12, weight: .medium))
                        Text(copied ? "Copied" : "Copy")
                            .font(.system(size: 12, weight: .semibold))
                    }
                    .foregroundStyle(copied ? Color(hex: "2ECC71") : Color.lynqAccent)
                    .padding(.horizontal, 12).padding(.vertical, 6)
                    .background(
                        (copied ? Color(hex: "2ECC71") : Color.lynqAccent).opacity(0.1),
                        in: Capsule()
                    )
                }
                .buttonStyle(.plain)
            }

            Text(result.content)
                .font(.system(size: 15))
                .foregroundStyle(.white)
                .textSelection(.enabled)
                .lineLimit(8)
                .frame(maxWidth: .infinity, alignment: .leading)

            HStack(spacing: 6) {
                Image(systemName: "clock")
                    .font(.system(size: 11))
                    .foregroundStyle(Color.lynqMuted)
                Text(result.scannedAt, style: .relative)
                    .font(.system(size: 12))
                    .foregroundStyle(Color.lynqMuted)
            }
        }
        .padding(18)
        .glassSurface(cornerRadius: 20)
    }

    // MARK: - Action Buttons

    @ViewBuilder
    private func actionButtons(_ data: QRScanResult.ExtractedData) -> some View {
        VStack(spacing: 10) {
            if let url = data.url, let parsed = URL(string: url) {
                Link(destination: parsed) {
                    Label("Open in Safari", systemImage: "safari.fill")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 17)
                }
                .buttonStyle(GradientButtonStyle())
            }
            if let phone = data.phoneNumber, let url = URL(string: "tel://\(phone)") {
                Link(destination: url) {
                    Label("Call \(phone)", systemImage: "phone.fill")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                }
                .buttonStyle(GradientButtonStyle(
                    colors: [Color(hex: "2ECC71"), Color(hex: "059669")]
                ))
            }
            if let email = data.emailAddress, let url = URL(string: "mailto:\(email)") {
                Link(destination: url) {
                    Label("Email \(email)", systemImage: "envelope.fill")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                }
                .buttonStyle(GradientButtonStyle(
                    colors: [Color(hex: "A78BFA"), Color(hex: "7C3AED")]
                ))
            }
        }
    }
}
