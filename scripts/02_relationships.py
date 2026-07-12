"""02_relationships.py — Map CI-to-CI relationships and dependency chains.

Usage:
    python 02_relationships.py [--ci-name <ci_name>]
"""
import os
import sys
import argparse
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

def get_ci_sys_id(token, name):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_ci",
        headers=headers,
        params={'sysparm_query': f'name={name}', 'sysparm_limit': 1, 'sysparm_display_value': 'true'},
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json()['result']
    if not results:
        sys.exit(f"CI '{name}' not found.")
    return results[0]['sys_id']

def get_relationships(token, ci_sys_id):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    params = {
        'sysparm_query': f'sys_id={ci_sys_id}',
        'sysparm_display_value': 'true',
        'sysparm_fields': 'sys_id,parent,child,type,parent.name,child.name',
    }

    parent_resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_rel_ci",
        headers=headers,
        params={**params, 'sysparm_query': f'child={ci_sys_id}'},
        timeout=30,
    )
    child_resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_rel_ci",
        headers=headers,
        params={**params, 'sysparm_query': f'parent={ci_sys_id}'},
        timeout=30,
    )
    parent_resp.raise_for_status()
    child_resp.raise_for_status()

    return parent_resp.json()['result'] + child_resp.json()['result']

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Show CI relationship map')
    parser.add_argument('--ci-name', default='', help='CI name to inspect. Defaults to all relationships.')
    args = parser.parse_args()

    token = get_token()

    if args.ci_name:
        sys_id = get_ci_sys_id(token, args.ci_name)
        rels = get_relationships(token, sys_id)
        print(f"\n=== Relationships for {args.ci_name} ({len(rels)} total) ===")
        for rel in rels:
            parent = rel.get('parent', {}).get('display_value', '')
            child = rel.get('child', {}).get('display_value', '')
            rtype = rel.get('type', {}).get('display_value', '')
            arrow = '→' if parent == args.ci_name else '←'
            label = f"{parent} {arrow} {child}"
            print(f"  [{rtype:30s}] {label}")
    else:
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        resp = requests.get(
            f"{INSTANCE}/api/now/table/cmdb_rel_ci",
            headers=headers,
            params={'sysparm_limit': 20, 'sysparm_display_value': 'true',
                    'sysparm_fields': 'parent.name,child.name,type_display'},
            timeout=30,
        )
        resp.raise_for_status()
        rels = resp.json()['result']
        print(f"\n=== Recent relationships ({len(rels)} total) ===")
        for rel in rels:
            parent = rel.get('parent', {}).get('display_value', '?')
            child = rel.get('child', {}).get('display_value', '?')
            rtype = rel.get('type_display', '')
            print(f"  {parent:25s} → {child:25s} [{rtype}]")
