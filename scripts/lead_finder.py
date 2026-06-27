#!/usr/bin/env python3
"""
lead_finder.py — Woodpecker Lead Finder (find NEW prospects, then enrich emails).

Woodpecker's Lead Finder is a B2B people database. You SEARCH by criteria (job
title, level, role, industry, country, company website/name, …) to get lead
records (name, LinkedIn, company, title — NO email), then ENRICH selected leads
(enrichment converts qualifying leads into prospects in your Woodpecker DB; read
the email from the prospect record via the prospects endpoints). Existing prospects
can be enriched directly by email. Async: enrichment returns a batch uuid you poll.
NOTE (tested 2026-06-27): enrichment often returns NOT_CONVERTED / NOT_ENRICHED for
known/duplicate records — treat Lead Finder mainly as a DISCOVERY source, then
verify/obtain emails through your normal verification before enrolling.

Endpoints (base https://api.woodpecker.co/rest/v2, header x-api-key):
  GET  /lead_finder/search_criteria                          catalog of fields (free)
  GET  /lead_finder/search_criteria/{NAME}/values            allowed enum values (free)
  POST /lead_finder/leads                                     search leads (1 credit/lead)
  POST /lead_finder/leads/enrichments                         queue lead enrichment (1.5cr/found)
  GET  /lead_finder/leads/enrichments[/{uuid}]               list / get enrichment batch
  POST /lead_finder/prospects/enrichments                     queue prospect (by-email) enrichment
  POST /lead_finder/prospects/enrichments/statuses/query      query prospect enrichment statuses
  GET  /lead_finder/prospects/enrichments/{uuid}             get prospect enrichment batch

Search body: {"search_criteria":[{"name":<FIELD>,"operator":"INCLUDE"|"EXCLUDE",
"value":"<string>"}], "size":N, "next_page":"<cursor>"}. Lead records carry a
`uid` used for enrichment. `size` controls page size; `next_page` cursor paginates.

TARGETED ACCOUNTS: the normal mode is account-based — search COMPANY_WEBSITE (or
COMPANY_NAME) for a target account, scoped by JOB_TITLE_LEVEL / JOB_TITLE_ROLE /
CURRENT_JOB_TITLE. A one-off person search (FIRST_NAME/LAST_NAME + COMPANY) is
supported but is the exception, not the default.

Usage:
  python lead_finder.py --criteria                       # list searchable fields
  python lead_finder.py --values JOB_TITLE_ROLE [--q fin]  # list a field's values
  python lead_finder.py --company-website example.com --level cxo --level director --size 10
  python lead_finder.py --country poland --role finance --level cxo --size 25 --enrich
  python lead_finder.py --enrich-emails a@co.com,b@co.com  # enrich existing prospects

Env: WOODPECKER_API_KEY
"""
import os, sys, json, time, argparse, urllib.request, urllib.error, urllib.parse

BASE = "https://api.woodpecker.co/rest/v2"

def die(m): print("ERROR:", m, file=sys.stderr); sys.exit(1)

def wp(method, path, body=None, timeout=60):
    key = os.environ.get("WOODPECKER_API_KEY") or die("missing WOODPECKER_API_KEY")
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("x-api-key", key)
    r.add_header("Accept", "application/json")
    if body is not None: r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:600]}
    except Exception as e:
        return {"_err": -1, "_body": str(e)}

# ---------- criteria discovery ----------
def list_criteria():
    return wp("GET", "/lead_finder/search_criteria")

def criteria_values(name, phrase=None, page=1, limit=50):
    p = f"/lead_finder/search_criteria/{name}/values?page={page}&limit={limit}"
    if phrase: p += "&search_phrase=" + urllib.parse.quote(phrase)
    return wp("GET", p)

# ---------- search ----------
def _crit(name, value, operator="INCLUDE"):
    return {"name": name, "operator": operator, "value": value}

def build_criteria(args):
    """Translate CLI args into the search_criteria array. Each value is a single
    string; pass an arg multiple times to OR several values (one criterion each)."""
    c = []
    for v in (args.company_website or []): c.append(_crit("COMPANY_WEBSITE", v))
    for v in (args.company_name or []):    c.append(_crit("COMPANY_NAME", v))
    for v in (args.country or []):          c.append(_crit("COUNTRY", v))
    for v in (args.industry or []):         c.append(_crit("INDUSTRY", v))
    for v in (args.level or []):            c.append(_crit("JOB_TITLE_LEVEL", v))
    for v in (args.role or []):             c.append(_crit("JOB_TITLE_ROLE", v))
    for v in (args.title or []):            c.append(_crit("CURRENT_JOB_TITLE", v))
    for v in (args.city or []):             c.append(_crit("CITY", v))
    for kv in (args.exclude or []):
        name, _, val = kv.partition("=")
        if name and val: c.append(_crit(name.strip().upper(), val.strip(), "EXCLUDE"))
    return c

def search(criteria, size=10, next_page=None):
    body = {"search_criteria": criteria, "size": size}
    if next_page: body["next_page"] = next_page
    return wp("POST", "/lead_finder/leads", body)

# ---------- enrichment (async; poll until done) ----------
TERMINAL = {"DONE", "COMPLETED", "FINISHED", "READY", "ERROR", "FAILED", "ENRICHED", "NOT_FOUND"}

def _is_terminal(status):
    s = str(status or "").upper()
    return s in TERMINAL or s.startswith("PROCESSED") or s.startswith("ENRICHED")

def _batch_done(r):
    """A lead/prospect enrichment batch is done when every record has a terminal
    per-record status. Records live under different keys per endpoint:
    lead_enrichment.leads[], prospect_enrichment.prospects[], or a top-level
    prospect_enrichments[] list."""
    if not isinstance(r, dict) or "_err" in r: return True
    body = r.get("lead_enrichment") or r.get("prospect_enrichment") or r
    recs = (body.get("leads") or body.get("prospects")
            or r.get("prospect_enrichments") or [])
    if not recs:
        return _is_terminal(r.get("status"))
    return all(_is_terminal(x.get("status")) for x in recs)

def queue_lead_enrichment(uids):
    return wp("POST", "/lead_finder/leads/enrichments",
              {"leads": [{"uid": u} for u in uids]})

def get_lead_enrichment(uuid):
    return wp("GET", f"/lead_finder/leads/enrichments/{uuid}")

def queue_prospect_enrichment(prospects):
    return wp("POST", "/lead_finder/prospects/enrichments", {"prospects": prospects})

def get_prospect_enrichment(uuid):
    return wp("GET", f"/lead_finder/prospects/enrichments/{uuid}")

def poll(getter, uuid, tries=45, delay=6):
    """Poll an enrichment batch until every record reaches a terminal status (or
    tries exhausted). Enrichment is async and can take 1–4 minutes."""
    r = getter(uuid)
    for _ in range(tries):
        if _batch_done(r):
            return r
        time.sleep(delay)
        r = getter(uuid)
    return r

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--criteria", action="store_true", help="list searchable fields")
    ap.add_argument("--values", help="list allowed values for a field (e.g. JOB_TITLE_ROLE)")
    ap.add_argument("--q", help="search phrase for --values")
    ap.add_argument("--company-website", action="append", help="COMPANY_WEBSITE (repeatable)")
    ap.add_argument("--company-name", action="append")
    ap.add_argument("--country", action="append")
    ap.add_argument("--industry", action="append")
    ap.add_argument("--level", action="append", help="JOB_TITLE_LEVEL (cxo, director, manager, …)")
    ap.add_argument("--role", action="append", help="JOB_TITLE_ROLE (finance, marketing, sales, …)")
    ap.add_argument("--title", action="append", help="CURRENT_JOB_TITLE freetext")
    ap.add_argument("--city", action="append")
    ap.add_argument("--exclude", action="append", help="FIELD=value to EXCLUDE (repeatable)")
    ap.add_argument("--size", type=int, default=10, help="page size (results to return)")
    ap.add_argument("--next-page", help="pagination cursor from a prior search")
    ap.add_argument("--enrich", action="store_true", help="enrich found leads (converts qualifying leads to prospects in DB; costs credits)")
    ap.add_argument("--enrich-emails", help="comma-separated emails: enrich EXISTING prospects by email")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.criteria:
        print(json.dumps(list_criteria(), indent=2)); return
    if a.values:
        print(json.dumps(criteria_values(a.values, a.q), indent=2)); return
    if a.enrich_emails:
        emails = [e.strip() for e in a.enrich_emails.split(",") if e.strip()]
        q = queue_prospect_enrichment([{"email": e} for e in emails])
        if "_err" in q: die(q)
        res = poll(get_prospect_enrichment, q["uuid"])
        print(json.dumps(res, indent=2, default=str)); return

    criteria = build_criteria(a)
    if not criteria:
        die("no search criteria — pass --company-website / --country / --role / etc., or --criteria to list fields")
    res = search(criteria, a.size, a.next_page)
    if "_err" in res: die(res)
    leads = res.get("leads", [])
    if a.enrich and leads:
        q = queue_lead_enrichment([l["uid"] for l in leads])
        if "_err" in q: die(q)
        enr = poll(get_lead_enrichment, q["uuid"])
        res["enrichment"] = enr

    if a.json:
        print(json.dumps(res, indent=2, default=str)); return
    print(f"total_found={res.get('total_found')} size={res.get('size')} next_page={res.get('next_page')}")
    for l in leads:
        print(f"  • {l.get('full_name')} — {l.get('job_title')} @ {l.get('company_name')} "
              f"({l.get('company_website')}) | {l.get('country')} | uid={l.get('uid')}")
        print(f"      linkedin={l.get('linkedin_url')}")
    if res.get("enrichment"):
        print("  enrichment:", json.dumps(res["enrichment"], default=str)[:800])

if __name__ == "__main__":
    main()
