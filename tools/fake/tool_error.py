#!/usr/bin/env python
from __future__ import annotations

import json

print(json.dumps({
    "ok": False,
    "error": {
        "code": "FAKE_TOOL_ERROR",
        "message": "simulated tool-level failure",
        "details": {"source": "test fixture"},
    },
    "metrics": {},
}))
