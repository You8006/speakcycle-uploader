# SpeakCycle TikTok Uploader

TikTok Content Posting API を使用した英語学習動画の自動投稿ツールです。

## 🚀 クイックスタート

### 1. セットアップ

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集してTikTok APIキーを設定
```

### 2. TikTok Developer Portal 設定

1. [TikTok for Developers](https://developers.tiktok.com/) でアプリを作成
2. 以下を設定:
   - **Redirect URI**: `http://localhost:8080/callback`
   - **Products**: Login Kit, Content Posting API
   - **Scopes**: `user.info.basic`, `video.publish`, `video.upload`

### 3. 認証

```bash
python tiktok_uploader.py --auth
```

ブラウザが開くので、TikTokアカウントでログインしてください。

### 4. Sandbox テスト投稿

```bash
# videosフォルダに動画を配置
python tiktok_uploader.py --post --sandbox
```

## 📁 プロジェクト構造

```
speakcycle-uploader/
├── docs/                    # GitHub Pages用静的サイト
│   ├── index.html          # ホームページ
│   ├── privacy.html        # プライバシーポリシー
│   └── terms.html          # 利用規約
├── videos/                  # アップロード用動画フォルダ
├── tiktok_uploader.py      # メインスクリプト
├── .env                    # 環境変数（要作成）
├── .env.example            # 環境変数テンプレート
├── requirements.txt        # Python依存関係
└── README.md               # このファイル
```

## 📋 コマンド一覧

| コマンド                | 説明                   |
| ----------------------- | ---------------------- |
| `--auth`                | TikTokアカウントを認証 |
| `--post --sandbox`      | Sandboxモードで投稿    |
| `--post --video <path>` | 本番モードで投稿       |
| `--status`              | 現在の状態を表示       |
| `--refresh`             | トークンをリフレッシュ |

## 🧪 TikTok Sandbox モード

Sandbox モードでは:

- 動画は `SELF_ONLY` (自分のみ閲覧可) として投稿されます
- 視聴数に制限があります
- 本番承認前のテストに使用してください

### デモ動画撮影のポイント

1. `--auth` で認証フローを録画
2. `--post --sandbox` で投稿フローを録画
3. TikTokアプリで投稿された動画を確認する様子を録画

## 🌐 GitHub Pages

`docs/` フォルダがGitHub Pagesとして公開されます。

設定方法:

1. GitHubリポジトリのSettings → Pages
2. Source: Deploy from a branch
3. Branch: main, Folder: /docs
4. カスタムドメイン: speakcycle.site (オプション)

### ページ一覧

- `/` - ホームページ
- `/privacy.html` - プライバシーポリシー
- `/terms.html` - 利用規約

## 🔐 セキュリティ

- `.env` ファイルは `.gitignore` に追加してください
- トークンファイル (`tiktok_tokens.json`) も公開しないでください

## 📝 TikTok審査対応

審査に必要なもの:

1. ✅ ホームページ URL: `https://yourusername.github.io/speakcycle-uploader/`
2. ✅ Privacy Policy: `https://yourusername.github.io/speakcycle-uploader/privacy.html`
3. ✅ Terms of Service: `https://yourusername.github.io/speakcycle-uploader/terms.html`
4. ✅ デモ動画: Sandboxでの認証→投稿フローを録画

## 🔗 関連リンク

- [TikTok for Developers](https://developers.tiktok.com/)
- [Content Posting API Guide](https://developers.tiktok.com/doc/content-posting-api-get-started)
- [Media Transfer Guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide)

## ライセンス

Private - All Rights Reserved
