"""
Interactive Q&A Assistant (Stretch Goal)
Allows users to ask plain-English questions about shipping cost trends and findings.
Example: 'Why did Chennai-Bangalore get pricier in March 2025?'
"""

import sys
import re
from typing import Optional
import pandas as pd


class InteractiveCostAssistant:
    """
    Plain-English query interface answering questions from pipeline results and context notes.
    """
    def __init__(self, analysis_df: pd.DataFrame, notes_df: pd.DataFrame):
        self.df = analysis_df.copy()
        self.notes_df = notes_df.copy()

    def query(self, user_question: str) -> str:
        q = user_question.lower().strip()
        if not q:
            return "Please ask a question about route costs, flags, or timeframes."

        # Detect route mentioned in query
        detected_route = None
        for r in self.df['route'].unique():
            parts = r.lower().split('-')
            if r.lower() in q or (parts[0] in q and parts[1] in q):
                detected_route = r
                break

        # Detect year / month
        year_match = re.search(r'202[45]', q)
        year = year_match.group(0) if year_match else None

        months = {
            'january': '01', 'jan': '01',
            'february': '02', 'feb': '02',
            'march': '03', 'mar': '03',
            'april': '04', 'apr': '04',
            'may': '05',
            'june': '06', 'jun': '06',
            'july': '07', 'jul': '07',
            'august': '08', 'aug': '08',
            'september': '09', 'sep': '09',
            'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }
        detected_month = None
        for m_name, m_num in months.items():
            if re.search(r'\b' + m_name + r'\b', q):
                detected_month = m_num
                break

        # Filter relevant records
        sub = self.df.copy()
        if detected_route:
            sub = sub[sub['route'] == detected_route]
        if year:
            sub = sub[sub['week_of'].str.startswith(year)]
        if detected_month:
            sub = sub[sub['week_of'].str.slice(5, 7) == detected_month]

        if sub.empty:
            return f"I couldn't find records matching your query for corridor '{detected_route or 'any'}' in timeframe '{year or ''}-{detected_month or ''}'."

        # Focus on anomalies or flagged entries if asking "why"
        flagged_sub = sub[sub['flagged'].isin(['Yes', 'No (justified)'])]
        if not flagged_sub.empty:
            responses = []
            for _, r in flagged_sub.iterrows():
                resp = (
                    f"Corridor: {r['route']} | Week of: {r['week_of']}\n"
                    f"Unit Cost: INR {float(r['cost_per_tonne_km']):.2f}/tonne-km ({r['vs_own_history']}, {r['vs_similar_routes']})\n"
                    f"Verdict: {r['flagged']}\n"
                    f"Explanation: {r['reason']}"
                )
                responses.append(resp)
            return "\n\n---\n\n".join(responses)
        else:
            avg_rate = sub['cost_per_tonne_km'].astype(float).mean()
            return (
                f"During this period on {detected_route or 'all routes'}, costs remained within normal parameters.\n"
                f"Average unit cost was INR {avg_rate:.2f} per tonne-km with no flagged anomalies."
            )


def start_interactive_cli(analysis_df: pd.DataFrame, notes_df: pd.DataFrame):
    """
    Launches an interactive prompt for CLI users.
    """
    assistant = InteractiveCostAssistant(analysis_df, notes_df)
    print("=" * 70)
    print("  FREIGHT TIGER SHIPPING COST ASSISTANT - INTERACTIVE Q&A (STRETCH GOAL)")
    print("  Type your question (e.g., 'Why did Chennai-Bangalore spike in March 2025?')")
    print("  Type 'exit' or 'quit' to return.")
    print("=" * 70)

    while True:
        try:
            user_input = input("\nFreightTiger Assistant > ").strip()
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Exiting assistant. Goodbye!")
                break
            if not user_input:
                continue
            answer = assistant.query(user_input)
            print("\n" + answer)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting assistant.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI direct query mode
        query_str = " ".join(sys.argv[1:])
        print(f"Query: {query_str}")
