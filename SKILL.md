---
name: woodpecker
description: "Find prospects and run outbound through Woodpecker — Lead Finder (search a B2B people database by title/role/industry/country/company and enrich verified work emails), campaigns, prospects, inboxes/replies, reports, blacklist, and webhooks (real-time reply/interested/opt-out/bounce events). Use when finding new leads for a target account, building or operating an outreach sequence, adding/enriching/suppressing prospects, wiring reply notifications, or checking campaign results. Drive everything from the CLI / scripts, not the web UI."
---

# Woodpecker (find prospects + run outbound)

Woodpecker does two big jobs: **find prospects** (Lead Finder — a B2B people
database you search and enrich for verified work emails) and **run email outreach**
(campaigns, prospects, replies, reports). Drive it from the CLI and the bundled
scripts; do not hand-edit in the web UI.

**Targeted accounts are the default.** Normal work is account-based: start from a
target account (its website/name) and find the buying committee inside it. A one-off
person search ("find John Smith at Acme") is supported but is the exception — when
no account list is given, ask for / assume the target account list first.

## Auth

- **Key:** `WOODPECKER_API_KEY` (env). The CLI reads it from the environment;
  precedence is flag → env → stored login config.
- In a running container that booted before the key was added, activate once with
  `woodpecker login "$WOODPECKER_API_KEY"`. After a rebuild with the key in `.env`
  no login is needed.
- Verify: `woodpecker me` and `woodpecker mailboxes list`.

## Command map

| Need                                      | Command                                                                                   |
| ----------------------------------------- | ----------------------------------------------------------------------------------------- |
| Account / sending identity                | `woodpecker me`, `woodpecker mailboxes list`                                              |
| List / inspect campaigns                  | `woodpecker campaigns list`, `woodpecker campaigns get <id>`                              |
| Create campaign (content + steps)         | `woodpecker campaigns create --body-file payload.json`                                    |
| Add prospects (with snippets)             | `woodpecker prospects add-to-campaign <id> --body-file prospects.json --send-after <ISO>` |
| Create prospect record                    | `woodpecker prospects create --body-file p.json`                                          |
| Start / pause / stop                      | `woodpecker campaigns run                                                                 | pause  | stop <id>`  |
| Replies                                   | `woodpecker inbox ...`, `woodpecker prospects responses <prospectId>`                     |
| List / search prospects                   | `woodpecker prospects list`, `prospects search`, `prospects list-campaign <ids>`          |
| Update prospects in campaign              | `woodpecker prospects update-prospects-campaign <id> --body-file …`                       |
| Stats / reports                           | `woodpecker reports ...`                                                                  |
| Webhooks (reply/open events → automation) | `woodpecker webhooks list                                                                 | create | delete ...` |
| Blacklist (suppress emails/domains)       | `woodpecker blacklist list                                                                | add    | delete ...` |
| Users / team                              | `woodpecker users ...`                                                                    |
| Agency (sub-accounts)                     | `woodpecker agency ...`                                                                   |
| Config / key                              | `woodpecker config show`, `woodpecker login <key>` (env `WOODPECKER_API_KEY` preferred)   |
| Anything unwrapped                        | `woodpecker raw request --method GET --path /v2/campaigns/<id>`                           |

Command groups: `campaigns · prospects · inbox · mailboxes · manual-tasks ·
linkedin · users · reports · webhooks · agency · blacklist · raw`. Use `--json`
(or `--output json`) for scripting; `raw request` for any v1/v2 endpoint not
wrapped as a command. **Lead Finder is NOT a CLI group** — use `scripts/lead_finder.py`
or `woodpecker raw request --path /v2/lead_finder/...` (see below).

> **Full endpoint map: `references/api-reference.md`** — every group with method,
> path, CLI command, and which calls need `raw` (campaign steps, bounce-shield
> thresholds, Microsoft mailboxes, …). **Scripts** (`scripts/`, all read
> `WOODPECKER_API_KEY`): `lead_finder.py` (find/enrich), `webhooks.py` (manage
> webhooks + bulk `setup`), `wp.py` (generic REST client:
> `python scripts/wp.py GET /v2/campaigns/<id>`). The CLI prefixes `/rest`; in
> `raw`/scripts pass `/v1/...` or `/v2/...` (campaign list/stats + prospects are
> **v1**; everything else **v2**).

## Lead Finder — find NEW prospects (search, then enrich)

Lead Finder is Woodpecker's built-in B2B people database. You **search** by criteria
to get lead records (name, LinkedIn, company, title — **no email**), then optionally
**enrich** chosen leads. Enrichment is async (returns a batch `uuid` you poll).

> **What's verified (2026-06-27):** SEARCH works reliably and is the main value —
> it's an excellent **discovery** source, especially for a targeted account
> (`COMPANY_WEBSITE`). ENRICHMENT runs async and **converts** qualifying leads into
> prospects in your Woodpecker DB (`processing_result: CONVERTED_TO_PROSPECT`); the
> email then lives on the **prospect record** (`woodpecker prospects search --company …`),
> NOT in the enrichment response. In our testing, already-known / duplicate leads came
> back `NOT_CONVERTED_TO_PROSPECT` (no email surfaced), so do **not** treat enrichment
> as a guaranteed email source — use Lead Finder to **discover** people, then verify /
> obtain the email through your normal sending checks before enrolling.

Use the bundled script (self-contained, reads `WOODPECKER_API_KEY`):

```bash
LF=skills/woodpecker/scripts/lead_finder.py
# discover searchable fields and their allowed values (FREE)
python $LF --criteria
python $LF --values JOB_TITLE_ROLE --q finance
# TARGETED ACCOUNT: find the buying committee at one company
python $LF --company-website example.com --level cxo --level director --size 25
# by segment: PL finance leaders
python $LF --country poland --role finance --level cxo --size 25
# search + reveal emails in one go (costs credits)
python $LF --company-website example.com --level cxo --size 10 --enrich
# enrich emails for prospects you already have
python $LF --enrich-emails jane@acme.com,john@acme.com
```

Endpoints (base `https://api.woodpecker.co/rest/v2`, header `x-api-key`; via CLI use
`raw request --path /v2/lead_finder/...`):

| Op                              | Method · path                                                                                              | Notes                                                                                                                                                                                              |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search criteria catalog         | `GET /lead_finder/search_criteria`                                                                         | freetext (CITY, COMPANY_NAME, COMPANY_WEBSITE, FIRST/LAST_NAME) + enumerated (INDUSTRY, CURRENT/PAST_JOB_TITLE, COUNTRY, JOB_TITLE_LEVEL, JOB_TITLE_ROLE, COMPANY_SIZE/COUNTRY/TYPE, …). **Free.** |
| Criteria values                 | `GET /lead_finder/search_criteria/{NAME}/values?search_phrase=&page=&limit=`                               | allowed enum values. **Free.**                                                                                                                                                                     |
| Search leads                    | `POST /lead_finder/leads`                                                                                  | body below. Returns `{leads:[{uid,…}], total_found, next_page}`. **1 credit/lead.**                                                                                                                |
| Queue lead enrichment           | `POST /lead_finder/leads/enrichments`                                                                      | `{"leads":[{"uid":"…"}]}` → `{uuid,status}`. **1.5 credits/found.**                                                                                                                                |
| Get / list lead enrichment      | `GET /lead_finder/leads/enrichments[/{uuid}]`                                                              | poll the uuid until each record is terminal. Free.                                                                                                                                                 |
| Queue prospect enrichment       | `POST /lead_finder/prospects/enrichments`                                                                  | `{"prospects":[{"email":"…","first_name":…,"last_name":…,"linkedin_url":…,"company_name":…,"website":…}]}` → `{uuid}`.                                                                             |
| Query / get prospect enrichment | `POST /lead_finder/prospects/enrichments/statuses/query` · `GET /lead_finder/prospects/enrichments/{uuid}` | status / results.                                                                                                                                                                                  |

**Search body shape (verified):**

```json
{
  "search_criteria": [
    { "name": "COMPANY_WEBSITE", "operator": "INCLUDE", "value": "example.com" },
    { "name": "JOB_TITLE_LEVEL", "operator": "INCLUDE", "value": "cxo" }
  ],
  "size": 25,
  "next_page": "<cursor from previous response>"
}
```

- `search_criteria` is an **array** of `{name, operator, value}`. `operator` is
  `INCLUDE` or `EXCLUDE`. `value` is a **single string** — repeat the criterion to
  OR several values. `size` = page size; paginate with the returned `next_page` cursor.
- A lead record: `uid, full_name, first_name, last_name, linkedin_url, company_name,
company_website, industry, job_title, job_title_role, job_title_levels, country, city`.
- **Credits:** searching/retrieving leads = 1 credit/lead; enrichment = 1.5 credits
  when an email is found; reading criteria/values/status = free. Keep `size` tight.

## Snippets (personalization) — slot map + verified token syntax

Woodpecker personalizes via **snippet fields** (`snippet1`…`snippet15`, plus
`first_name`, `last_name`, `company`, `email`, `title`, etc.) carried on each
prospect. Write the step copy once in the campaign, then pass per-prospect
snippet values when adding prospects.

**Verified live (2026-07-03, draft 1584681):** step copy referencing
`{{SNIPPET_N | "fallback"}}` (underscore + optional quoted fallback) IS
accepted by the v2 campaign **create** — the earlier "custom {{SNIPPET1}}
rejected" finding was the underscore-less form. The fallback string renders
for prospects whose slot is empty.

**Slot map (the outreach standard — guard §11 in the outreach skills):**

| Slot       | Label         | Content                                             |
| ---------- | ------------- | --------------------------------------------------- |
| `snippet1` | `signal`      | captured signal note — REVIEW-ONLY, never in a body |
| `snippet2` | `observation` | observation note — REVIEW-ONLY, never in a body     |
| `snippet3` | `line_1`      | SENT email body line 1                              |
| `snippet4` | `line_2`      | SENT email body line 2                              |
| `snippet5` | `line_3`      | SENT email body line 3                              |
| `snippet6` | `cta`         | SENT soft CTA line                                  |

Slots 1-2 are informational context for the reviewer/BD (what we
personalized on); ONLY slots 3-6 are woven into campaign copy
(`{{SNIPPET_3..6 | "fallback"}}`). First-class prospect fields (first/last
name, company, title, email, website, industry, address, city, state,
country, phone) have their OWN merge tags (`{{FIRST_NAME}}`, `{{COMPANY}}`,
`{{TITLE}}`, …) — they never consume snippet slots.

The token names (`{{SNIPPET_1}}`…) are FIXED; only the **labels** (column
names) are renameable — in the Woodpecker web UI settings. There is **no
labels API** (probed 2026-07-03: `/v1|v2/snippet_labels`, `/v2/custom_fields`
all 404; `snippet_labels` on the prospect record is read-only) — rename the
six labels above once in the UI so the columns read meaningfully.

**Gotchas (wet-verified 2026-07-03):** an upsert only touches the keys you
SEND — an omitted snippet key leaves a stale value from an earlier campaign
in place, while an explicit `""` CLEARS the slot (so when re-personalizing,
send all six slots explicitly). Prospect email lookup is
`GET /v1/prospects?search=email%3D<addr>` — a bare `?email=` param is silently
IGNORED (returns the whole DB) and `?search=<freetext>` 400s.

## Tags (prospect lists & status) — POLICY

Woodpecker has **no list object** — the prospect database + tags ARE the
lists. Tags live in ONE space-separated string of `#TOKEN`s on each prospect.

Rules (wet-verified 2026-07-03):

- Upsert tags are **additive** — Woodpecker unions new tags into the existing
  string server-side; still READ-MERGE-WRITE when updating so intent is
  explicit. Removing a tag requires writing the reduced string.
- Opt-out is NEVER a tag: delete the prospect + blacklist the email.
- Filter by tag: `woodpecker prospects search --tags "#HSLIST_6266"`.

## Creating a campaign (verified schema)

`campaigns create --body-file` builds a DRAFT. Verified body shape:

- `email_account_ids` — **attach ALL sending mailboxes, not one.** List the sending
  (SMTP) ids (`woodpecker mailboxes list`; the domain-rotation set — e.g. .net/.co/
  .org/.us/.xyz/.co.uk — each has a paired IMAP id you skip). More senders = better
  deliverability + volume; Woodpecker rotates.
- `settings` — `{timezone, daily_enroll}`.
- `steps` — a node with `type:"START"` whose `followup` is step 1; each step:
  `type:"EMAIL"`, `followup_after:{range:"DAY",value:N}` (**N must be > 0, even step 1**),
  `delivery_time:{WEEKDAY:[{from,to}]}`, `body:{versions:[{version:"A",subject,
message(HTML),signature:"NO_SIGNATURE"}]}`, chained via `followup` (last = `null`).
- **Merge fields (each wet-verified against the create validator 2026-07-03):**
  `{{FIRST_NAME}}`, `{{LAST_NAME}}`, `{{COMPANY}}`, `{{TITLE}}`, `{{CITY}}`,
  `{{COUNTRY}}`, `{{INDUSTRY}}`, `{{PHONE}}`, `{{EMAIL}}` and
  `{{SNIPPET_N | "fallback"}}` (underscore form; the historical rejection was
  the underscore-less `{{SNIPPET1}}`). **`{{WEBSITE}}` is REJECTED** — the
  website field stores on the record but has no merge tag (use a snippet slot
  if a URL must appear in copy). First-class fields never consume snippet
  slots. Set snippet VALUES per prospect at add time (see "Snippets").

## Authoring a campaign body (legacy reference)

The campaign JSON follows the Woodpecker v2 schema (steps, delays, mailbox,
subject/body). **Before authoring, inspect a real campaign to copy its exact
shape:**

```bash
woodpecker campaigns get <existingId> --json
# or the raw endpoint for the full schema
woodpecker raw request --method GET --path /v2/campaigns/<existingId>
```

Then write `payload.json` to match, and create with `--body-file`. Iterate small;
validate with `campaigns get` before adding prospects.

### Editing steps, stats & bounce-shield (via `raw` / `wp.py`)

The CLI wraps create/get/list/run/pause/stop/delete; the rest is `raw`/`wp.py`
(full list in `references/api-reference.md`):

- **Edit a running campaign:** `POST /v2/campaigns/{id}/editable` to unlock, then
  `POST /v2/campaigns/{id}/steps` (add), `PATCH …/steps/{stepId}` /
  `…/steps/{stepId}/versions/{verId}` (edit), `DELETE …/steps/{stepId}`.
- **Settings:** `PATCH /v2/campaigns/{id}` (name, timezone, daily_enroll, mailboxes).
- **Bounce-shield** (auto-pause when bounce rate is too high):
  `GET/PUT/DELETE /v2/campaigns/{id}/bounce_shield/threshold`, body
  `{"bounce_rate_threshold": <pct>}`. Pairs with the `campaign_paused_by_bounce_shield`
  webhook — keep it set so a bad list pauses itself before it burns the domain.
- **Stats:** `woodpecker reports generate campaigns|messages|open_rate|complete`
  (→ hash → `reports get <hash>`); per-campaign summary is also in `campaigns list` (v1).

## Prospects — add, update, suppress (do-not-contact)

| Need                                      | Command                                                                                        |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------- |
| List in DB / in campaign / search         | `woodpecker prospects list`, `prospects list-campaign <ids>`, `prospects search --query <q>`   |
| Add to DB / add to campaign               | `prospects create --body-file p.json`, `prospects add-to-campaign <id> --body-file …`          |
| Update in DB / in campaign                | `prospects create` (upsert by email), `prospects update-prospects-campaign <id> --body-file …` |
| Replies for one prospect                  | `prospects responses <prospectId>`                                                             |
| **Delete / unsubscribe / do-not-contact** | `prospects delete <prospectId>` **and** add to blacklist (below)                               |

**Populate the FULL record when adding** (all wet-verified persisted
2026-07-03): `email, first_name, last_name, company, title, linkedin_url,
website, industry, address, city, state, country, tags, snippet1..15`.
`phone` also exists. **`time_zone` is NOT storable** — the v1 API silently
drops it; a prospect's timezone must drive the CAMPAIGN `settings.timezone`
(send windows) instead. Upserts touch ONLY the keys you send: omit a field to
leave it alone; send `""` to clear it (so never send empty firmographics —
you would blank UI-entered data — but DO send all six snippet slots when
re-personalizing). `add_prospects_list` returns the prospect ids:
`{"prospects":[{"email","id"}]}`.

**Opt-out / "don't contact me" / GDPR erasure:** when a prospect asks to be
removed, do BOTH — `prospects delete` (removes them from sequences) **and**
blacklist their email/domain so they can never be re-enrolled:

```bash
woodpecker blacklist emails add --body-file emails.json     # suppress addresses
woodpecker blacklist domains add --body-file domains.json   # suppress whole domains
woodpecker blacklist emails list ; woodpecker blacklist domains list
woodpecker blacklist emails delete … ; woodpecker blacklist domains delete …
```

## Email validation (built-in)

Woodpecker validates recipient emails with its **built-in verification** and flags
bad addresses at send time via the `prospect_invalid` / `prospect_bounced` webhook
events — that send-time signal is the reliable one. Always confirm an address is
deliverable **before** enrolling; bounces wreck the sending-domain reputation.

> **Tested (2026-06-27):** the `lead_finder/prospects/enrichments` "enrich an
> existing prospect by email" call returned `PROCESSED_NOT_ENRICHED` (no validation
> verdict or extra data) on our account — so it is **not** a usable standalone
> email-validator today. Verify emails with your normal verification step before
> enrolling, and rely on the send-time `prospect_invalid`/`prospect_bounced` events
> for the authoritative bounce signal.

**How the built-in validation actually behaves (verified live 2026-06-27):** it's
**Bouncer**, native + free, and runs **at send time inside a _running_ campaign** — NOT
on add/import. A bad address flips to `INVALID` (caught pre-send, **no email sent**) or,
if the provider accepts-then-bounces (e.g. O365), it sends and flips to `BOUNCED`. It is
best-effort/domain-dependent, so keep verifying before enrolling. **Gotcha:** `INVALID`
is a **campaign-local** status — it does NOT appear in the global
`prospects list --status INVALID` (that still shows ACTIVE); read it per campaign with
`prospects list-campaign <id> --status INVALID`.

## Webhooks — real-time events (replies, interest, opt-outs → automation)

Subscribe webhooks so downstream systems react the moment something happens —
**especially replies and interest**, which must reach the people running outreach
and the executive assistant immediately.

```bash
# manage via the script (bulk-subscribe the prospecting set in one go):
python skills/woodpecker/scripts/webhooks.py list
python skills/woodpecker/scripts/webhooks.py events
python skills/woodpecker/scripts/webhooks.py setup https://<endpoint>     # prospecting set
python skills/woodpecker/scripts/webhooks.py setup https://<endpoint> --all
python skills/woodpecker/scripts/webhooks.py subscribe prospect_replied https://<endpoint>
# or the CLI:
woodpecker webhooks subscribe --event prospect_replied --target-url https://<endpoint>
woodpecker webhooks unsubscribe --event prospect_replied --target-url https://<endpoint>
```

(REST, verified: list `GET /v2/webhooks`; subscribe/unsubscribe
`POST /v1/webhooks/subscribe|unsubscribe` body `{event, target_url}`.)

**Allowed events** (verified live) and what they mean:

| Event                                             | Meaning                            | Route to                                     |
| ------------------------------------------------- | ---------------------------------- | -------------------------------------------- |
| `prospect_replied`                                | a prospect replied                 | **BD + executive assistant (high priority)** |
| `prospect_interested`                             | reply classified as interested     | **BD + EA — hot lead, act now**              |
| `prospect_maybe_later`                            | interested but later               | BD — nurture / snooze                        |
| `prospect_not_interested`                         | reply classified not interested    | BD — close out, suppress                     |
| `prospect_autoreplied`                            | auto-reply (OOO etc.)              | BD — pause follow-up                         |
| `followup_after_autoreply`                        | follow-up resumed after auto-reply | log                                          |
| `secondary_replied`                               | a second/later reply detected      | **BD + EA**                                  |
| `prospect_opt_out`                                | unsubscribe / opt-out              | **delete + blacklist (do-not-contact)**      |
| `prospect_blacklisted`                            | prospect was blacklisted           | log suppression                              |
| `prospect_bounced` / `prospect_invalid`           | bounce / invalid address           | suppress, fix list hygiene                   |
| `email_opened` / `link_clicked`                   | open / click (if tracked)          | engagement signal                            |
| `prospect_non_responsive`                         | no reply after sequence            | BD — recycle / re-angle                      |
| `campaign_sent` / `campaign_completed`            | send / campaign finished           | reporting                                    |
| `prospect_saved`                                  | prospect saved                     | log                                          |
| `task_created` / `task_done` / `task_ignored`     | manual task lifecycle              | EA — task tracking                           |
| `linkedin_automation_connection_request_accepted` | LinkedIn connect accepted          | BD                                           |

**The non-negotiable routing:** `prospect_replied`, `prospect_interested`, and
`secondary_replied` are the ones that drive revenue — they must notify the team
(BD) and the executive assistant in real time. `prospect_opt_out` must trigger
delete + blacklist automatically.

## Reports, mailboxes, inbox, manual tasks, LinkedIn

- **Reports:** `woodpecker reports types`, `reports generate <name>`, `reports get <hash>`,
  `reports poll <hash>` — sent counts, open rate, general stats, per-user stats.
- **Inbox:** `woodpecker inbox list`, `inbox reply <messageId>` — read/reply to threads.
- **Mailboxes:** `woodpecker mailboxes list|get <id>`, `mailboxes add-bulk`,
  `mailboxes update <id>` (footer), `mailboxes get-batch-summary <batchId>`.
  **Microsoft 365** (via `raw`/`wp.py`): credentials CRUD at
  `/v2/mailboxes/microsoft/credentials` (POST/GET/PATCH/DELETE) + connect a mailbox
  `POST /v2/mailboxes/microsoft`. See `references/api-reference.md`.
- **Manual tasks:** `woodpecker manual-tasks …` — LinkedIn/manual steps in a sequence.
- **LinkedIn accounts:** `woodpecker linkedin …` — connected LinkedIn accounts for
  LinkedIn steps.

## Operating rules

1. **Nothing sends without approval.** Create campaigns in DRAFT, add prospects,
   show the rendered copy + recipient list, and only `campaigns run` after explicit
   go-ahead. Prefer `--send-after` to schedule rather than blast.
2. **Verify recipients first.** Confirm a valid, deliverable address before adding
   a prospect; skip movers/bounces.
3. **Reflect state into your system of record.** Every send / reply / booking
   should be logged wherever you track outreach — the Woodpecker campaign is the
   channel, not the record.
4. **Respect blacklist + cadence.** Check `woodpecker blacklist`; don't
   double-sequence a live thread.

## Typical flow

1. **Find prospects** — Lead Finder: `lead_finder.py --company-website <target> --level …`
   (or by segment), then `--enrich` to reveal verified work emails. (Skip if you
   already have the list.)
2. `campaigns create` with the email steps and `{{SNIPPET}}` placeholders.
3. `prospects add-to-campaign <id>` with per-prospect snippet values, scheduled
   via `--send-after`.
4. Review rendered copy + list → `campaigns run`.
5. **Subscribe webhooks** (`prospect_replied`, `prospect_interested`, `prospect_opt_out`)
   so replies/interest notify the team + EA and opt-outs auto-suppress.
6. Watch `inbox` / `reports`; log replies + bookings.
