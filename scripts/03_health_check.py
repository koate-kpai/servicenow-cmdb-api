"""03_health_check.py — Score CI health based on last seen, compliance, and incidents.

Usage:
    python 03_health_check.py [--threshold 60]
"""
import os
import sys
import argparse
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

INSTANCE = os.getenv('SN_INSTANCE_URL')
CLIENT_ID = os.getenv('SN_CLIENT_ID')
CLIENT_SECRET = os.getenv('SN_CLIENT_SECRET')
USERNAME = os.getenv('SN_USERNAME')
PASSWORD = os.getenv('SN_PASSWORD')

HEALTH_WEIGHTS = {'last_seen': 40, 'incident_count': 30, 'compliance': 30}

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

def get_cis(token, limit=50):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_ci",
        headers=headers,
        params={
            'sysparm_limit': limit,
            'sysparm_display_value': 'true',
            'sysparm_fields': 'sys_id,name,sys_class_name,last_discovered,install_status,operational_status',
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['result']

def get_ci_incidents(token, ci_sys_id):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/incident",
        headers=headers,
        params={
            'sysparm_query': f'cmdb_ci={ci_sys_id}^state<6',
            'sysparm_limit': 100,
            'sysparm_display_value': 'true',
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['result']

def calc_health_score(ci, incident_count):
    now = datetime.now(timezone.utc)

    last_seen_str = ci.get('last_discovered', '')
    last_seen_score = 0
    if last_seen_str:
        try:
            last_seen = datetime.strptime(last_seen_str[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            hours_ago = (now - last_seen).total_seconds() / 3600
            if hours_ago < 24:
                last_seen_score = 40
            elif hours_ago < 72:
                last_seen_score = 25
            elif hours_ago < 168:
                last_seen_score = 10
        except ValueError:
            last_seen_score = 0

    incident_score = max(0, (10 - incident_count) / 10) * 30 if incident_count < 10 else 0

    install_status = ci.get('install_status', '')
    if install_status in ('1', 'Installed'):
        compliance_score = 30
    elif install_status in ('8', 'In Repair'):
        compliance_score = 15
    else:
        compliance_score = 5

    return last_seen_score + incident_score + compliance_score

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CI health check')
    parser.add_argument('--threshold', type=int, default=60, help='Health score threshold (default: 60)')
    args = parser.parse_args()

    token = get_token()
    cis = get_cis(token, limit=50)

    print(f"{'CI Name':25s} {'Class':25s} {'Score':>6s} {'Status':12s} {'Incidents':>10s}")
    print('-' * 80)

    unhealthy = []
    for ci in cis:
        incidents = get_ci_incidents(token, ci['sys_id'])
        score = calc_health_score(ci, len(incidents))
        status = 'HEALTHY' if score >= args.threshold else 'UNHEALTHY'
        name = ci.get('name', '?')[:24]
        cls = ci.get('sys_class_name', '?')[:24]
        print(f"  {name:25s} {cls:25s} {score:5d}/100 {status:12s} {len(incidents):10d}")
        if score < args.threshold:
            unhealthy.append(ci)

    print(f"\nTotal CIs: {len(cis)}")
    print(f"Unhealthy (score < {args.threshold}): {len(unhealthy)}")
    for ci in unhealthy:
        print(f"  ⚠ {ci.get('name', '?')} — score {calc_health_score(ci, len(get_ci_incidents(token, ci['sys_id'])))}/100")
