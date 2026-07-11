# UAC Program — System Capacity & Care Load Analytics Dashboard

A Streamlit dashboard analyzing the CBP → HHS care pipeline for unaccompanied
children: system load, capacity strain, and inflow/outflow balance, built from
daily HHS UAC Program reporting data (Jan 2023 – Dec 2025).

## Files in this folder
- `app.py` — the dashboard application
- `uac_features.csv` — the cleaned, feature-engineered dataset the app reads
- `requirements.txt` — Python packages needed to run it

## Option A — Run it locally (fastest way to check it works)
1. Install Python 3.10+ if you don't have it.
2. Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Your browser will open automatically at `http://localhost:8501`.

## Option B — Deploy it live for free (recommended for submission)
Streamlit Community Cloud hosts your app on a public URL for free, using GitHub.

1. **Create a GitHub account** (skip if you have one): github.com/join
2. **Create a new repository**
   - Go to github.com → click the **+** icon (top right) → **New repository**
   - Name it e.g. `uac-care-load-dashboard`
   - Set it to **Public** → click **Create repository**
3. **Upload these 3 files** to the repository
   - On the repo page, click **Add file → Upload files**
   - Drag in `app.py`, `uac_features.csv`, and `requirements.txt`
   - Click **Commit changes**
4. **Deploy on Streamlit Community Cloud**
   - Go to share.streamlit.io and sign in with your GitHub account
   - Click **Create app** → choose **"Deploy a public app from GitHub"**
   - Select your repository, branch `main`, and set the main file path to `app.py`
   - Click **Deploy**
5. Wait 1–2 minutes. You'll get a live URL like
   `https://your-app-name.streamlit.app` — this is what you submit.

## What each dashboard module shows
- **KPI Summary** — 5 headline metrics (Total Under Care, Net Intake Pressure,
  Volatility, Backlog Accumulation Rate, Discharge Offset Ratio), recalculated
  live for whatever date range is selected.
- **System Load Overview** — total system load over time with optional 7-day
  and 14-day rolling averages and a strain threshold reference line.
- **CBP vs HHS Load Comparison** — stacked area chart showing each agency's
  share of the total load.
- **Net Intake & Backlog Trends** — daily net intake (red = load building,
  green = load relieving) alongside the current backlog streak length.

## User controls (sidebar)
- **Date range** — restrict all charts and KPIs to a specific window
- **Time granularity** — Daily / Weekly / Monthly aggregation of the trend charts
- **Metric toggles** — show/hide the 7-day avg, 14-day avg, and strain threshold line

## Data note
Reporting in the source data is irregular (not every calendar day has an
entry). The dataset was reindexed to a full daily calendar in Phase 2 of this
project: capacity counts (stock values) are forward-filled across gap days,
while daily event counts (flow values, e.g. transfers/discharges) are left
blank on unreported days rather than estimated.
