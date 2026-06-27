# Woodpecker REST API — full reference

Complete endpoint map for the Woodpecker API. Drive everything from the CLI
(`woodpecker <group> <cmd>`) where a command exists; use the bundled `scripts/`
or `woodpecker raw request` for the rest.

- **Base URL:** `https://api.woodpecker.co/rest`
- **Auth:** header `x-api-key: $WOODPECKER_API_KEY` (the CLI reads it from env).
- **Versions:** campaign **list/stats** are **v1** (`/rest/v1/...`); prospects use
  **v1** (legacy); everything else — campaigns get/create/steps, webhooks,
  mailboxes, blacklist, manual_tasks, linkedin_accounts, lead_finder — is **v2**.
- **raw:** `woodpecker raw request --method <M> --path /v2/... [--body-json '{}']`
  (the CLI prefixes `/rest`; pass `/v2/...` or `/v1/...`, never `/rest/v2/...`).
- **Generic client:** `python scripts/wp.py <METHOD> <path> [json-body]`.

`✓` = path verified live on this account (2026-06-27). Others are from the
official docs (https://developers.woodpecker.co/docs/) — verify with a dry call
before relying on the exact path/body.

---

## Campaigns

| Op | Method · path | CLI | Notes |
| --- | --- | --- | --- |
| List campaigns | `GET /v1/campaign_list` ✓ | `campaigns list` | array w/ status, from_*, per_day, folder, counts |
| Campaign stats (v1) | `GET /v1/campaign_list?id={id}` ✓ | `campaigns list` (single) / `reports` | **single** `id` → adds a `stats` object; multiple ids → list without stats |
| Get campaign | `GET /v2/campaigns/{id}` ✓ | `campaigns get <id>` | full schema: settings, email_account_ids, steps, bounce_shield_*. Some legacy campaigns return `409 API_UNSUPPORTED_CAMPAIGN` on v2 — read those from `campaigns list` (v1) instead |
| Create campaign | `POST /v2/campaigns` | `campaigns create --body-file p.json` | DRAFT; see SKILL.md "Creating a campaign" for the verified body |
| Make editable | `POST /v2/campaigns/{id}/editable` | `raw` | unlock a RUNNING campaign to edit steps |
| Update settings | `PATCH /v2/campaigns/{id}` | `raw` | name, settings (timezone, daily_enroll), email_account_ids |
| Delete campaign | `DELETE /v2/campaigns/{id}` | `campaigns delete <id>` | |
| Run / Pause / Stop | `POST /v2/campaigns/{id}/run\|pause\|stop` | `campaigns run\|pause\|stop <id>` | run only after approval |
| Add step | `POST /v2/campaigns/{id}/steps` | `raw` | append an EMAIL/manual step (followup_after, delivery_time, body.versions) |
| Update step | `PATCH /v2/campaigns/{id}/steps/{stepId}` | `raw` | |
| Update step version | `PATCH /v2/campaigns/{id}/steps/{stepId}/versions/{versionId}` | `raw` | A/B version copy (subject, message, signature) |
| Delete step | `DELETE /v2/campaigns/{id}/steps/{stepId}` | `raw` | |
| **Bounce-shield** get threshold | `GET /v2/campaigns/{id}/bounce_shield/threshold` ✓ | `raw` | → `{bounce_rate_threshold}` |
| Bounce-shield set threshold | `PUT /v2/campaigns/{id}/bounce_shield/threshold` | `raw` | body `{"bounce_rate_threshold": <1-99>}` (integer %) → 204; auto-pauses the campaign past that bounce rate |
| Bounce-shield remove threshold | `DELETE /v2/campaigns/{id}/bounce_shield/threshold` | `raw` | revert to default |

Docs: `/docs/campaigns/...`, bounce-shield under `/docs/campaigns/bounce-shield/`.

## Prospects (v1 legacy unless noted)

| Op | Method · path | CLI | Notes |
| --- | --- | --- | --- |
| List in DB | `GET /v1/prospects` ✓ | `prospects list` | paginate; each prospect has email, snippets, status, last_contacted |
| Search prospects | `GET /v1/prospects?<filters>` ✓ | `prospects search --email\|--company\|--where k=v` | filter by email/company/tags/status/campaign/activity |
| Get in campaign | `GET /v1/prospects?campaigns_id=<id>` | `prospects list-campaign <ids>` | prospects in given campaign(s) |
| Get responses | `GET /v2/prospects/{id}/responses` | `prospects responses <id>` | reply threads for one prospect |
| Add to DB | `POST /v1/add_prospects_list` | `prospects create --body-file p.json` | upsert by email |
| Add to campaign | `POST /v1/add_prospects_campaign` | `prospects add-to-campaign <id> --body-file … [--send-after <ISO>]` | enroll w/ per-prospect snippets |
| Update in DB | `POST /v1/update_prospects_list` (via `prospects create`) | `prospects create` | |
| Update in campaign | `POST /v1/update_prospects_campaign` | `prospects update-prospects-campaign <id> --body-file …` | |
| **Delete prospect** | `DELETE /v1/prospects?id=<id>` | `prospects delete <id>` | **opt-out / GDPR erasure → delete AND blacklist (below)** |

Docs: `/docs/prospects/...`.

## Inbox

| Op | Method · path | CLI |
| --- | --- | --- |
| List inbox messages | `GET /v2/inbox/messages` | `inbox list` |
| Reply to a message | `POST /v2/inbox/messages/{id}/reply` | `inbox reply <messageId> --body '…'` |

Docs: `/docs/inbox/...`.

## Mailboxes (sending identities)

| Op | Method · path | CLI | Notes |
| --- | --- | --- | --- |
| List mailboxes | `GET /v2/mailboxes` ✓ | `mailboxes list` | SMTP + paired IMAP ids |
| Get mailbox | `GET /v2/mailboxes/{id}` | `mailboxes get <id>` | |
| Add mailbox(es) (manual connect) | `POST /v2/mailboxes` | `mailboxes add-bulk` | wizard / bulk manual connection |
| Update mailbox footer | `PATCH /v2/mailboxes/{id}` | `mailboxes update <id>` | SMTP mailbox footer/signature |
| Get connection batch summary | `GET /v2/mailboxes/batch/{batchId}` | `mailboxes get-batch-summary <batchId>` | status of a manual-connection batch |
| **Microsoft** add credentials | `POST /v2/mailboxes/microsoft/credentials` | `raw` | OAuth app credentials for M365 |
| Microsoft get credentials | `GET /v2/mailboxes/microsoft/credentials` | `raw` | |
| Microsoft update credentials | `PATCH /v2/mailboxes/microsoft/credentials` | `raw` | |
| Microsoft delete credentials | `DELETE /v2/mailboxes/microsoft/credentials` | `raw` | |
| Microsoft add mailbox | `POST /v2/mailboxes/microsoft` | `raw` | connect a Microsoft 365 mailbox |

Docs: `/docs/mailboxes/...`, Microsoft under `/docs/mailboxes/microsoft/`.

## Manual tasks

| Op | Method · path | CLI |
| --- | --- | --- |
| List manual tasks | `GET /v2/manual_tasks` ✓ | `manual-tasks list` |

LinkedIn/manual steps surface here; pair with the `task_created/done/ignored` webhooks.

## LinkedIn accounts

| Op | Method · path | CLI |
| --- | --- | --- |
| List LinkedIn accounts | `GET /v2/linkedin_accounts` ✓ | `linkedin list` |
| (Agency) connect a LinkedIn account | `POST` (agency LinkedIn connect) | `agency …` | Agency addon; docs `/docs/agency-api/linkedin/POST-connect-linkedin` |
| (Agency) get LinkedIn connect link | `POST` (li-connect-link) | `agency …` | Agency addon; docs `/docs/agency-api/linkedin/POST-li-connect-link` |

## Reports

Run via the CLI (`reports generate <name>` → hash, then `reports get <hash>` /
`reports poll <hash>`). Report names (`reports types`):

| Name (aliases) | Content |
| --- | --- |
| `campaigns` (general, general-statistics, campaign-stats) | general statistics per campaign |
| `messages` (sent-messages, message-counts) | number of messages sent per level/step/version (daily) |
| `open_rate` | open rate per campaign |
| `complete` (complete-statistics) | combined stats (general + sent + open) |

Date window: `--from/--to` or `--last-7-days/--last-30-days/--this-month/--previous-month`.
Docs: `/docs/reports/...`.

## Webhooks (real-time events)

| Op | Method · path | CLI |
| --- | --- | --- |
| List subscriptions | `GET /v2/webhooks` ✓ | `webhooks list` |
| List allowed events | (CLI convenience) | `webhooks events` |
| Subscribe | `POST /v1/webhooks/subscribe` ✓ body `{event, target_url}` | `webhooks subscribe --event <e> --target-url <url>` |
| Unsubscribe | `POST /v1/webhooks/unsubscribe` ✓ body `{event, target_url}` | `webhooks unsubscribe --event <e> --target-url <url>` |

Use `scripts/webhooks.py` to manage them (incl. bulk-subscribing the prospecting set).

**Subscribable events — the authoritative 21 (verified live via `webhooks events`):**
`campaign_completed`, `campaign_sent`, `followup_after_autoreply`,
`linkedin_automation_connection_request_accepted`, `prospect_autoreplied`,
`prospect_blacklisted`, `prospect_bounced`, `link_clicked`, `prospect_interested`,
`prospect_invalid`, `prospect_maybe_later`, `prospect_non_responsive`,
`prospect_not_interested`, `email_opened`, `prospect_opt_out`, `prospect_replied`,
`prospect_saved`, `secondary_replied`, `task_created`, `task_done`, `task_ignored`.

> The docs also describe payloads for `campaign_paused_by_bounce_shield`,
> `linkedin_account_connected`, `linkedin_account_disconnected`,
> `prospect_li_cr_accepted`, `prospect_li_dm_sent` — these were **not** in the
> account's subscribable list, so don't `subscribe` them blindly (a bad event
> errors; `webhooks.py` handles that gracefully).

Routing (see SKILL.md "Webhooks"): `prospect_replied` / `prospect_interested` /
`secondary_replied` → notify team + EA (high priority); `prospect_opt_out` →
delete + blacklist; `prospect_bounced` / `prospect_invalid` → suppress.
Many events carry an AI **classification** (interested / not-interested /
maybe-later / non-responsive). Docs: `/docs/webhooks/...`.

## Blacklist (suppression — emails & domains)

| Op | Method · path | CLI |
| --- | --- | --- |
| List blacklisted emails | `GET /v2/blacklist/emails` ✓ | `blacklist emails list` |
| Add blacklisted emails | `POST /v2/blacklist/emails` | `blacklist emails add --body-file …` |
| Delete blacklisted emails | `DELETE /v2/blacklist/emails` | `blacklist emails delete …` |
| List blacklisted domains | `GET /v2/blacklist/domains` | `blacklist domains list` |
| Add blacklisted domains | `POST /v2/blacklist/domains` | `blacklist domains add --body-file …` |
| Delete blacklisted domains | `DELETE /v2/blacklist/domains` | `blacklist domains delete …` |

REST body for add/delete (verified): `{"emails":["a@x.com", …]}` / `{"domains":["x.com", …]}`
(arrays of **strings**, not objects). GET is **paginated** (~100/page, alphabetical;
read `total`). (2025-04 blacklist changes apply — see `/docs/2025-04-blacklist-changes`.)
Agency-wide blacklist: `agency blacklist …` (Agency addon).

## Lead Finder (find + enrich prospects)

| Op | Method · path | Notes |
| --- | --- | --- |
| Search criteria catalog | `GET /v2/lead_finder/search_criteria` ✓ | free |
| Criteria values | `GET /v2/lead_finder/search_criteria/{NAME}/values` ✓ | free; `?search_phrase=&page=&limit=` |
| Search leads | `POST /v2/lead_finder/leads` ✓ | body `{search_criteria:[{name,operator:INCLUDE\|EXCLUDE,value}], size, next_page}`; 1 cr/lead |
| Queue lead enrichment | `POST /v2/lead_finder/leads/enrichments` ✓ | `{"leads":[{"uid":…}]}` → batch uuid |
| List / get lead enrichment | `GET /v2/lead_finder/leads/enrichments[/{uuid}]` ✓ | poll status |
| Queue prospect enrichment | `POST /v2/lead_finder/prospects/enrichments` ✓ | `{"prospects":[{email,…}]}` |
| Query prospect enrichment | `POST /v2/lead_finder/prospects/enrichments/statuses/query` ✓ | by email |
| Get prospect enrichment | `GET /v2/lead_finder/prospects/enrichments/{uuid}` ✓ | |

Use `scripts/lead_finder.py`. See SKILL.md "Lead Finder" for body shapes, credits,
and the honest enrichment caveats. Docs: `/docs/lead-finder/...`.

## Agency (Agency addon only)

`agency companies` (sub-accounts), `agency deliverability`, `agency blacklist`,
`agency …/linkedin/connect`. Returns `403 No Agency addon` without the addon.
