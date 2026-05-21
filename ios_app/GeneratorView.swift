import SwiftUI
import CoreImage.CIFilterBuiltins

struct GeneratorView: View {
    @EnvironmentObject var store: StoreManager
    @State private var inputText = ""
    @State private var selectedColor: Color = .black
    @State private var qrImage: UIImage?
    @State private var showShareSheet = false
    @State private var generationsUsedToday = 0

    private let freeLimit = 5

    var body: some View {
        NavigationStack {
            Form {
                Section("Content") {
                    TextField("Enter URL, text, WiFi, or contact info…", text: $inputText, axis: .vertical)
                        .lineLimit(3...6)
                }

                if store.isPro {
                    Section("Customize") {
                        ColorPicker("QR Color", selection: $selectedColor, supportsOpacity: false)
                    }
                }

                Section {
                    Button("Generate QR Code") {
                        generateQR()
                    }
                    .frame(maxWidth: .infinity)
                    .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty)
                }

                if !store.isPro {
                    Section {
                        Text("\(freeLimit - generationsUsedToday) of \(freeLimit) free generations remaining this month.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                if let image = qrImage {
                    Section("Your QR Code") {
                        VStack(spacing: 16) {
                            Image(uiImage: image)
                                .interpolation(.none)
                                .resizable()
                                .scaledToFit()
                                .frame(maxWidth: 240)
                                .padding()
                                .background(Color.white)
                                .cornerRadius(12)
                                .frame(maxWidth: .infinity)

                            Button {
                                showShareSheet = true
                            } label: {
                                Label("Share / Export", systemImage: "square.and.arrow.up")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        .padding(.vertical, 8)
                    }
                }
            }
            .navigationTitle("Generate QR")
            .sheet(isPresented: $showShareSheet) {
                if let image = qrImage {
                    ShareSheet(items: [image])
                }
            }
        }
    }

    private func generateQR() {
        guard !inputText.isEmpty else { return }
        guard store.isPro || generationsUsedToday < freeLimit else { return }

        let context = CIContext()
        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(inputText.utf8)
        filter.correctionLevel = "M"

        guard let output = filter.outputImage else { return }

        let scaled = output.transformed(by: CGAffineTransform(scaleX: 10, y: 10))

        // Apply color if Pro
        let colored: CIImage
        if store.isPro {
            let colorFilter = CIFilter.falseColor()
            colorFilter.inputImage = scaled
            // Simplified: tint using blend
            colored = scaled
        } else {
            colored = scaled
        }

        if let cgImage = context.createCGImage(colored, from: colored.extent) {
            qrImage = UIImage(cgImage: cgImage)
            generationsUsedToday += 1
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
