# Woodpecker skill

An agent **skill** for [Woodpecker](https://woodpecker.co) — find prospects and run
cold-email outreach from the CLI / scripts instead of the web UI.

It's a self-contained skill: a `SKILL.md` an AI agent can load, a complete REST
**API reference**, and a few small **Python scripts** (stdlib only) that wrap the
parts of the API the official CLI doesn't.

## What's inside

| File                          | Purpose                                                                                                                 |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `SKILL.md`                    | The skill: how to drive Woodpecker (Lead Finder, campaigns, prospects, inbox, mailboxes, reports, webhooks, blacklist). |
| `references/api-reference.md` | Full REST endpoint map — method, path, CLI command, request-body notes, version split (v1/v2).                          |
| `scripts/lead_finder.py`      | Lead Finder: search the B2B people DB by title/role/industry/country/company, paginate, and enrich.                     |
| `scripts/webhooks.py`         | Manage webhooks: list / subscribe / unsubscribe, and bulk-`setup` the reply/interest/opt-out event set.                 |
| `scripts/wp.py`               | Tiny generic REST client for any endpoint (`python scripts/wp.py GET /v2/campaigns`).                                   |

## Setup

You need a Woodpecker API key (Woodpecker → Marketplace/Integrations → API keys).
The scripts and the CLI read it from the environment — **nothing is hardcoded.**

```bash
export WOODPECKER_API_KEY="your-key"

# find prospects at a target account, reveal emails
python scripts/lead_finder.py --company-website example.com --level cxo --size 25 --enrich

# subscribe the prospecting webhook set to your endpoint
python scripts/webhooks.py setup https://your-endpoint/woodpecker

# any endpoint directly
python scripts/wp.py GET /v2/campaigns
```

The Woodpecker CLI (`npm i -g woodpecker` or the official distribution) is used for
the wrapped command groups; `scripts/` + `woodpecker raw request` cover the rest.

## Security

- No credentials are stored in this repo. The only secret is `WOODPECKER_API_KEY`,
  read from the environment at runtime.
- Don't commit a `.env` (see `.gitignore`). Rotate your key if it's ever exposed.

## License

MIT — see [LICENSE](LICENSE).
