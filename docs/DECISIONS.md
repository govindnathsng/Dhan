# Decision log

## D-001 (Phase 0): Config errors refuse to start; ceilings reject rather than clip
Clipping silently changes what the owner wrote. Rejecting makes the mismatch visible.
Unknown keys, duplicate YAML keys, string numbers and non-exact `mode` values are all errors.
A missing config file (when none is explicitly requested) means built-in defaults, which are paper.

## D-002 (Phase 0): Hard ceiling values
The owner fixed risk per trade at 0.5% of the cap. The other ceilings were set at about 2x the
owner's defaults so that small adjustments are possible without code changes, while large
mistakes (such as a typo of 5 instead of 0.5) are impossible:

| Limit | Default | Ceiling |
|---|---|---|
| risk per trade | 0.25% | 0.5% |
| daily loss | 0.5% | 1.0% |
| weekly loss | 1.5% | 3.0% |
| max drawdown | 4% | 8% |
| open positions | 2 | 4 |
| position value | 20% | 40% |
| orders per day | 10 | 20 |
| price band vs LTP | 0.5% | 1.0% |
| live capital cap | INR 50,000 | INR 100,000 |

Config also requires risk per trade <= daily loss <= weekly loss <= drawdown.
Changing a ceiling is a code change that needs the owner's explicit instruction.

## D-003 (Phase 0): Our own rate-limit budget sits well below Dhan's limits
Defaults are a small fraction of the documented limits. Config may lower them, but never
raise them above the documented values.

## D-004 (Phase 0): argparse instead of a CLI framework
Fewer dependencies, and the commands are simple.

## D-005 (Phase 0): Dependency pinning
`pyproject.toml` pins direct dependencies exactly (`dhanhq==2.3.0`, confirmed as the latest
on PyPI on 2026-11-05). `requirements.lock` pins the full transitive set for reproducibility.

## D-006 (Phase 0): Redaction is aggressive by design
Any run of 40 or more token-like characters is redacted, along with JWTs, bearer tokens,
key=value pairs for sensitive keys (token, pin, totp, password, client id, chat id and so on),
and the literal values of the known secret variables. This can hide harmless long IDs in
logs. That trade-off is accepted.
