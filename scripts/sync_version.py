"""Bump every version reference to the given jsql-neo version."""

import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: sync_version.py <version>")
    version = sys.argv[1]

    pyproject = Path("pyproject.toml")
    text = pyproject.read_text()
    text, n = re.subn(r'(?m)^version = "[^"]+"', 'version = "%s"' % version, text, count=1)
    if n != 1:
        raise SystemExit("could not update pyproject.toml version")
    pyproject.write_text(text)

    init = Path("jsql_neo/__init__.py")
    text = init.read_text()
    text, n = re.subn(r'(?m)^__version__ = "[^"]+"', '__version__ = "%s"' % version, text, count=1)
    if n != 1:
        raise SystemExit("could not update jsql_neo/__init__.py version")
    init.write_text(text)

    readme = Path("README.md")
    text = readme.read_text()
    text = re.sub(r"\b\d+\.\d+\.\d+\b", version, text)
    readme.write_text(text)

    ci = Path(".github/workflows/ci.yml")
    text = ci.read_text()
    text = re.sub(r"jsql-neo@\d+\.\d+\.\d+", "jsql-neo@%s" % version, text)
    ci.write_text(text)

    print("version references updated to %s" % version)


if __name__ == "__main__":
    main()
