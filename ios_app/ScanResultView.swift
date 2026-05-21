import SwiftUI

// MARK: - Result model

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
            case .safe:    return .green
            case .caution: return .orange
            case .danger:  return .red
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
        var ssid: String?           // WiFi network name
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
    @State private var showCopyConfirmation = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    safetyBadge
                    contentCard
                    if let extracted = result.extractedData { actionButtons(extracted) }
                }
                .padding()
            }
            .navigationTitle("Scan Result")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    // MARK: Components

    private var safetyBadge: some View {
        VStack(spacing: 12) {
            Image(systemName: result.safety.icon)
                .font(.system(size: 64))
                .foregroundStyle(result.safety.color)

            Text(result.safety.label)
                .font(.title2.bold())
                .foregroundStyle(result.safety.color)

            Text(result.safetyExplanation)
                .font(.body)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(result.safety.color.opacity(0.1))
        .cornerRadius(20)
    }

    private var contentCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(result.category.rawValue.capitalized, systemImage: result.category.icon)
                .font(.caption.bold())
                .foregroundStyle(.secondary)
                .textCase(.uppercase)

            Text(result.content)
                .font(.body)
                .textSelection(.enabled)
                .lineLimit(6)

            Button {
                UIPasteboard.general.string = result.content
                showCopyConfirmation = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    showCopyConfirmation = false
                }
            } label: {
                Label(showCopyConfirmation ? "Copied!" : "Copy", systemImage: showCopyConfirmation ? "checkmark" : "doc.on.doc")
                    .font(.footnote.bold())
            }
            .buttonStyle(.bordered)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(16)
    }

    @ViewBuilder
    private func actionButtons(_ data: QRScanResult.ExtractedData) -> some View {
        VStack(spacing: 12) {
            if let url = data.url, let parsed = URL(string: url) {
                Link(destination: parsed) {
                    Label("Open in Safari", systemImage: "safari.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
            }
            if let phone = data.phoneNumber, let url = URL(string: "tel://\(phone)") {
                Link(destination: url) {
                    Label("Call \(phone)", systemImage: "phone.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
            if let email = data.emailAddress, let url = URL(string: "mailto:\(email)") {
                Link(destination: url) {
                    Label("Email \(email)", systemImage: "envelope.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
        }
    }
}
