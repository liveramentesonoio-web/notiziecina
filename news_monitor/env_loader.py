from __future__ import annotations

import os
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
SECRET_KEYS = [
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_TRANSLATION_MODEL",
    "DEEPSEEK_API_URL",
]


def load_local_env() -> None:
    if not ENV_PATH.exists():
        _load_streamlit_secrets()
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

    _load_streamlit_secrets()


def _load_streamlit_secrets() -> None:
    try:
        import streamlit as st
    except Exception:
        return

    try:
        secrets = st.secrets
        for key in SECRET_KEYS:
            if key not in os.environ and key in secrets:
                os.environ[key] = str(secrets[key])
    except Exception:
        return
