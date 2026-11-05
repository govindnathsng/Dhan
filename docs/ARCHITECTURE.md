# Architecture

Single-process package, SQLite plus append-only journal files, structured JSON logs.
The mode (paper / sandbox / live) and the risk profile are chosen **once** at startup.

```
  config.yaml + config/whitelist.yaml (owner-edited)      env vars (credentials; never in repo)
                 |                                                   |
         +-------v--------+   hard ceilings / floors (code)          |
         | config (strict)|<---------------------------------        |
         +-------+--------+                                          |
                 | modes.resolve_mode (live gate; refused before Phase 6)
                 v
 +------------+     +-------------+     +----------------------+     +---------------------+
 |   data     |---->|  snapshot   |---->|  AI research agent   |---->| proposals: schema,  |
 | hist/live, |     | (determin-  |     |  UNTRUSTED, no creds,|     | validator, claim    |
 | instrument |     |  istic JSON,|     |  writes JSON only    |     | checker (recomputes |
 | master,    |     |  hash)      |     +----------------------+     | numbers from snap)  |
 | calendar   |     +------+------+                                  +----------+----------+
 +------------+            |                                                    |
                           |            shadow baseline (no order path)         v
                           |                                         +----------------------+
                           +---------------------------------------->|  risk engine (VETO,  |
                                                                     |  fails closed, sizes)|
                                                                     +----------+-----------+
                                                                                |
                                                          approval: auto (paper) | Telegram (live,
                                                          always)                v  always)
                                                                     +----------------------+
                             journal (SQLite + append-only) <--------|  order manager       |
                             daily/weekly reviews, alerts            |  re-checks, idempot.,|
                                                                     |  reconciliation      |
                                                                     +----------+-----------+
                                                                                |
                                                                     +----------v-----------+
                                                                     | brokers (interface)  |
                                                                     | PaperBroker (sim)    |
                                                                     | DhanSandboxBroker    |
                                                                     | DhanLiveBroker (gate)|
                                                                     +----------------------+
```

Rules the layout enforces:

- Only `brokers/` may import the `dhanhq` SDK (a test checks this).
- The AI agent and the shadow baseline produce data only. Only the order manager talks to a
  broker, and only with orders the risk engine accepted and (in live) a human approved.
- Backtest (baseline only), paper and live share the same risk engine and order-manager code.

Status: Phase 0 implements `config` (schema, ceilings, whitelist, loader), `modes`, `secrets`,
`logging_setup` and `cli`. The other boxes are planned for later phases.
