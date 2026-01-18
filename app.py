import streamlit as st
import pandas as pd
import plotly.express as px

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

# ---------------------------
# Load data
# ---------------------------
@st.cache_data(show_spinner=True)
def load_data(file):
    df = pd.read_excel(file, sheet_name="cleaned_long", engine="openpyxl")

    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["geo"] = df["geo"].astype(str).str.upper()
    df["series"] = df["series"].astype(str)
    df["topic"] = df["topic"].astype(str)

    df = df.dropna(subset=["date", "value"]).copy()
    df["year"] = df["date"].dt.year

    return df

df = load_data(uploaded_file)
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

state = st.sidebar.selectbox("State", state_list if state_list else ["MD"])

year_min, year_max = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider("Year range", year_min, year_max, (max(year_min, 2000), year_max))

# ---------------------------
# CPI Deflator
# ---------------------------
base_year = st.sidebar.number_input("Deflation base year", 1985, 2030, 2017)

cpi = df[(df["geo_level"] == "national") & (df["series"] == "CPIAUCSL")].copy()
cpi["year"] = cpi["date"].dt.year

cpi_annual = cpi.groupby("year", as_index=False)["value"].mean()
base_cpi = cpi_annual.loc[cpi_annual["year"] == base_year, "value"].mean()

if pd.isna(base_cpi) or base_cpi == 0:
    st.warning("Invalid CPI base year selected.")
    st.stop()

cpi_annual["cpi_index"] = (cpi_annual["value"] / base_cpi) * 100

# ---------------------------
# Income data
# ---------------------------
income_topics = [t for t in df["topic"].unique().tolist() if "income" in str(t).lower()]
if "income_per_capita" in df["topic"].unique():
    income_topic = "income_per_capita"
elif income_topics:
    income_topic = income_topics[0]
else:
    income_topic = None

if income_topic is None:
    st.error("This dataset doesn't include income data. Choose a different view or rebuild with BEA enabled.")
    st.stop()

income = df[(df["topic"] == income_topic) & (df["geo_level"] == "state") & (df["geo"].str.len() == 2)].copy()

# ---------------------------
# Display
# ---------------------------
st.subheader(f"{state} — Nominal vs Real Income")

if sel.empty:
    st.warning("No income data for selected state.")
    st.stop()

chart = sel.melt(
    id_vars=["year"],
    value_vars=["value", "real_income"],
    var_name="Type",
    value_name="Income"
)

fig = px.line(
    chart,
    x="year",
    y="Income",
    color="Type",
    markers=True,
    labels={"value": "Nominal", "real_income": f"Real ({base_year}$)"},
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Rankings
# ---------------------------
st.subheader("Real Income Growth by State")

growth = (
    income.sort_values("year")
    .groupby("geo")["real_income"]
    .agg(lambda x: (x.iloc[-1] / x.iloc[0] - 1) * 100 if len(x) > 1 else None)
    .dropna()
    .reset_index(name="real_income_growth_pct")
    .sort_values("real_income_growth_pct", ascending=False)
)

c1, c2 = st.columns(2)
c1.write("Top 10 States")
c1.dataframe(growth.head(10), use_container_width=True)

c2.write("Bottom 10 States")
c2.dataframe(growth.tail(10).sort_values("real_income_growth_pct"), use_container_width=True)

# ---------------------------
# Download
# ---------------------------
st.download_button(
    f"Download {state} real income data",
    sel.to_csv(index=False).encode("utf-8"),
    file_name=f"{state}_real_income.csv",
    mime="text/csv",
)

st.caption("No folders. No paths. Just upload and go.")
