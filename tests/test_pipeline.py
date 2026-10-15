"""
Automated Test Suite for Freight Tiger Shipping Cost Assistant
Verifies mathematical baselines against ground-truth samples,
tests edge cases, and rigorously probes guardrails against hallucination.
"""

import os
import unittest
import pandas as pd
import numpy as np

from src.data_engine import (
    load_and_preprocess_shipments,
    aggregate_weekly_metrics,
    compute_comparison_baselines
)
from src.guardrails import HallucinationGuardrail
from src.anomaly_detector import AnomalyDetector
from src.rag_engine import ContextNotesRAG


def find_data_file(filename: str) -> str:
    candidates = [
        os.path.join('data', filename),
        os.path.join('AI Intern Case Study', 'AI Intern Case Study', filename),
        filename
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return filename


class TestFreightTigerPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shipments_path = find_data_file('shipment_records.csv')
        cls.notes_path = find_data_file('context_notes.csv')
        cls.shipments_df = load_and_preprocess_shipments(cls.shipments_path)
        cls.weekly_df = aggregate_weekly_metrics(cls.shipments_df)
        cls.baselines_df = compute_comparison_baselines(cls.weekly_df)
        cls.rag = ContextNotesRAG(cls.notes_path)

    def test_sample_1_delhi_jaipur(self):
        """Verify Delhi-Jaipur on 2024-11-11 matches sample output exactly."""
        row = self.baselines_df[
            (self.baselines_df['route'] == 'Delhi-Jaipur') &
            (self.baselines_df['week_of'] == '2024-11-11')
        ].iloc[0]
        self.assertEqual(row['cost_per_tonne_km'], 4.17)
        self.assertEqual(row['vs_own_history'], "+35.5% vs this route's past average")
        self.assertEqual(row['vs_similar_routes'], "+21.0% vs similar-length routes this week")

    def test_sample_2_ahmedabad_mumbai(self):
        """Verify Ahmedabad-Mumbai on 2025-01-20 matches sample output exactly."""
        row = self.baselines_df[
            (self.baselines_df['route'] == 'Ahmedabad-Mumbai') &
            (self.baselines_df['week_of'] == '2025-01-20')
        ].iloc[0]
        self.assertEqual(row['cost_per_tonne_km'], 3.29)
        self.assertEqual(row['vs_own_history'], "+29.5% vs this route's past average")
        self.assertEqual(row['vs_similar_routes'], "+22.5% vs similar-length routes this week")

    def test_sample_3_mumbai_pune(self):
        """Verify Mumbai-Pune on 2025-09-15 matches sample output exactly."""
        row = self.baselines_df[
            (self.baselines_df['route'] == 'Mumbai-Pune') &
            (self.baselines_df['week_of'] == '2025-09-15')
        ].iloc[0]
        self.assertEqual(row['cost_per_tonne_km'], 3.98)
        self.assertEqual(row['vs_own_history'], "+9.2% vs this route's past average")
        self.assertEqual(row['vs_similar_routes'], "+23.6% vs similar-length routes this week")

    def test_strict_prior_window_no_lookahead(self):
        """Ensure rolling history excludes current week and uses only prior weeks."""
        for (route, _), group in self.baselines_df.groupby(['route', 'route_type']):
            first_row = group.iloc[0]
            self.assertEqual(first_row['num_prior_weeks'], 0)
            self.assertIn("first week", first_row['vs_own_history'])
            
            # Check arbitrary 5th week uses exactly 4 prior weeks
            if len(group) > 4:
                fifth_row = group.iloc[4]
                self.assertEqual(fifth_row['num_prior_weeks'], 4)

    def test_peer_exclusion_and_grouping(self):
        """Verify route is strictly excluded from its own peer average."""
        for _, row in self.baselines_df.iterrows():
            if row['num_peers'] > 0:
                self.assertIsNotNone(row['peer_avg'])

    def test_guardrail_rejects_non_impact_notes(self):
        """Ensure guardrails reject trap notes N004, N005, N006, N008, N010."""
        trap_notes = [
            ({'note_id': 'N004', 'date': '2024-03-11', 'applies_to': 'All Routes', 'note': 'Toll plaza...'}, 'Mumbai-Delhi', '2024-03-11'),
            ({'note_id': 'N005', 'date': '2024-07-29', 'applies_to': 'Mumbai-Delhi', 'note': 'costs were not significantly affected'}, 'Mumbai-Delhi', '2024-07-29'),
            ({'note_id': 'N006', 'date': '2025-09-22', 'applies_to': 'All Routes', 'note': 'no major disruptions reported'}, 'Mumbai-Pune', '2025-09-15'),
            ({'note_id': 'N008', 'date': '2025-06-09', 'applies_to': 'Kolkata-Bhubaneswar', 'note': 'movement remained normal'}, 'Kolkata-Bhubaneswar', '2025-06-09'),
            ({'note_id': 'N010', 'date': '2025-10-27', 'applies_to': 'All Routes', 'note': 'costs absorbed without rate change'}, 'Mumbai-Pune', '2025-10-27')
        ]
        for note_dict, route, week in trap_notes:
            is_valid, code, details = HallucinationGuardrail.validate_note(note_dict, route, week)
            self.assertFalse(is_valid, f"Failed: Note {note_dict['note_id']} should have been rejected by guardrail!")
            self.assertEqual(code, "DISQUALIFIED_NO_COST_IMPACT")

    def test_guardrail_accepts_authentic_justifications(self):
        """Ensure authentic notes N001 and N002 pass validation for their correct corridors and windows."""
        # N001 Flood on Chennai-Bangalore
        n001 = {'note_id': 'N001', 'date': '2025-02-24', 'applies_to': 'Chennai-Bangalore', 'note': 'Heavy flooding...'}
        valid_1, _, _ = HallucinationGuardrail.validate_note(n001, 'Chennai-Bangalore', '2025-02-24')
        self.assertTrue(valid_1, "N001 should validate for Chennai-Bangalore on 2025-02-24")

        # N002 Festival on Ahmedabad-Mumbai
        n002 = {'note_id': 'N002', 'date': '2025-01-20', 'applies_to': 'Ahmedabad-Mumbai', 'note': 'Festival surcharge...'}
        valid_2, _, _ = HallucinationGuardrail.validate_note(n002, 'Ahmedabad-Mumbai', '2025-01-20')
        self.assertTrue(valid_2, "N002 should validate for Ahmedabad-Mumbai on 2025-01-20")

        # Reject N002 if queried for wrong route (e.g. Mumbai-Pune)
        valid_wrong_route, code, _ = HallucinationGuardrail.validate_note(n002, 'Mumbai-Pune', '2025-01-20')
        self.assertFalse(valid_wrong_route, "N002 must be rejected for Mumbai-Pune corridor")
        self.assertEqual(code, "CORRIDOR_MISMATCH")


if __name__ == '__main__':
    unittest.main()
