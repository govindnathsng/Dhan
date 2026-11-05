"""Command-line entry point: `automator`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from automator import __version__
from automator.config import ConfigError, LoadedConfig, load_config
from automator.config import ceilings as C
from automator.logging_setup import configure_logging
from automator.modes import LiveGateRefusedError, ModeError, resolve_mode
from automator.secrets import (
    DATA_ACCESS_TOKEN,
    DATA_CLIENT_ID,
    LIVE_ACCESS_TOKEN,
    LIVE_CLIENT_ID,
    credential_status,
    get_secret,
    live_host_vars_present,
)

EXIT_OK = 0
EXIT_CONFIG_INVALID = 2
EXIT_MODE_REFUSED = 3
EXIT_CHECK_FAILED = 4
EXIT_MISSING_CREDENTIALS = 5

_EPILOG = """\
Paper mode is the default. Live trading is not available in this version
(the live gate arrives in Phase 6). Credentials are read only from environment
variables; this tool never prints their values.
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="automator",
        description="Safety-first, AI-assisted, long-only CNC trading automator for DhanHQ.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"automator {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    cc = sub.add_parser(
        "check-config",
        help="validate config and whitelist, show effective mode, limits and credential presence",
    )
    cc.add_argument(
        "--config",
        default=None,
        help="path to config YAML (default: $AUTOMATOR_CONFIG, then ./config.yaml, "
        "then built-in paper defaults)",
    )
    cc.add_argument(
        "--live",
        action="store_true",
        help="ask whether live mode would be allowed (it never is before Phase 6)",
    )

    dc = sub.add_parser(
        "dhan-check",
        help="READ-ONLY Dhan check: token, Data API, DDPI, funds, holdings, orders, "
        "static IP, LTP. Never places orders.",
    )
    dc.add_argument("--config", default=None, help="path to config YAML")
    dc.add_argument(
        "--credentials",
        choices=["auto", "live", "data"],
        default="auto",
        help="which env vars to use: live = DHAN_CLIENT_ID/DHAN_ACCESS_TOKEN, "
        "data = DHAN_DATA_CLIENT_ID/DHAN_DATA_ACCESS_TOKEN, auto = data if set, else live",
    )
    dc.add_argument(
        "--detect-ip",
        action="store_true",
        help="look up this machine's public IP (api.ipify.org) and compare it with "
        "Dhan's registered IPs",
    )
    dc.add_argument(
        "--symbols",
        default="NIFTYBEES",
        help="comma-separated whitelisted symbols to fetch LTP for (default NIFTYBEES)",
    )
    dc.add_argument(
        "--refresh-instruments", action="store_true", help="re-download the Dhan scrip master"
    )
    return parser


def _summary(loaded: LoadedConfig) -> list[str]:
    cfg = loaded.config
    p = cfg.active_profile
    r = cfg.rules

    def lim(field: str) -> str:
        return f"Rs {getattr(p, field):>9,.2f}  (ceiling Rs {p.ceiling_inr(field):,.2f})"

    source = str(loaded.source) if loaded.source else "<built-in defaults>"
    lines = [
        f"config source         : {source}",
        f"whitelist             : {loaded.whitelist_path} "
        f"({len(loaded.whitelist.instruments)} instruments)",
        f"config hash           : {loaded.config_hash}",
        f"configured mode       : {cfg.mode.value}",
        f"active profile        : {cfg.profile} (kind {p.kind.value}, "
        f"capital Rs {p.capital_inr:,.0f}; ceiling Rs {C.MAX_PROFILE_CAPITAL_INR:,.0f})",
        f"timezone              : {cfg.timezone}",
        f"entry window (IST)    : {cfg.entry_window}, NSE trading days only",
        f"risk per trade        : {lim('risk_per_trade_inr')}",
        f"max daily loss        : {lim('max_daily_loss_inr')}",
        f"max weekly loss       : {lim('max_weekly_loss_inr')}",
        f"drawdown halt         : {lim('max_drawdown_halt_inr')}",
        f"max position value    : {lim('max_position_value_inr')}",
        f"max total invested    : {lim('max_total_invested_inr')}",
        f"open positions / week entries / orders per day / proposals per day : "
        f"{p.max_open_positions} / {p.max_new_entries_per_week} / "
        f"{p.max_orders_per_day} / {p.max_proposals_per_day}",
        f"entry price band      : {r.entry_price_band_pct}% of LTP",
        f"stop distance         : {r.stop_distance_min_pct}%-{r.stop_distance_max_pct}% "
        f"and >= {r.stop_min_atr_multiple} x ATR({r.atr_period})",
        f"min net reward:risk   : {r.min_net_reward_to_risk}",
        f"cooldown / streak     : {r.reentry_cooldown_days} days after stop-out; "
        f"{r.losing_streak_losses} losses -> pause {r.losing_streak_pause_trading_days} "
        "trading days + review note",
        f"min AI confidence     : {r.min_confidence} (advisory filter; never increases size)",
        f"orders                : {cfg.orders.exchange_segment}, "
        f"{list(cfg.orders.allowed_product_types)}, {list(cfg.orders.allowed_order_types)}, "
        "long-only, protective stop required",
        f"approval              : paper={cfg.approval.paper_mode}; live=telegram (always), "
        f"expiry {cfg.approval.expiry_minutes} min, before {cfg.approval.latest_approval_time}",
        f"blackout entries      : {len(cfg.instruments.blackout)}",
        f"cost rates checked on : {cfg.costs.rates_checked_on} (re-check Dhan pricing page)",
        "credentials (presence only, values never shown):",
    ]
    for name, present in credential_status().items():
        lines.append(f"  {name:<26}: {'set' if present else 'not set'}")
    return lines


def _check_config(args: argparse.Namespace) -> int:
    try:
        loaded = load_config(args.config)
    except ConfigError as exc:
        print(f"REFUSING TO START: {exc}", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    cfg = loaded.config
    configure_logging(cfg.logging.level, cfg.logging.json_format)
    print("\n".join(_summary(loaded)))

    live_vars = live_host_vars_present()
    if live_vars:
        print(
            f"WARNING: live-host-only variables are set: {', '.join(live_vars)}. "
            "They must never be set in a cloud environment.",
            file=sys.stderr,
        )

    try:
        effective = resolve_mode(cfg, live_flag=args.live)
    except (LiveGateRefusedError, ModeError) as exc:
        print(f"effective mode        : REFUSED\n{exc}", file=sys.stderr)
        return EXIT_MODE_REFUSED
    print(f"effective mode        : {effective.value}")
    print("config OK")
    return EXIT_OK


def _credentials(choice: str) -> tuple[str, str] | None:
    pairs = {
        "live": (LIVE_CLIENT_ID, LIVE_ACCESS_TOKEN),
        "data": (DATA_CLIENT_ID, DATA_ACCESS_TOKEN),
    }
    order = ["data", "live"] if choice == "auto" else [choice]
    for name in order:
        cid, tok = (get_secret(n) for n in pairs[name])
        if cid is not None and tok is not None:
            return cid.get_secret_value(), tok.get_secret_value()
    return None


def _dhan_check(args: argparse.Namespace) -> int:
    from automator.brokers.dhan_readonly import DhanReadOnlyClient
    from automator.data.instruments import InstrumentError, cached_scrip_master, load_nse_equities
    from automator.dhan_check import detect_public_ip, run_dhan_check

    try:
        loaded = load_config(args.config)
    except ConfigError as exc:
        print(f"REFUSING TO START: {exc}", file=sys.stderr)
        return EXIT_CONFIG_INVALID
    cfg = loaded.config
    configure_logging(cfg.logging.level, cfg.logging.json_format)

    creds = _credentials(args.credentials)
    if creds is None:
        print(
            "Missing credentials. Set them yourself in this terminal (values are not echoed):\n"
            "  read -rs DHAN_CLIENT_ID && export DHAN_CLIENT_ID\n"
            "  read -rs DHAN_ACCESS_TOKEN && export DHAN_ACCESS_TOKEN\n"
            "Never paste a token into chat, a file in this repo, or a command line.",
            file=sys.stderr,
        )
        return EXIT_MISSING_CREDENTIALS

    symbols = {s.strip() for s in args.symbols.split(",") if s.strip()}
    not_listed = symbols - loaded.whitelist.symbols
    if not_listed:
        print(f"not in whitelist: {', '.join(sorted(not_listed))}", file=sys.stderr)
        return EXIT_CONFIG_INVALID
    try:
        master = cached_scrip_master(cfg.paths.data_dir / "cache", refresh=args.refresh_instruments)
        instruments = load_nse_equities(master, symbols)
    except (OSError, InstrumentError) as exc:
        print(f"instrument master unavailable: {exc}", file=sys.stderr)
        instruments = {}

    canary = cfg.profiles.get("live_canary", cfg.active_profile)
    detected = detect_public_ip() if args.detect_ip else None
    client = DhanReadOnlyClient(*creds)
    checks = run_dhan_check(client, instruments, canary.capital_inr, detected)
    for c in checks:
        print(f"[{c.status:<4}] {c.name:<20} {c.detail}")
    if args.detect_ip and detected is None:
        print("[WARN] this machine's IP   could not be detected")
    failed = any(c.status == "FAIL" for c in checks)
    print("RESULT: " + ("some checks FAILED" if failed else "all read-only checks passed"))
    return EXIT_CHECK_FAILED if failed else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "check-config":
        return _check_config(args)
    if args.command == "dhan-check":
        return _dhan_check(args)
    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
