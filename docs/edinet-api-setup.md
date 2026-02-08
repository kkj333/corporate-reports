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

## 4. 環境変数に設定

```bash
# .zshrc や .bashrc に追加
export EDINET_API_KEY="取得したAPIキー"

# 反映
source ~/.zshrc
```

**`.env` ファイルを使う場合:**

```bash
# プロジェクトルートに .env を作成（.gitignore 済み）
EDINET_API_KEY=取得したAPIキー
```

## 5. 動作確認

```bash
# 本日の開示書類一覧を取得
curl -s "https://api.edinet-fsa.go.jp/api/v2/documents.json?date=$(date +%Y-%m-%d)&type=2&Subscription-Key=$EDINET_API_KEY" \
  | python3 -m json.tool | head -20
```

`"status": "200"` が返ってくれば成功。

## 6. API 概要

### エンドポイント

| API | URL | 用途 |
|---|---|---|
| 書類一覧 | `https://api.edinet-fsa.go.jp/api/v2/documents.json` | 提出日で書類を検索 |
| 書類取得 | `https://api.edinet-fsa.go.jp/api/v2/documents/{docID}` | 書類をダウンロード |

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

- **レートリミット**: 秒間3リクエストまで
- **取得可能期間**: 過去5年分
- **証券コード**: EDINET 内では5桁（末尾0付き）。例: カナレ電気 `5819` → `58190`

## 参考リンク

- [EDINET API 仕様書（Version 2）](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf)
- [EDINET API 登録ページ](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1)
- [EDINET トップページ](https://disclosure.edinet-fsa.go.jp/)
