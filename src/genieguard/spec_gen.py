from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

from .models import GameSpec
from .prompts import SPEC_SYSTEM_PROMPT
from .validation import validate_gamespec


def default_gamespec(seed: int = 1337) -> GameSpec:
    # Intentionally biased baseline spec for a clear before/after demo.
    spec = {
        "meta": {"name": "CTF10-Biased", "seed": seed, "version": "0.1"},
        "map": {
            "w": 10,
            "h": 10,
            "walls": [[4, y] for y in range(10) if y not in (4, 5)] + [[6, 5], [6, 6]],
            "flags": {"A": [0, 9], "B": [2, 0]},
        },
        "spawns": {"A": [0, 0], "B": [9, 9]},
        "rules": {"max_turns": 60, "win": "capture_flag"},
        "params": {"move_cost": 1, "capture_range": 0, "deadlock_repeat": 6},
    }
    return GameSpec.from_dict(spec)


def _extract_first_json(text: str) -> dict[str, Any] | None:
    fence = re.search(r"\{[\s\S]*\}", text)
    if not fence:
        return None
    snippet = fence.group(0)
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def _call_gemini(prompt: str, seed: int) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{SPEC_SYSTEM_PROMPT}\n\n"
                            f"Design prompt: {prompt}\n"
                            f"Use seed={seed}."
                        )
                    }
                ]
            }
        ]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
    except Exception:
        return None
    text = ""
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    return _extract_first_json(text)


def generate_gamespec(prompt: str, seed: int = 1337, use_gemini: bool = False) -> GameSpec:
    if use_gemini:
        data = _call_gemini(prompt=prompt, seed=seed)
        if data is not None:
            try:
                candidate = GameSpec.from_dict(data)
                ok, _ = validate_gamespec(candidate)
                if ok:
                    return candidate
            except Exception:
                pass
    baseline = default_gamespec(seed=seed)
    ok, errors = validate_gamespec(baseline)
    if not ok:
        raise ValueError(f"Built-in default spec is invalid: {errors}")
    return baseline
