<div align="center">

# 🐅 Freight Tiger — Smart Shipping Cost Assistant

**Autonomous Monitoring, Baseline Anomaly Detection & Anti-Hallucination RAG for Freight Logistics**

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://pandas.pydata.org/"><img src="https://img.shields.io/badge/Pandas-2.3-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" /></a>
  <a href="https://scikit-learn.org/"><img src="https://img.shields.io/badge/Scikit--Learn-RAG%20Search-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="Scikit-Learn" /></a>
  <img src="https://img.shields.io/badge/Reproducibility-100%25%20Deterministic-success?style=for-the-badge&logo=checkmarx&logoColor=white" alt="Reproducibility" />
  <img src="https://img.shields.io/badge/Total%20Scan%20Cost-%3C%240.0005-blueviolet?style=for-the-badge&logo=google-cloud&logoColor=white" alt="Cost" />
  <img src="https://img.shields.io/badge/License-MIT-2ea44f?style=for-the-badge" alt="License" />
</p>

[Overview](#-overview) •
[Architecture](#-architecture) •
[Mathematical Baselines](#-mathematical-baselines) •
[Guardrails](#-anti-hallucination-guardrails) •
[Quickstart](#-quickstart) •
[Evaluation](#-evaluation--verification) •
[Stretch Goal](#-interactive-qa-assistant-stretch-goal)

---

</div>

## 📌 Overview

In freight transportation, haulage rates frequently fluctuate due to route detours, diesel swings, festive surcharges, or arbitrary transporter hikes. 

This repository contains a **production-grade shipping cost watcher** that:
1. Aggregates multi-year shipment invoices into weekly Monday-to-Sunday buckets.
2. Tracks unit cost per tonne-km against strictly defined **rolling 8-week history** and **weekly peer routes**.
3. Detects anomalous cost surges and searches real-world intelligence notes via **Retrieval-Augmented Generation (RAG)**.
4. Validates justifications using **deterministic anti-hallucination guardrails** (disqualifying non-impact notes like `N004`, `N005`, `N006`, `N008`, `N010`).
5. Generates the exact contract-compliant output CSV (`output.csv`) with zero deviation across multiple runs.

---

## 🏗️ Architecture

```
                       [shipment_records.csv] (2,940 rows)
                                 │
                                 ▼
        ┌──────────────────────────────────────────────────┐
        │  1. Data Engine (src/data_engine.py)             │
        │     - Group by Route & Route Type                │
        │     - Aggregate to Monday `week_of`              │
        │     - Cost/Tonne-Km = Total Cost / Tonne-Km      │
        └────────────────────────┬─────────────────────────┘
                                 │
                                 ▼
        ┌──────────────────────────────────────────────────┐
        │  2. Rolling Baseline Engine                      │
        │     - vs. Own History: Trailing 8 weeks strictly │
        │       prior (no look-ahead, current excluded)    │
        │     - vs. Similar Routes: Same week & route_type │
        │       (self strictly excluded from peer avg)     │
        └────────────────────────┬─────────────────────────┘
                                 │
                                 ▼
        ┌──────────────────────────────────────────────────┐
        │  3. Anomaly Detector (src/anomaly_detector.py)   │
        │     - Statistical cost spike isolation           │
        └────────────────────────┬─────────────────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            │ [Normal Weeks]                          │ [Cost Surge Weeks]
            ▼                                         ▼
   [output_all_weeks.csv]          ┌──────────────────────────────────────┐
   (Flagged: "No")                 │  4. Context RAG (src/rag_engine.py)  │
                                   │     - Hybrid TF-IDF & Temporal Match │
                                   └──────────────────┬───────────────────┘
                                                      │
                                                      ▼
                                   ┌──────────────────────────────────────┐
                                   │  5. Guardrails (src/guardrails.py)   │
                                   │     - Corridor check                 │
                                   │     - Event window validation        │
                                   │     - Positive cost-impact filter    │
                                   └──────────────────┬───────────────────┘
                                                      │
                                                      ▼
                                   ┌──────────────────────────────────────┐
                                   │  6. Reasoning (src/reasoning_agent)  │
                                   │     - Plain-English synthesis        │
                                   │     - Temp=0 / deterministic output  │
                                   └──────────────────┬───────────────────┘
                                                      │
                                                      ▼
                                                 [output.csv]
                                         (Final Graded Submission File)
```

---

## 📐 Mathematical Baselines

### 1. Metric Definition
$$\text{Cost per tonne-km} = \frac{\sum \text{freight\_cost\_inr}}{\sum (\text{quantity\_tonnes} \times \text{distance\_km})}$$

### 2. Comparison Graded Baselines
* **vs. own history:** The route's trailing 8-week rolling average cost per tonne-km strictly prior to the current week ($t-8$ to $t-1$). If $<8$ prior weeks exist, all available prior weeks are averaged without extrapolation or padding.
* **vs. similar routes:** Arithmetic mean cost per tonne-km in that same week across all other routes sharing the same `route_type` (`Short`, `Medium`, `Long`). The route itself is strictly excluded from its peer group.

### 3. Baseline Exact Match Verification
| Corridor | Week of | Cost / Tonne-Km | vs. Own History | vs. Similar Routes | Target Parity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Delhi-Jaipur** | `2024-11-11` | `4.17` | `+35.5%` | `+21.0%` | **100% Match** |
| **Ahmedabad-Mumbai** | `2025-01-20` | `3.29` | `+29.5%` | `+22.5%` | **100% Match** |
| **Mumbai-Pune** | `2025-09-15` | `3.98` | `+9.2%` | `+23.6%` | **100% Match** |

---

## 🛡️ Anti-Hallucination Guardrails

> *"A confident wrong reason scores worse than 'couldn't find one.' We will spot-check justified rows against the given notes. Failed checks are marked fabricated even if the flag was right."*

The pipeline enforces a **3-stage validation gate** before any note can be marked `No (justified)`:
1. **Corridor Verification:** The note must explicitly apply to that corridor or `All Routes`.
2. **Temporal Window Overlap:** Multi-day event dates (e.g., `N001` flood window Feb 24–Mar 8) must overlap with the week under review.
3. **Cost-Impact Filter (Trap Prevention):**
   * `N004` (Toll plaza on routes not in dataset) $\rightarrow$ **REJECTED**
   * `N005` (Maintenance, costs not significantly affected) $\rightarrow$ **REJECTED**
   * `N006` (Stable demand, no disruptions) $\rightarrow$ **REJECTED**
   * `N008` (Normal operations) $\rightarrow$ **REJECTED**
   * `N010` (Tracking costs absorbed by transporters) $\rightarrow$ **REJECTED**

If no note survives all 3 gates, the spike is classified as **`flagged: Yes`**, `matched_note_id` is left empty, and an honest note stating the rise is unexplained is generated.

---

## 🚀 Quickstart

### 1. Installation
```bash
git clone https://github.com/Nigam-Vaghani/Freightiger.git
cd Freightiger
pip install -r requirements.txt
```

### 2. Run Pipeline
Generates `output.csv` (17 investigated anomalies) and `output_all_weeks.csv` (all 728 route-weeks):
```bash
python run_pipeline.py
```

### 3. Run Automated Tests
Executes unit tests verifying baseline mathematics and anti-hallucination gates:
```bash
python -m unittest discover tests
```

### 4. Run Reproducibility & Cost Audit Suite
Executes 3 independent runs, computes SHA-256 hashes, and confirms zero diff:
```bash
python run_reproducibility.py
```

---

## 📊 Evaluation & Verification

### Reproducibility Across 3 Untouched Runs
| Run ID | File Generated | Rows | SHA-256 Checksum | Match Status |
| :--- | :--- | :--- | :--- | :--- |
| **Run #1** | `run_1.csv` | 17 | `993f1d4d11e8c51ce5ad3a06fb496654eda6cca6c2b82d4c6c051c14431f87b8` | Baseline |
| **Run #2** | `run_2.csv` | 17 | `993f1d4d11e8c51ce5ad3a06fb496654eda6cca6c2b82d4c6c051c14431f87b8` | **100% Match** |
| **Run #3** | `run_3.csv` | 17 | `993f1d4d11e8c51ce5ad3a06fb496654eda6cca6c2b82d4c6c051c14431f87b8` | **100% Match** |

### Responsible Token & Cost Audit
| Metric | Full Run Value | Note |
| :--- | :--- | :--- |
| **Shipments Evaluated** | 2,940 records | 100% dataset coverage |
| **Route-Weeks Evaluated** | 728 weeks | 7 corridors over 104 weeks |
| **LLM / Reasoning Calls** | **17 calls** | 0 wasted calls on normal weeks |
| **Total Tokens** | 3,198 tokens | 2,312 input / 886 output |
| **Estimated Scan Cost** | **$0.000439** | **~₹0.038 (less than 4 paise)** |

---

## 💬 Interactive Q&A Assistant (Stretch Goal)

Run the plain-English conversational assistant:
```bash
python interactive_assistant.py
```

```text
FreightTiger Assistant > Why did Chennai-Bangalore get pricier in late February 2025?

Corridor: Chennai-Bangalore | Week of: 2025-02-24
Unit Cost: INR 3.58/tonne-km (+31.5% vs past average, +38.7% vs similar-length routes)
Verdict: No (justified)
Explanation: Matches note N001 dated 2025-02-24: heavy flooding on the highway forced
detours and significantly higher trip costs between Feb 24 and Mar 8.
```

---

## 📁 Repository Structure

```
├── data/                         # Shipment records, context notes, sample schemas
├── src/                          # Core modular package
│   ├── data_engine.py            # Baseline mathematics and weekly grouping
│   ├── anomaly_detector.py       # Dual-threshold cost surge detector
│   ├── rag_engine.py             # TF-IDF & temporal metadata retriever
│   ├── guardrails.py             # Strict anti-hallucination validation gates
│   ├── reasoning_agent.py        # Deterministic plain-English synthesis
│   └── cli.py                    # Interactive Q&A Assistant engine
├── tests/
│   └── test_pipeline.py          # Unit test suite (7/7 tests passing)
├── interactive_assistant.py      # CLI launcher for stretch goal
├── run_pipeline.py               # Main execution pipeline
├── run_reproducibility.py        # 3-run reproducibility audit harness
├── requirements.txt              # Minimal project dependencies
├── output.csv                    # Final graded submission output
├── reproducibility_report.md     # SHA-256 checksum & diff documentation
├── token_cost_log.md             # Token usage & compute cost audit
├── INTERVIEW_WALKTHROUGH.md      # 10-minute Round 2 interview script
└── README.md                     # Project documentation
```

---

<div align="center">
  <b>Built for Freight Tiger Software Engineer Intern (AI & Data) Evaluation</b><br>
  Candidate: <b>Nigam Vaghani</b>
</div>
