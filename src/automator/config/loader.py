"""Config loading. Fails closed: anything doubtful raises ConfigError."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from automator.config.models import AppConfig

CONFIG_ENV_VAR = "AUTOMATOR_CONFIG"
DEFAULT_CONFIG_PATH = Path("config.yaml")


class ConfigError(Exception):
    """Raised when config is missing a required file, ambiguous, or invalid."""


@dataclass(frozen=True)
class LoadedConfig:
    config: AppConfig
    source: Path | None  # None means built-in defaults were used
    config_hash: str


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (PyYAML keeps the last one silently)."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ConfigError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def parse_config_text(text: str) -> AppConfig:
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)  # noqa: S506 - SafeLoader subclass
    except yaml.YAMLError as exc:
        raise ConfigError(f"config is not valid YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")
    try:
        return AppConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(exc)) from exc


def _format_validation_error(exc: ValidationError) -> str:
    lines = ["config is invalid:"]
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "<root>"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)


def config_hash(config: AppConfig) -> str:
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def resolve_config_path(explicit: str | Path | None) -> Path | None:
    """Explicit path > $AUTOMATOR_CONFIG > ./config.yaml > built-in defaults (None).

    An explicitly requested path that does not exist is an error, never a silent fallback.
    """
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        return path
    env_value = os.environ.get(CONFIG_ENV_VAR)
    if env_value:
        path = Path(env_value)
        if not path.is_file():
            raise ConfigError(f"{CONFIG_ENV_VAR} points to a missing file: {path}")
        return path
    if DEFAULT_CONFIG_PATH.is_file():
        return DEFAULT_CONFIG_PATH
    return None


def load_config(explicit: str | Path | None = None) -> LoadedConfig:
    path = resolve_config_path(explicit)
    cfg = AppConfig() if path is None else parse_config_text(path.read_text(encoding="utf-8"))
    return LoadedConfig(config=cfg, source=path, config_hash=config_hash(cfg))
