# System Capacity & Care Load Analytics for Unaccompanied Children

**A healthcare-systems analytics project analyzing the CBP → HHS care pipeline for Unaccompanied Alien Children (UAC), built as part of an internship with Unified Mentor (dataset context: U.S. Department of Health and Human Services).**

🔗 **Live Dashboard:** *[https://uac-dashboardgit-gogadfdaq4mloyexfrnqj3.streamlit.app]*

---

## Table of Contents

1. [Project Background](#project-background)
2. [Problem Statement](#problem-statement)
3. [Objectives](#objectives)
4. [Dataset](#dataset)
5. [Project Architecture](#project-architecture)
6. [Methodology, Phase by Phase](#methodology-phase-by-phase)
7. [Key Performance Indicators (KPIs)](#key-performance-indicators-kpis)
8. [Key Findings](#key-findings)
9. [Dashboard Walkthrough](#dashboard-walkthrough)
10. [Repository Structure](#repository-structure)
11. [How to Run This Project](#how-to-run-this-project)
12. [Tech Stack](#tech-stack)
13. [Data Quality & Limitations](#data-quality--limitations)
14. [Possible Future Improvements](#possible-future-improvements)

---

## Project Background

The Unaccompanied Alien Children (UAC) Program is a federally mandated pipeline for children who arrive at the U.S. border without a parent or legal guardian. It works in two stages:

1. **CBP custody** — U.S. Customs and Border Protection apprehends and briefly holds the child.
2. **HHS care** — the child is transferred to the Department of Health and Human Services for medical screening, sheltering, and welfare support, until they're discharged to a vetted sponsor (usually a relative already in the U.S.).

This project treats that two-stage pipeline the same way a hospital system would treat a ward with an admissions queue and a discharge queue: as something with **capacity**, **load**, and **flow**, that can build up pressure or relieve it depending on how intake and outflow balance over time.

## Problem Statement

HHS publishes daily counts, but there is no built-in framework for continuously answering questions like:

- How full is the system right now, and is that changing?
- Is intake outpacing discharge, or the reverse?
- When has the system been under sustained strain, and for how long?
- Is today's situation stable, or historically volatile?

Without this kind of structured view, decisions about staffing and shelter capacity are made reactively rather than proactively. This project turns the raw daily counts into a continuously-updatable analytics layer that answers those questions directly.

## Objectives

**Primary**
- Quantify daily and cumulative care load across CBP and HHS
- Identify periods of capacity strain and relief
- Analyze the balance between intake, transfers, and discharges

**Secondary**
- Support healthcare staffing and shelter planning
- Improve situational awareness for policymakers
- Enable data-driven evaluation of the humanitarian response over time

## Dataset

**Source:** HHS Unaccompanied Alien Children Program daily reporting
**Span:** January 12, 2023 – December 21, 2025
**Raw size:** 720 reported days (plus trailing blank rows removed during cleaning)

| Column | Description |
|---|---|
| Date | Reporting date |
| Children apprehended and placed in CBP custody | Daily intake volume |
| Children in CBP custody | Active CBP care load (a snapshot count) |
| Children transferred out of CBP custody | Flow into the HHS system |
| Children in HHS Care | Active HHS care load (a snapshot count) |
| Children discharged from HHS Care | Successful sponsor placements |

An important distinction drove several design decisions in this project:

- **Stock columns** (`Children in CBP custody`, `Children in HHS Care`) describe a count *at a moment in time*.
- **Flow columns** (`apprehended`, `transferred out`, `discharged`) describe an *event total for that specific day*.

This matters because the data isn't reported every calendar day — treating a missing day the same way for both column types would either invent flow events that never happened, or lose track of a stock count that hasn't actually reset to zero. See [Phase 2](#phase-2--feature-engineering) for how this was handled.

## Project Architecture

The project was built as a linear pipeline, where each phase's output is the next phase's input:

```
Raw CSV
   │
   ▼
[Phase 1] Data Cleaning & Structuring  ──▶ uac_cleaned.csv
   │
   ▼
[Phase 2] Feature Engineering           ──▶ uac_features.csv
   │
   ▼
[Phase 3] EDA & Trend Analysis          ──▶ charts + strain window data
   │
   ▼
[Phase 4] KPI Layer                     ──▶ kpi_snapshot.csv
   │
   ▼
[Phase 5] Streamlit Dashboard (app.py)  ──▶ live, interactive analytics
   │
   ▼
Research Paper + Executive Summary (Phases 6-7)
```

Phases 1–4 were built as Google Colab notebooks (kept as separate, well-commented `.ipynb` files so each step's logic is fully auditable). Phase 5 consumes the final `uac_features.csv` directly and re-implements the KPI formulas natively so the dashboard is self-contained and always reflects the currently loaded data.

## Methodology, Phase by Phase

### Phase 1 — Data Cleaning & Structuring
- Removed ~450 blank trailing rows left over from the raw export
- Standardized column names (e.g. stripped a stray footnote marker from `Children apprehended and placed in CBP custody*`)
- Parsed the `Date` column (originally text like `"December 21, 2025"`) into proper datetime values
- Converted numeric columns from comma-formatted text (e.g. `"2,484"`) into integers
- Sorted chronologically and checked for duplicate dates (none found)
- Identified **355 calendar days with no report** out of the full ~1,075-day span — confirming this is an irregular, not strictly daily, reporting schedule
- Validated two logical constraints the data should obey:
  - `transfers out of CBP ≤ children in CBP custody`
  - `discharges from HHS ≤ children in HHS care`
  - **86 rows** were flagged for the first rule (0 for the second) — noted as an observed anomaly rather than an error, since same-day arrival-and-departure can legitimately produce this pattern

### Phase 2 — Feature Engineering
The cleaned data was reindexed onto a **complete daily calendar** (1,075 days). Applying the stock/flow distinction from above:
- **Stock columns** (`cbp_in_custody`, `hhs_in_care`) were **forward-filled** across gap days — a reasonable assumption, since the real-world count doesn't reset just because a report wasn't published.
- **Flow columns** (`apprehended`, `transferred_out`, `discharged`) were **left blank** on gap days — no daily event count was invented for days with no report.

Derived metrics computed on top of this:

| Metric | Formula |
|---|---|
| Total System Load | `cbp_in_custody + hhs_in_care` |
| Net Daily Intake | `cbp_transferred_out − hhs_discharged` |
| Care Load Growth Rate | Day-over-day % change in Total System Load |
| 7-day / 14-day Rolling Average | Rolling mean of Total System Load |
| Care Load Volatility | 7-day rolling standard deviation of the Growth Rate |
| Backlog Streak | Consecutive days of positive Net Daily Intake |
| Backlog Indicator | `True` when the streak reaches 3+ consecutive days |
| Discharge Offset Ratio | `hhs_discharged / cbp_transferred_out` |

### Phase 3 — EDA & Trend Analysis
Produced daily, weekly, and monthly trend views, a year-over-year comparison, and a **sustained high-load ("strain") window detector**. Rather than a fixed absolute load threshold (which would miss real strain periods given how much the overall load level has shifted over the three years), the detector flags any day in the **top 25% of load values** and reports runs of 7+ consecutive such days as a genuine strain window. This surfaced the project's headline finding — see [Key Findings](#key-findings).

### Phase 4 — KPI Layer
Formalized the five KPIs below as reusable functions, each producing a current value and a plain-language status (e.g. "rising", "relieving backlog"), computed over a trailing 30-day window as of the latest date in the data.

### Phase 5 — Streamlit Dashboard
A live, interactive analytics app (`app.py`) built on Streamlit + Plotly. See [Dashboard Walkthrough](#dashboard-walkthrough) below.

## Key Performance Indicators (KPIs)

| KPI | What it measures | How to read it |
|---|---|---|
| **Total Children Under Care** | System-wide responsibility right now | Higher = more children in the combined pipeline |
| **Net Intake Pressure** | Inflow vs. outflow imbalance | Positive = load building; negative = load relieving |
| **Care Load Volatility Index** | How stable the system is, independent of load level | Higher = more unpredictable day-to-day swings |
| **Backlog Accumulation Rate** | Share of recent days spent in a sustained backlog state | Higher % = pressure has been persistent, not just a one-day spike |
| **Discharge Offset Ratio** | HHS's ability to relieve load | Above 1.0 = discharging faster than intake; below 1.0 = falling behind |

## Key Findings

1. **A 167-day sustained strain window** occurred from **August 1, 2023 to January 14, 2024**, averaging a total system load of ~10,363 children — by far the longest and highest-intensity strain period in the dataset. Two shorter strain windows also occurred (Apr–May 2023, Jan–Mar 2024).
2. **A strong declining trend across the full period**: average total system load fell from **~8,825** (2023) → **~7,324** (2024) → **~2,577** (2025).
3. **Volatility declined alongside load**: the system was noticeably more erratic in 2023 (multiple sharp spikes in the 7-day volatility index) and became markedly calmer through 2025.
4. As of the most recent data (Dec 21, 2025), the system shows: total load **2,502** (rising slightly, +4.4% over the trailing 30 days), net intake pressure mildly positive (load building), low volatility, no active backlog streak, and a discharge offset ratio above 1.0 (currently relieving).

*(Full charts and supporting statistics are in the Phase 3 notebook outputs and the research paper.)*

## Dashboard Walkthrough

The live dashboard has four core modules, matching the project brief:

1. **KPI Summary** — the five KPI cards above, recalculated live for whichever date range is currently selected (not fixed to all-time).
2. **System Load Overview** — Total System Load over time, with optional 7-day / 14-day rolling averages and a strain-threshold reference line.
3. **CBP vs. HHS Load Comparison** — a stacked area chart showing each agency's share of the total system load.
4. **Net Intake & Backlog Trends** — a bar chart of net daily intake (red = building, green = relieving) alongside the current backlog streak length.

**User controls (sidebar):**
- **Date range** — restrict every chart and KPI card to a specific window
- **Time granularity** — Daily / Weekly / Monthly aggregation
- **Metric toggles** — show/hide the rolling averages and strain threshold line

## Repository Structure

```
uac-dashboard/
├── app.py                 # Streamlit dashboard application
├── uac_features.csv       # Cleaned, feature-engineered dataset (dashboard's data source)
├── requirements.txt       # Python dependencies
├── runtime.txt            # Pins the Python version for Streamlit Cloud
└── README.md               # This file

notebooks/ (development artifacts, not required to run the dashboard)
├── Phase1_Data_Cleaning.ipynb
├── Phase2_Feature_Engineering.ipynb
├── Phase3_EDA_Trend_Analysis.ipynb
└── Phase4_KPI_Layer.ipynb
```

## How to Run This Project

**View it live:** *[insert your Streamlit Cloud URL]* — no installation needed.

**Run it locally:**
```bash
pip install -r requirements.txt
streamlit run app.py
```
This opens the dashboard at `http://localhost:8501`.

**Reproduce the analysis from scratch:** open each `Phase*.ipynb` notebook in Google Colab, in order, uploading the previous phase's CSV output when prompted.

## Tech Stack

- **Python** — pandas (data processing), NumPy
- **Streamlit** — dashboard framework
- **Plotly** — interactive charting
- **Google Colab** — notebook development environment
- **Streamlit Community Cloud** — free hosting/deployment

## Data Quality & Limitations

- Reporting is **not strictly daily**; 355 of 1,075 calendar days in the span have no report. Stock values are forward-filled across these gaps; flow values are left blank rather than estimated (see Phase 2 methodology above).
- 86 rows show transfers-out exceeding the same-day CBP custody count. This is flagged in the data but not treated as an error — it can occur legitimately when children both arrive and leave CBP custody within the same reporting day.
- The Discharge Offset Ratio is undefined (division by zero) on any day with zero transfers out; these days are excluded from averages rather than treated as zero or infinite.
- All KPI "trailing 30-day" figures depend on the most recent date present in the loaded dataset — if the CSV isn't refreshed, the dashboard will keep reporting relative to that fixed date.

## Possible Future Improvements

- Automate ingestion of new daily reports (currently a manual CSV refresh)
- Add per-region or per-facility breakdowns if that granularity becomes available in the source data
- Add anomaly alerting (e.g. flag in real time when a new sustained strain window begins)
- Add a forecasting layer (e.g. short-horizon load projection) building on the trend and volatility metrics already computed
