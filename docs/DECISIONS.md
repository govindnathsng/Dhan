# Decision log

## D-001 (Phase 0): Config errors refuse to start; bounds reject rather than clip
Clipping silently changes what the owner wrote. Rejecting makes the mismatch visible. Unknown keys,
duplicate YAML keys, numbers written as strings, non-exact `mode`/`kind` values, an unknown profile,
`mode: live` with a paper-kind profile, and a missing or invalid whitelist are all errors. A missing
config file (when none is explicitly requested) means built-in defaults, which are paper.

## D-002 (Phase 0): Hard ceilings and floors
The owner fixed risk per trade at a ceiling of Rs 250 / Rs 125, which is 0.5% of each profile's
capital. The ceilings are therefore expressed as **% of profile capital**, so they scale
automatically for a manually scaled live profile. The other exposure ceilings are about 2x the
owner's defaults: small adjustments need no code change, while large mistakes are impossible.

| Exposure limit | Ceiling | paper (50k) | live_canary (25k) |
|---|---|---|---|
| any profile's capital | Rs 50,000 absolute | 50,000 | 25,000 |
| risk per trade | 0.5% | 250 | 125 |
| daily loss | 1% | 500 | 250 |
| weekly loss | 3% | 1,500 | 750 |
| drawdown halt | 8% | 4,000 | 2,000 |
| position value | 40% | 20,000 | 10,000 |
| total invested | 80% | 40,000 | 20,000 |
| open positions / new entries per week / orders per day / proposals per day | 4 / 5 / 10 / 5 | | |
| entry price band | 1.0% | | |

**Protective settings** use the owner's values as hard floors, so config can only make them
stricter: stop distance at least 1% and at most 6%, at least 0.75 x ATR(14), minimum net
reward-to-risk 1.5, re-entry cooldown 5 days, losing streak of at most 3 losses then a pause of at
least 2 trading days, review note always required, minimum confidence at least 0.5.

Config also requires risk per trade <= daily <= weekly <= drawdown halt, and
position value <= total invested. Changing any bound is a code change that needs the owner's
explicit instruction.

## D-003 (Phase 0): Live approval is always Telegram and is not configurable
`approval.paper_mode` (auto | telegram) applies only to paper mode. There is deliberately no key
that can change live approval, and unknown keys are rejected, so `live_mode: auto` and similar
cannot be configured.

## D-004 (Phase 0): Whitelist is a separate owner-maintained file
`config/whitelist.yaml` records symbol, kind (ETF | EQUITY) and category (equity | gold | liquid |
gilt). The category drives the STT exemption. Its content is part of the config hash, so any change
shows up in the journal. Blackout entries must reference whitelisted symbols.

## D-005 (Phase 0): Our own rate-limit budget sits well below Dhan's limits
Config may lower the documented limits, never raise them.

## D-006 (Phase 0): Small dependency surface
`argparse` for the CLI. `pyproject.toml` pins direct dependencies exactly (`dhanhq==2.3.0`,
confirmed as the latest on PyPI on 2026-11-05). `requirements.lock` pins the full transitive set.

## D-007 (Phase 0): Redaction is aggressive by design
Any run of 40 or more token-like characters is redacted, along with JWTs, bearer tokens,
key=value pairs for sensitive keys (token, pin, totp, password, client/chat/user id and so on), and
the literal values of every known secret variable. Harmless long IDs may be hidden. That trade-off
is accepted.
