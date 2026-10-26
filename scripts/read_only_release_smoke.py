"""Measure local GET-only API behavior; never seed, import or mutate records."""
import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter
from urllib.error import HTTPError
from urllib.request import urlopen
from urllib.parse import urlsplit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:5173')
    parser.add_argument('--out',type=Path,default=Path('.test-support/final-handoff/read-only-smoke.json'))
    args=parser.parse_args()
    target=urlsplit(args.base)
    if target.hostname!='127.0.0.1' or target.scheme!='http' or target.username or target.password or target.path or target.query or target.fragment:
        parser.error('Use a loopback HTTP origin without credentials or a path')
    checks={}
    for path,status in [('/api/ready',200),('/api/events/?page=1&page_size=5',200),('/api/institutions?page=1&page_size=25',200),('/api/institutions?state=Uttar%20Pradesh&page_size=1',200),('/api/institutions?state=Gujarat&page_size=1',200),('/api/institutions?state=Maharashtra&page_size=1',200),('/api/institutions?q=University&page_size=25',200),('/api/institutions?page=0',422),('/api/admin/stats',401),('/api/predictions/readiness',200)]:
        timings=[];payload={}
        for _ in range(5 if status==200 else 1):
            started=perf_counter()
            try:
                with urlopen(args.base+path,timeout=10) as response:
                    actual=response.status;payload=json.load(response)
            except HTTPError as response:
                actual=response.code;payload=json.load(response)
            assert actual==status,(path,actual,status)
            timings.append((perf_counter()-started)*1000)
        check={'http_status':actual,'requests':len(timings),'median_ms':round(median(timings),2),'max_ms':round(max(timings),2)}
        if 'total' in payload:check['total']=payload['total']
        if path.endswith('/predictions/readiness'):
            assert payload['data']['public_predictions_enabled'] is False
            check['status']=payload['data']['status']
        checks[path]=check
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps({'method':'GET only, small local loopback sample; not a load test','checks':checks},indent=2),encoding='utf-8')
    print(json.dumps(checks))


if __name__=='__main__':main()
