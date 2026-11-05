# Open questions and unverified behaviour

Each item stays open until it is checked against https://dhanhq.co/docs/v2/, the SDK source
(https://github.com/dhan-oss/DhanHQ-py, pinned 2.3.0), or the sandbox.

| # | Question | Needed by | Status |
|---|---|---|---|
| Q1 | Instrument whitelist: placeholders `NIFTYBEES`, `JUNIORBEES` are used. Owner to confirm the real symbols. | Phase 1 | open (owner) |
| Q2 | Hard ceilings in D-002 (about 2x defaults; cap ceiling INR 100,000). Owner to confirm. | Phase 0 review | open (owner) |
| Q3 | Rate-limit figures in `ceilings.py` come from the owner's research brief. Re-check them against the current docs before Phase 3. | Phase 3 | unverified |
| Q4 | Does Super Order support CNC with a resting stop-loss leg on NSE_EQ for delivery positions held overnight? | Phase 5 | unverified |
| Q5 | Exact NSE holiday list for 2026/2027. It will ship as an editable data file in Phase 2. | Phase 2 | open |
| Q6 | Does the scrip master CSV carry ASM/GSM flags, or is a separate source needed? | Phase 1 | unverified |
