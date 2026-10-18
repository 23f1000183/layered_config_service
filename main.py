
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce(key: str, value: Any) -> Any:
    """Convert configuration values to the required types."""

    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true", "1", "yes", "on"
        }

    if key in ("api_key", "log_level"):
        return str(value)

    return value


def normalize_key(key: str) -> str:
    """Normalize configuration keys and support aliases."""

    key = key.strip()

    if key.startswith("APP_"):
        key = key[4:]

    key = key.lower()

    if key == "num_workers":
        return "workers"

    return key


def merge_layer(config: dict, layer: dict) -> None:
    """Merge one configuration layer into the existing configuration."""

    for raw_key, value in layer.items():
        if value is None:
            continue

        key = normalize_key(str(raw_key))

        if key in DEFAULTS:
            config[key] = coerce(key, value)


def effective_config(sets: list[str] | None = None) -> dict:
    """Resolve configuration using increasing precedence."""

    config = dict(DEFAULTS)

    # 1. Environment-specific YAML configuration
    env_name = os.getenv("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"

    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}
            merge_layer(config, yaml_config)

    # 2. .env file
    env_file = dotenv_values(BASE_DIR / ".env")
    merge_layer(config, env_file)

    # 3. Actual operating-system environment variables
    # These must override values from the .env file.
    for raw_key, value in os.environ.items():
        if raw_key.startswith("APP_"):
            key = normalize_key(raw_key)

            if key in DEFAULTS:
                config[key] = coerce(key, value)

    # 4. Query-string overrides have the highest precedence.
    # Supports repeated parameters, e.g. ?set=port=9000&set=debug=true
    for item in sets or []:
        if "=" not in item:
            continue

        raw_key, value = item.split("=", 1)
        key = normalize_key(raw_key)

        if key in DEFAULTS:
            config[key] = coerce(key, value)

    # Always return exactly five keys and mask the API key.
    return {
        "port": coerce("port", config["port"]),
        "workers": coerce("workers", config["workers"]),
        "debug": coerce("debug", config["debug"]),
        "log_level": str(config["log_level"]),
        "api_key": "****",
    }


app = FastAPI(title="Layered Configuration Service")

# Allow cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/effective-config")
def get_effective_config(
    set: list[str] | None = Query(default=None),
):
    return effective_config(set)
