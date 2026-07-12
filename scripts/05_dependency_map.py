"""05_dependency_map.py — Build dependency maps for critical business services.

Usage:
    python 05_dependency_map.py [--service-name <business_service_name>]
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

def get_business_services(token, limit=10):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_ci_service",
        headers=headers,
        params={'sysparm_limit': limit, 'sysparm_display_value': 'true',
                'sysparm_fields': 'sys_id,name,sys_class_name,operational_status'},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['result']

def get_service_ci_members(token, service_sys_id):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_rel_ci",
        headers=headers,
        params={
            'sysparm_query': f'parent={service_sys_id}^type=cmdb_rel_ci_contains',
            'sysparm_display_value': 'true',
            'sysparm_fields': 'sys_id,parent,child,child.name,child.sys_class_name',
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['result']

def get_ci_downstream(token, ci_sys_id, depth=0, max_depth=3, visited=None):
    if visited is None:
        visited = set()
    if ci_sys_id in visited or depth > max_depth:
        return []
    visited.add(ci_sys_id)
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    resp = requests.get(
        f"{INSTANCE}/api/now/table/cmdb_rel_ci",
        headers=headers,
        params={
            'sysparm_query': f'child={ci_sys_id}',
            'sysparm_display_value': 'true',
            'sysparm_fields': 'sys_id,parent,child,parent.name,parent.sys_class_name',
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = []
    for rel in resp.json()['result']:
        parent_name = rel.get('parent', {}).get('display_value', '?')
        parent_class = rel.get('parent', {}).get('sys_class_name', '')
        result.append({'name': parent_name, 'class': parent_class, 'depth': depth + 1})
        parent_id = rel.get('parent', {}).get('value', '')
        if parent_id:
            result.extend(get_ci_downstream(token, parent_id, depth + 1, max_depth, visited))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Business service dependency map')
    parser.add_argument('--service-name', default='', help='Business service name')
    args = parser.parse_args()

    token = get_token()

    if args.service_name:
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        resp = requests.get(
            f"{INSTANCE}/api/now/table/cmdb_ci_service",
            headers=headers,
            params={
                'sysparm_query': f'name={args.service_name}',
                'sysparm_limit': 1,
                'sysparm_display_value': 'true',
                'sysparm_fields': 'sys_id,name,operational_status',
            },
            timeout=30,
        )
        resp.raise_for_status()
        services = resp.json()['result']
        if not services:
            sys.exit(f"Business service '{args.service_name}' not found.")
        svc = services[0]
        members = get_service_ci_members(token, svc['sys_id'])
        print(f"\n=== Service: {svc.get('name', '?')} ===")
        print(f"  Status: {svc.get('operational_status', '?')}")
        print(f"  Member CIs: {len(members)}")
        for m in members:
            child = m.get('child', {}).get('display_value', '?')
            child_class = m.get('child', {}).get('sys_class_name', '')
            print(f"    ├─ {child:25s} [{child_class}]")
            downstream = get_ci_downstream(token, m.get('child', {}).get('value', ''))
            for d in downstream:
                indent = '    │   ' + '  ' * d['depth']
                print(f"  {indent}→ {d['name']:25s} [{d['class']}]")
    else:
        services = get_business_services(token)
        print(f"\n=== Business services ({len(services)}) ===")
        for svc in services:
            members = get_service_ci_members(token, svc['sys_id'])
            print(f"  {svc.get('name',''):30s} | {svc.get('operational_status',''):12s} | {len(members)} member CIs")
