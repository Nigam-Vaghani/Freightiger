# Freight Tiger Round 2 — 10-Minute Walkthrough Guide & Cheat Sheet

> **Preparation guide for the Software Engineering Intern (AI & Data) Round 2 Walkthrough**  
> Use this script and structured talking points to ace the 10-minute technical interview.

---

## 1. Walkthrough Agenda (10 Minutes Breakdown)

| Time | Phase | Focus & Talking Points |
| :--- | :--- | :--- |
| **0:00 - 1:30** | **Problem & Approach** | High-level problem context, why shipping costs fluctuate, and the 2-tier architectural solution. |
| **1:30 - 3:30** | **Core Data Engine & Math** | Walk through the grouping logic, Monday-Sunday weekly window, trailing 8-week history, and peer averaging formulas. |
| **3:30 - 5:30** | **RAG & Anti-Hallucination Guardrails** | How candidate notes are retrieved and the 3-stage validation gate that prevents fabricated justifications. |
| **5:30 - 7:00** | **Results & Edge Cases Handled** | Spot-checking key rows: `Ahmedabad-Mumbai` (N002), `Chennai-Bangalore` (N001), and trap notes (`N004`, `N005`, `N006`). |
| **7:00 - 8:30** | **Reproducibility & Responsible Spend** | 3-run identical SHA-256 hashes, zero drift, and sub-cent LLM cost. |
| **8:30 - 10:00** | **Demo & Live Q&A** | Brief demo of `interactive_assistant.py` CLI and opening for interviewer discussion. |

---

## 2. Detailed Talking Script

### Minute 0:00 – 1:30: Introduction & Architecture
* **Opening:** *"Hi everyone, today I'm presenting the Smart Shipping Cost Monitoring Assistant. The challenge was to detect abnormal freight cost increases across corridors and explain them in plain English using real-world context notes, with zero tolerance for hallucinations."*
* **Architecture:** *"I designed the system around a **two-tier architecture**:*
  * *Tier 1 is a high-performance, deterministic data engine that computes exact rolling historical baselines and peer route comparisons across 728 route-weeks.*
  * *Tier 2 is an AI and RAG engine that is triggered exclusively when an anomaly is spotted. This design ensures responsible compute spend—less than half a cent for a full multi-year scan—while maintaining 100% determinism."*

---

### Minute 1:30 – 3:30: Core Math & Baselines
* **Formulas:**
  * *"Every shipment is normalized to its Monday `week_of` date.*
  * *Unit freight cost is calculated as: `Total INR / (Quantity in Tonnes * Distance in Km)`.*
  * *For **vs. own history**, we calculate the trailing 8-week rolling average using strictly prior weeks—excluding the current week to eliminate look-ahead bias.*
  * *For **vs. similar routes**, we average all other routes sharing the same `route_type` in that same week, explicitly excluding the route itself from its peer group."*
* **Verification:** *"We verified this against the provided sample rows: Delhi-Jaipur on 2024-11-11 matched the +35.5% past average and +21.0% peer average down to the decimal point."*

---

### Minute 3:30 – 5:30: Context RAG & Anti-Hallucination Guardrails
* **The AI Challenge:** *"The biggest risk in this challenge was hallucination: an LLM inventing a plausible-sounding excuse when no valid note exists."*
* **The 3-Gate Guardrail:**
  1. *Corridor alignment:* Note must apply to the exact corridor or represent an authentic nationwide event (`All Routes`).
  2. *Temporal window:* Events like the Chennai-Bangalore flood (`N001`) have specific validity dates (Feb 24 to Mar 8).
  3. *Cost-causality check:* Notes like `N005` (costs not significantly affected), `N006` (demand stable, no disruptions), and `N010` (costs absorbed without rate change) are explicitly blocked from justifying a rate increase.
* **Result:** *"If no genuine note survives all 3 gates, the system refuses to guess, outputs `flagged: Yes`, leaves `matched_note_id` blank, and notes that the spike requires human review."*

---

### Minute 5:30 – 7:00: Key Findings & Edge Cases
* **Justified Cases:**
  * `Ahmedabad-Mumbai (2025-01-20)`: Identified festival surcharge (`N002`), flagged as `No (justified)`.
  * `Chennai-Bangalore (2025-02-24 & 2025-03-03)`: Identified detour flood costs (`N001`), flagged as `No (justified)`.
* **Trap Note Handling:**
  * `Mumbai-Pune (2025-09-15)`: The closest note in time was `N006` (stable demand). Our guardrail correctly identified that `N006` cannot justify a cost hike, flagging it `Yes` for human review.
  * `Chennai-Bangalore (2025-03-10 & 2025-03-17)`: Note `N009` mentions road conditions returned to normal after flood repairs. The system correctly refused to use it as an excuse for an elevated rate.

---

### Minute 7:00 – 8:30: Reproducibility & Cost Audit
* **Reproducibility:** *"We executed 3 untouched consecutive runs across all 2,940 shipments. All 3 runs produced the identical SHA-256 hash `993f1d4d...` with zero diff in flags, numbers, or verdicts."*
* **Cost Efficiency:** *"We processed 728 route-weeks with only 17 LLM/reasoning calls. Total tokens consumed across the full dataset: 3,198 tokens, yielding an estimated cost of **$0.000439 (less than 4 paise)**."*

---

### Minute 8:30 – 10:00: Interactive CLI Demo & Q&A
* Run `python interactive_assistant.py` and demonstrate a query:
  * *"Why did Chennai-Bangalore spike in March 2025?"*
  * *"What happened on Ahmedabad-Mumbai in January 2025?"*

---

## 3. Anticipated Technical Questions & Strong Answers

### Q1: "Why did you use TF-IDF instead of heavy vector embeddings like ChromaDB / Pinecone?"
> **Answer:** *"For a dataset of 10-100 contextual notes, dense embedding models and external vector databases introduce heavy binary dependencies, network latency, and potential version conflicts for evaluators without adding precision. TF-IDF combined with metadata filtering (corridor and date window) provides microsecond retrieval speed, 100% determinism, and zero external infrastructure overhead. For enterprise scale with millions of notes, we can seamlessly swap the retrieval interface with pgvector or FAISS."*

### Q2: "How would you deploy this pipeline in production at Freight Tiger?"
> **Answer:**
> 1. *"**Streaming Ingestion:** Ingest shipment records via Apache Kafka or AWS Kinesis as trip invoices finalize."*
> 2. *"**Real-time Aggregation:** Use Apache Spark / Flink or dbt scheduled jobs to maintain daily and rolling weekly baselines in ClickHouse or Snowflake."*
> 3. *"**Alerting & Human-in-the-Loop:** Pipe unexplained `flagged: Yes` anomalies into Slack/Teams webhooks or an operations dashboard for logistics managers to renegotiate transporter rates."*

### Q3: "What would happen if an LLM is called with temperature > 0?"
> **Answer:** *"If temperature is > 0, wording may slightly vary. However, because our architecture uses a strict deterministic guardrail layer *before* synthesis, the binary verdict (`flagged`), the cited `matched_note_id`, and the underlying numbers are mathematically locked and can never drift, ensuring absolute business consistency."*
