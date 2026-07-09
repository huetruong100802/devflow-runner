#!/usr/bin/env python
from __future__ import annotations

import json
import sys

print("human-only stderr log", file=sys.stderr)
print(json.dumps({"ok": True, "data": {"status": "ok"}, "warnings": [], "metrics": {}}))
