"""Read-only deployed-platform smoke checks; no login, messages or data writes."""
import argparse
import json
import os
import sys
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError


def fetch(base,path,key=None):
    headers={"Accept":"application/json"}
    if key:headers["X-API-Key"]=key
    try:
        with urlopen(Request(base+path,headers=headers),timeout=20) as response:
            return response.status,response.read(),response.headers
    except HTTPError as error:return error.code,error.read(),error.headers


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('--environment',choices=['staging','production'],default='staging')
    args=parser.parse_args()
    base=args.url.rstrip('/')
    parsed=urlparse(base)
    if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error('Use a clean HTTP(S) base URL without credentials or query parameters')
    if args.environment=='production' and parsed.scheme!='https':parser.error('Production verification requires HTTPS')
    checks={}
    for path in ('/health','/ready','/','/app/','/login.html'):
        code,body,headers=fetch(base,path)
        checks[path]=code==200
        if path=='/app/':
            checks['dashboard_built']=b'not been built' not in body.lower()
            checks['app_script_policy_enforced']="script-src 'self'" in headers.get('Content-Security-Policy','')
    code,body,_=fetch(base,'/api/v1/auth/config')
    checks['demo_bypass_disabled']=code==200 and json.loads(body).get('development_bypass') is False
    for path in ('/api/v1/auth/accounts','/api/v1/delivery/queue','/api/v1/field-users','/metrics'):
        code,_,_=fetch(base,path)
        checks['anonymous_blocked:'+path]=code in (401,403)
    key=os.environ.get('DEPLOYMENT_CHECK_API_KEY','')
    if key:
        for path in ('/api/v1/admin/readiness','/api/v1/delivery/queue','/api/v1/irrigation-schemes'):
            code,_,_=fetch(base,path,key)
            checks['administrator_access:'+path]=code==200
    print(json.dumps({'checks':checks,'administrator_checks':'completed' if key else 'not run: optional secret not configured',
        'writes_performed':False,'field_acceptance_established':False},indent=2))
    raise SystemExit(not all(checks.values()))

if __name__=='__main__':main()
