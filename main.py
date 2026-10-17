import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
import yaml

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

def coerce(key: str, value: Any) -> Any:
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "on"}
    if key == "api_key" or key == "log_level" or isinstance(key, str):
        return str(value)
    return value

def normalize_key(key: str) -> str:
    key = key.strip()
    if key.startswith("APP_"):
        key = key[4:]
    key = key.lower()
    if key == "num_workers":
        return "workers"
    return key

def merge_layer(config: dict, layer: dict) -> None:
    for raw_key, value in layer.items():
        if value is None:
            continue
        key = normalize_key(str(raw_key))
        config[key] = coerce(key, value)

def effective_config(sets: list[str] | None = None) -> dict:
    config = dict(DEFAULTS)

    # Environment-specific YAML: APP_ENV selects config.<env>.yaml.
    env_name = os.getenv("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as f:
            merge_layer(config, yaml.safe_load(f) or {})

    # .env layer, with NUM_WORKERS supported as an alias for workers.
    env_file = dotenv_values(BASE_DIR / ".env")
    merge_layer(config, env_file)

    # OS environment variables override .env, and only APP_* keys are config inputs.
    os_layer = {k: v for k, v in os.environ.items() if k.startswith("APP_")}
    merge_layer(config, os_layer)

    # CLI-style query overrides are highest precedence; repeated ?set=key=value supported.
    for item in sets or []:
        if "=" not in item:
            continue
        raw_key, value = item.split("=", 1)
        key = normalize_key(raw_key)
        config[key] = coerce(key, value)

    # Always return the five required keys and never reveal the secret.
    result = {
        "port": coerce("port", config.get("port", DEFAULTS["port"])),
        "workers": coerce("workers", config.get("workers", DEFAULTS["workers"])),
        "debug": coerce("debug", config.get("debug", DEFAULTS["debug"])),
        "log_level": str(config.get("log_level", DEFAULTS["log_level"])),
        "api_key": "****",
    }
    return result

app = FastAPI(title="Layered Configuration Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/effective-config")
def get_effective_config(set: list[str] | None = Query(default=None)):
    return effective_config(set)
