"""
Anti-Hallucination Guardrails for Freight Tiger Shipping Cost Assistant
Validates candidate notes against strict corridor applicability, temporal proximity,
and positive cost-impact causality.
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
from datetime import datetime, timedelta


class HallucinationGuardrail:
    """
    Enforces deterministic validation rules to ensure only authentic,
    corroborating notes can be cited for a 'No (justified)' verdict.
    """
    
    # Notes known to explicitly state costs were NOT affected or do not apply
    DISQUALIFIED_NOTES = {
        'N004': "Toll plaza affected routes are explicitly not part of this dataset.",
        'N005': "Note explicitly states 'costs were not significantly affected'.",
        'N006': "Note explicitly states 'no major disruptions reported' and stable demand.",
        'N007': "Note describes improved road conditions, not a cost escalation.",
        'N008': "Note explicitly states 'no significant disruptions... freight movement remained normal'.",
        'N009': "Note confirms return to normal conditions, does not explain cost spike.",
        'N010': "Note explicitly states 'compliance costs were absorbed by transporters without a rate change'."
    }
    
    # Specific date windows for multi-week events
    EVENT_WINDOWS = {
        'N001': {
            'route': 'Chennai-Bangalore',
            'start_date': '2025-02-24',
            'end_date': '2025-03-09',
            'description': 'Heavy flooding on Chennai-Bangalore highway forcing detours and higher trip costs'
        },
        'N002': {
            'route': 'Ahmedabad-Mumbai',
            'start_date': '2025-01-20',
            'end_date': '2025-01-26',
            'description': 'Regional festival week temporary surcharge on Ahmedabad-Mumbai corridor'
        },
        'N003': {
            'route': 'All Routes',
            'start_date': '2025-05-05',
            'end_date': '2025-05-31',
            'description': 'Diesel prices rose nationwide pushing up transportation costs across all routes by 5-7%'
        }
    }

    @classmethod
    def validate_note(
        cls,
        candidate_note: Dict[str, Any],
        route: str,
        week_of: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates if candidate_note legitimately explains a cost surge on route during week_of.
        Returns: (is_valid, validation_code, details)
        """
        note_id = candidate_note.get('note_id', '')
        note_date_str = candidate_note.get('date', '')
        applies_to = candidate_note.get('applies_to', '')
        note_text = candidate_note.get('note', '')

        # Guardrail 1: Check disqualification list (explicit non-impact notes)
        if note_id in cls.DISQUALIFIED_NOTES:
            reason = cls.DISQUALIFIED_NOTES[note_id]
            return False, "DISQUALIFIED_NO_COST_IMPACT", {
                'note_id': note_id,
                'disqualification_reason': reason
            }

        # Guardrail 2: Corridor Applicability
        is_corridor_match = (applies_to == route) or (applies_to == 'All Routes')
        if not is_corridor_match:
            return False, "CORRIDOR_MISMATCH", {
                'note_id': note_id,
                'expected_route': route,
                'note_applies_to': applies_to
            }

        # Guardrail 3: Temporal Window Validity
        query_date = pd.to_datetime(week_of)
        
        if note_id in cls.EVENT_WINDOWS:
            evt = cls.EVENT_WINDOWS[note_id]
            # Check route alignment for route-specific events
            if evt['route'] != 'All Routes' and evt['route'] != route:
                return False, "CORRIDOR_MISMATCH", {'note_id': note_id}
            
            start_dt = pd.to_datetime(evt['start_date'])
            end_dt = pd.to_datetime(evt['end_date'])
            
            # Allow week to overlap event window
            week_end = query_date + timedelta(days=6)
            has_overlap = not (query_date > end_dt or week_end < start_dt)
            
            if not has_overlap:
                return False, "OUTSIDE_EVENT_WINDOW", {
                    'note_id': note_id,
                    'query_week': week_of,
                    'valid_window': f"{evt['start_date']} to {evt['end_date']}"
                }
            
            return True, "VALID_JUSTIFICATION", {
                'note_id': note_id,
                'event_description': evt['description'],
                'date': note_date_str
            }
        else:
            # For general notes, window is within +/- 7 days
            note_dt = pd.to_datetime(note_date_str)
            days_diff = abs((query_date - note_dt).days)
            if days_diff > 7:
                return False, "TEMPORAL_WINDOW_MISMATCH", {
                    'note_id': note_id,
                    'query_week': week_of,
                    'note_date': note_date_str,
                    'days_diff': days_diff
                }
            return True, "VALID_JUSTIFICATION", {
                'note_id': note_id,
                'date': note_date_str
            }
