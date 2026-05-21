import SwiftUI
import AVFoundation

// MARK: - Main Scanner Screen

struct ScannerView: View {
    @EnvironmentObject var store: StoreManager
    @EnvironmentObject var history: ScanHistory
    @State private var scannedResult: QRScanResult?
    @State private var isAnalyzing = false
    @State private var showPaywall = false
    @State private var dailyScans = 0

    private let freeDailyLimit = 20

    var body: some View {
        NavigationStack {
            ZStack {
                QRCameraView(onScan: handleScan)
                    .ignoresSafeArea()

                VStack {
                    // Top HUD
                    HStack {
                        Spacer()
                        if !store.isPro {
                            Text("\(freeDailyLimit - dailyScans) scans left today")
                                .font(.caption)
                                .padding(8)
                                .background(.ultraThinMaterial)
                                .cornerRadius(20)
                        }
                    }
                    .padding()

                    Spacer()

                    // Viewfinder guide
                    RoundedRectangle(cornerRadius: 16)
                        .strokeBorder(.white, lineWidth: 3)
                        .frame(width: 260, height: 260)

                    Spacer()

                    // Status area
                    if isAnalyzing {
                        AnalyzingView()
                    }
                }
            }
            .navigationTitle("LynQ")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $scannedResult) { result in
                ScanResultView(result: result)
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
        }
    }

    private func handleScan(_ content: String) {
        guard !isAnalyzing else { return }

        // Enforce free tier limit
        if !store.isPro && dailyScans >= freeDailyLimit {
            showPaywall = true
            return
        }

        isAnalyzing = true
        dailyScans += 1

        Task {
            let result = await LynQAI.shared.analyze(content: content)
            await MainActor.run {
                scannedResult = result
                history.add(result)
                isAnalyzing = false
            }
        }
    }
}

// MARK: - Analyzing indicator

struct AnalyzingView: View {
    @State private var dots = ""
    let timer = Timer.publish(every: 0.4, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(spacing: 8) {
            ProgressView()
                .tint(.white)
            Text("AI analyzing\(dots)")
                .foregroundColor(.white)
                .font(.subheadline)
        }
        .padding()
        .background(.ultraThinMaterial)
        .cornerRadius(16)
        .onReceive(timer) { _ in
            dots = dots.count < 3 ? dots + "." : ""
        }
    }
}

// MARK: - Camera wrapper

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
            guard let object = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
                  let content = object.stringValue,
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
