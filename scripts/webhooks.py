#!/usr/bin/env python3
"""
webhooks.py — manage Woodpecker webhooks (real-time events → your endpoint).

Paths (verified live 2026-06-27):
  GET  /v2/webhooks                  list current subscriptions
  POST /v1/webhooks/subscribe        body {event, target_url}   (201)
  POST /v1/webhooks/unsubscribe      body {event, target_url}   (200)

Usage:
  python webhooks.py list
  python webhooks.py events
  python webhooks.py subscribe prospect_replied https://my-endpoint/wp
  python webhooks.py unsubscribe prospect_replied https://my-endpoint/wp
  python webhooks.py setup https://my-endpoint/wp                # the prospecting set
  python webhooks.py setup https://my-endpoint/wp --all          # every event
  python webhooks.py teardown https://my-endpoint/wp [--all]     # unsubscribe the set

Env: WOODPECKER_API_KEY
"""
import os, sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from wp import wp  # noqa: E402

# All allowed/subscribable events — EXACTLY what the API returns from
# `GET webhooks events` (verified live 2026-06-27). Keep in sync with that list.
EVENTS = [
    "campaign_completed", "campaign_sent", "followup_after_autoreply",
    "linkedin_automation_connection_request_accepted", "prospect_autoreplied",
    "prospect_blacklisted", "prospect_bounced", "link_clicked",
    "prospect_interested", "prospect_invalid", "prospect_maybe_later",
    "prospect_non_responsive", "prospect_not_interested", "email_opened",
    "prospect_opt_out", "prospect_replied", "prospect_saved", "secondary_replied",
    "task_created", "task_done", "task_ignored",
]

# The events worth routing for prospecting (replies/interest → team + EA;
# opt-out/bounce → suppression). This is the default `setup` set.
PROSPECTING_SET = [
    "prospect_replied", "prospect_interested", "secondary_replied",
    "prospect_maybe_later", "prospect_not_interested", "prospect_autoreplied",
    "prospect_opt_out", "prospect_bounced", "prospect_invalid",
    "prospect_blacklisted", "task_created",
]

def list_webhooks():
    r = wp("GET", "/v2/webhooks")
    return r.get("webhooks", []) if isinstance(r, dict) else r

def subscribe(event, url):
    return wp("POST", "/v1/webhooks/subscribe", {"event": event, "target_url": url})

def unsubscribe(event, url):
    return wp("POST", "/v1/webhooks/unsubscribe", {"event": event, "target_url": url})

def _bulk(events, url, fn):
    out = []
    for e in events:
        r = fn(e, url)
        ok = "_err" not in r
        out.append({"event": e, "ok": ok, "detail": (r if not ok else "ok")})
        print(f"  {'✓' if ok else '✗'} {e}" + ("" if ok else f"  {r.get('_err')}: {r.get('_body','')[:80]}"))
    return out

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(2)
    cmd = a[0]
    if cmd == "events":
        print("\n".join(EVENTS)); return
    if cmd == "list":
        print(json.dumps(list_webhooks(), indent=2, default=str)); return
    if cmd in ("subscribe", "unsubscribe"):
        if len(a) < 3: print("need: <event> <target_url>"); sys.exit(2)
        fn = subscribe if cmd == "subscribe" else unsubscribe
        print(json.dumps(fn(a[1], a[2]), indent=2, default=str)); return
    if cmd in ("setup", "teardown"):
        if len(a) < 2: print("need: <target_url> [--all]"); sys.exit(2)
        url = a[1]
        events = EVENTS if "--all" in a else PROSPECTING_SET
        fn = subscribe if cmd == "setup" else unsubscribe
        print(f"{cmd} {len(events)} events → {url}")
        _bulk(events, url, fn)
        print("\nCurrent subscriptions:")
        print(json.dumps(list_webhooks(), indent=2, default=str))
        return
    print(f"unknown command: {cmd}\n"); print(__doc__); sys.exit(2)

if __name__ == "__main__":
    main()
