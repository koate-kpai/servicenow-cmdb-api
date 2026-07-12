"""04_asset_lifecycle.py — Track asset lifecycle from procurement to retirement.

Usage:
    python 04_asset_lifecycle.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

INSTANCE = os.getenv('SN_INSTANCE_URL')
CLIENT_ID = os.getenv('SN_CLIENT_ID')
CLIENT_SECRET = os.getenv('SN_CLIENT_SECRET')
USERNAME = os.getenv('SN_USERNAME')
PASSWORD = os.getenv('SN_PASSWORD')

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

def query_assets(token, query=None, limit=20):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    params = {
        'sysparm_limit': limit,
        'sysparm_display_value': 'true',
        'sysparm_fields': (
            'sys_id,asset_tag,display_name,model_id,sys_class_name,'
            'installed,department,cost,residual_date,retired,'
            'depreciation_method,salvage_value,comments'
        ),
    }
    if query:
        params['sysparm_query'] = query
    resp = requests.get(
        f"{INSTANCE}/api/now/table/alm_asset",
        headers=headers,
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['result']

if __name__ == '__main__':
    token = get_token()

    print("=== Active assets (installed=Yes) ===")
    active = query_assets(token, query='installed=true^ORDERBYasset_tag', limit=10)
    for a in active:
        model = a.get('model_id', {}).get('display_value', 'N/A')[:25]
        dept = a.get('department', '')[:20]
        cost = a.get('cost', '')
        print(f"  {a.get('asset_tag',''):15s} | {model:25s} | {dept:20s} | cost={cost}")

    print("\n=== Retired assets ===")
    retired = query_assets(token, query='retired=true^ORDERBYasset_tag', limit=10)
    for a in retired:
        model = a.get('model_id', {}).get('display_value', 'N/A')[:25]
        retired_date = a.get('residual_date', '')
        print(f"  {a.get('asset_tag',''):15s} | {model:25s} | retired={retired_date}")

    print("\n=== Lifecycle summary ===")
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    for status, label in [('installed=true', 'Active'), ('retired=true', 'Retired'),
                          ('installed=false^retired=false', 'In Stock')]:
        resp = requests.get(
            f"{INSTANCE}/api/now/table/alm_asset",
            headers=headers,
            params={'sysparm_query': status, 'sysparm_limit': 1, 'sysparm_count': 'true'},
            timeout=30,
        )
        count = resp.headers.get('X-Total-Count', '0')
        print(f"  {label:12s}: {count}")
