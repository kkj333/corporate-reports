"""
EDINET API クライアントのユニットテスト
"""

import os
from unittest.mock import Mock, patch, mock_open
import pytest

# テスト用に環境変数を設定
os.environ["EDINET_API_KEY"] = "test_api_key_12345"

from corporate_reports.edinet import (
    search_documents,
    download_document,
    EdinetAPIError,
    check_api_key,
)


class TestSearchDocuments:
    """search_documents 関数のテスト"""

    @patch("corporate_reports.edinet.requests.get")
    @patch("corporate_reports.edinet.time.sleep")
    def test_search_success(self, mock_sleep, mock_get):
        """正常系: 書類検索が成功"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.json.return_value = {
            "metadata": {"status": "200"},
            "results": [
                {
                    "docID": "S100XXXX",
                    "secCode": "58190",
                    "filerName": "カナレ電気株式会社",
                    "ordinanceCode": "010",
                    "formCode": "030000",
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # 実行
        results = search_documents(date="2025-03-27")

        # 検証
        assert len(results) == 1
        assert results[0]["docID"] == "S100XXXX"
        mock_get.assert_called_once()
        mock_sleep.assert_called_once()

    @patch("corporate_reports.edinet.requests.get")
    @patch("corporate_reports.edinet.time.sleep")
    def test_search_with_sec_code_filter(self, mock_sleep, mock_get):
        """証券コードでフィルタリング"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "metadata": {"status": "200"},
            "results": [
                {"docID": "S100A", "secCode": "58190"},
                {"docID": "S100B", "secCode": "12340"},
                {"docID": "S100C", "secCode": "58195"},
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # 4桁コードで検索（前方一致）
        results = search_documents(date="2025-03-27", sec_code="5819")

        # 5819で始まる2件だけ取得できる
        assert len(results) == 2
        assert all(r["secCode"][:4] == "5819" for r in results)

    @patch("corporate_reports.edinet.requests.get")
    @patch("corporate_reports.edinet.time.sleep")
    def test_search_with_ordinance_and_form_code(self, mock_sleep, mock_get):
        """府令コード・様式コードでフィルタリング"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "metadata": {"status": "200"},
            "results": [
                {
                    "docID": "S100A",
                    "ordinanceCode": "010",
                    "formCode": "030000",
                },  # 有報
                {
                    "docID": "S100B",
                    "ordinanceCode": "010",
                    "formCode": "043000",
                },  # 四半期
                {"docID": "S100C", "ordinanceCode": "020", "formCode": "999999"},
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # 有価証券報告書のみ
        results = search_documents(
            date="2025-03-27", ordinance_code="010", form_code="030000"
        )

        assert len(results) == 1
        assert results[0]["docID"] == "S100A"

    @patch("corporate_reports.edinet.requests.get")
    def test_search_api_error(self, mock_get):
        """API エラー時の挙動"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "metadata": {"status": "400", "message": "Bad Request"}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(EdinetAPIError):
            search_documents(date="2025-03-27")

    @patch("corporate_reports.edinet.requests.get")
    def test_search_network_error(self, mock_get):
        """ネットワークエラー時の挙動"""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Network error")

        with pytest.raises(EdinetAPIError):
            search_documents(date="2025-03-27")


class TestDownloadDocument:
    """download_document 関数のテスト"""

    @patch("corporate_reports.edinet.requests.get")
    @patch("corporate_reports.edinet.time.sleep")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_success(self, mock_mkdir, mock_file, mock_sleep, mock_get):
        """正常系: 書類ダウンロードが成功"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.iter_content = Mock(return_value=[b"chunk1", b"chunk2"])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # 実行
        output_path = download_document(
            doc_id="S100XXXX", doc_type="2", output_path="test/output.zip"
        )

        # 検証
        assert output_path == "test/output.zip"
        mock_get.assert_called_once()
        mock_sleep.assert_called_once()
        mock_file.assert_called_once()

    @patch("corporate_reports.edinet.requests.get")
    def test_download_network_error(self, mock_get):
        """ネットワークエラー時の挙動"""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Network error")

        with pytest.raises(EdinetAPIError):
            download_document(
                doc_id="S100XXXX", doc_type="2", output_path="test/output.zip"
            )


class TestCheckApiKey:
    """check_api_key 関数のテスト"""

    def test_api_key_exists(self):
        """APIキーが設定されている場合"""
        # 環境変数は setUp で設定済みなので、例外が発生しないことを確認
        check_api_key()  # 例外が出なければOK

    @patch("corporate_reports.edinet.API_KEY", None)
    @patch.dict(os.environ, {}, clear=True)
    def test_api_key_missing(self):
        """APIキーが未設定の場合"""
        with pytest.raises(SystemExit):
            check_api_key()


class TestMainCLI:
    """main() 関数（CLI）のテスト"""

    @patch("corporate_reports.cli.search_documents")
    @patch(
        "sys.argv",
        ["corporate-reports", "edinet", "search", "--date", "2025-03-27"],
    )
    def test_cli_search_command(self, mock_search):
        """search コマンドの実行"""
        from corporate_reports.cli import main

        mock_search.return_value = [{"docID": "S100XXXX"}]

        # 例外が出なければOK
        main()
        mock_search.assert_called_once_with(
            date="2025-03-27",
            sec_code=None,
            ordinance_code=None,
            form_code=None,
        )

    @patch("corporate_reports.cli.download_document")
    @patch(
        "sys.argv",
        [
            "corporate-reports",
            "edinet",
            "download",
            "--doc-id",
            "S100XXXX",
            "--type",
            "2",
            "--output",
            "test.zip",
        ],
    )
    def test_cli_download_command(self, mock_download):
        """download コマンドの実行"""
        from corporate_reports.cli import main

        mock_download.return_value = "test.zip"

        main()
        mock_download.assert_called_once_with(
            doc_id="S100XXXX", doc_type="2", output_path="test.zip"
        )

    @patch("corporate_reports.cli.search_documents")
    @patch(
        "sys.argv",
        ["corporate-reports", "edinet", "search", "--date", "2025-03-27"],
    )
    def test_cli_error_handling(self, mock_search):
        """CLIエラーハンドリング"""
        from corporate_reports.cli import main

        mock_search.side_effect = EdinetAPIError("API Error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["corporate-reports"])
    def test_cli_no_command(self):
        """コマンド未指定時"""
        from corporate_reports.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
