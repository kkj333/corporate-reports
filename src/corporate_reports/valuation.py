"""
バリュエーション計算モジュール

数値計算を決定的に実行する。LLM推論で計算しない。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ValuationError(Exception):
    """バリュエーション計算エラー"""


@dataclass(frozen=True)
class ValuationInput:
    """バリュエーション計算の入力データ（内部統一単位）

    株数: 株（千株ではない）
    金額: 百万円（特記なき限り）
    1株あたり: 円
    """

    stock_price: float  # 円
    shares: float  # 株（自己株除き）
    bps: float  # 円
    eps_actual: float | None  # 円
    eps_forecast: float | None  # 円
    dividend_annual: float | None  # 円
    revenue: float  # 百万円
    operating_profit: float  # 百万円
    net_income: float  # 百万円
    operating_cf: float  # 百万円
    fcf: float  # 百万円
    net_cash: float  # 百万円
    ebitda: float  # 百万円
    net_assets: float  # 百万円
    effective_tax_rate: float  # 0-1
    discount_rate: float  # 0-1
    liquidation_value_per_share: float | None  # 円
    dcf_growth_middle: float  # 0-1
    dcf_growth_strong: float  # 0-1
    dcf_years: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValuationInput:
        """入力dictからValuationInputを生成。単位変換を行う。"""
        shares_raw = data.get("shares_outstanding_ex_treasury")
        if shares_raw is None:
            outstanding = data.get("shares_outstanding")
            treasury = data.get("treasury_shares", 0)
            if outstanding is None:
                raise ValuationError(
                    "shares_outstanding_ex_treasury または shares_outstanding が必要です"
                )
            shares_raw = outstanding - treasury

        # 千株→株変換
        shares_unit = data.get("shares_unit", "shares")
        if shares_unit == "thousands":
            shares = shares_raw * 1000
        else:
            shares = shares_raw

        # 大きすぎる値は千円→百万円変換
        def normalize_millions(val: float | None) -> float | None:
            if val is None:
                return None
            if abs(val) > 1_000_000:
                return val / 1000
            return val

        return cls(
            stock_price=data["stock_price"],
            shares=shares,
            bps=data["bps"],
            eps_actual=data.get("eps_actual"),
            eps_forecast=data.get("eps_forecast"),
            dividend_annual=data.get("dividend_annual"),
            revenue=data["revenue"],
            operating_profit=data["operating_profit"],
            net_income=data["net_income"],
            operating_cf=normalize_millions(data["operating_cf"]),
            fcf=normalize_millions(data["fcf"]),
            net_cash=normalize_millions(data["net_cash"]),
            ebitda=normalize_millions(data["ebitda"]),
            net_assets=normalize_millions(data["net_assets"]),
            effective_tax_rate=data.get("effective_tax_rate", 0.30),
            discount_rate=data.get("discount_rate", 0.10),
            liquidation_value_per_share=data.get("liquidation_value_per_share"),
            dcf_growth_middle=data.get("dcf_growth_middle", 0.05),
            dcf_growth_strong=data.get("dcf_growth_strong", 0.10),
            dcf_years=data.get("dcf_years", 5),
        )


@dataclass(frozen=True)
class DCFResult:
    """DCF1シナリオの結果"""

    label: str
    growth_rate: float
    terminal_value: float  # 百万円
    equity_value: float  # 百万円
    per_share: float  # 円
    upside: float  # 倍率（例: 0.12 = +12%）


# --- 個別計算関数（純粋関数） ---


def calc_market_cap(price: float, shares: float) -> float:
    """時価総額（百万円） = 株価 × 株数 / 1,000,000"""
    return price * shares / 1_000_000


def calc_per(price: float, eps: float | None) -> float | None:
    """PER = 株価 / EPS"""
    if eps is None or eps == 0:
        return None
    return price / eps


def calc_pbr(price: float, bps: float) -> float:
    """PBR = 株価 / BPS（簿価）"""
    if bps == 0:
        raise ValuationError("BPSが0です")
    return price / bps


def calc_pcr(market_cap: float, operating_cf: float) -> float | None:
    """PCR = 時価総額 / 営業CF"""
    if operating_cf is None or operating_cf <= 0:
        return None
    return market_cap / operating_cf


def calc_psr(market_cap: float, revenue: float) -> float | None:
    """PSR = 時価総額 / 売上高"""
    if revenue is None or revenue <= 0:
        return None
    return market_cap / revenue


def calc_dividend_yield(dividend: float | None, price: float) -> float | None:
    """配当利回り = 年間配当 / 株価"""
    if dividend is None or price == 0:
        return None
    return dividend / price


def calc_ev_ebitda(market_cap: float, net_cash: float, ebitda: float) -> float | None:
    """EV/EBITDA = (時価総額 - ネットキャッシュ) / EBITDA"""
    if ebitda is None or ebitda <= 0:
        return None
    ev = market_cap - net_cash
    return ev / ebitda


def calc_nopat(operating_profit: float, tax_rate: float) -> float:
    """NOPAT = 営業利益 × (1 - 実効税率)"""
    return operating_profit * (1 - tax_rate)


def calc_invested_capital(net_assets: float, net_cash: float) -> float:
    """事業投下資本 = 純資産 - ネットキャッシュ"""
    return net_assets - net_cash


def calc_roic(nopat: float, invested_capital: float) -> float | None:
    """ROIC = NOPAT / 事業投下資本"""
    if invested_capital is None or invested_capital <= 0:
        return None
    return nopat / invested_capital


def calc_liquidation_discount(
    liquidation_value_per_share: float | None, price: float
) -> float | None:
    """清算価値ディスカウント = (清算価値 - 株価) / 清算価値"""
    if liquidation_value_per_share is None or liquidation_value_per_share == 0:
        return None
    return (liquidation_value_per_share - price) / liquidation_value_per_share


def _calc_dcf_scenario(
    fcf: float,
    growth_rate: float,
    discount_rate: float,
    years: int,
    net_cash: float,
    shares: float,
    price: float,
    label: str,
) -> DCFResult:
    """DCF共通ヘルパー（成長FCFを割り引いて合算 + ターミナルバリュー）

    弱気(growth=0): TV = FCF / r のみ（成長なし永続価値）
    ミドル/強気: 成長期間のFCFを割引 + ターミナルバリュー
    """
    if discount_rate == 0:
        raise ValuationError("割引率が0です")

    if growth_rate == 0:
        # 成長なし: 永続価値のみ
        terminal_value = fcf / discount_rate
        equity_value = terminal_value + net_cash
    else:
        # 成長期間のFCF割引現在価値
        pv_fcfs = 0.0
        projected_fcf = fcf
        for year in range(1, years + 1):
            projected_fcf = projected_fcf * (1 + growth_rate)
            pv_fcfs += projected_fcf / (1 + discount_rate) ** year

        # ターミナルバリュー（成長期間後のFCFを永続価値化して割引）
        terminal_value = projected_fcf / discount_rate
        pv_terminal = terminal_value / (1 + discount_rate) ** years

        equity_value = pv_fcfs + pv_terminal + net_cash

    per_share = equity_value * 1_000_000 / shares  # 百万円→円
    upside = (per_share - price) / price

    return DCFResult(
        label=label,
        growth_rate=growth_rate,
        terminal_value=terminal_value,
        equity_value=equity_value,
        per_share=round(per_share, 0),
        upside=round(upside, 4),
    )


# --- 統合関数 ---


def calculate_valuation(inp: ValuationInput) -> dict[str, Any]:
    """全指標を計算してdictで返す"""
    mcap = calc_market_cap(inp.stock_price, inp.shares)
    per_actual = calc_per(inp.stock_price, inp.eps_actual)
    per_forecast = calc_per(inp.stock_price, inp.eps_forecast)
    pbr = calc_pbr(inp.stock_price, inp.bps)
    pcr = calc_pcr(mcap, inp.operating_cf)
    psr = calc_psr(mcap, inp.revenue)
    div_yield = calc_dividend_yield(inp.dividend_annual, inp.stock_price)
    ev_ebitda = calc_ev_ebitda(mcap, inp.net_cash, inp.ebitda)

    nopat = calc_nopat(inp.operating_profit, inp.effective_tax_rate)
    ic = calc_invested_capital(inp.net_assets, inp.net_cash)
    roic = calc_roic(nopat, ic)

    liq_discount = calc_liquidation_discount(
        inp.liquidation_value_per_share, inp.stock_price
    )

    # PER × PBR
    per_pbr = None
    if per_forecast is not None:
        per_pbr = per_forecast * pbr

    # DCF 3シナリオ
    dcf_bear = _calc_dcf_scenario(
        fcf=inp.fcf,
        growth_rate=0,
        discount_rate=inp.discount_rate,
        years=inp.dcf_years,
        net_cash=inp.net_cash,
        shares=inp.shares,
        price=inp.stock_price,
        label="弱気",
    )
    dcf_middle = _calc_dcf_scenario(
        fcf=inp.fcf,
        growth_rate=inp.dcf_growth_middle,
        discount_rate=inp.discount_rate,
        years=inp.dcf_years,
        net_cash=inp.net_cash,
        shares=inp.shares,
        price=inp.stock_price,
        label="ミドル",
    )
    dcf_strong = _calc_dcf_scenario(
        fcf=inp.fcf,
        growth_rate=inp.dcf_growth_strong,
        discount_rate=inp.discount_rate,
        years=inp.dcf_years,
        net_cash=inp.net_cash,
        shares=inp.shares,
        price=inp.stock_price,
        label="強気",
    )

    def _round(val: float | None, digits: int = 2) -> float | None:
        if val is None:
            return None
        return round(val, digits)

    return {
        "stock_price": inp.stock_price,
        "shares": inp.shares,
        "market_cap": _round(mcap),
        "per_actual": _round(per_actual),
        "per_forecast": _round(per_forecast),
        "pbr": _round(pbr),
        "pcr": _round(pcr),
        "psr": _round(psr),
        "dividend_yield": _round(div_yield, 4),
        "per_x_pbr": _round(per_pbr),
        "ev_ebitda": _round(ev_ebitda),
        "nopat": _round(nopat),
        "invested_capital": _round(ic),
        "roic": _round(roic, 4),
        "liquidation_discount": _round(liq_discount, 4),
        "dcf": [
            {
                "label": d.label,
                "growth_rate": d.growth_rate,
                "terminal_value": _round(d.terminal_value),
                "equity_value": _round(d.equity_value),
                "per_share": d.per_share,
                "upside": d.upside,
            }
            for d in [dcf_bear, dcf_middle, dcf_strong]
        ],
    }


# --- I/O ---


def load_input(path: Path) -> ValuationInput:
    """JSONファイルからValuationInputを読み込む"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ValuationError(f"入力ファイルの読み込みに失敗: {e}") from e
    return ValuationInput.from_dict(data)


def format_output(result: dict[str, Any]) -> str:
    """計算結果をJSON文字列に変換"""
    return json.dumps(result, ensure_ascii=False, indent=2)
