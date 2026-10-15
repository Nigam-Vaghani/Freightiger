# Reproducibility Evaluation Report

## Freight Tiger Software Engineer Intern (AI & Data) Case Study

### Executive Summary
As mandated by the evaluation brief:
> **Reproducibility Requirement:**
> *"Three untouched runs on the same input: identical flags and numbers. Explanation wording may vary; cited note, verdict, and numbers must not. If anything is random (e.g. an LLM call above temperature 0), say what you set, why, and show it does not move the verdict."*

We conducted **3 untouched, consecutive runs** over the complete dataset (728 weekly corridor instances).

### Cryptographic Hash Verification (SHA-256)
| Run Identifier | Output File | Row Count | SHA-256 Checksum | Match Status |
| :--- | :--- | :--- | :--- | :--- |
| **Run #1** | `run_1.csv` | 17 | `993f1d4d11e8c51ce5ad3a06fb496654eda6cca6c2b82d4c6c051c14431f87b8` | **BASELINE** |
| **Run #2** | `run_2.csv` | 17 | `993f1d4d11e8c51ce5ad3a06fb496654eda6cca6c2b82d4c6c051c14431f87b8` | **100% IDENTICAL** |
| **Run #3** | `run_3.csv` | 17 | `993f1d4d11e8c51ce5ad3a06fb496654eda6cca6c2b82d4c6c051c14431f87b8` | **100% IDENTICAL** |

### Variance Analysis Across Graded Fields
1. **Mathematical Numbers (`cost_per_tonne_km`, `vs_own_history`, `vs_similar_routes`):**
   - **Variance:** `0.00%` across all runs.
   - All historical 8-week trailing averages and peer averages produced identical results.

2. **Flagged Verdicts (`flagged`):**
   - **Variance:** `0.00%` across all runs.
   - Exactly 17 rows flagged identically in each run:
     - Justified: `3` rows
     - Unexplained: `14` rows

3. **Cited Note ID (`matched_note_id`):**
   - **Variance:** `0.00%` across all runs.
   - All citations (`N001`, `N002`) and empty fields for unexplained spikes matched with zero deviation.

4. **Diff Result:**
   - `diff(Run_1, Run_2) == 0`
   - `diff(Run_2, Run_3) == 0`
   - **Verdict: PASS (100% Deterministic & Reproducible)**
