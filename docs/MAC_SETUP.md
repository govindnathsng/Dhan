# Mac setup and first connection check

What this gets you **today**: the app installed on your Mac, your config validated, and a
**read-only** check that your Dhan token, Data API plan, DDPI, funds, holdings, orders, static IP
and market data all work. Nothing in this version can place an order.

## 1. Install (one time)

```bash
# Homebrew (skip if already installed): https://brew.sh
brew install python@3.12 git

git clone <your repo URL> automator
cd automator
git checkout cursor/phase0-scaffold-9adc   # until it is merged

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

pytest -q                 # expect: all passed
automator check-config    # expect: effective mode: paper, config OK
```

## 2. Every morning: load a fresh token (never paste it into chat or a file)

1. Log in to web.dhan.co, open My Profile, then "Access DhanHQ APIs", and generate an Access Token
   (it is valid for 24 hours).
2. In the terminal where you will run the app:

```bash
cd automator && source .venv/bin/activate
read -rs DHAN_CLIENT_ID && export DHAN_CLIENT_ID        # type your client ID, press Enter (not shown)
read -rs DHAN_ACCESS_TOKEN && export DHAN_ACCESS_TOKEN  # paste the token, press Enter (not shown)
```

`read -rs` keeps the value out of your shell history and off the screen. The variables vanish
when you close the terminal. Do **not** set `DHAN_LIVE_ENABLED`.

## 3. Run the read-only check

```bash
automator dhan-check --detect-ip --symbols NIFTYBEES,GOLDBEES,RELIANCE
```

Expected output, with one line per check:

| Check | What PASS means | If it fails |
|---|---|---|
| access token | `/profile` accepted the token | generate a new token (DH-901 = expired or invalid) |
| equity segment | Equity is active on the account | activate it in the Dhan app |
| Data API plan | your Rs 499 plan shows `Active` | check the subscription on web.dhan.co |
| DDPI | DDPI is active | WARN only. Without DDPI, resting sell stops may need TPIN/eDIS [verify] |
| funds | available balance >= Rs 25,000 (the canary cap); the amount is not printed | WARN only |
| open positions / orders | none open | WARN only (live pre-flight will later require none unexpected) |
| static IP | a static IP is registered with Dhan | needed only for orders (not for data); see section 5 |
| this machine's IP | your Mac's public IP equals a registered IP | expected to FAIL until you have a static IP |
| LTP ... | live prices arrive through the Data API | 806 = Data API not active |

Paste the output into chat if you want me to read it. It contains no token, balance or full
client ID; only the last 4 digits are shown.

## 4. What can and cannot happen tomorrow

- **Can:** everything above, plus `automator check-config`.
- **Cannot yet:** trading, whether paper or live. The deterministic core (snapshot, proposal
  validation, risk engine, paper simulator) is Phase 1. The AI research loop is Phase 2. Live
  trading is Phase 6, after the paper evidence period.

## 5. Static IP: can I use a proxy or geo IP?

Dhan's docs say: static IP whitelisting is mandatory under SEBI/exchange rules, **each individual
needs a unique static IP**, it is required only for order placement (orders, Super Orders, Forever
Orders), and once set it **cannot be changed for 7 days**. Reads and data calls need no static IP.

| Option | Verdict |
|---|---|
| Rotating, residential or "geo" proxies | **No.** The IP changes and is shared with other people. Orders would be refused, and a shared IP breaks the unique-IP rule. |
| A shared VPN server IP | **No.** Shared with other users. |
| A dedicated (exclusive) static IP from a VPN provider | Might work technically, but whether Dhan/exchanges accept VPN or foreign IPs is unconfirmed [verify]. It also adds a third party in the order path. Ask Dhan support before relying on it. |
| **Static IP from your home ISP** (Airtel, Jio Fiber, ACT and others sell it as an add-on) | **Recommended for the Mac.** The traffic really originates from your connection. |
| **Small Indian VPS with a static IP** (for example AWS Mumbai with an Elastic IP) | **Recommended alternative.** It is always on, and the bot runs there instead of on the Mac. |

Whatever you choose, set it in web.dhan.co (or via the API), then run
`automator dhan-check --detect-ip` from the machine that will trade. It must say "matches".

## 6. Keeping the Mac awake (later phases)

While the bot runs during market hours, the Mac must not sleep: run `caffeinate -dimsu` in a
second terminal, or change Energy settings. The scheduled runner (Phase 6) will document
`launchd` jobs.
