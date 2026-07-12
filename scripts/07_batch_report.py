"""07_batch_report.py — Export CI and asset data to CSV for Power BI ingestion.

Usage:
    python 07_batch_report.py
"""
import os
import sys
import csv
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

INSTANCE = os.getenv('SN_INSTANCE_URL')
CLIENT_ID = os.getenv('SN_CLIENT_ID')
CLIENT_SECRET = os.getenv('SN_CLIENT_SECRET')
USERNAME = os.getenv('SN_USERNAME')
PASSWORD = os.getenv('SN_PASSWORD')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'csv')

def get_token():
    resp = requests.post(f"{INSTANCE}/oauth_token.do", data={
        'grant_type': 'password',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'username': USERNAME,
        'password': PASSWORD,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()['access_token']

def fetch_all(token, table, query='', fields='', limit=10000):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    params = {'sysparm_limit': limit, 'sysparm_display_value': 'true'}
    if query:
        params['sysparm_query'] = query
    if fields:
        params['sysparm_fields'] = fields
    results = []
    offset = 0
    while True:
        params['sysparm_offset'] = offset
        resp = requests.get(
            f"{INSTANCE}/api/now/table/{table}",
            headers=headers, params=params, timeout=60,
        )
        resp.raise_for_status()
        batch = resp.json()['result']
        if not batch:
            break
        results.extend(batch)
        offset += len(batch)
        print(f"  {table}: fetched {len(results)}...")
    return results

def flatten(obj):
    def _val(field):
        v = obj.get(field)
        if isinstance(v, dict):
            return v.get('display_value', v.get('value', ''))
        return v or ''
    return {
        k.rstrip('_'): _val(k)
        for k in obj if not k.startswith('sys_')
    }

def export_csv(filename, fieldnames, rows):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"  → {path} ({len(rows)} rows)")

if __name__ == '__main__':
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    token = get_token()

    print("\n=== Exporting CMDB CIs ===")
    ci_fields = 'name,sys_class_name,environment,operational_status,location,install_status,managed_by,assigned_to,last_discovered,os,ip_address'
    cis = fetch_all(token, 'cmdb_ci', 'install_status=1', ci_fields)
    export_csv(f'ci_inventory_{timestamp}.csv', ci_fields.split(','), [flatten(ci) for ci in cis])

    print("\n=== Exporting CI Relationships ===")
    rel_fields = 'parent.name,child.name,type_display'
    rels = fetch_all(token, 'cmdb_rel_ci', '', rel_fields)
    export_csv(f'ci_relationships_{timestamp}.csv', rel_fields.split(','), [flatten(r) for r in rels])

    print("\n=== Exporting Assets ===")
    asset_fields = 'asset_tag,display_name,model_id,sys_class_name,installed,department,cost,depreciation_method,salvage_value,residual_date,retired'
    assets = fetch_all(token, 'alm_asset', '', asset_fields)
    export_csv(f'assets_{timestamp}.csv', asset_fields.split(','), [flatten(a) for a in assets])

    print(f"\nDone. All exports in {OUTPUT_DIR}")
