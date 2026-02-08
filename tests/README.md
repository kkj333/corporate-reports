# テスト

EDINET API クライアントのユニットテストです。

## テストの実行

```bash
# すべてのテストを実行
uv run pytest tests/

# 詳細表示
uv run pytest tests/ -v

# カバレッジ付き（pytest-cov をインストール後）
uv run pytest tests/ --cov=corporate_reports --cov-report=html
```

## テスト構成

- `test_edinet_api.py` - EDINET API クライアント (`corporate_reports.edinet`) のテスト
  - 書類検索機能
  - 書類ダウンロード機能
  - エラーハンドリング
  - APIキー検証

## テスト方針

- **モックを使用**: 実際の EDINET API を呼ばず、`requests` をモックして高速・安定したテストを実現
- **正常系・異常系**: 成功パターンとエラーケースの両方をカバー
- **環境独立**: APIキーがなくてもテストが実行可能

## カバレッジ目標

- 主要な関数（search_documents, download_document, check_api_key）は 100% カバー
- エッジケース（証券コードフィルタ、書類種別フィルタ等）もテスト済み
