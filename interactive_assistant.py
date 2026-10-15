"""
Interactive CLI entrypoint for Freight Tiger Shipping Cost Assistant (Stretch Goal)
Run this script to ask questions about shipping costs and corridor anomalies in plain English.
Usage:
    python interactive_assistant.py
"""

import os
import pandas as pd
from src.cli import start_interactive_cli

if __name__ == '__main__':
    all_weeks_file = 'output_all_weeks.csv'
    notes_file = 'AI Intern Case Study/AI Intern Case Study/context_notes.csv'
    
    if not os.path.exists(all_weeks_file):
        from run_pipeline import run_full_pipeline
        run_full_pipeline(quiet=True)
        
    df_all = pd.read_csv(all_weeks_file)
    df_notes = pd.read_csv(notes_file)
    
    start_interactive_cli(df_all, df_notes)
