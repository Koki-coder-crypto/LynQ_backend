import Foundation
import CryptoKit

// MARK: - AI Analysis Engine (calls backend / Anthropic directly)

actor LynQAI {
    static let shared = LynQAI()

    // Replace with your deployed backend URL or use Anthropic directly
    private let backendURL = URL(string: "https://api.anthropic.com/v1/messages")!
    private let apiKey: String = {
        // Load from app config / keychain in production
        Bundle.main.object(forInfoDictionaryKey: "ANTHROPIC_API_KEY") as? String ?? ""
    }()

    func analyze(content: String) async -> QRScanResult {
        let category = detectCategory(content)
        let extracted = extractData(content: content, category: category)

        // Hash URL before sending (privacy: never send raw URL)
        let safeContent = hashSensitiveData(content)

        do {
            let (safety, explanation) = try await callClaudeAPI(content: safeContent, raw: content, category: category)
            return QRScanResult(
                id: UUID(),
                content: content,
                scannedAt: Date(),
                safety: safety,
                safetyExplanation: explanation,
                category: category,
                extractedData: extracted
            )
        } catch {
            // Fallback: basic heuristic analysis when offline
            let (safety, explanation) = heuristicAnalysis(content: content)
            return QRScanResult(
                id: UUID(),
                content: content,
                scannedAt: Date(),
                safety: safety,
                safetyExplanation: explanation + " (Offline — basic analysis only)",
                category: category,
                extractedData: extracted
            )
        }
    }

    // MARK: - Claude API call

    private func callClaudeAPI(
        content: String,
        raw: String,
        category: QRScanResult.QRCategory
    ) async throws -> (QRScanResult.SafetyLevel, String) {
        let prompt = """
        Analyze this QR code content for safety. Respond with ONLY valid JSON, no other text.

        QR content: \(content)
        Category: \(category.rawValue)

        Respond with exactly this JSON structure:
        {
          "safety": "safe" | "caution" | "danger",
          "explanation": "One sentence explaining why (max 80 chars, plain language, user-friendly)"
        }

        Safety criteria:
        - "danger": phishing URL, malware link, known bad domain, credential harvesting, suspicious redirect chains
        - "caution": shortened URL (bit.ly, t.co etc), unknown domain, unusual content for category
        - "safe": known legitimate domain, benign content, standard WiFi/contact/calendar data
        """

        var request = URLRequest(url: backendURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
        request.timeoutInterval = 10

        let body: [String: Any] = [
            "model": "claude-haiku-4-5",
            "max_tokens": 150,
            "messages": [["role": "user", "content": prompt]]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        let apiResponse = try JSONDecoder().decode(AnthropicResponse.self, from: data)
        let text = apiResponse.content.first?.text ?? "{}"

        // Parse Claude's JSON response
        if let jsonData = text.data(using: .utf8),
           let parsed = try? JSONSerialization.jsonObject(with: jsonData) as? [String: String],
           let safetyStr = parsed["safety"],
           let explanation = parsed["explanation"] {
            let safety = QRScanResult.SafetyLevel(rawValue: safetyStr) ?? .caution
            return (safety, explanation)
        }

        return (.caution, "Could not analyze — treat with caution.")
    }

    // MARK: - Local helpers

    private func hashSensitiveData(_ content: String) -> String {
        guard content.lowercased().hasPrefix("http") else { return content }
        // For URLs: keep domain only, hash the path
        if let url = URL(string: content), let host = url.host {
            let path = url.path
            let pathHash = SHA256.hash(data: Data(path.utf8))
                .compactMap { String(format: "%02x", $0) }.joined().prefix(8)
            return "https://\(host)/[path:\(pathHash)]"
        }
        return content
    }

    private func detectCategory(_ content: String) -> QRScanResult.QRCategory {
        let lower = content.lowercased()
        if lower.hasPrefix("http://") || lower.hasPrefix("https://") { return .url }
        if lower.hasPrefix("wifi:") { return .wifi }
        if lower.hasPrefix("begin:vcard") { return .contact }
        if lower.hasPrefix("mailto:") { return .email }
        if lower.hasPrefix("tel:") { return .phone }
        if lower.hasPrefix("smsto:") || lower.hasPrefix("sms:") { return .sms }
        if lower.hasPrefix("begin:vevent") { return .calendar }
        return .text
    }

    private func extractData(content: String, category: QRScanResult.QRCategory) -> QRScanResult.ExtractedData? {
        var data = QRScanResult.ExtractedData()
        switch category {
        case .url:
            data.url = content
        case .wifi:
            let parts = content.components(separatedBy: ";")
            data.ssid = parts.first(where: { $0.hasPrefix("S:") })?.dropFirst(2).description
        case .email:
            data.emailAddress = content.replacingOccurrences(of: "mailto:", with: "")
        case .phone:
            data.phoneNumber = content.replacingOccurrences(of: "tel:", with: "")
        default:
            return nil
        }
        return data
    }

    private func heuristicAnalysis(content: String) -> (QRScanResult.SafetyLevel, String) {
        let lower = content.lowercased()
        let dangerPatterns = ["bit.ly", "tinyurl", "t.co", "ow.ly", "phishing", "login", "verify-account", "update-your"]
        if dangerPatterns.contains(where: { lower.contains($0) }) {
            return (.caution, "Shortened or suspicious URL — verify before opening.")
        }
        return (.safe, "No obvious threats detected in offline check.")
    }
}

// MARK: - Anthropic API response model

private struct AnthropicResponse: Decodable {
    struct Content: Decodable { let text: String }
    let content: [Content]
}
