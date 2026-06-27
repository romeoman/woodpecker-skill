# Woodpecker skill — for OpenClaw

An agent **skill** for [Woodpecker](https://woodpecker.co): find prospects and run
cold-email outreach from the CLI and small scripts instead of the web UI.

Built for **OpenClaw** agents (the `SKILL.md` format an OpenClaw agent loads), but
fully self-contained — any agent that can read a `SKILL.md`, or a human at a
terminal, can use it. The scripts are plain Python (standard library only).

## Install into OpenClaw

Drop the folder into your OpenClaw workspace skills directory — it's auto-discovered
(no restart, no registry entry):

```bash
git clone https://github.com/romeoman/woodpecker-skill ~/.openclaw/workspace/skills/woodpecker
export WOODPECKER_API_KEY="your-key"   # or set it in the container/.env
```

A new agent session scans `~/.openclaw/workspace/skills/`, finds the `SKILL.md`, and
can drive Woodpecker. (Works the same in any agent runtime that loads skills from a
folder.)

## Use standalone (no agent)

```bash
export WOODPECKER_API_KEY="your-key"
# find prospects at a target account and reveal emails
python scripts/lead_finder.py --company-website example.com --level cxo --size 25 --enrich
# subscribe the reply/interest/opt-out webhook set to your endpoint
python scripts/webhooks.py setup https://your-endpoint/woodpecker
# call any endpoint directly
python scripts/wp.py GET /v2/campaigns
```

The Woodpecker CLI (official distribution) drives the wrapped command groups; the
`scripts/` here + `woodpecker raw request` cover the rest (Lead Finder, campaign
steps, bounce-shield thresholds, Microsoft mailboxes, …).

## What's inside

| File | Purpose |
| --- | --- |
| `SKILL.md` | The skill: how to operate Woodpecker end to end. |
| `references/api-reference.md` | Full REST endpoint map — method, path, CLI command, version split (v1/v2). |
| `scripts/lead_finder.py` | Lead Finder: search the B2B people DB by title/role/industry/country/company, paginate, enrich. |
| `scripts/webhooks.py` | Manage webhooks: list / subscribe / unsubscribe + bulk `setup` of the prospecting event set. |
| `scripts/wp.py` | Tiny generic REST client for any endpoint. |

## Security

- **No credentials are stored.** The only secret is `WOODPECKER_API_KEY`, read from
  the environment at runtime — never hardcoded.
- Don't commit a `.env` (see `.gitignore`). Rotate your key if it is ever exposed.

## License

MIT — see [LICENSE](LICENSE).
