# LynQ App Portfolio — 月10万円×10アプリ戦略

## 収益モデル設計

月10万円 = **月額¥600 × 167ユーザー** または **年額¥4,800 × 21ユーザー/月**
- App Store手数料15%（Small Business Program）
- API費用控除後の手取り目標: ¥85,000/月/アプリ

---

## App Portfolio（優先順位順）

### 1. LynQ — AI QR Scanner & Safety ✅ 開発中
- **ジャンル**: Utilities  
- **課金**: ¥600/月 | ¥4,800/年 | ¥14,800 買い切り
- **差別化**: AIによるQRフィッシング検出（日本でほぼ唯一）
- **Target DAU**: 2,000 → 転換率8% → ¥96,000/月

---

### 2. SnapAI — AI Receipt & Expense Tracker
- **概要**: レシート撮影 → AIが自動カテゴリ分類・月次レポート
- **ジャンル**: Finance / Productivity
- **課金**: ¥400/月 | ¥3,200/年
- **差別化**: 日本語レシート特化、確定申告・経費精算レポート出力
- **AI使用**: Claude Haiku でOCR + カテゴリ分類
- **実装難易度**: ★★★☆☆

---

### 3. VoiceNote AI — 会議録・文字起こし
- **概要**: 録音 → AIが文字起こし + 要点整理 + TODO抽出
- **ジャンル**: Productivity / Business
- **課金**: ¥800/月 | ¥6,400/年（使用量上限あり）
- **差別化**: 日本語高精度、議事録フォーマット自動生成
- **AI使用**: OpenAI Whisper（STT）+ Claude Sonnet（要約）
- **実装難易度**: ★★★★☆

---

### 4. PhotoCut AI — 背景除去・写真加工
- **概要**: 1タップで背景除去、AIで写真補正・スタイル変換
- **ジャンル**: Photo & Video
- **課金**: ¥300/月 | ¥2,400/年 | 都度課金(¥120/10枚)
- **差別化**: オフライン動作対応、高解像度出力
- **AI使用**: CoreML（背景除去）+ 画像変換API
- **実装難易度**: ★★★☆☆

---

### 5. SleepAI — AI睡眠コーチ
- **概要**: 睡眠記録 → AIがパターン分析 → 改善アドバイス
- **ジャンル**: Health & Fitness
- **課金**: ¥600/月 | ¥4,800/年
- **差別化**: HealthKit連携 + AIによる個別化アドバイス
- **AI使用**: Claude Haiku（分析・アドバイス生成）
- **実装難易度**: ★★★☆☆

---

### 6. DocLens AI — PDF翻訳・要約
- **概要**: PDF/画像をスキャン → AI翻訳・要約・QA
- **ジャンル**: Productivity / Education
- **課金**: ¥700/月 | ¥5,600/年
- **差別化**: 学術論文・契約書特化、日英中対応
- **AI使用**: Claude Sonnet（長文処理）
- **実装難易度**: ★★★★☆

---

### 7. CardScan AI — 名刺管理
- **概要**: 名刺撮影 → OCR → 連絡先自動登録・CRM連携
- **ジャンル**: Business / Productivity
- **課金**: ¥500/月 | ¥3,600/年
- **差別化**: 日本語名刺精度、LinkedInエクスポート
- **AI使用**: Claude Haiku（OCR補正・構造化）
- **実装難易度**: ★★★☆☆

---

### 8. TranslateSnap — リアルタイムカメラ翻訳
- **概要**: カメラを向けるだけでリアルタイム翻訳（AR表示）
- **ジャンル**: Utilities / Education
- **課金**: ¥500/月 | ¥4,000/年
- **差別化**: 看板・メニュー・書類に特化、オフライン対応
- **AI使用**: Vision OCR + DeepL/Claude翻訳
- **実装難易度**: ★★★★☆

---

### 9. CalorieSnap AI — 食事カロリー計算
- **概要**: 食事の写真を撮るだけでカロリー・栄養素を自動計算
- **ジャンル**: Health & Fitness
- **課金**: ¥400/月 | ¥3,200/年
- **差別化**: 日本食データベース充実、HealthKit連携
- **AI使用**: Claude Vision（食材認識・推定）
- **実装難易度**: ★★★★☆

---

### 10. PasswordVault AI — AIパスワードマネージャー
- **概要**: パスワード管理 + AIによる漏洩チェック・強度分析
- **ジャンル**: Utilities / Security
- **課金**: ¥600/月 | ¥4,800/年 | ¥19,800 買い切り
- **差別化**: ローカル暗号化 + AI診断 + iCloud Keychain統合
- **AI使用**: Claude（セキュリティアドバイス）
- **実装難易度**: ★★★★★

---

## 価格戦略まとめ

| プラン | 価格 | 備考 |
|--------|------|------|
| Monthly | ¥400–¥800 | 試し買いユーザー向け |
| Annual | ¥3,200–¥6,400 | 月額比33%OFF — 最重要プラン |
| Lifetime | ¥12,800–¥19,800 | 買い切り希望層 |
| Free tier | 機能制限あり | DAU獲得→転換 |

**Annual推しの理由**: LTV最大化、解約率低下、App Store収益計算が安定

---

## App Store最適化（ASO）

### キーワード戦略（例：LynQ）
- 英語: `qr scanner, qr reader, ai qr, barcode scan, safe qr, phishing detector`
- 日本語: `QRコード, QRスキャナー, QR読み取り, バーコード, フィッシング, AI, 安全確認`

### スクリーンショット構成（6枚）
1. Hero: アプリの最大価値（"AIがQRの危険を即判定"）
2. スキャン画面 + 結果例（SAFE/DANGER）
3. 詳細分析レポート
4. QRコード生成画面
5. 履歴・管理機能
6. Pro機能一覧 + 価格

### 説明文のABCフォーマット
- **A（最初の3行）**: 最重要ベネフィットを箇条書き
- **B（本文）**: 機能説明 + ユースケース
- **C（末尾）**: 課金説明 + プライバシー文言

---

## 開発ロードマップ

### Phase 1（今月）
- [x] LynQ UI全面リデザイン
- [ ] LynQ App Store提出
- [ ] #2 SnapAI 着工

### Phase 2（来月）
- [ ] SnapAI リリース
- [ ] #3 VoiceNote AI 着工
- [ ] LynQ マーケティング（SNS, ASO改善）

### Phase 3（3ヶ月目以降）
- [ ] PhotoCut AI / SleepAI
- [ ] 各アプリ月5万円到達後に次へ展開

---

## ChatGPT / Grok への依頼テンプレート（スクショ生成用）

```
プロンプト例（DALL-E / Midjourney）:
"iPhone 16 Pro mockup, app screenshot, dark navy background #0A0E1A, 
QR scanner UI, glassmorphism cards, electric blue #4F8EF7 accents, 
neon green safety badge, premium fintech aesthetic, 
App Store screenshot style, 6.7 inch display"
```
