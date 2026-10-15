"""
Anomaly Detector for Freight Tiger Shipping Cost Assistant
Identifies routes where unit freight cost is rising and looks out of the ordinary
compared to its own trailing 8-week history or peer routes of the same route_type.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class AnomalyDetector:
    """
    Detects cost anomalies using statistical & rule-based thresholds
    calibrated against freight corridor baselines.
    """
    def __init__(
        self,
        own_history_threshold: float = 20.0,
        peer_threshold: float = 20.0,
        joint_own_threshold: float = 10.0,
        joint_peer_threshold: float = 15.0,
        min_positive_rise: float = 5.0
    ):
        """
        Thresholds for detecting when cost is rising and out of the ordinary:
        - own_history_threshold: percentage surge vs trailing 8-week rolling avg
        - peer_threshold: percentage premium vs similar routes in the same week
        - joint_own_threshold / joint_peer_threshold: combined elevated levels
        - min_positive_rise: ensures peer-high costs are also experiencing positive cost rise
        """
        self.own_history_threshold = own_history_threshold
        self.peer_threshold = peer_threshold
        self.joint_own_threshold = joint_own_threshold
        self.joint_peer_threshold = joint_peer_threshold
        self.min_positive_rise = min_positive_rise

    def evaluate_row(self, row: pd.Series) -> Dict[str, Any]:
        """
        Evaluates a single route-week record.
        Returns a dict with 'is_anomaly', 'trigger_reasons', and 'severity_score'.
        """
        diff_own = row.get('diff_own_pct')
        diff_peer = row.get('diff_peer_pct')
        
        # If no baselines available, cannot establish anomaly
        if pd.isna(diff_own) and pd.isna(diff_peer):
            return {
                'is_anomaly': False,
                'triggers': [],
                'severity_score': 0.0
            }

        diff_own_val = 0.0 if pd.isna(diff_own) else float(diff_own)
        diff_peer_val = 0.0 if pd.isna(diff_peer) else float(diff_peer)

        triggers = []
        
        # Condition 1: Sharp cost spike compared to own 8-week trailing history
        if diff_own_val >= self.own_history_threshold:
            triggers.append(f"Sharp historical cost surge (+{diff_own_val:.1f}% vs trailing 8-week avg)")
            
        # Condition 2: Significant cost premium over peer routes in the same week with positive local rise
        if diff_peer_val >= self.peer_threshold and diff_own_val >= self.min_positive_rise:
            triggers.append(f"Substantial peer premium (+{diff_peer_val:.1f}% vs peers, local rise +{diff_own_val:.1f}%)")

        # Condition 3: Joint elevated cost vs both own history and peer corridor
        if diff_own_val >= self.joint_own_threshold and diff_peer_val >= self.joint_peer_threshold:
            triggers.append(f"Joint divergence (+{diff_own_val:.1f}% vs own, +{diff_peer_val:.1f}% vs peers)")

        is_anomaly = len(triggers) > 0
        severity = max(diff_own_val, 0) * 0.5 + max(diff_peer_val, 0) * 0.5

        return {
            'is_anomaly': is_anomaly,
            'triggers': triggers,
            'severity_score': severity
        }

    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Runs anomaly detection across all rows in the weekly baselines dataframe.
        """
        results = []
        for idx, row in df.iterrows():
            eval_res = self.evaluate_row(row)
            results.append({
                'is_cost_surge': eval_res['is_anomaly'],
                'triggers': "; ".join(eval_res['triggers']),
                'severity_score': eval_res['severity_score']
            })
        
        flagged_df = df.copy()
        flagged_meta = pd.DataFrame(results)
        for col in flagged_meta.columns:
            flagged_df[col] = flagged_meta[col]
            
        return flagged_df
