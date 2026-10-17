import pandas as pd


def clean_data(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["geo"] = df["geo"].astype(str).str.strip().str.upper()
    df["geo_level"] = df["geo_level"].astype(str).str.strip().str.lower()
    df["series"] = df["series"].astype(str).str.strip()
    df["topic"] = df["topic"].astype(str).str.strip()

    df = df.dropna(subset=["date", "value"]).copy()
    df["year"] = df["date"].dt.year

    return df


def annual_cpi_index(df, base_year):
    """Annual average CPI rebased so base_year = 100. Returns None if base_year has no CPI."""
    cpi = df[(df["geo_level"] == "national") & (df["series"] == "CPIAUCSL")]
    cpi_annual = cpi.groupby("year", as_index=False)["value"].mean()
    base_cpi = cpi_annual.loc[cpi_annual["year"] == base_year, "value"].mean()

    if pd.isna(base_cpi) or base_cpi == 0:
        return None

    cpi_annual["cpi_index"] = (cpi_annual["value"] / base_cpi) * 100
    return cpi_annual[["year", "cpi_index"]]


def pick_income_topic(topics):
    topics = list(topics)
    if "income_per_capita" in topics:
        return "income_per_capita"
    income_topics = sorted(t for t in topics if "income" in str(t).lower())
    return income_topics[0] if income_topics else None


def state_real_income(df, income_topic, cpi_index):
    """Annual nominal and real income per state, in base-year dollars."""
    income = df[
        (df["topic"] == income_topic)
        & (df["geo_level"] == "state")
        & (df["geo"].str.len() == 2)
    ]
    income = income.groupby(["geo", "year"], as_index=False)["value"].mean()
    income = income.merge(cpi_index, on="year", how="inner")
    income["real_income"] = income["value"] / (income["cpi_index"] / 100)

    return income.sort_values(["geo", "year"]).reset_index(drop=True)


def real_income_growth(income):
    """Percent change in real income from each state's first to last year."""
    def pct_change(x):
        if len(x) < 2 or x.iloc[0] == 0:
            return None
        return (x.iloc[-1] / x.iloc[0] - 1) * 100

    growth = (
        income.sort_values("year")
        .groupby("geo")["real_income"]
        .agg(pct_change)
        .dropna()
        .astype(float)
        .reset_index(name="real_income_growth_pct")
        .sort_values("real_income_growth_pct", ascending=False)
        .reset_index(drop=True)
    )

    return growth
