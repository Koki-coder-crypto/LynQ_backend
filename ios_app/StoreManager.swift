import StoreKit
import Foundation

@MainActor
class StoreManager: ObservableObject {
    @Published var isPro = false
    @Published var isBusiness = false
    @Published var products: [Product] = []

    private let productIDs = [
        "com.lynq.app.pro.monthly",
        "com.lynq.app.pro.annual",
        "com.lynq.app.lifetime",
        "com.lynq.app.business.monthly",
        "com.lynq.app.business.annual"
    ]

    init() {
        Task {
            await loadProducts()
            await updatePurchasedStatus()
            for await result in Transaction.updates {
                if case .verified(let tx) = result { await handle(tx) }
            }
        }
    }

    func loadProducts() async {
        products = (try? await Product.products(for: productIDs)) ?? []
    }

    func purchase(_ product: Product) async throws {
        let result = try await product.purchase()
        if case .success(let verification) = result,
           case .verified(let tx) = verification {
            await handle(tx)
        }
    }

    func restorePurchases() async {
        try? await AppStore.sync()
        await updatePurchasedStatus()
    }

    private func updatePurchasedStatus() async {
        for await result in Transaction.currentEntitlements {
            if case .verified(let tx) = result { await handle(tx) }
        }
    }

    private func handle(_ transaction: Transaction) async {
        let id = transaction.productID
        if transaction.revocationDate == nil {
            if id.contains("business") { isBusiness = true; isPro = true }
            else if id.contains("pro") || id.contains("lifetime") { isPro = true }
        } else {
            // Revoked — re-evaluate
            isPro = isBusiness
        }
        await transaction.finish()
    }

    // Convenience accessors for paywall
    var proMonthly: Product? { products.first { $0.id.contains("pro.monthly") } }
    var proAnnual: Product? { products.first { $0.id.contains("pro.annual") } }
    var lifetime: Product? { products.first { $0.id.contains("lifetime") } }
}
