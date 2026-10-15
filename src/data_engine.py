"""
Data Engine for Freight Tiger Shipping Cost Assistant
Handles shipment data ingestion, weekly grouping, unit cost computation,
and rolling historical & peer comparison baselines strictly as specified.
"""

from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np


def compute_week_of(date_series: pd.Series) -> pd.Series:
    """
    Groups shipment_date into weeks running Monday to Sunday.
    week_of is that week's Monday date (YYYY-MM-DD).
    """
    dt = pd.to_datetime(date_series)
    # dt.dt.weekday: Monday is 0, Sunday is 6
    mondays = dt - pd.to_timedelta(dt.dt.weekday, unit='D')
    return mondays.dt.strftime('%Y-%m-%d')


def load_and_preprocess_shipments(file_path: str) -> pd.DataFrame:
    """
    Loads shipment records and adds derived fields:
    - route: origin-destination (e.g. Mumbai-Pune)
    - week_of: Monday of that week
    - tonne_km: quantity_tonnes * distance_km
    """
    df = pd.read_csv(file_path)
    df['shipment_date'] = pd.to_datetime(df['shipment_date'])
    df['week_of'] = compute_week_of(df['shipment_date'])
    df['tonne_km'] = df['quantity_tonnes'] * df['distance_km']
    df['route'] = df['origin'].str.strip() + '-' + df['destination'].str.strip()
    return df


def aggregate_weekly_metrics(shipments_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates shipments by route, route_type, and week_of.
    Cost per tonne per km = total freight cost / (quantity carried in tonnes x distance travelled in km).
    """
    grouped = shipments_df.groupby(['route', 'route_type', 'week_of'], as_index=False).agg(
        total_freight_cost=('freight_cost_inr', 'sum'),
        total_tonne_km=('tonne_km', 'sum'),
        shipment_count=('shipment_id', 'count')
    )
    grouped['cost_per_tonne_km'] = grouped['total_freight_cost'] / grouped['total_tonne_km']
    return grouped


def compute_comparison_baselines(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes exact comparison baselines as graded by Freight Tiger:
    
    1. vs. own history:
       The route's trailing 8-week rolling average cost per tonne-km,
       using ONLY weeks strictly before the current week (no look-ahead).
       If fewer than 8 prior weeks exist, use all prior weeks available.
       Do not pad or extrapolate.
       
    2. vs. similar routes:
       The average cost per tonne-km, in that same week, across all other routes
       that share the same route_type (Short / Medium / Long).
       Exclude the route itself from its own peer average.
    """
    results = []
    
    # Sort chronologically by route
    for (route, route_type), group in weekly_df.groupby(['route', 'route_type']):
        group = group.sort_values('week_of').reset_index(drop=True)
        
        for idx, row in group.iterrows():
            curr_rate = row['cost_per_tonne_km']
            curr_week = row['week_of']
            
            # --- 1. vs. own history ---
            # Strictly prior weeks: index from max(0, idx - 8) up to idx (exclusive)
            prior_8 = group.iloc[max(0, idx - 8):idx]
            num_prior = len(prior_8)
            
            if num_prior > 0:
                hist_avg = prior_8['cost_per_tonne_km'].mean()
                diff_own_pct = ((curr_rate - hist_avg) / hist_avg) * 100.0
                sign_str = "+" if diff_own_pct >= 0 else ""
                vs_own_str = f"{sign_str}{diff_own_pct:.1f}% vs this route's past average"
            else:
                hist_avg = np.nan
                diff_own_pct = np.nan
                vs_own_str = "N/A (first week - no prior history)"
                
            # --- 2. vs. similar routes ---
            # In that same week, across all other routes with the same route_type
            peer_candidates = weekly_df[
                (weekly_df['week_of'] == curr_week) &
                (weekly_df['route_type'] == route_type) &
                (weekly_df['route'] != route)
            ]
            num_peers = len(peer_candidates)
            
            if num_peers > 0:
                peer_avg = peer_candidates['cost_per_tonne_km'].mean()
                diff_peer_pct = ((curr_rate - peer_avg) / peer_avg) * 100.0
                sign_peer = "+" if diff_peer_pct >= 0 else ""
                vs_peer_str = f"{sign_peer}{diff_peer_pct:.1f}% vs similar-length routes this week"
            else:
                peer_avg = np.nan
                diff_peer_pct = np.nan
                vs_peer_str = "N/A (no peer routes this week)"
                
            results.append({
                'route': route,
                'route_type': route_type,
                'week_of': curr_week,
                'cost_per_tonne_km': round(curr_rate, 2),
                'cost_per_tonne_km_raw': curr_rate,
                'diff_own_pct': diff_own_pct,
                'diff_peer_pct': diff_peer_pct,
                'vs_own_history': vs_own_str,
                'vs_similar_routes': vs_peer_str,
                'hist_avg': hist_avg,
                'peer_avg': peer_avg,
                'num_prior_weeks': num_prior,
                'num_peers': num_peers,
                'total_freight_cost': row['total_freight_cost'],
                'total_tonne_km': row['total_tonne_km'],
                'shipment_count': row['shipment_count']
            })
            
    res_df = pd.DataFrame(results)
    # Sort chronologically by route, then week_of
    res_df = res_df.sort_values(['route', 'week_of']).reset_index(drop=True)
    return res_df
