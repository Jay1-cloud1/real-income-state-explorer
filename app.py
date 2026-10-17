import streamlit as st
import pandas as pd
import plotly.express as px

from income_calc import (
    annual_cpi_index,
    clean_data,
    pick_income_topic,
    real_income_growth,
    state_real_income,
)

st.set_page_config(page_title="Real Income by State Explorer", layout="wide")

st.title("Real Income by State Explorer")
st.caption("Upload your cleaned economic dataset to begin")

# ---------------------------
# Upload file
# ---------------------------
uploaded_file = st.file_uploader(
    "Upload cleaned_economic_dataset.xlsx",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Please upload cleaned_economic_dataset.xlsx to continue.")
    st.stop()

REQUIRED_COLUMNS = {"date", "geo", "geo_level", "series", "topic", "value"}

# ---------------------------
# Load data
# ---------------------------


@st.cache_data(show_spinner=True)
def load_data(file):
    df = pd.read_excel(file, sheet_name="cleaned_long", engine="openpyxl")
    return clean_data(df)


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

st.subheader("Data check (what's in your file)")
st.write("Topics:", sorted(df["topic"].unique().tolist()))
st.write("Geo levels:", sorted(df["geo_level"].unique().tolist()))

if "income_per_capita" in df["topic"].unique():
    st.success("✅ income_per_capita is present")
else:
    st.error("❌ income_per_capita is NOT present (BEA data missing)")

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.title("Controls")

state_list = sorted(
    df.loc[df["geo_level"].eq("state") & (df["geo"].str.len() == 2), "geo"].unique()
)

if not state_list:
    st.error("No state-level rows (2-letter state codes) found in the dataset.")
    st.stop()

state = st.sidebar.selectbox("State", state_list)

year_min, year_max = int(df["year"].min()), int(df["year"].max())
if year_min < year_max:
    year_range = st.sidebar.slider(
        "Year range", year_min, year_max, (min(max(year_min, 2000), year_max), year_max)
    )
else:
    year_range = (year_min, year_max)

# ---------------------------
# CPI Deflator
# ---------------------------
base_year = int(st.sidebar.number_input("Deflation base year", 1985, 2030, 2017))

cpi_index = annual_cpi_index(df, base_year)

if cpi_index is None:
    st.warning(f"No national CPI (CPIAUCSL) data for {base_year}. Pick a different base year.")
    st.stop()

# ---------------------------
# Income data
# ---------------------------
income_topic = pick_income_topic(df["topic"].unique())

if income_topic is None:
    st.error("This dataset doesn't include income data. Choose a different view or rebuild with BEA enabled.")
    st.stop()

income = state_real_income(df, income_topic, cpi_index)
income = income[income["year"].between(*year_range)]

sel = income[income["geo"] == state]

# ---------------------------
# Display
# ---------------------------
st.subheader(f"{state} — Nominal vs Real Income")

if sel.empty:
    st.warning("No income data for selected state.")
    st.stop()

chart = sel.rename(columns={"value": "Nominal", "real_income": f"Real ({base_year}$)"}).melt(
    id_vars=["year"],
    value_vars=["Nominal", f"Real ({base_year}$)"],
    var_name="Type",
    value_name="Income"
)

fig = px.line(
    chart,
    x="year",
    y="Income",
    color="Type",
    markers=True,
)

fig.update_xaxes(tickformat="d")

st.plotly_chart(fig, width="stretch")

# ---------------------------
# Rankings
# ---------------------------
st.subheader("Real Income Growth by State")

st.caption(f"{year_range[0]}–{year_range[1]}, in {base_year} dollars")

growth = real_income_growth(income)

c1, c2 = st.columns(2)
c1.write("Top 10 States")
c1.dataframe(growth.head(10), width="stretch", hide_index=True)

c2.write("Bottom 10 States")
c2.dataframe(growth.tail(10).sort_values("real_income_growth_pct"), width="stretch", hide_index=True)

# ---------------------------
# Download
# ---------------------------
st.download_button(
    f"Download {state} real income data",
    sel.rename(columns={"geo": "state", "value": "nominal_income"}).to_csv(index=False).encode("utf-8"),
    file_name=f"{state}_real_income.csv",
    mime="text/csv",
)

st.caption("No folders. No paths. Just upload and go.")
