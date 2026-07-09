#!/usr/bin/env python
"""Fake JSON stdin/stdout tool for DevFlow Runner tests."""

from __future__ import annotations

import json
import sys


def main() -> int:
    raw = sys.stdin.read()
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({
            "ok": False,
            "data": {},
            "warnings": [],
            "metrics": {},
            "error": {"code": "BAD_STDIN", "message": str(exc)},
        }))
        return 2

    inputs = envelope.get("inputs", {})
    print(json.dumps({
        "ok": True,
        "data": inputs,
        "warnings": [],
        "metrics": {
            "input_keys": len(inputs),
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
