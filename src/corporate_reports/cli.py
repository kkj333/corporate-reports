"""
corporate-reports CLI エントリポイント
"""

import json
import sys
import argparse

from corporate_reports.edinet import (
    search_documents,
    download_document,
    extract_financial_data,
    EdinetAPIError,
)


def main():
    parser = argparse.ArgumentParser(description="corporate-reports CLI")
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # edinet コマンド
    edinet_parser = subparsers.add_parser("edinet", help="EDINET API 操作")
    edinet_subparsers = edinet_parser.add_subparsers(
        dest="edinet_command", help="EDINET サブコマンド"
    )

    # edinet search
    search_parser = edinet_subparsers.add_parser("search", help="書類を検索")
    search_parser.add_argument("--date", required=True, help="検索対象日 (YYYY-MM-DD)")
    search_parser.add_argument("--sec-code", help="証券コード (4桁または5桁)")
    search_parser.add_argument("--ordinance-code", help="府令コード (例: 010)")
    search_parser.add_argument("--form-code", help="様式コード (例: 030000)")

    # edinet extract
    extract_parser = edinet_subparsers.add_parser(
        "extract", help="CSVから財務データを抽出"
    )
    extract_parser.add_argument(
        "--csv-dir", required=True, help="CSVディレクトリのパス"
    )
    extract_parser.add_argument(
        "--output", help="出力先ファイルパス（省略時は標準出力）"
    )

    # edinet download
    download_parser = edinet_subparsers.add_parser(
        "download", help="書類をダウンロード"
    )
    download_parser.add_argument("--doc-id", required=True, help="書類管理番号")
    download_parser.add_argument(
        "--type",
        required=True,
        choices=["1", "2", "3", "5"],
        help="取得形式 (1:XBRL, 2:PDF, 3:代替PDF, 5:CSV)",
    )
    download_parser.add_argument("--output", required=True, help="保存先パス")

    # valuation コマンド
    valuation_parser = subparsers.add_parser("valuation", help="バリュエーション計算")
    valuation_parser.add_argument("input_file", help="入力JSONファイルのパス")

    # build-report コマンド
    build_parser = subparsers.add_parser(
        "build-report", help="report.md から report.html を生成"
    )
    build_parser.add_argument("report_dir", help="レポートディレクトリのパス")
    build_parser.add_argument(
        "--no-charts",
        action="store_true",
        help="チャートなしでHTML生成（chart_config.jsonを無視）",
    )
    build_parser.add_argument(
        "--no-toc",
        action="store_true",
        help="サイドバーTOCなしでHTML生成",
    )

    args = parser.parse_args()

    try:
        if args.command == "valuation":
            from pathlib import Path

            from corporate_reports.valuation import (
                ValuationError,
                calculate_valuation,
                format_output,
                load_input,
            )

            try:
                inp = load_input(Path(args.input_file))
                result = calculate_valuation(inp)
                print(format_output(result))
            except ValuationError as e:
                print(
                    json.dumps(
                        {"status": "error", "message": str(e)}, ensure_ascii=False
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)

        elif args.command == "build-report":
            from pathlib import Path

            from corporate_reports.build_report import build_report

            output = build_report(
                report_dir=Path(args.report_dir),
                no_charts=args.no_charts,
                no_toc=args.no_toc,
            )
            print(
                json.dumps(
                    {"status": "success", "file": str(output)},
                    ensure_ascii=False,
                )
            )

        elif args.command == "edinet":
            if args.edinet_command == "search":
                results = search_documents(
                    date=args.date,
                    sec_code=args.sec_code,
                    ordinance_code=args.ordinance_code,
                    form_code=args.form_code,
                )
                print(json.dumps(results, ensure_ascii=False, indent=2))

            elif args.edinet_command == "extract":
                data = extract_financial_data(csv_dir=args.csv_dir)
                output_json = json.dumps(data, ensure_ascii=False, indent=2)
                if args.output:
                    from pathlib import Path

                    out = Path(args.output)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(output_json + "\n", encoding="utf-8")
                    print(
                        json.dumps(
                            {"status": "success", "file": str(out)},
                            ensure_ascii=False,
                        )
                    )
                else:
                    print(output_json)

            elif args.edinet_command == "download":
                output_path = download_document(
                    doc_id=args.doc_id,
                    doc_type=args.type,
                    output_path=args.output,
                )
                print(
                    json.dumps(
                        {"status": "success", "file": output_path},
                        ensure_ascii=False,
                    )
                )

            else:
                edinet_parser.print_help()
                sys.exit(1)

        else:
            parser.print_help()
            sys.exit(1)

    except EdinetAPIError as e:
        print(
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(1)
    except FileNotFoundError as e:
        print(
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
