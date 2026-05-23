import SwiftUI
import CoreImage.CIFilterBuiltins

struct GeneratorView: View {
    @EnvironmentObject var store: StoreManager
    @State private var inputText = ""
    @State private var qrColor: Color = .white
    @State private var qrImage: UIImage?
    @State private var showShareSheet = false
    @State private var showPaywall = false
    @State private var generationsUsedToday = 0
    @FocusState private var inputFocused: Bool

    private let freeLimit = 5

    var body: some View {
        NavigationStack {
            ZStack {
                Color.lynqBG.ignoresSafeArea()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 14) {
                        inputCard
                        if store.isPro { colorCard }
                        generateButton
                        if !store.isPro { freeCounter }
                        if let img = qrImage {
                            qrPreview(img)
                                .transition(.scale(scale: 0.92).combined(with: .opacity))
                        }
                        Spacer(minLength: 20)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 16)
                }
            }
            .navigationTitle("Create QR")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(Color.lynqBG, for: .navigationBar)
            .sheet(isPresented: $showShareSheet) {
                if let img = qrImage { ShareSheet(items: [img]) }
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
        }
    }

    // MARK: - Input Card

    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Content", systemImage: "text.cursor")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(Color.lynqMuted)
                .textCase(.uppercase)
                .tracking(0.6)

            ZStack(alignment: .topLeading) {
                if inputText.isEmpty {
                    Text("URL, text, WiFi, contact info…")
                        .font(.system(size: 15))
                        .foregroundStyle(Color.lynqMuted.opacity(0.5))
                        .padding(.top, 8).padding(.leading, 4)
                        .allowsHitTesting(false)
                }
                TextEditor(text: $inputText)
                    .font(.system(size: 15))
                    .foregroundStyle(.white)
                    .focused($inputFocused)
                    .frame(minHeight: 80, maxHeight: 140)
                    .scrollContentBackground(.hidden)
                    .background(Color.clear)
                    .onChange(of: inputText) { _ in
                        if store.isPro && !inputText.isEmpty { generateQR() }
                    }
            }
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color.lynqSurfaceHigh)
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(
                                inputFocused ? Color.lynqAccent.opacity(0.4) : Color.white.opacity(0.06),
                                lineWidth: 1
                            )
                    )
            )
            .animation(.easeInOut(duration: 0.2), value: inputFocused)
        }
        .padding(18)
        .glassSurface(cornerRadius: 20)
    }

    // MARK: - Color Card (Pro)

    private var colorCard: some View {
        HStack {
            HStack(spacing: 10) {
                Image(systemName: "paintpalette.fill")
                    .font(.system(size: 15))
                    .foregroundStyle(Color.lynqAccent)
                Text("QR Color")
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(.white)
            }
            Spacer()
            ColorPicker("", selection: $qrColor, supportsOpacity: false)
                .labelsHidden()
                .onChange(of: qrColor) { _ in
                    if !inputText.isEmpty { generateQR() }
                }
        }
        .padding(18)
        .glassSurface(cornerRadius: 20)
    }

    // MARK: - Generate Button

    private var generateButton: some View {
        let disabled = inputText.trimmingCharacters(in: .whitespaces).isEmpty

        return Button {
            guard !disabled else { return }
            if !store.isPro && generationsUsedToday >= freeLimit { showPaywall = true; return }
            Haptics.impact(.medium)
            inputFocused = false
            withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) { generateQR() }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "qrcode")
                    .font(.system(size: 16, weight: .semibold))
                Text("Generate QR Code")
                    .font(.system(size: 16, weight: .bold))
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 18)
        }
        .buttonStyle(GradientButtonStyle())
        .disabled(disabled)
        .opacity(disabled ? 0.45 : 1.0)
        .animation(.easeInOut(duration: 0.15), value: disabled)
    }

    // MARK: - Free Counter

    private var freeCounter: some View {
        HStack(spacing: 8) {
            Image(systemName: "sparkles")
                .font(.system(size: 12))
                .foregroundStyle(Color(hex: "F39C12"))
            Text("\(freeLimit - generationsUsedToday) of \(freeLimit) free generations this month")
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(Color.lynqMuted)
            Spacer()
            Button("Upgrade") { showPaywall = true }
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.lynqAccent)
        }
        .padding(.horizontal, 16).padding(.vertical, 12)
        .background(Color.lynqSurface, in: RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.white.opacity(0.06), lineWidth: 1)
        )
    }

    // MARK: - QR Preview

    private func qrPreview(_ image: UIImage) -> some View {
        VStack(spacing: 18) {
            Text("Your QR Code")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(Color.lynqMuted)
                .textCase(.uppercase)
                .tracking(0.6)
                .frame(maxWidth: .infinity, alignment: .leading)

            Image(uiImage: image)
                .interpolation(.none)
                .resizable()
                .scaledToFit()
                .frame(width: 210, height: 210)
                .padding(20)
                .background(Color.white, in: RoundedRectangle(cornerRadius: 18))
                .shadow(color: Color.lynqAccent.opacity(0.22), radius: 24, y: 10)
                .frame(maxWidth: .infinity)

            Button {
                Haptics.impact(.light)
                showShareSheet = true
            } label: {
                Label("Share / Export", systemImage: "square.and.arrow.up")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
            }
            .buttonStyle(GradientButtonStyle())
        }
        .padding(20)
        .glassSurface(cornerRadius: 24)
    }

    // MARK: - QR Generation

    private func generateQR() {
        guard !inputText.isEmpty else { return }
        let ctx = CIContext()
        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(inputText.utf8)
        filter.correctionLevel = "M"
        guard let output = filter.outputImage else { return }
        let scaled = output.transformed(by: CGAffineTransform(scaleX: 10, y: 10))
        if let cgImg = ctx.createCGImage(scaled, from: scaled.extent) {
            qrImage = UIImage(cgImage: cgImg)
            if !store.isPro { generationsUsedToday += 1 }
        }
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}
