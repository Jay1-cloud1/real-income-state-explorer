import pandas as pd
import pytest

from income_calc import (
    annual_cpi_index,
    clean_data,
    pick_income_topic,
    real_income_growth,
    state_real_income,
)


def make_raw():
    rows = []
    # Monthly national CPI: 100 in 2017, 110 in 2018, 121 in 2019
    for year, cpi in [(2017, 100.0), (2018, 110.0), (2019, 121.0)]:
        for month in range(1, 13):
            rows.append({
                "Date": f"{year}-{month:02d}-01", "Geo": "US", "Geo_Level": "National",
                "Series": "CPIAUCSL", "Topic": "cpi", "Value": cpi,
            })
    # Annual state income
    for geo, values in {"md": [50000, 55000, 60500], "TX": [40000, 44000, 50000]}.items():
        for year, value in zip([2017, 2018, 2019], values):
            rows.append({
                "Date": f"{year}-01-01", "Geo": geo, "Geo_Level": "state",
                "Series": f"{geo}PCPI", "Topic": "income_per_capita", "Value": value,
            })
    rows.append({
        "Date": "not a date", "Geo": "MD", "Geo_Level": "state",
        "Series": "x", "Topic": "income_per_capita", "Value": 1,
    })
    return pd.DataFrame(rows)


def test_clean_data_normalizes_columns_and_drops_bad_rows():
    df = clean_data(make_raw())
    assert {"date", "geo", "geo_level", "series", "topic", "value", "year"} <= set(df.columns)
    assert set(df["geo_level"]) == {"national", "state"}
    assert "MD" in set(df["geo"])
    assert df["date"].notna().all()


def test_annual_cpi_index_rebases_to_base_year():
    cpi = annual_cpi_index(clean_data(make_raw()), 2018).set_index("year")["cpi_index"]
    assert cpi[2018] == pytest.approx(100)
    assert cpi[2017] == pytest.approx(100 / 1.1)
    assert cpi[2019] == pytest.approx(110)


def test_annual_cpi_index_missing_base_year():
    assert annual_cpi_index(clean_data(make_raw()), 1990) is None


def test_state_real_income_deflates_to_base_year_dollars():
    df = clean_data(make_raw())
    income = state_real_income(df, "income_per_capita", annual_cpi_index(df, 2017))
    md = income[income["geo"] == "MD"].set_index("year")
    # MD nominal income grew exactly with CPI, so real income is flat
    assert md["real_income"].tolist() == pytest.approx([50000, 50000, 50000])
    assert md["value"].tolist() == [50000, 55000, 60500]


def test_real_income_growth_ranks_states():
    df = clean_data(make_raw())
    growth = real_income_growth(state_real_income(df, "income_per_capita", annual_cpi_index(df, 2017)))
    assert growth["geo"].tolist() == ["TX", "MD"]
    assert growth.loc[1, "real_income_growth_pct"] == pytest.approx(0)
    assert growth.loc[0, "real_income_growth_pct"] == pytest.approx((50000 / 1.21 / 40000 - 1) * 100)


def test_pick_income_topic():
    assert pick_income_topic(["cpi", "median_income", "income_per_capita"]) == "income_per_capita"
    assert pick_income_topic(["cpi", "median_income"]) == "median_income"
    assert pick_income_topic(["cpi"]) is None
