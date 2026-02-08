---
name: download-edinet
description: EDINET APIから有価証券報告書・決算短信をダウンロードする（PDF/CSV/XBRL対応）。使い方 /download-edinet [証券コード] [企業名]
---

# EDINET 書類ダウンロード

証券コード `$0`、企業名 `$1` の開示書類を EDINET API v2 からダウンロードする。

---

## 前提条件

- EDINET API キー（Subscription-Key）が必要
- `.env` ファイルに `EDINET_API_KEY=キー` の形式で設定
- 未設定の場合は [edinet-api-setup.md](../../../docs/edinet-api-setup.md) を参照して設定を案内する
- **重要**: APIキーを直接 curl コマンドに埋め込まない（会話ログに露出するため）
- `corporate-reports` CLI 経由で API 呼び出しを行う

---

## 手順

### 1. 保存先の準備

企業ディレクトリが存在するか確認し、なければ作成:

```
{証券コード}_{企業名英語小文字}/
└── data/
    ├── pdf/       # PDF書類
    ├── csv/       # CSV構造化データ
    └── xbrl/      # XBRL一式
```

### 2. docID の検索

`corporate-reports` CLI で対象企業の開示書類を検索する。

**基本コマンド:**
```bash
uv run corporate-reports edinet search \
  --date 提出日 \
  --sec-code 証券コード \
  [--ordinance-code 府令コード] \
  [--form-code 様式コード]
```

**レスポンス形式:**
```json
[
  {
    "docID": "S100XXXX",
    "secCode": "58190",
    "edinetCode": "EXXXXX",
    "filerName": "カナレ電気株式会社",
    "docDescription": "有価証券報告書...",
    "ordinanceCode": "010",
    "formCode": "030000",
    "periodEnd": "2024-12-31",
    "submitDateTime": "2025-03-27 09:00"
  }
]
```

**書類種別フィルタ:**

| 書類 | ordinanceCode | formCode |
|---|---|---|
| 有価証券報告書 | `010` | `030000` |
| 四半期報告書 | `010` | `043000` |
| 決算短信（通期） | — | — |
| 決算短信（四半期） | — | — |

決算短信は取引所開示のため ordinanceCode/formCode が不定。`secCode` + `docDescription` の文字列マッチで絞り込む。

**証券コードの注意:** EDINET内では5桁（末尾0付き）。4桁コードの場合は先頭4桁で前方一致させる（スクリプトが自動対応）。

### 3. 提出日の推定と日付範囲検索

提出日が不明な場合、決算月から推定して日付範囲検索する:

| 決算月 | 有報の提出月目安 | 短信の提出月目安 |
|---|---|---|
| 3月 | 6月 | 4〜5月 |
| 12月 | 3月 | 2月 |
| 9月 | 12月 | 11月 |
| 6月 | 9月 | 8月 |

想定月の1日〜末日を順に検索する。見つかった時点で終了。

```bash
# 例: 12月決算企業の有報を2025年3月中に検索
for day in $(seq 1 31); do
  d=$(printf "2025-03-%02d" $day)
  result=$(uv run corporate-reports edinet search \
    --date "$d" \
    --sec-code 5819 \
    --ordinance-code 010 \
    --form-code 030000 2>/dev/null \
    | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data:
        print(data[0]['docID'])
except:
    pass
")
  if [ -n "$result" ]; then
    echo "Found on $d: $result"
    break
  fi
  sleep 0.5
done
```

### 4. 書類ダウンロード

**基本コマンド:**
```bash
uv run corporate-reports edinet download \
  --doc-id {docID} \
  --type {type} \
  --output {保存先パス}
```

**取得形式（type パラメータ）:**

| type | 形式 | 内容 | 用途 |
|---|---|---|---|
| `1` | ZIP | XBRL + PDF + 監査報告書 | 完全な開示書類一式 |
| `2` | PDF | 提出書類のPDF | 目視確認、`/extract-data` の入力 |
| `3` | PDF | 代替書類（英文等） | 英文開示がある場合 |
| `5` | CSV | 構造化財務データ | **推奨**: 数値抽出が正確で効率的 |

**実行例:**
```bash
# PDF取得
uv run corporate-reports edinet download \
  --doc-id S100XXXX \
  --type 2 \
  --output temp/doc.zip
unzip temp/doc.zip -d temp/ && mv temp/*.pdf {保存先}

# CSV取得（構造化データ）
uv run corporate-reports edinet download \
  --doc-id S100XXXX \
  --type 5 \
  --output temp/doc_csv.zip
unzip temp/doc_csv.zip -d {保存先}/csv/

# XBRL一式取得
uv run corporate-reports edinet download \
  --doc-id S100XXXX \
  --type 1 \
  --output temp/doc_xbrl.zip
unzip temp/doc_xbrl.zip -d {保存先}/xbrl/
```

### 5. 推奨ダウンロード手順

効率的な分析のため、以下の順でダウンロードする:

1. **CSV（type=5）を最優先** — 財務データが構造化済み。`/extract-data` より正確
2. **PDF（type=2）を補助的に** — CSVに含まれない定性情報（リスク、沿革、事業説明等）の確認用
3. **XBRL（type=1）は必要時のみ** — タクソノミ情報が必要な場合

### 6. ファイル保存規約

```
{証券コード}_{企業名}/data/
├── pdf/
│   ├── yuho_2024.pdf            # 有価証券報告書（2024年12月期）
│   ├── yuho_2023.pdf
│   ├── tanshin_2025q4.pdf       # 決算短信（2025年12月期 本決算）
│   └── tanshin_2025q2.pdf       # 決算短信（第2四半期）
├── csv/
│   ├── yuho_2024_csv/           # CSVはフォルダごと保存
│   └── yuho_2023_csv/
└── xbrl/
    └── yuho_2024_xbrl/
```

### 7. 注意点

- **APIキーの安全性**: `corporate-reports` CLI を使用することでAPIキーが会話ログに露出しない
- **レートリミット**: スクリプトが自動的に秒間3回以内に制御（0.35秒間隔）
- **ZIP展開**: 全形式がZIPで返される。一時ディレクトリに展開してからリネーム・移動する
- **保存期間**: 過去5年分の書類が取得可能
- **CSV対応開始**: 2024年4月以降の提出書類からCSV取得可能。それ以前はPDFのみ
- **大量取得時**: 日付ループ中にエラーが出たら中断して原因確認（APIキー期限切れ、休日等）
- **他スキルとの連携**: CSV取得後は `/extract-data` 不要で直接レポートに利用可能。PDFのみの場合は `/extract-data` でデータ抽出する
