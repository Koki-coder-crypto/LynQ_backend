import SwiftUI
import AVFoundation

// MARK: - Scanner Screen

struct ScannerView: View {
    @EnvironmentObject var store: StoreManager
    @EnvironmentObject var history: ScanHistory
    @State private var scannedResult: QRScanResult?
    @State private var isAnalyzing = false
    @State private var showPaywall = false
    @State private var dailyScans = 0
    @State private var pulseScale: CGFloat = 1.0
    @State private var pulseOpacity: Double = 0.6

    private let freeDailyLimit = 20

    var body: some View {
        ZStack {
            QRCameraView(onScan: handleScan)
                .ignoresSafeArea()

            // Vignette
            RadialGradient(
                colors: [Color.clear, Color.lynqBG.opacity(0.75)],
                center: .center,
                startRadius: 130,
                endRadius: UIScreen.main.bounds.width * 0.8
            )
            .ignoresSafeArea()
            .allowsHitTesting(false)

            VStack(spacing: 0) {
                topHUD.padding(.top, 64)
                Spacer()
                viewfinderArea
                Text(isAnalyzing ? "" : "Point at any QR or barcode")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(Color.white.opacity(0.55))
                    .padding(.top, 22)
                    .animation(.easeInOut, value: isAnalyzing)
                Spacer()
                if isAnalyzing {
                    analyzingBadge
                        .padding(.bottom, 120)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
        }
        .sheet(item: $scannedResult) { result in
            ScanResultView(result: result)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $showPaywall) {
            PaywallView()
        }
        .onAppear { startPulse() }
    }

    // MARK: - Components

    private var topHUD: some View {
        HStack {
            Text("LynQ")
                .font(.system(size: 26, weight: .bold, design: .rounded))
                .foregroundStyle(
                    LinearGradient(
                        colors: [Color.lynqAccent, Color.lynqSecondary],
                        startPoint: .leading, endPoint: .trailing
                    )
                )
            Spacer()
            if store.isPro {
                HStack(spacing: 5) {
                    Image(systemName: "crown.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(Color(hex: "F59E0B"))
                    Text("Pro")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.white)
                }
                .padding(.horizontal, 12).padding(.vertical, 6)
                .background(Color(hex: "F59E0B").opacity(0.15), in: Capsule())
                .overlay(Capsule().stroke(Color(hex: "F59E0B").opacity(0.3), lineWidth: 1))
            } else {
                HStack(spacing: 5) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(Color(hex: "F39C12"))
                    Text("\(freeDailyLimit - dailyScans) left")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.white)
                }
                .padding(.horizontal, 12).padding(.vertical, 6)
                .background(.ultraThinMaterial, in: Capsule())
                .overlay(Capsule().stroke(Color.white.opacity(0.1), lineWidth: 1))
                .onTapGesture { showPaywall = true }
            }
        }
        .padding(.horizontal, 24)
    }

    private var viewfinderArea: some View {
        ZStack {
            // Pulse rings (only while analyzing)
            if isAnalyzing {
                ForEach(0..<3, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 24)
                        .stroke(Color.lynqAccent.opacity(0.12 - Double(i) * 0.03), lineWidth: 1)
                        .frame(width: 268 + CGFloat(i) * 22, height: 268 + CGFloat(i) * 22)
                        .scaleEffect(pulseScale)
                        .opacity(pulseOpacity)
                }
            }

            // Frosted inner area
            RoundedRectangle(cornerRadius: 20)
                .fill(Color.white.opacity(0.025))
                .frame(width: 260, height: 260)

            // Corner brackets
            CornerBrackets(size: 260, isActive: isAnalyzing)
        }
    }

    private var analyzingBadge: some View {
        HStack(spacing: 10) {
            ProgressView().tint(Color.lynqAccent)
            Text("AI analyzing…")
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 22).padding(.vertical, 13)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.lynqAccent.opacity(0.35), lineWidth: 1)
        )
    }

    // MARK: - Logic

    private func startPulse() {
        withAnimation(.easeInOut(duration: 1.6).repeatForever(autoreverses: true)) {
            pulseScale = 1.06
            pulseOpacity = 0.0
        }
    }

    private func handleScan(_ content: String) {
        guard !isAnalyzing else { return }

        if !store.isPro && dailyScans >= freeDailyLimit {
            Haptics.notification(.warning)
            showPaywall = true
            return
        }

        Haptics.impact(.medium)
        withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
            isAnalyzing = true
        }
        dailyScans += 1

        Task {
            let result = await LynQAI.shared.analyze(content: content)
            await MainActor.run {
                Haptics.notification(result.safety == .danger ? .error : .success)
                scannedResult = result
                history.add(result)
                withAnimation { isAnalyzing = false }
            }
        }
    }
}

// MARK: - Camera (UIViewRepresentable)

struct QRCameraView: UIViewRepresentable {
    var onScan: (String) -> Void

    func makeUIView(context: Context) -> QRCameraUIView {
        let view = QRCameraUIView()
        view.delegate = context.coordinator
        return view
    }

    func updateUIView(_ uiView: QRCameraUIView, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator(onScan: onScan) }

    class Coordinator: NSObject, AVCaptureMetadataOutputObjectsDelegate {
        var onScan: (String) -> Void
        private var lastScanned: String?
        private var lastScanTime = Date.distantPast

        init(onScan: @escaping (String) -> Void) { self.onScan = onScan }

        func metadataOutput(_ output: AVCaptureMetadataOutput,
                            didOutput metadataObjects: [AVMetadataObject],
                            from connection: AVCaptureConnection) {
            guard let obj = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
                  let content = obj.stringValue,
                  content != lastScanned || Date().timeIntervalSince(lastScanTime) > 3
            else { return }
            lastScanned = content
            lastScanTime = Date()
            DispatchQueue.main.async { self.onScan(content) }
        }
    }
}

class QRCameraUIView: UIView {
    weak var delegate: AVCaptureMetadataOutputObjectsDelegate?
    private var captureSession: AVCaptureSession?

    override func didMoveToWindow() {
        super.didMoveToWindow()
        guard window != nil else { captureSession?.stopRunning(); return }
        setupCamera()
    }

    private func setupCamera() {
        let session = AVCaptureSession()
        guard let device = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input)
        else { return }

        session.addInput(input)
        let output = AVCaptureMetadataOutput()
        session.addOutput(output)
        output.setMetadataObjectsDelegate(delegate, queue: .main)
        output.metadataObjectTypes = [.qr, .ean13, .ean8, .code128, .pdf417]

        let preview = AVCaptureVideoPreviewLayer(session: session)
        preview.frame = bounds
        preview.videoGravity = .resizeAspectFill
        layer.addSublayer(preview)
        captureSession = session

        DispatchQueue.global(qos: .userInitiated).async { session.startRunning() }
    }
}
