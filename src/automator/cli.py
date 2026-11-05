"""Command-line entry point: `automator`."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from automator import __version__
from automator.config import ConfigError, ceilings, load_config
from automator.config.models import AppConfig
from automator.logging_setup import configure_logging
from automator.modes import LiveGateRefusedError, ModeError, resolve_mode
from automator.secrets import credential_status

EXIT_OK = 0
EXIT_CONFIG_INVALID = 2
EXIT_MODE_REFUSED = 3

log = logging.getLogger("automator.cli")

_EPILOG = """\
Paper mode is the default. Live trading is not available in this version
(the live gate arrives in Phase 5). Credentials are read only from environment
variables; this tool never prints their values.
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="automator",
        description="Safety-first, long-only CNC trading automator for DhanHQ.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"automator {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    cc = sub.add_parser(
        "check-config",
        help="validate config, show effective mode, limits and credential presence",
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
        help="ask whether live mode would be allowed (it never is before Phase 5)",
    )
    return parser


def _summary(cfg: AppConfig, source: str, config_hash: str) -> list[str]:
    cap = cfg.capital.live_capital_cap_inr
    r = cfg.risk

    def inr(pct: float) -> str:
        return f"{pct}% = INR {cap * pct / 100:,.2f}"

    lines = [
        f"config source        : {source}",
        f"config hash          : {config_hash}",
        f"configured mode      : {cfg.mode.value}",
        f"timezone             : {cfg.timezone}",
        f"trading window (IST) : {cfg.trading_window}",
        f"live capital cap     : INR {cap:,.2f} (ceiling {ceilings.MAX_LIVE_CAPITAL_CAP_INR:,.0f})",
        f"risk per trade       : {inr(r.risk_per_trade_pct)} "
        f"(ceiling {ceilings.MAX_RISK_PER_TRADE_PCT}%)",
        f"max daily loss       : {inr(r.max_daily_loss_pct)}",
        f"max weekly loss      : {inr(r.max_weekly_loss_pct)}",
        f"max drawdown         : {inr(r.max_drawdown_pct)}",
        f"max position value   : {inr(r.max_position_value_pct)}",
        f"max open positions   : {r.max_open_positions}",
        f"max orders per day   : {r.max_orders_per_day}",
        f"price band vs LTP    : {r.price_band_pct}%",
        f"products / orders    : {list(cfg.orders.allowed_product_types)} / "
        f"{list(cfg.orders.allowed_order_types)}, long-only, stop-loss required",
        f"whitelist            : {', '.join(cfg.instruments.whitelist)}",
        f"manual approval(live): {cfg.live.require_manual_approval}",
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
    source = str(loaded.source) if loaded.source else "<built-in defaults>"
    print("\n".join(_summary(cfg, source, loaded.config_hash)))

    try:
        effective = resolve_mode(cfg, live_flag=args.live)
    except (LiveGateRefusedError, ModeError) as exc:
        print(f"effective mode       : REFUSED\n{exc}", file=sys.stderr)
        return EXIT_MODE_REFUSED
    print(f"effective mode       : {effective.value}")
    print("config OK")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "check-config":
        return _check_config(args)
    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
