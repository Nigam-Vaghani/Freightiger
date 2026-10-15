"""
Main Execution Pipeline for Freight Tiger Shipping Cost Assistant
Ingests shipment records & context notes, computes historical & peer baselines,
detects cost surges, enforces anti-hallucination guardrails, and outputs final CSVs.
"""

import os
import sys
import argparse
from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np

from src.data_engine import (
    load_and_preprocess_shipments,
    aggregate_weekly_metrics,
    compute_comparison_baselines
)
from src.anomaly_detector import AnomalyDetector
from src.rag_engine import ContextNotesRAG
from src.guardrails import HallucinationGuardrail
from src.reasoning_agent import ReasoningAgent


def find_data_file(filename: str) -> str:
    """Finds dataset file dynamically across standard locations."""
    candidates = [
        os.path.join('data', filename),
        os.path.join('AI Intern Case Study', 'AI Intern Case Study', filename),
        filename
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return filename


def run_full_pipeline(
    shipments_path: Optional[str] = None,
    notes_path: Optional[str] = None,
    output_anomalies_path: str = 'output.csv',
    output_all_weeks_path: str = 'output_all_weeks.csv',
    quiet: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    if shipments_path is None:
        shipments_path = find_data_file('shipment_records.csv')
    if notes_path is None:
        notes_path = find_data_file('context_notes.csv')
    if not quiet:
        print("=" * 75)
        print(" FREIGHT TIGER - SMART SHIPPING COST MONITORING ASSISTANT")
        print("=" * 75)
        print(f"Loading shipment data: {shipments_path}")
        print(f"Loading context notes: {notes_path}")

    # 1. Ingestion and Weekly Aggregation
    shipments_df = load_and_preprocess_shipments(shipments_path)
    weekly_df = aggregate_weekly_metrics(shipments_df)
    
    # 2. Comparison Baselines (Strict Formulas)
    baselines_df = compute_comparison_baselines(weekly_df)
    if not quiet:
        print(f"Total weekly route records: {len(baselines_df)}")

    # 3. Anomaly Detection
    detector = AnomalyDetector()
    flagged_df = detector.detect_anomalies(baselines_df)
    
    # 4. RAG and Reasoning Setup
    rag = ContextNotesRAG(notes_path)
    agent = ReasoningAgent()
    
    anomalies_records = []
    all_records = []
    
    for idx, row in flagged_df.iterrows():
        route = row['route']
        week_of = row['week_of']
        cost_rate = row['cost_per_tonne_km']
        vs_own = row['vs_own_history']
        vs_peer = row['vs_similar_routes']
        is_surge = row['is_cost_surge']
        diff_own = row['diff_own_pct']
        diff_peer = row['diff_peer_pct']
        
        if is_surge:
            # Retrieve candidate notes via hybrid RAG
            candidates = rag.retrieve_candidates(route, week_of, top_k=3)
            
            # Evaluate candidates against deterministic guardrails
            guardrail_evals = []
            for cand in candidates:
                is_valid, code, details = HallucinationGuardrail.validate_note(cand, route, week_of)
                guardrail_evals.append((is_valid, code, details))
                
            # Synthesize explanation via Reasoning Agent
            agent_result = agent.explain_anomaly(
                route=route,
                week_of=week_of,
                cost_per_tonne_km=cost_rate,
                diff_own=0.0 if pd.isna(diff_own) else diff_own,
                diff_peer=0.0 if pd.isna(diff_peer) else diff_peer,
                candidates=candidates,
                guardrail_results=guardrail_evals
            )
            
            entry = {
                'route': route,
                'week_of': week_of,
                'cost_per_tonne_km': f"{cost_rate:.2f}",
                'vs_own_history': vs_own,
                'vs_similar_routes': vs_peer,
                'flagged': agent_result['flagged'],
                'matched_note_id': agent_result['matched_note_id'],
                'reason': agent_result['reason']
            }
            anomalies_records.append(entry)
            all_records.append(entry)
        else:
            entry = {
                'route': route,
                'week_of': week_of,
                'cost_per_tonne_km': f"{cost_rate:.2f}",
                'vs_own_history': vs_own,
                'vs_similar_routes': vs_peer,
                'flagged': "No",
                'matched_note_id': "",
                'reason': "Cost per tonne-km is within normal historical and peer boundaries."
            }
            all_records.append(entry)

    df_anomalies = pd.DataFrame(anomalies_records)
    df_all = pd.DataFrame(all_records)

    # Save to CSV
    cols = ['route', 'week_of', 'cost_per_tonne_km', 'vs_own_history', 'vs_similar_routes', 'flagged', 'matched_note_id', 'reason']
    df_anomalies = df_anomalies[cols]
    df_all = df_all[cols]

    df_anomalies.to_csv(output_anomalies_path, index=False)
    df_all.to_csv(output_all_weeks_path, index=False)

    token_summary = agent.get_token_and_cost_summary()

    if not quiet:
        print("\n" + "=" * 75)
        print(" EXECUTION SUMMARY")
        print("=" * 75)
        print(f"Total Corridors Analyzed:        {baselines_df['route'].nunique()}")
        print(f"Total Route-Weeks Processed:     {len(baselines_df)}")
        print(f"Cost Surges Detected:            {len(df_anomalies)}")
        justified_count = (df_anomalies['flagged'] == 'No (justified)').sum()
        unexplained_count = (df_anomalies['flagged'] == 'Yes').sum()
        print(f"  - Justified by Context Notes:  {justified_count}")
        print(f"  - Unexplained (Flagged 'Yes'): {unexplained_count}")
        print(f"\nOutputs Generated:")
        print(f"  1. Primary Submission File:    {output_anomalies_path} ({len(df_anomalies)} rows)")
        print(f"  2. Complete Weekly Log:        {output_all_weeks_path} ({len(df_all)} rows)")
        print("\nToken & Cost Audit:")
        print(f"  LLM / Reasoning Calls:         {token_summary['llm_calls']}")
        print(f"  Total Input Tokens:            {token_summary['total_input_tokens']:,}")
        print(f"  Total Output Tokens:           {token_summary['total_output_tokens']:,}")
        print(f"  Total Tokens:                  {token_summary['total_tokens']:,}")
        print(f"  Estimated Full-Run Cost:       ${token_summary['estimated_cost_usd']:.6f} ({token_summary['cost_in_cents']:.4f} cents)")
        print("=" * 75)

    return df_anomalies, df_all, token_summary


if __name__ == '__main__':
    run_full_pipeline()
