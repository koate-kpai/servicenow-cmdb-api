"""08_dashboard.py — Generate interactive Plotly HTML dashboard for CMDB and asset metrics.

Usage:
    python 08_dashboard.py [--ci-csv ci_inventory_<date>.csv] [--asset-csv assets_<date>.csv]
"""
import os
import sys
import argparse
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'html')
CSV_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'csv')


def latest_csv(prefix):
    files = sorted(
        [f for f in os.listdir(CSV_DIR) if f.startswith(prefix) and f.endswith('.csv')],
        reverse=True,
    )
    return os.path.join(CSV_DIR, files[0]) if files else None


def load_data(ci_csv_path, asset_csv_path):
    if ci_csv_path and os.path.exists(ci_csv_path):
        ci_df = pd.read_csv(ci_csv_path)
    else:
        sys.exit("CI CSV not found. Run 07_batch_report.py first.")
    asset_df = pd.read_csv(asset_csv_path) if asset_csv_path and os.path.exists(asset_csv_path) else pd.DataFrame()
    return ci_df, asset_df


def build_dashboard(ci_df, asset_df):
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'CIs by Class', 'CIs by Environment',
            'Operational Status', 'CIs by Location (Top 10)',
            'Install Status', 'Assets by Department',
        ),
        specs=[
            [{'type': 'bar'}, {'type': 'pie'}],
            [{'type': 'pie'}, {'type': 'bar'}],
            [{'type': 'bar'}, {'type': 'bar'}],
        ],
        vertical_spacing=0.12, horizontal_spacing=0.1,
    )

    class_counts = ci_df['sys_class_name'].value_counts().head(10)
    fig.add_trace(go.Bar(
        x=class_counts.values, y=class_counts.index, orientation='h',
        marker_color=px.colors.qualifier.Set2[:len(class_counts)],
        text=class_counts.values, textposition='auto',
    ), row=1, col=1)

    env_counts = ci_df['environment'].value_counts()
    fig.add_trace(go.Pie(
        labels=env_counts.index, values=env_counts.values,
        marker=dict(colors=px.colors.qualifier.Pastel),
    ), row=1, col=2)

    if 'operational_status' in ci_df.columns:
        op_counts = ci_df['operational_status'].value_counts()
        fig.add_trace(go.Pie(
            labels=op_counts.index, values=op_counts.values,
            marker=dict(colors=px.colors.qualifier.Set3),
        ), row=2, col=1)

    if 'location' in ci_df.columns:
        loc_counts = ci_df['location'].value_counts().head(10)
        fig.add_trace(go.Bar(
            x=loc_counts.values, y=loc_counts.index, orientation='h',
            marker_color='#3498db', text=loc_counts.values, textposition='auto',
        ), row=2, col=2)

    if 'install_status' in ci_df.columns:
        inst_counts = ci_df['install_status'].value_counts()
        fig.add_trace(go.Bar(
            x=inst_counts.index, y=inst_counts.values,
            marker_color='#9b59b6', text=inst_counts.values, textposition='auto',
        ), row=3, col=1)

    if not asset_df.empty and 'department' in asset_df.columns:
        dept_counts = asset_df['department'].value_counts().head(10)
        fig.add_trace(go.Bar(
            x=dept_counts.index, y=dept_counts.values,
            marker_color='#2ecc71', text=dept_counts.values, textposition='auto',
        ), row=3, col=2)

    fig.update_layout(
        title_text='CMDB & Asset Management Dashboard — Live Data',
        height=900, showlegend=False,
    )
    return fig


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate CMDB dashboard')
    parser.add_argument('--ci-csv', default='')
    parser.add_argument('--asset-csv', default='')
    args = parser.parse_args()

    ci_path = args.ci_csv or latest_csv('ci_inventory')
    asset_path = args.asset_csv or latest_csv('assets')

    ci_df, asset_df = load_data(ci_path, asset_path)
    fig = build_dashboard(ci_df, asset_df)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, 'cmdb_dashboard.html')
    fig.write_html(output_path)
    print(f"Dashboard generated: {output_path}")
