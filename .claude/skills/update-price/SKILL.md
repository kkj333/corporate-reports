---
name: update-price
description: 株価を入力してバリュエーション指標を再計算する。使い方 /update-price [企業ディレクトリ] [株価]
---

# バリュエーション再計算

`$0` の企業レポートを、株価 `$1` 円で再計算する。

---

## 手順

### 1. 既存データ読み取り

`$0/report.md` から以下を取得:

- BPS、EPS（実績・予想）
- 発行済株式数（自己株除く）
- ネットキャッシュ（百万円）
- 営業CF、FCF（百万円）
- 売上高（百万円）
- 営業利益（百万円）
- 当期純利益（百万円）
- EBITDA（百万円）
- 純資産（百万円）
- 予想年間配当
- 清算価値（1株あたり）
- 実効税率、割引率
- DCF成長率（ミドル・強気）、算定年数

### 2. valuation_input.json を組み立てる

読み取ったデータを `$0/valuation_input.json` に書き出す。フォーマット:

```json
{
  "stock_price": <新しい株価>,
  "shares_outstanding_ex_treasury": <自己株除き発行済株式数>,
  "shares_unit": "thousands",
  "bps": <BPS>,
  "eps_actual": <実績EPS>,
  "eps_forecast": <予想EPS>,
  "dividend_annual": <年間配当>,
  "revenue": <売上高（百万円）>,
  "operating_profit": <営業利益（百万円）>,
  "net_income": <当期純利益（百万円）>,
  "operating_cf": <営業CF（百万円）>,
  "fcf": <FCF（百万円）>,
  "net_cash": <ネットキャッシュ（百万円）>,
  "ebitda": <EBITDA（百万円）>,
  "net_assets": <純資産（百万円）>,
  "effective_tax_rate": <実効税率>,
  "discount_rate": <割引率>,
  "liquidation_value_per_share": <清算価値1株あたり（円）>,
  "dcf_growth_middle": <ミドル成長率>,
  "dcf_growth_strong": <強気成長率>,
  "dcf_years": <算定年数>
}
```

**注意:**
- 金額は百万円単位（千円単位の場合、1,000,000超なら自動で÷1000される）
- 株式数は `shares_unit` で千株/株を指定

### 3. valuation.py で計算実行

```bash
uv run corporate-reports valuation $0/valuation_input.json
```

出力されたJSONから各指標を読み取る。

### 4. 更新箇所

report.md の以下を更新:

- 冒頭の `**株価：{株価}円（{日付}）**`
- 「株価指標」セクションのテーブル全体
- 「企業価値」セクションのDCFシナリオ比較表のアップサイド列
- 「資産バリューチェック」の現在株価・ディスカウント率
- ネットキャッシュ vs 時価総額の時価総額
- 五段階評価のコメント（倍率が変わった場合）
- 総括の株価関連の記述

### 5. 確認

- 更新後、valuation.py の出力と report.md の数値が一致していることを確認する
