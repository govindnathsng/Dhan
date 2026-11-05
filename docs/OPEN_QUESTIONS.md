# Open questions and unverified behaviour

Items tagged [verify] stay open until checked against https://dhanhq.co/docs/v2/,
https://cursor.com/docs, the SDK source (https://github.com/dhan-oss/DhanHQ-py, pinned 2.3.0), or a
sandbox probe.

| # | Question | Needed by | Status |
|---|---|---|---|
| Q1 | Nifty 50 constituents in `config/whitelist.yaml` are best-effort as of late 2025. All 54 symbols do exist in Dhan's NSE_EQ scrip master (checked 2026-11-05); index membership still needs checking against niftyindices.com. | Phase 1 | [verify] (owner) |
| Q2 | Ceilings and floors in D-002. Owner to confirm. | Phase 0 review | open (owner) |
| Q3 | Rate-limit figures in `ceilings.py` come from the owner's brief. Re-check against the current docs. | Phase 3 | [verify] |
| Q4 | Can a Dhan token be scoped to data only? If not, `DHAN_DATA_ACCESS_TOKEN` in the cloud is a full-account token, and only the static-IP rule stops it from placing orders. | Phase 2 | [verify] |
| Q5 | Forever Order OCO: which leg is the stop and which is the target; validity; persistence for CNC. | Phase 3 probe | [verify] |
| Q6 | Do Super Order legs persist beyond the day for CNC? | Phase 3 probe | [verify] |
| Q7 | Are DDPI/TPIN required for resting sell stops on delivery holdings? | Phase 3 probe | [verify] |
| Q8 | Broker-side P&L Exit behaviour for delivery positions. | Phase 6 | [verify] |
| Q9 | Does the sandbox leave orders PENDING forever (as a third-party client reports)? | Phase 3 | [verify] |
| Q10 | Does the scrip master CSV carry ASM/GSM flags, or is another source needed? | Phase 1 | [verify] |
| Q11 | Can a Cursor Automation push to a non-default `data` branch without a PR? | Phase 2 | [verify] |
| Q12 | NSE holiday list for 2026/2027 (it will be an editable data file). | Phase 1 | open |
| Q13 | Cost rates (STT, stamp duty, NSE transaction charge, SEBI fee, GST, DP charge) as of 2026-11-05. | Phase 1 | [verify] |
| Q14 | Does Dhan accept a dedicated VPN or foreign static IP, or only Indian ISP/VPS IPs? | Phase 6 | [verify] (ask Dhan support) |
| Q15 | Units of `SEM_TICK_SIZE` in the scrip master (it appears to be paise: NIFTYBEES 1.0, RELIANCE 10.0). | Phase 1 | [verify] |
| Q16 | Fund-limit balance field name (`availabelBalance` as spelled in the docs, vs `availableBalance`). Both are accepted. | Phase 1 | [verify] |
| Q17 | Reply from GET /holdings when there are no holdings (an error vs an empty list). | Phase 1 | [verify] |
