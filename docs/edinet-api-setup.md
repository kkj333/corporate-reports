# EDINET API セットアップ手順

金融庁の EDINET API v2 を使って有価証券報告書・決算短信等をダウンロードするための準備手順。

## 1. アカウント登録

[EDINET API 登録ページ](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1) にアクセスし、以下を入力する。

- 氏名
- メールアドレス
- 電話番号（SMS認証用）

※ 無料。個人でも利用可能。

## 2. 多要素認証

1. メールに届く確認コードを入力
2. SMS認証コードを入力
   - **注意**: 日本の携帯番号は先頭の0を省略して入力する（`090-xxxx-xxxx` → `+81-90-xxxx-xxxx`）

## 3. APIキー取得

認証完了後、画面に APIキー（`Subscription-Key`）が**ポップアップで表示**される。

### トラブルシューティング

- ブラウザがポップアップをブロックすることがある
- **Edge** を使うか、`https://api.edinet-fsa.go.jp` のポップアップを許可しておく
- 表示されたキーは必ず控えておく

## 4. 環境設定

### 4-1. `.env` ファイルの作成

プロジェクトルートに `.env` ファイルを作成（**推奨**: APIキーが会話ログに露出しない）

```bash
# .env.example をコピーして作成
cp .env.example .env

# エディタで .env を開き、取得したAPIキーを入力
# EDINET_API_KEY=ここに取得したAPIキーを貼り付け
```

※ `.env` は既に `.gitignore` で除外設定済み。Git にコミットされないので安全です。

### 4-2. 依存パッケージのインストール

```bash
# uv でインストール（推奨）
uv sync

# または pip でインストール
pip install python-dotenv requests
```

## 5. 動作確認

```bash
# CLI で本日の開示書類一覧を取得
uv run corporate-reports edinet search --date $(date +%Y-%m-%d)
```

JSON 形式で書類一覧が返ってくれば成功。

## 6. 使用例

### 書類を検索（証券コード指定）

```bash
# カナレ電気（5819）の2025年3月27日の開示書類を検索
uv run corporate-reports edinet search \
  --date 2025-03-27 \
  --sec-code 5819

# 有価証券報告書に絞り込み
uv run corporate-reports edinet search \
  --date 2025-03-27 \
  --sec-code 5819 \
  --ordinance-code 010 \
  --form-code 030000
```

### 書類をダウンロード

```bash
# PDF取得
uv run corporate-reports edinet download \
  --doc-id S100XXXX \
  --type 2 \
  --output data/report.zip

# CSV取得（構造化財務データ、2024年4月以降）
uv run corporate-reports edinet download \
  --doc-id S100XXXX \
  --type 5 \
  --output data/report_csv.zip
```

### ダウンロード形式（type パラメータ）

| type | 形式 | 内容 |
|---|---|---|
| `1` | ZIP | XBRL + PDF + 監査報告書一式 |
| `2` | PDF | 提出書類のPDF |
| `3` | PDF | 代替書類（英文等） |
| `5` | CSV | 構造化財務データ（2024年4月〜） |

### 書類種別フィルタ

| 書類 | ordinanceCode | formCode |
|---|---|---|
| 有価証券報告書 | `010` | `030000` |
| 四半期報告書 | `010` | `043000` |

### 制約事項

- **レートリミット**: 秒間3リクエストまで（スクリプトで自動対応）
- **取得可能期間**: 過去5年分
- **証券コード**: EDINET 内では5桁（末尾0付き）。例: カナレ電気 `5819` → `58190`

## 参考リンク

- [EDINET API 仕様書（Version 2）](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf)
- [EDINET API 登録ページ](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1)
- [EDINET トップページ](https://disclosure.edinet-fsa.go.jp/)
