import streamlit as st
import pandas as pd
import plotly.express as px

from income_calc import (
    annual_cpi_index,
    clean_data,
    demo_dataset,
    pick_income_topic,
    real_income_growth,
    state_name,
    state_real_income,
)

st.set_page_config(page_title="Real Income by State Explorer", page_icon="📈", layout="wide")

REQUIRED_COLUMNS = {"date", "geo", "geo_level", "series", "topic", "value"}
DEFAULT_BASE_YEAR = 2017

st.title("Real Income by State Explorer")
st.caption(
    "Compare per capita income across U.S. states after adjusting for inflation "
    "(CPI-U, all items, series CPIAUCSL)."
)

# ---------------------------
# Data source
# ---------------------------
st.sidebar.title("Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload cleaned_economic_dataset.xlsx",
    type=["xlsx"],
    help="An Excel workbook with a sheet named 'cleaned_long' and the columns: "
         + ", ".join(sorted(REQUIRED_COLUMNS)) + ".",
)
use_demo = uploaded_file is None and st.sidebar.toggle(
    "Use demo data",
    help="Made-up numbers so you can try the app without a file.",
)

if uploaded_file is None and not use_demo:
    st.info(
        "**To begin**, upload `cleaned_economic_dataset.xlsx` in the sidebar, "
        "or turn on **Use demo data** to try the app with made-up numbers."
    )
    with st.expander("What the file needs to contain"):
        st.markdown(
            """
A sheet named **`cleaned_long`** with one row per observation and these columns:

| Column | Meaning | Example |
|---|---|---|
| `date` | Observation date | 2019-01-01 |
| `geo` | 2-letter state code, or `US` | MD |
| `geo_level` | `state` or `national` | state |
| `series` | Source series ID | CPIAUCSL |
| `topic` | What is measured | income_per_capita |
| `value` | The number | 61234 |

Income rows use `geo_level = state` and a topic containing "income" (preferably `income_per_capita`).
Inflation comes from rows with `geo_level = national` and `series = CPIAUCSL`.
"""
        )
    st.stop()


@st.cache_data(show_spinner="Reading your workbook…")
def load_data(file):
    df = pd.read_excel(file, sheet_name="cleaned_long", engine="openpyxl")
    return clean_data(df)


@st.cache_data
def load_demo_data():
    return clean_data(demo_dataset())


if use_demo:
    df = load_demo_data()
    st.warning("You're looking at **demo data**. The numbers are made up and are not real statistics.", icon="🧪")
else:
    try:
        df = load_data(uploaded_file)
    except ValueError as e:
        st.error(f"Couldn't read the 'cleaned_long' sheet: {e}")
        st.stop()
    except KeyError as e:
        st.error(f"The 'cleaned_long' sheet is missing column {e}. It needs: {', '.join(sorted(REQUIRED_COLUMNS))}.")
        st.stop()

if df.empty:
    st.error("The 'cleaned_long' sheet has no rows with a valid date and value.")
    st.stop()

# ---------------------------
# Check the data has what we need
# ---------------------------
income_topic = pick_income_topic(df["topic"].unique())
cpi_years = sorted(
    df.loc[(df["geo_level"] == "national") & (df["series"] == "CPIAUCSL"), "year"].unique().tolist()
)
state_list = sorted(
    df.loc[df["geo_level"].eq("state") & (df["geo"].str.len() == 2), "geo"].unique()
)

with st.expander("Data check", expanded=income_topic is None or not cpi_years or not state_list):
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("States", len(state_list))
    c3.metric("Years", f"{int(df['year'].min())}–{int(df['year'].max())}")
    st.write("Topics:", ", ".join(sorted(df["topic"].unique())))
    st.write("Geo levels:", ", ".join(sorted(df["geo_level"].unique())))
    if income_topic == "income_per_capita":
        st.success("income_per_capita is present.")
    elif income_topic:
        st.warning(f"income_per_capita is missing, so the app is using **{income_topic}** instead.")

if income_topic is None:
    st.error("This dataset doesn't include income data. Rebuild it with BEA income enabled.")
    st.stop()

if not cpi_years:
    st.error("This dataset has no national CPI rows (geo_level = national, series = CPIAUCSL) to adjust for inflation.")
    st.stop()

if not state_list:
    st.error("No state-level rows (2-letter state codes) found in the dataset.")
    st.stop()

# ---------------------------
# Controls
# ---------------------------
st.sidebar.title("Controls")

default_state = state_list.index("MD") if "MD" in state_list else 0
state = st.sidebar.selectbox("State", state_list, index=default_state, format_func=lambda c: f"{state_name(c)} ({c})")

income_years = df.loc[df["topic"] == income_topic, "year"]
year_min, year_max = int(income_years.min()), int(income_years.max())
if year_min < year_max:
    year_range = st.sidebar.slider(
        "Year range", year_min, year_max, (min(max(year_min, 2000), year_max), year_max)
    )
else:
    year_range = (year_min, year_max)

base_year = st.sidebar.selectbox(
    "Dollars of year",
    cpi_years,
    index=cpi_years.index(DEFAULT_BASE_YEAR) if DEFAULT_BASE_YEAR in cpi_years else len(cpi_years) - 1,
    help="Real income is shown in this year's dollars.",
)

cpi_index = annual_cpi_index(df, base_year)

if cpi_index is None:
    st.warning(f"No national CPI (CPIAUCSL) data for {base_year}. Pick a different year.")
    st.stop()

# ---------------------------
# Calculations
# ---------------------------
income = state_real_income(df, income_topic, cpi_index)
income = income[income["year"].between(*year_range)]

sel = income[income["geo"] == state]

if sel.empty:
    st.warning(f"No income data for {state_name(state)} between {year_range[0]} and {year_range[1]}.")
    st.stop()

growth = real_income_growth(income)
growth["state"] = growth["geo"].map(state_name)
growth["rank"] = range(1, len(growth) + 1)

first, last = sel.iloc[0], sel.iloc[-1]
state_growth = growth.loc[growth["geo"] == state]
nominal_growth_pct = (last["value"] / first["value"] - 1) * 100 if first["value"] else None

# ---------------------------
# Headline numbers
# ---------------------------
st.subheader(f"{state_name(state)}, {int(first['year'])}–{int(last['year'])}")

m1, m2, m3, m4 = st.columns(4)
m1.metric(f"Income in {int(last['year'])}", f"${last['value']:,.0f}", help="Nominal dollars (not adjusted for inflation).")
m2.metric(f"Real income ({base_year}$)", f"${last['real_income']:,.0f}")
if state_growth.empty:
    m3.metric("Real growth", "n/a")
    m4.metric("Rank among states", "n/a")
else:
    real_pct = state_growth["real_income_growth_pct"].iloc[0]
    m3.metric(
        "Real growth",
        f"{real_pct:+.1f}%",
        delta=f"{nominal_growth_pct:+.1f}% before inflation" if nominal_growth_pct is not None else None,
        delta_color="off",
    )
    m4.metric("Rank among states", f"{int(state_growth['rank'].iloc[0])} of {len(growth)}")

# ---------------------------
# Nominal vs real chart
# ---------------------------
real_label = f"Real ({base_year} dollars)"
chart = sel.rename(columns={"value": "Nominal", "real_income": real_label}).melt(
    id_vars=["year"],
    value_vars=["Nominal", real_label],
    var_name="Type",
    value_name="Income",
)

fig = px.line(
    chart,
    x="year",
    y="Income",
    color="Type",
    markers=True,
    title="Per capita income: nominal vs real",
    labels={"year": "Year", "Income": "Income per person", "Type": ""},
)
fig.update_xaxes(tickformat="d")
fig.update_yaxes(tickprefix="$", tickformat=",.0f")
fig.update_traces(hovertemplate="%{x}: $%{y:,.0f}")
fig.update_layout(legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))

st.plotly_chart(fig, width="stretch")

# ---------------------------
# Rankings
# ---------------------------
st.subheader("Real income growth by state")
st.caption(f"Change from {year_range[0]} to {year_range[1]}, in {base_year} dollars.")

if growth.empty:
    st.info("Pick a year range of at least two years to compare growth across states.")
else:
    map_fig = px.choropleth(
        growth,
        locations="geo",
        locationmode="USA-states",
        scope="usa",
        color="real_income_growth_pct",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        hover_name="state",
        hover_data={"geo": False, "real_income_growth_pct": ":.1f"},
        labels={"real_income_growth_pct": "Real growth (%)"},
    )
    map_fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(orientation="h", y=-0.05, yanchor="top", thickness=12, ticksuffix="%", title_side="top"),
    )
    st.plotly_chart(map_fig, width="stretch")

    table_cols = {
        "rank": st.column_config.NumberColumn("Rank", width="small"),
        "state": st.column_config.TextColumn("State"),
        "real_income_growth_pct": st.column_config.NumberColumn("Real growth", format="%.1f%%"),
    }
    table = growth[["rank", "state", "real_income_growth_pct"]]

    c1, c2 = st.columns(2)
    c1.markdown("**Top 10 states**")
    c1.dataframe(table.head(10), width="stretch", hide_index=True, column_config=table_cols)

    c2.markdown("**Bottom 10 states**")
    c2.dataframe(
        table.tail(10).sort_values("rank", ascending=False),
        width="stretch",
        hide_index=True,
        column_config=table_cols,
    )

# ---------------------------
# Download
# ---------------------------
download = sel.assign(state=state_name(state))[["state", "geo", "year", "value", "cpi_index", "real_income"]].rename(
    columns={"geo": "state_code", "value": "nominal_income", "real_income": f"real_income_{base_year}_dollars"}
)
st.download_button(
    f"Download {state_name(state)} data (CSV)",
    download.round(2).to_csv(index=False).encode("utf-8"),
    file_name=f"{state}_real_income.csv",
    mime="text/csv",
)

st.divider()
st.caption(
    "Real income = nominal income ÷ (annual average CPI ÷ CPI in the chosen year). "
    "Growth compares each state's first and last year in the selected range."
)
