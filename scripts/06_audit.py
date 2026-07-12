"""06_audit.py — Run compliance audits against CMDB and flag discrepancies.

Usage:
    python 06_audit.py
"""
import os
import sys
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

INSTANCE = os.getenv('SN_INSTANCE_URL')
CLIENT_ID = os.getenv('SN_CLIENT_ID')
CLIENT_SECRET = os.getenv('SN_CLIENT_SECRET')
USERNAME = os.getenv('SN_USERNAME')
PASSWORD = os.getenv('SN_PASSWORD')

AUDIT_RULES = [
    {'name': 'Missing Location', 'table': 'cmdb_ci', 'query': 'locationISEMPTY^install_status=1',
     'severity': 'Medium', 'action': 'Assign location'},
    {'name': 'Undiscovered > 7 Days', 'table': 'cmdb_ci', 'query': 'last_discoveredONLast 7 days@javascript:gs.beginningOfLast7Days()@javascript:gs.endOfLast7Days()',
     'severity': 'High', 'action': 'Verify discovery source'},
    {'name': 'Orphaned Asset (no CI)', 'table': 'alm_asset', 'query': 'ciISEMPTY^installed=true',
     'severity': 'High', 'action': 'Link to CI or retire'},
    {'name': 'In Repair > 14 Days', 'table': 'cmdb_ci', 'query': 'install_status=8^sys_updated_onONLast 14 days@javascript:gs.beginningOfLast14Days()@javascript:gs.endOfLast14Days()',
     'severity': 'Low', 'action': 'Review repair status'},
    {'name': 'No Assigned Owner', 'table': 'cmdb_ci', 'query': 'managed_byISEMPTY^install_status=1',
     'severity': 'Medium', 'action': 'Assign CI owner'},
]

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

def run_audit_rule(token, rule):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/{rule['table']}",
        headers=headers,
        params={
            'sysparm_query': rule['query'],
            'sysparm_limit': 100,
            'sysparm_count': 'true',
            'sysparm_display_value': 'true',
            'sysparm_fields': 'sys_id,name,last_discovered,location,managed_by,install_status',
        },
        timeout=30,
    )
    resp.raise_for_status()
    count = resp.headers.get('X-Total-Count', '0')
    items = resp.json()['result']
    return int(count), items

if __name__ == '__main__':
    token = get_token()

    print(f"CMDB Compliance Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('=' * 80)

    total_findings = 0
    for rule in AUDIT_RULES:
        count, items = run_audit_rule(token, rule)
        total_findings += count
        icon = '🔴' if count > 0 else '✅'
        print(f"\n{icon} {rule['name']} ({rule['severity']})")
        print(f"   {rule['action']}")
        print(f"   Findings: {count}")

        for item in items[:5]:
            name = item.get('name', item.get('display_name', '?'))
            print(f"     - {name}")
        if count > 5:
            print(f"     ... and {count - 5} more")

    print(f"\n{'=' * 80}")
    print(f"Total audit findings: {total_findings}")

    if total_findings > 0:
        print("\nRecommendations:")
        print("  1. Prioritise High severity items for immediate remediation")
        print("  2. Assign CI owners for unmanaged CIs")
        print("  3. Verify discovery sources for CIs not seen in 7+ days")
        print("  4. Schedule quarterly CMDB health reviews")
