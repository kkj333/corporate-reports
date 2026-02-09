"""
EDINET API v2 クライアント

書類検索・ダウンロード・CSV抽出を行うライブラリ。
"""

import csv
import os
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# プロジェクトルートの .env を読み込み
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

API_KEY = os.getenv("EDINET_API_KEY")
BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"
RATE_LIMIT_DELAY = 0.35  # 秒間3リクエスト = 約0.33秒間隔


class EdinetAPIError(Exception):
    """EDINET API エラー"""

    pass


def _get_api_key() -> Optional[str]:
    """APIキーを取得（テスト時の環境変数変更に対応するため実行時に読む）"""
    return API_KEY or os.getenv("EDINET_API_KEY")


def check_api_key() -> str:
    """APIキーの存在確認。キーを返す。"""
    import sys

    key = _get_api_key()
    if not key:
        print("ERROR: EDINET_API_KEY が設定されていません", file=sys.stderr)
        print("", file=sys.stderr)
        print("設定方法:", file=sys.stderr)
        print("1. プロジェクトルートに .env ファイルを作成", file=sys.stderr)
        print("2. 以下の内容を追加:", file=sys.stderr)
        print("   EDINET_API_KEY=あなたのAPIキー", file=sys.stderr)
        print("", file=sys.stderr)
        print("APIキーの取得:", file=sys.stderr)
        print(
            "https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1", file=sys.stderr
        )
        sys.exit(1)
    return key


def search_documents(
    date: str,
    sec_code: Optional[str] = None,
    ordinance_code: Optional[str] = None,
    form_code: Optional[str] = None,
) -> list[dict]:
    """
    書類一覧APIで検索

    Args:
        date: 検索対象日 (YYYY-MM-DD)
        sec_code: 証券コード（4桁または5桁）
        ordinance_code: 府令コード (例: "010" = 金商法)
        form_code: 様式コード (例: "030000" = 有価証券報告書)

    Returns:
        書類情報のリスト
    """
    api_key = check_api_key()

    url = f"{BASE_URL}/documents.json"
    params = {
        "date": date,
        "type": "2",  # メタデータ + 書類一覧
        "Subscription-Key": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("metadata", {}).get("status") != "200":
            raise EdinetAPIError(f"API returned status: {data.get('metadata')}")

        results = data.get("results", [])

        # フィルタリング
        if sec_code:
            # 4桁コードの場合は前方一致（EDINETは5桁で末尾0付き）
            sec_prefix = sec_code[:4]
            results = [
                r
                for r in results
                if r.get("secCode") and r.get("secCode")[:4] == sec_prefix
            ]

        if ordinance_code:
            results = [r for r in results if r.get("ordinanceCode") == ordinance_code]

        if form_code:
            results = [r for r in results if r.get("formCode") == form_code]

        time.sleep(RATE_LIMIT_DELAY)
        return results

    except requests.exceptions.RequestException as e:
        raise EdinetAPIError(f"API request failed: {e}")


def download_document(doc_id: str, doc_type: str, output_path: str) -> str:
    """
    書類をダウンロード

    Args:
        doc_id: 書類管理番号 (例: S100XXXX)
        doc_type: 取得形式
            1 = ZIP (XBRL + PDF + 監査報告書)
            2 = PDF (提出書類)
            3 = PDF (代替書類・英文)
            5 = CSV (構造化財務データ)
        output_path: 保存先パス

    Returns:
        保存先のパス
    """
    api_key = check_api_key()

    url = f"{BASE_URL}/documents/{doc_id}"
    params = {
        "type": doc_type,
        "Subscription-Key": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=60, stream=True)
        response.raise_for_status()

        # ファイルに保存
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        time.sleep(RATE_LIMIT_DELAY)
        return str(output_file)

    except requests.exceptions.RequestException as e:
        raise EdinetAPIError(f"Download failed: {e}")


# --- CSV 抽出 ---

# 経営指標等 (SummaryOfBusinessResults) で抽出する要素IDと出力キー名のマッピング
_SUMMARY_ELEMENTS: dict[str, str] = {
    "jpcrp_cor:NetSalesSummaryOfBusinessResults": "売上高",
    "jpcrp_cor:OrdinaryIncomeLossSummaryOfBusinessResults": "経常利益",
    "jpcrp_cor:ProfitLossAttributableToOwnersOfParentSummaryOfBusinessResults": "親会社株主帰属純利益",
    "jpcrp_cor:ComprehensiveIncomeSummaryOfBusinessResults": "包括利益",
    "jpcrp_cor:NetAssetsSummaryOfBusinessResults": "純資産",
    "jpcrp_cor:TotalAssetsSummaryOfBusinessResults": "総資産",
    "jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResults": "BPS",
    "jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults": "EPS",
    "jpcrp_cor:RateOfReturnOnEquitySummaryOfBusinessResults": "ROE",
    "jpcrp_cor:EquityToAssetRatioSummaryOfBusinessResults": "自己資本比率",
    "jpcrp_cor:PriceEarningsRatioSummaryOfBusinessResults": "PER",
    "jpcrp_cor:NetCashProvidedByUsedInOperatingActivitiesSummaryOfBusinessResults": "営業CF",
    "jpcrp_cor:NetCashProvidedByUsedInInvestingActivitiesSummaryOfBusinessResults": "投資CF",
    "jpcrp_cor:NetCashProvidedByUsedInFinancingActivitiesSummaryOfBusinessResults": "財務CF",
    "jpcrp_cor:CashAndCashEquivalentsSummaryOfBusinessResults": "現金同等物",
    "jpcrp_cor:NumberOfEmployees": "従業員数",
}

# 個別（NonConsolidatedMember）から取得する要素
_NON_CONSOLIDATED_ELEMENTS: dict[str, str] = {
    "jpcrp_cor:DividendPaidPerShareSummaryOfBusinessResults": "1株配当",
    "jpcrp_cor:PayoutRatioSummaryOfBusinessResults": "配当性向",
}

# コンテキストIDから相対年度へのマッピング
_CONTEXT_YEAR_MAP: dict[str, str] = {
    "Prior4Year": "4期前",
    "Prior3Year": "3期前",
    "Prior2Year": "2期前",
    "Prior1Year": "1期前",
    "CurrentYear": "当期",
}


def _parse_value(value: str) -> int | float | str | None:
    """値文字列を適切な型に変換"""
    if not value or value == "－":
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_edinet_csv(csv_path: str | Path) -> list[dict[str, str]]:
    """EDINET CSV（UTF-16LE TSV）を読み込んでレコードのリストを返す"""
    rows = []
    with open(csv_path, encoding="utf-16le", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        # BOM・ダブルクォート除去（BOMとクォートが交互に入る場合も考慮）
        header = [h.strip().strip("\ufeff").strip('"').strip("\ufeff") for h in header]
        for row in reader:
            if len(row) < len(header):
                continue
            record = {}
            for i, col in enumerate(header):
                record[col] = row[i].strip().strip('"')
            rows.append(record)
    return rows


def extract_financial_data(csv_dir: str | Path) -> dict:
    """
    EDINET CSVディレクトリから主要財務データを抽出

    Args:
        csv_dir: CSVディレクトリのパス（XBRL_TO_CSV/ を含む親ディレクトリ）

    Returns:
        構造化された財務データのdict
    """
    csv_dir = Path(csv_dir)

    # jpcrp030000-asr-*.csv を探す（XBRL_TO_CSV サブディレクトリも検索）
    patterns = [
        csv_dir / "jpcrp030000-asr-*.csv",
        csv_dir / "XBRL_TO_CSV" / "jpcrp030000-asr-*.csv",
    ]

    csv_files = []
    for pattern in patterns:
        csv_files.extend(pattern.parent.glob(pattern.name))

    if not csv_files:
        raise EdinetAPIError(f"jpcrp030000-asr-*.csv が見つかりません: {csv_dir}")

    csv_path = csv_files[0]
    rows = _parse_edinet_csv(csv_path)

    # 経営指標等（5期分）
    summary: dict[str, dict] = {}
    for year_label in _CONTEXT_YEAR_MAP.values():
        summary[year_label] = {}

    for row in rows:
        elem_id = row.get("要素ID", "")
        context_id = row.get("コンテキストID", "")
        value = row.get("値", "")

        # 連結の経営指標等
        if elem_id in _SUMMARY_ELEMENTS:
            for ctx_prefix, year_label in _CONTEXT_YEAR_MAP.items():
                if (
                    context_id.startswith(ctx_prefix)
                    and "NonConsolidated" not in context_id
                ):
                    key = _SUMMARY_ELEMENTS[elem_id]
                    summary[year_label][key] = _parse_value(value)

        # 個別（NonConsolidatedMember）の指標
        if elem_id in _NON_CONSOLIDATED_ELEMENTS:
            for ctx_prefix, year_label in _CONTEXT_YEAR_MAP.items():
                if (
                    context_id.startswith(ctx_prefix)
                    and "NonConsolidated" in context_id
                ):
                    key = _NON_CONSOLIDATED_ELEMENTS[elem_id]
                    summary[year_label][key] = _parse_value(value)

    result = {
        "source": str(csv_path),
        "経営指標等": summary,
    }

    return result
