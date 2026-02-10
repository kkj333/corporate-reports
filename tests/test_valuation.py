"""
バリュエーション計算のユニットテスト

ジェコス・カナレの実データで検算する。
"""

import json

import pytest

from corporate_reports.valuation import (
    ValuationError,
    ValuationInput,
    _calc_dcf_scenario,
    calc_dividend_yield,
    calc_ev_ebitda,
    calc_invested_capital,
    calc_liquidation_discount,
    calc_market_cap,
    calc_nopat,
    calc_pbr,
    calc_per,
    calc_roic,
    calculate_valuation,
    format_output,
    load_input,
)


# --- ジェコス テストデータ ---
JECOS_INPUT = {
    "stock_price": 1668,
    "shares_outstanding": 33794,
    "shares_unit": "thousands",
    "bps": 1861.66,
    "eps_actual": 134.8,
    "eps_forecast": 163,
    "dividend_annual": 65,
    "revenue": 130000,
    "operating_profit": 7800,
    "net_income": 5500,
    "operating_cf": 8781,
    "fcf": 5800,
    "net_cash": 5486,
    "ebitda": 12000,
    "net_assets": 62918,
    "effective_tax_rate": 0.30,
    "discount_rate": 0.10,
    "liquidation_value_per_share": 1035,
    "dcf_growth_middle": 0.10,
    "dcf_growth_strong": 0.20,
    "dcf_years": 5,
}

# --- カナレ テストデータ ---
CANARE_INPUT = {
    "stock_price": 2527,
    "shares_outstanding_ex_treasury": 6841,
    "shares_unit": "thousands",
    "bps": 2635.79,
    "eps_actual": 152.64,
    "eps_forecast": 160,
    "dividend_annual": 55,
    "revenue": 12383,
    "operating_profit": 1200,
    "net_income": 1040,
    "operating_cf": 1634,
    "fcf": 1666,
    "net_cash": 13692,
    "ebitda": 1800,
    "net_assets": 17965,
    "effective_tax_rate": 0.30,
    "discount_rate": 0.10,
    "liquidation_value_per_share": 3200,
    "dcf_growth_middle": 0.05,
    "dcf_growth_strong": 0.10,
    "dcf_years": 5,
}


class TestValuationInput:
    """ValuationInput のテスト"""

    def test_from_dict_thousands(self):
        """千株単位の変換"""
        inp = ValuationInput.from_dict(JECOS_INPUT)
        assert inp.shares == 33794 * 1000
        assert inp.stock_price == 1668

    def test_from_dict_ex_treasury_priority(self):
        """shares_outstanding_ex_treasury が優先される"""
        inp = ValuationInput.from_dict(CANARE_INPUT)
        assert inp.shares == 6841 * 1000

    def test_from_dict_shares_minus_treasury(self):
        """outstanding - treasury_shares のフォールバック"""
        data = {
            **JECOS_INPUT,
            "shares_outstanding": 35000,
            "treasury_shares": 1206,
        }
        # shares_outstanding_ex_treasury が無いのでフォールバック
        inp = ValuationInput.from_dict(data)
        assert inp.shares == (35000 - 1206) * 1000

    def test_from_dict_missing_shares_raises(self):
        """株式数データなしでエラー"""
        data = {**JECOS_INPUT}
        del data["shares_outstanding"]
        with pytest.raises(ValuationError, match="shares_outstanding"):
            ValuationInput.from_dict(data)

    def test_from_dict_normalize_millions(self):
        """1,000,000超の値は千円→百万円に変換"""
        data = {
            **JECOS_INPUT,
            "net_cash": 5486000,  # 千円単位（>1M）
        }
        inp = ValuationInput.from_dict(data)
        assert inp.net_cash == 5486.0

    def test_frozen(self):
        """frozenなので変更不可"""
        inp = ValuationInput.from_dict(JECOS_INPUT)
        with pytest.raises(AttributeError):
            inp.stock_price = 2000


class TestMarketCap:
    """時価総額の計算"""

    def test_jecos(self):
        """ジェコス: 1668 × 33,794,000 / 1,000,000 = 56,368.39"""
        mcap = calc_market_cap(1668, 33794000)
        assert mcap == pytest.approx(56368.39, rel=1e-4)

    def test_canare(self):
        """カナレ: 2527 × 6,841,000 / 1,000,000 = 17,287.21"""
        mcap = calc_market_cap(2527, 6841000)
        assert mcap == pytest.approx(17287.21, rel=1e-3)


class TestPER:
    """PERの計算"""

    def test_jecos_actual(self):
        """ジェコス実績PER: 1668 / 134.8 = 12.37"""
        assert calc_per(1668, 134.8) == pytest.approx(12.37, rel=1e-2)

    def test_jecos_forecast(self):
        """ジェコス予想PER: 1668 / 163 = 10.23"""
        assert calc_per(1668, 163) == pytest.approx(10.23, rel=1e-2)

    def test_eps_zero(self):
        assert calc_per(1668, 0) is None

    def test_eps_none(self):
        assert calc_per(1668, None) is None


class TestPBR:
    """PBRの計算（簿価BPSで計算）"""

    def test_jecos(self):
        """ジェコス: 1668 / 1861.66 = 0.896"""
        pbr = calc_pbr(1668, 1861.66)
        assert pbr == pytest.approx(0.896, rel=1e-2)

    def test_canare(self):
        """カナレ: 2527 / 2635.79 = 0.959"""
        pbr = calc_pbr(2527, 2635.79)
        assert pbr == pytest.approx(0.959, rel=1e-2)

    def test_bps_zero_raises(self):
        with pytest.raises(ValuationError, match="BPS"):
            calc_pbr(1668, 0)


class TestDividendYield:
    """配当利回りの計算"""

    def test_jecos(self):
        """ジェコス: 65 / 1668 = 3.90%"""
        dy = calc_dividend_yield(65, 1668)
        assert dy == pytest.approx(0.0390, rel=1e-2)

    def test_none_dividend(self):
        assert calc_dividend_yield(None, 1668) is None


class TestEVEBITDA:
    """EV/EBITDAの計算"""

    def test_jecos(self):
        """ジェコス: (56368 - 5486) / 12000 = 4.24"""
        mcap = calc_market_cap(1668, 33794000)
        ev_ebitda = calc_ev_ebitda(mcap, 5486, 12000)
        assert ev_ebitda == pytest.approx(4.24, rel=1e-2)

    def test_ebitda_zero(self):
        assert calc_ev_ebitda(50000, 5000, 0) is None

    def test_ebitda_negative(self):
        assert calc_ev_ebitda(50000, 5000, -100) is None


class TestROIC:
    """ROICの計算"""

    def test_jecos(self):
        """ジェコス: NOPAT=7800*0.7=5460, IC=62918-5486=57432, ROIC=9.51%"""
        nopat = calc_nopat(7800, 0.30)
        assert nopat == pytest.approx(5460, rel=1e-4)
        ic = calc_invested_capital(62918, 5486)
        assert ic == pytest.approx(57432, rel=1e-4)
        roic = calc_roic(nopat, ic)
        assert roic == pytest.approx(0.0951, rel=1e-2)

    def test_ic_zero(self):
        assert calc_roic(5460, 0) is None

    def test_ic_negative(self):
        assert calc_roic(5460, -100) is None


class TestLiquidationDiscount:
    """清算価値ディスカウントの計算"""

    def test_jecos(self):
        """ジェコス: (1035 - 1668) / 1035 = -0.6116（プレミアム）"""
        ld = calc_liquidation_discount(1035, 1668)
        assert ld == pytest.approx(-0.6116, rel=1e-2)

    def test_canare(self):
        """カナレ: (3200 - 2527) / 3200 = 0.2103（ディスカウント）"""
        ld = calc_liquidation_discount(3200, 2527)
        assert ld == pytest.approx(0.2103, rel=1e-2)

    def test_none_value(self):
        assert calc_liquidation_discount(None, 1668) is None


class TestDCFScenario:
    """DCFシナリオの計算"""

    def test_jecos_bear(self):
        """ジェコス弱気: TV = 5800/0.10 = 58000, EV = 58000+5486 = 63486百万円
        1株 = 63486*1000000/33794000 = 1878.6円"""
        result = _calc_dcf_scenario(
            fcf=5800,
            growth_rate=0,
            discount_rate=0.10,
            years=5,
            net_cash=5486,
            shares=33794000,
            price=1668,
            label="弱気",
        )
        assert result.terminal_value == pytest.approx(58000, rel=1e-4)
        assert result.equity_value == pytest.approx(63486, rel=1e-4)
        assert result.per_share == pytest.approx(1879, abs=2)

    def test_canare_bear(self):
        """カナレ弱気: TV = 1666/0.10 = 16660, EV = 16660+13692 = 30352百万円
        1株 = 30352*1000000/6841000 = 4436円"""
        result = _calc_dcf_scenario(
            fcf=1666,
            growth_rate=0,
            discount_rate=0.10,
            years=5,
            net_cash=13692,
            shares=6841000,
            price=2527,
            label="弱気",
        )
        assert result.terminal_value == pytest.approx(16660, rel=1e-4)
        assert result.equity_value == pytest.approx(30352, rel=1e-4)
        assert result.per_share == pytest.approx(4436, abs=2)

    def test_growth_scenario(self):
        """成長シナリオでは弱気より高い値になる"""
        bear = _calc_dcf_scenario(
            fcf=5800,
            growth_rate=0,
            discount_rate=0.10,
            years=5,
            net_cash=5486,
            shares=33794000,
            price=1668,
            label="弱気",
        )
        middle = _calc_dcf_scenario(
            fcf=5800,
            growth_rate=0.10,
            discount_rate=0.10,
            years=5,
            net_cash=5486,
            shares=33794000,
            price=1668,
            label="ミドル",
        )
        strong = _calc_dcf_scenario(
            fcf=5800,
            growth_rate=0.20,
            discount_rate=0.10,
            years=5,
            net_cash=5486,
            shares=33794000,
            price=1668,
            label="強気",
        )
        assert middle.per_share > bear.per_share
        assert strong.per_share > middle.per_share

    def test_discount_rate_zero_raises(self):
        with pytest.raises(ValuationError, match="割引率"):
            _calc_dcf_scenario(
                fcf=5800,
                growth_rate=0,
                discount_rate=0,
                years=5,
                net_cash=5486,
                shares=33794000,
                price=1668,
                label="test",
            )


class TestCalculateValuation:
    """統合関数のテスト"""

    def test_jecos_full(self):
        """ジェコスの全指標が計算される"""
        inp = ValuationInput.from_dict(JECOS_INPUT)
        result = calculate_valuation(inp)

        assert result["stock_price"] == 1668
        assert result["market_cap"] == pytest.approx(56368.39, rel=1e-3)
        assert result["per_actual"] == pytest.approx(12.37, rel=1e-2)
        assert result["per_forecast"] == pytest.approx(10.23, rel=1e-2)
        assert result["pbr"] == pytest.approx(0.90, rel=1e-1)
        assert result["dividend_yield"] == pytest.approx(0.0390, rel=1e-2)

        # DCF 3シナリオが存在する
        assert len(result["dcf"]) == 3
        assert result["dcf"][0]["label"] == "弱気"
        assert result["dcf"][1]["label"] == "ミドル"
        assert result["dcf"][2]["label"] == "強気"

    def test_canare_full(self):
        """カナレの全指標が計算される"""
        inp = ValuationInput.from_dict(CANARE_INPUT)
        result = calculate_valuation(inp)

        assert result["stock_price"] == 2527
        assert result["pbr"] == pytest.approx(0.959, rel=1e-2)
        assert result["dcf"][0]["per_share"] == pytest.approx(4436, abs=2)

    def test_per_x_pbr(self):
        """PER×PBRが計算される"""
        inp = ValuationInput.from_dict(JECOS_INPUT)
        result = calculate_valuation(inp)
        expected = result["per_forecast"] * result["pbr"]
        assert result["per_x_pbr"] == pytest.approx(expected, rel=1e-2)

    def test_none_eps(self):
        """EPS=Noneの場合PERがNone"""
        data = {**JECOS_INPUT, "eps_actual": None, "eps_forecast": None}
        inp = ValuationInput.from_dict(data)
        result = calculate_valuation(inp)
        assert result["per_actual"] is None
        assert result["per_forecast"] is None
        assert result["per_x_pbr"] is None


class TestLoadInput:
    """JSONファイル読み込みのテスト"""

    def test_load_valid(self, tmp_path):
        """正常なJSONファイルの読み込み"""
        json_file = tmp_path / "input.json"
        json_file.write_text(json.dumps(JECOS_INPUT), encoding="utf-8")

        inp = load_input(json_file)
        assert inp.stock_price == 1668
        assert inp.shares == 33794000

    def test_load_invalid_json(self, tmp_path):
        """不正なJSONでエラー"""
        json_file = tmp_path / "bad.json"
        json_file.write_text("not json", encoding="utf-8")

        with pytest.raises(ValuationError, match="読み込み"):
            load_input(json_file)

    def test_load_missing_file(self, tmp_path):
        """存在しないファイルでエラー"""
        with pytest.raises(ValuationError, match="読み込み"):
            load_input(tmp_path / "missing.json")

    def test_format_output(self):
        """JSON出力フォーマット"""
        result = {"stock_price": 1668, "per_actual": 12.37}
        output = format_output(result)
        parsed = json.loads(output)
        assert parsed["stock_price"] == 1668
