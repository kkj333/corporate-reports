# セットアップ手順

## 前提条件

- Python 3.12 以上
- [uv](https://github.com/astral-sh/uv) パッケージマネージャ
- EDINET API キー（[取得方法](edinet-api-setup.md)）

## 初回セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/kkj333/corporate-reports.git
cd corporate-reports
```

### 2. EDINET API の設定

```bash
# .env ファイルを作成
cp .env.example .env

# エディタで EDINET_API_KEY を設定
vim .env
```

APIキーの取得方法は [edinet-api-setup.md](edinet-api-setup.md) を参照。

### 3. 依存パッケージのインストール

```bash
uv sync
```

### 4. 動作確認

```bash
# EDINET API が動作するか確認
uv run corporate-reports edinet search --date $(date +%Y-%m-%d)

# テストを実行
uv run pytest tests/ -v
```

## Claude Code での利用

### 利用可能なスキル

| スキル | 説明 | 使用例 |
|---|---|---|
| `/corporate-report` | 企業分析レポートとチャートを生成 | `/corporate-report 5819 カナレ電気` |
| `/download-edinet` | EDINET APIから書類をダウンロード | `/download-edinet 5819 カナレ電気` |
| `/extract-data` | PDFから財務データを抽出 | `/extract-data path/to/report.pdf` |
| `/update-report` | 既存レポートに新決算データを反映 | `/update-report 5819_canare` |
| `/update-price` | 株価更新してバリュエーション再計算 | `/update-price 5819_canare 1250` |
| `/compare` | 複数企業を横比較 | `/compare 5819_canare 6857_advantest` |

詳細は [skills.md](skills.md) を参照。

## ディレクトリ構成

```
corporate-reports/
├── .env                    # APIキー（.gitignore済み）
├── .env.example            # APIキーのテンプレート
├── src/corporate_reports/  # Python パッケージ
│   ├── edinet.py          # EDINET API クライアント
│   └── cli.py             # CLI エントリポイント
├── tests/                  # ユニットテスト
├── docs/                   # ドキュメント
├── .claude/
│   └── skills/            # Claude Code スキル定義
└── [証券コード]_[企業名]/  # 企業ごとのディレクトリ
    ├── report.md          # 分析レポート
    ├── charts.html        # 財務チャート
    └── data/              # 元データ（.gitignore済み）
        ├── pdf/
        ├── csv/
        └── xbrl/
```

## 開発時のワークフロー

1. **企業分析の開始**: `/corporate-report [証券コード] [企業名]`
2. **データ取得**: `/download-edinet` で EDINET から最新書類を取得
3. **データ更新**: 新決算発表後は `/update-report` で既存レポートを更新
4. **株価反映**: `/update-price` で最新株価に基づくバリュエーション指標を再計算
5. **企業比較**: `/compare` で複数企業の横比較表を生成

## トラブルシューティング

### EDINET API エラー

```
ERROR: EDINET_API_KEY が設定されていません
```

→ `.env` ファイルに `EDINET_API_KEY=あなたのAPIキー` を設定してください。

### 依存パッケージエラー

```
ModuleNotFoundError: No module named 'requests'
```

→ `uv sync` を実行して依存パッケージをインストールしてください。

### テスト失敗

テストが失敗する場合は、pytest の詳細出力で確認:

```bash
uv run pytest tests/ -vv
```

## 参考リンク

- [EDINET API 仕様書](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf)
- [Claude Code ドキュメント](https://docs.anthropic.com/claude/docs)
- [uv ドキュメント](https://github.com/astral-sh/uv)
