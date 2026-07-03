#!/usr/bin/env python3
"""
wp.py — tiny Woodpecker REST client for any endpoint (and a CLI for ad-hoc calls).

Base https://api.woodpecker.co/rest, auth header x-api-key=$WOODPECKER_API_KEY.
Pass paths as /v1/... or /v2/... (see references/api-reference.md for the map).

Module:
    from wp import wp
    wp("GET", "/v2/campaigns/123")
    wp("POST", "/v2/blacklist/emails", {"emails":["x@y.com"]})  # FLAT strings (wet-verified)

CLI:
    python wp.py GET /v2/campaigns
    python wp.py GET /v2/campaigns/123/bounce_shield/threshold
    python wp.py POST /v2/webhooks '{"event":"prospect_replied","target_url":"https://…"}'
    python wp.py PUT /v2/campaigns/123/bounce_shield/threshold '{"bounce_rate_threshold":5}'

Env: WOODPECKER_API_KEY
"""
import os, sys, json, urllib.request, urllib.error

BASE = "https://api.woodpecker.co/rest"

def wp(method, path, body=None, timeout=60):
    key = os.environ.get("WOODPECKER_API_KEY")
    if not key:
        return {"_err": -1, "_body": "missing WOODPECKER_API_KEY"}
    if not path.startswith("/"):
        path = "/" + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method.upper())
    r.add_header("x-api-key", key)
    r.add_header("Accept", "application/json")
    if body is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:800]}
    except Exception as e:
        return {"_err": -1, "_body": str(e)}

def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__); sys.exit(2)
    method, path = a[0], a[1]
    body = json.loads(a[2]) if len(a) > 2 and a[2] else None
    print(json.dumps(wp(method, path, body), indent=2, default=str))

if __name__ == "__main__":
    main()
