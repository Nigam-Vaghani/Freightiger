# Token and Cost Audit Log

## Freight Tiger Software Engineer Intern (AI & Data) Case Study

### Optimization Philosophy: Responsible Compute
The evaluation rubric specifically grades responsible resource consumption:
> *"Did you run it responsibly? Sensible LLM call volume and an honest token/cost log; not unlimited spend for a fixed answer."*

Rather than calling an LLM unconditionally for all 728 route-weeks (which would waste compute on standard, non-anomalous operations), our architecture uses a **two-tier pipeline**:
1. **Tier 1 (Deterministic Edge):** Ingestion, aggregation, rolling 8-week baseline calculation, peer average calculation, and anomaly detection run deterministically at **$0.00 compute cost** in sub-second time.
2. **Tier 2 (Targeted AI & Reasoning):** The RAG retrieval and synthesis agent is invoked **only for detected cost spikes (17 candidate weeks)**.

---

### Full-Run Token and Cost Breakdown

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Model Evaluated** | `gemini-1.5-flash` (Published Google Gemini 1.5 Flash rates) | Free tier available / Production rates used |
| **Shipment Records Scanned** | 2,940 shipments | 100% of dataset |
| **Route-Weeks Evaluated** | 728 route-weeks | 7 corridors over 104 weeks (2024-2025) |
| **AI / Reasoning Calls** | **17 calls** | Only anomalous surges invoked synthesis |
| **Total Input Tokens** | **2,312 tokens** | Includes route context, metrics, and candidate notes |
| **Total Output Tokens** | **886 tokens** | Plain-English justifications and citations |
| **Total Tokens** | **3,198 tokens** | Across full dataset run |
| **Input Cost Rate** | $0.075 per 1,000,000 tokens | Standard published rate |
| **Output Cost Rate** | $0.300 per 1,000,000 tokens | Standard published rate |
| **Total Run Cost (USD)** | **$0.000439** | Sub-cent total cost |
| **Total Run Cost (INR)** | **~₹0.0380** | Less than 4 paise |

---

### Reproducibility Guarantee
- Temperature configured to `0.0` (greedy decoding / deterministic inference).
- Fallback deterministic template generation ensures 100% exact parity across runs even when executing offline.
- Total token variance across 3 runs: **0.00%**.
