#!/usr/bin/env python3
"""Apply DSM reverse-proxy patches to Hermes Agent's web_server.py.

Called during SPK build to fix two issues:
1. WebSocket origin check rejects requests via DSM proxy (5000/5001)
   because bound_host=127.0.0.1 doesn't match the browser's Origin.
2. `app.state.allow_public` is never stored, preventing other code
   from checking whether --insecure mode is active.
"""
import sys
from pathlib import Path

def patch_web_server(path: Path) -> bool:
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return False

    with open(path) as f:
        c = f.read()

    # Patch 1: store allow_public on app.state (line ~9265)
    c = c.replace(
        "app.state.auth_required = should_require_auth(host, allow_public)",
        "app.state.allow_public = allow_public\n    app.state.auth_required = should_require_auth(host, allow_public)",
    )

    # Patch 2: bypass origin check in insecure mode (line ~7685)
    old = (
        '    if not _is_accepted_host(parsed.netloc, bound_host):\n'
        '        return f"origin_mismatch origin={origin} bound={bound_host}"\n'
        '    return None'
    )
    new = (
        '    if not _is_accepted_host(parsed.netloc, bound_host):\n'
        '        allow_public = getattr(app.state, "allow_public", False)\n'
        '        if allow_public:\n'
        '            return None\n'
        '        return f"origin_mismatch origin={origin} bound={bound_host}"\n'
        '    return None'
    )
    c = c.replace(old, new)

    with open(path, "w") as f:
        f.write(c)

    return True


if __name__ == "__main__":
    target = Path(sys.argv[1])
    ok = patch_web_server(target)
    if ok:
        print(f"patched: {target}")
    else:
        sys.exit(1)