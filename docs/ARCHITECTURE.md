# Architecture

Single process, event-driven, SQLite for state and journal, structured JSON logs.
The mode (paper / sandbox / live) is chosen **once** at startup and never changes at runtime.

```
                    +-------------------+
 config.yaml ---->  |  config (strict,  |---- hard ceilings (code constants)
 env vars  ------>  |  pydantic)        |
                    +---------+---------+
                              |
                     modes.resolve_mode  (live gate; refuses before Phase 5)
                              |
   +-----------+     +--------v--------+     +-------------+     +------------------+
   |   data    |---->|    strategy     |---->|    risk     |---->|      orders      |
   | hist/live |     | pure function:  |     | engine with |     | order manager,   |
   | instrument|     | candles->signals|     | VETO, fails |     | idempotency,     |
   | master    |     +-----------------+     | closed      |     | reconciliation   |
   +-----------+                             +------+------+     +--------+---------+
                                                    |                     |
                                                    |             +-------v---------------+
                                           journal (SQLite) <-----|  brokers (interface)  |
                                                    |             |  PaperBroker (sim)    |
                                              alerts / reports    |  DhanSandboxBroker    |
                                                                  |  DhanLiveBroker (gate)|
                                                                  +-----------------------+
```

Rules the layout enforces:

- Only `brokers/` may import the `dhanhq` SDK (a test checks this).
- The strategy has no broker access. It emits signals. Only the order manager talks to a
  broker, and only with orders the risk engine approved.
- Backtest, paper and live run the same strategy and risk code.

Status: Phase 0 implements `config`, `modes`, `secrets`, `logging_setup` and `cli`.
The other boxes are planned for later phases.
