# LynQ App Store Submission Checklist

## STATUS KEY
- [x] Done / created in this session
- [ ] Requires manual action from developer

---

## 1. Apple Developer Account Setup
- [ ] Log in to App Store Connect: https://appstoreconnect.apple.com
- [ ] Create a new App: Apps → + → New App
  - Platform: iOS
  - Name: `LynQ - AI QR Scanner & Safety`
  - Bundle ID: `com.lynq.app`
  - SKU: `LYNQ001`
  - Language: English (U.S.)
- [ ] Apply for Apple Small Business Program (15% instead of 30%): https://developer.apple.com/app-store/small-business-program/

---

## 2. App Store Metadata (copy from app_store/ files)
- [x] App Name: `LynQ - AI QR Scanner & Safety` ← metadata.json
- [x] Subtitle: `Scan Safe. Know More. Go Fast.` ← metadata.json
- [x] Description (EN): ← description_en.txt
- [x] Description (JA): ← description_ja.txt
- [x] Keywords (EN, 100 chars): ← metadata.json
- [x] Keywords (JA, 100 chars): ← metadata.json
- [x] What's New (EN): ← whats_new_en.txt
- [x] What's New (JA): ← whats_new_ja.txt
- [x] Support URL: https://github.com/Koki-coder-crypto/LynQ_backend/issues
- [x] Privacy Policy URL: (host privacy_policy.html and paste URL here)

---

## 3. Host Privacy Policy & Terms
- [ ] **ACTION REQUIRED:** Host privacy_policy.html on a public URL
  - Option A: Enable GitHub Pages on the repo (free)
    → Settings → Pages → Source: Deploy from branch (master / app_store/)
    → URL will be: https://koki-coder-crypto.github.io/LynQ_backend/app_store/privacy_policy.html
  - Option B: Paste content into a Notion public page
- [ ] Paste the public Privacy Policy URL into App Store Connect
- [x] Terms of Service: ← terms_of_service.html (host same way)

---

## 4. In-App Purchases (IAP)
Set up in App Store Connect → Your App → In-App Purchases:

### Subscription Groups
- [ ] Create group: "LynQ Pro"
  - [ ] Add: `com.lynq.app.pro.monthly` ($4.99/mo, 7-day trial)
  - [ ] Add: `com.lynq.app.pro.annual` ($34.99/yr, 7-day trial)
- [ ] Create group: "LynQ Business"
  - [ ] Add: `com.lynq.app.business.monthly` ($14.99/mo, 14-day trial)
  - [ ] Add: `com.lynq.app.business.annual` ($99.99/yr, 14-day trial)

### One-Time Purchase
- [ ] Add: `com.lynq.app.lifetime` (Non-Consumable, $49.99)

Full specs: ← iap_products.json

---

## 5. App Icon
- [ ] Create icon at 1024×1024px PNG (no alpha, no rounded corners — Apple applies them)
  - Suggested concept: Shield + QR code motif on dark blue background
  - Tool: Figma, Sketch, or Canva
  - Required sizes: Xcode generates all from 1024px source

---

## 6. Screenshots (SKIPPED per user request)
Required sets:
- [ ] iPhone 6.9" (1320×2868 or 1290×2796) — 3 minimum, 10 max
- [ ] iPhone 6.5" (1242×2688) — for older devices
- [ ] iPad Pro 13" — required if iPad supported

---

## 7. Build & Upload
- [ ] Open ios_app/ in Xcode (create .xcodeproj: File → New → Project → iOS → App)
      Copy all .swift files into the Xcode project
- [ ] Set Bundle ID to `com.lynq.app`
- [ ] Set Team to your Apple Developer account
- [ ] Add `ANTHROPIC_API_KEY` to xcconfig (never commit the key)
- [ ] Set minimum deployment target: iOS 17.0
- [ ] Add capabilities in Xcode: In-App Purchase, Camera
- [ ] Product → Archive
- [ ] Window → Organizer → Distribute App → App Store Connect → Upload

---

## 8. App Review Information
- [x] Review notes: ← review_notes.txt
  (Paste into App Store Connect → App Review Information → Notes)
- [ ] Demo account: Not required (no login in app)
- [ ] Contact: kouki_1203@icloud.com

---

## 9. Pricing & Availability
- [ ] Price: Free (base app)
- [ ] Availability: All territories (or Japan + US to start)
- [ ] Release: Manual release (so you can approve after review)

---

## 10. Pre-Launch
- [ ] TestFlight beta with 5-10 friends (catch crashes before submission)
- [ ] Answer Apple's Privacy Questionnaire in App Store Connect:
  - Data collected: None (no account required)
  - Data linked to user: None
  - Data used to track: None
  → Results in "No Data Collected" badge (massive trust signal)
- [ ] Submit for review

---

## Estimated Timeline
| Step | Duration |
|------|----------|
| Icon design | 1-2 days |
| Xcode project setup + build | 2-3 days |
| TestFlight beta | 3-5 days |
| Apple review | 1-3 days (average 24h in 2025) |
| **Total to launch** | **~1-2 weeks** |

---

## Revenue Targets
See: revenue_model.md
ASO strategy: aso_strategy.md
