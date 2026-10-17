# Real Income by State Explorer

An interactive Streamlit dashboard for U.S. per capita income by state, adjusted for inflation.

Pick a state, a range of years and the year whose dollars you want to see, and the app shows:

- Headline numbers: latest income, real income, real growth over the period, and the state's rank
- A chart of nominal vs real (inflation-adjusted) income over time
- A map and top 10 / bottom 10 tables of real income growth across all states
- A CSV download of the selected state's numbers

You can load your own `cleaned_economic_dataset.xlsx`, or turn on **Use demo data** to try the app with made-up numbers.

## Run it on Windows (easiest)

1. Install Python 3.10 or newer from <https://www.python.org/downloads/>. On the first installer screen, tick **Add python.exe to PATH**.
2. Download this project: on GitHub click **Code → Download ZIP**, then right-click the ZIP and choose **Extract All**.
3. Open the extracted folder and double-click **`run_app.bat`**.

The first launch installs the app's packages, which takes a minute or two. The app then opens in your browser at <http://localhost:8501>. Close the black command window to stop it.

## Run it from a terminal (Windows, macOS or Linux)

```bash
git clone https://github.com/Jay1-cloud1/real-income-state-explorer.git
cd real-income-state-explorer
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Run it in the browser with GitHub Codespaces

On the GitHub page click **Code → Codespaces → Create codespace on main**. The dev container installs everything and starts the app; it opens in a preview tab on port 8501.

## Your data file

Upload an Excel workbook with a sheet named **`cleaned_long`** containing one row per observation:

| Column | Meaning | Example |
|---|---|---|
| `date` | Observation date | 2019-01-01 |
| `geo` | 2-letter state code, or `US` | MD |
| `geo_level` | `state` or `national` | state |
| `series` | Source series ID | CPIAUCSL |
| `topic` | What is measured | income_per_capita |
| `value` | The number | 61234 |

- **Income** rows use `geo_level = state` and a topic containing "income" (preferably `income_per_capita`, e.g. from BEA).
- **Inflation** comes from rows with `geo_level = national` and `series = CPIAUCSL` (monthly CPI is averaged per year).

Real income = nominal income ÷ (annual average CPI ÷ CPI in the chosen year).

## Development

```bash
pip install -r requirements.txt pytest flake8
pytest
flake8 . --max-line-length=127
```

The calculations live in `income_calc.py` and are covered by `tests/`. `app.py` is the Streamlit page.
