# App Store 提出ガイド — 3アプリ同時提出

## 対象アプリ

| App | Bundle ID | 価格 | 状態 |
|-----|-----------|------|------|
| LynQ | com.lynq.app | ¥600/月, ¥4,800/年, ¥14,800買い切り | UI完成✅ |
| VoxNote | com.voxnote.app | ¥400/月, ¥3,200/年, ¥9,800買い切り | UI完成✅ |
| DocLens | com.doclens.app | ¥500/月, ¥3,600/年, ¥12,800買い切り | UI完成✅ |

---

## Mac側 必須手順（各アプリ共通）

### Step 1: XcodeGenでプロジェクト生成
```bash
cd ~/Desktop/LynQ && xcodegen generate --spec project.yml
cd ~/Desktop/VoxNote && xcodegen generate --spec project.yml
cd ~/Desktop/DocLens && xcodegen generate --spec project.yml
```

### Step 2: 環境変数を設定
```bash
export DEVELOPMENT_TEAM="YOUR_APPLE_TEAM_ID"
export ANTHROPIC_API_KEY="sk-ant-..."
export ASC_KEY_ID="XXXXXXXXXX"
export ASC_ISSUER_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export ITC_TEAM_ID="XXXXXXXXX"
```

### Step 3: アプリアイコン作成（ChatGPT/Grokに依頼）
各アプリ 1024×1024px PNG（透明背景なし）
- **LynQ**: ダークネイビー背景、AIシールド＋QRコードシンボル、電気ブルー
- **VoxNote**: ディープパープル背景、音波＋AIスパークル
- **DocLens**: ダークティール背景、書類スキャン＋AIレンズ

### Step 4: スクリーンショット生成（ChatGPT/Grok）
各アプリ、以下サイズが必要:
- iPhone 6.7" (1290×2796px) — 最重要、6枚
- iPhone 6.5" (1242×2688px) — 6枚
- iPad Pro 12.9" (2048×2732px) — 任意（審査は通過可能）

**プロンプトテンプレート（DALL-E 3 / Grok）:**
```
Ultra-realistic iPhone 16 Pro mockup, App Store screenshot style.
Dark navy background #0A0E1A, glassmorphism UI cards,
[アプリ固有の説明を追加].
Premium fintech aesthetic, electric blue accents, 6.7 inch display,
clean white text, no device frame, screenshot fills entire canvas.
1290x2796 pixels.
```

---

## App Store Connect 設定

### LynQ — App Store Connect設定

**基本情報**
- App Name: LynQ - AI QR Scanner & Safety
- Subtitle: Scan Smart. Stay Safe.
- Category: Utilities (Primary), Productivity (Secondary)

**キーワード（英語）**
```
qr scanner,qr reader,ai qr,barcode scan,safe qr,phishing detector,qr code,qr generator
```

**キーワード（日本語）**
```
QRコード,QRスキャナー,QR読み取り,バーコード,フィッシング,AI,安全確認,QR作成
```

**年齢制限**: 4+

**In-App Purchase 設定**
| Product ID | Type | 表示価格 |
|-----------|------|---------|
| com.lynq.app.pro.monthly | Auto-Renewable Subscription | ¥600/月 |
| com.lynq.app.pro.annual | Auto-Renewable Subscription | ¥4,800/年 |
| com.lynq.app.lifetime | Non-Consumable | ¥14,800 |

**Subscription Group名**: LynQ Pro
- Annual を最初に表示（Best Value バッジ付き）
- 7日間無料トライアルを annual に設定

---

### VoxNote — App Store Connect設定

**基本情報**
- App Name: VoxNote - AI Voice Memos
- Subtitle: Record. Transcribe. Summarize.
- Category: Productivity (Primary), Utilities (Secondary)

**キーワード（英語）**
```
voice memo,transcription,ai notes,meeting notes,speech to text,audio recorder,summary
```

**キーワード（日本語）**
```
音声メモ,文字起こし,AI,議事録,会議録,録音,テキスト変換,要約
```

**In-App Purchase**
| Product ID | Type | 表示価格 |
|-----------|------|---------|
| com.voxnote.app.pro.monthly | Auto-Renewable Subscription | ¥400/月 |
| com.voxnote.app.pro.annual | Auto-Renewable Subscription | ¥3,200/年 |
| com.voxnote.app.lifetime | Non-Consumable | ¥9,800 |

---

### DocLens — App Store Connect設定

**基本情報**
- App Name: DocLens - AI Document Scanner
- Subtitle: Scan. Extract. Understand.
- Category: Productivity (Primary), Utilities (Secondary)

**キーワード（英語）**
```
document scanner,ocr,pdf scanner,ai summary,text extract,scan pdf,document reader
```

**キーワード（日本語）**
```
書類スキャン,OCR,PDF,AI要約,テキスト抽出,文書管理,スキャナー
```

**In-App Purchase**
| Product ID | Type | 表示価格 |
|-----------|------|---------|
| com.doclens.app.pro.monthly | Auto-Renewable Subscription | ¥500/月 |
| com.doclens.app.pro.annual | Auto-Renewable Subscription | ¥3,600/年 |
| com.doclens.app.lifetime | Non-Consumable | ¥12,800 |

---

## 提出フロー（Fastlane）

```bash
# LynQ
cd ~/Desktop/LynQ
bundle exec fastlane submit

# VoxNote (fastlane/Fastfile の app_identifier を確認)
cd ~/Desktop/VoxNote
bundle exec fastlane submit

# DocLens
cd ~/Desktop/DocLens
bundle exec fastlane submit
```

---

## Privacy Manifest 確認事項

各アプリの `PrivacyInfo.xcprivacy` に必要な項目:
- **カメラ**: QRスキャン/書類スキャンに使用
- **マイク** (VoxNoteのみ): 音声録音に使用
- **NSUserDefaults**: 設定保存
- **ネットワーク接続**: AI API通信

---

## 審査Notes（review_notes.txt に追記）

```
This app uses the camera for QR code scanning / document scanning.
The AI analysis feature requires network connection to process content
using Claude AI API (Anthropic). No personal data is stored on external
servers. All QR content is processed and immediately discarded after analysis.
Test account for review: Not required (no login needed).
```

---

## 収益目標と達成指標

| 指標 | 目標 |
|------|------|
| DAU (各アプリ) | 1,000人 (1ヶ月後) |
| 有料転換率 | 5-8% |
| 必要有料ユーザー数 | ~170人/アプリ (月¥100K) |
| 年間プラン比率目標 | 60%以上 |

**ASO戦略**: 最初の2週間は「Today」タブ掲載を狙うため、リリース後24時間でレーティング4.5+を維持する。知人・SNSフォロワーにレビュー依頼を優先。
