"""01_query_ci.py — Query configuration items by class, status, and location.

Usage:
    python 01_query_ci.py
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

def query_cmdb(token, table='cmdb_ci', query=None, fields=None, limit=20):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    params = {'sysparm_limit': limit, 'sysparm_display_value': 'true'}
    if query:
        params['sysparm_query'] = query
    if fields:
        params['sysparm_fields'] = ','.join(fields)
    resp = requests.get(
        f"{INSTANCE}/api/now/table/{table}",
        headers=headers, params=params, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['result']

if __name__ == '__main__':
    token = get_token()

    print("=== Production servers ===")
    servers = query_cmdb(
        token,
        query='sys_class_name=cmdb_ci_server^install_status=1^environment=production^ORDERBYname',
        fields=['name', 'sys_class_name', 'environment', 'operational_status', 'location', 'os'],
        limit=10,
    )
    for ci in servers:
        print(f"  {ci.get('name',''):20s} | {ci.get('operational_status',''):12s} | "
              f"{ci.get('location',''):20s} | {ci.get('os',''):20s}")

    print("\n=== Offline or maintenance CIs ===")
    offline = query_cmdb(
        token,
        query='install_statusIN2,3^ORDERBYname',
        fields=['name', 'sys_class_name', 'install_status', 'operational_status'],
        limit=10,
    )
    for ci in offline:
        print(f"  {ci.get('name',''):20s} | {ci.get('sys_class_name',''):20s} | status={ci.get('install_status','')}")

    print("\n=== Network devices ===")
    network = query_cmdb(
        token,
        query='sys_class_nameINcmdb_ci_switch,cmdb_ci_router,cmdb_ci_network_device^ORDERBYname',
        fields=['name', 'sys_class_name', 'ip_address', 'location'],
        limit=10,
    )
    for ci in network:
        print(f"  {ci.get('name',''):20s} | {ci.get('sys_class_name',''):25s} | {ci.get('ip_address',''):15s}")
