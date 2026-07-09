#!/usr/bin/env python
from __future__ import annotations

import json

print(json.dumps({"ok": True, "data": {"status": "before-exit"}, "warnings": [], "metrics": {}}))
raise SystemExit(3)
