"""``jsql`` command line proxy to the Node.js CLI."""

import os
import subprocess
import sys

from ._node import JSQLNotInstalled, find_package_root, node_executable


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        node = node_executable()
        root = find_package_root()
    except JSQLNotInstalled as exc:
        sys.stderr.write("jsql: %s\n" % exc)
        return 1

    script = os.path.join(str(root), "bin", "jsql")
    if not os.path.isfile(script):
        sys.stderr.write("jsql: missing CLI entry point: %s\n" % script)
        return 1

    if os.name == "posix":
        os.execv(node, [node, script] + args)
        return 1

    return subprocess.call([node, script] + args)


if __name__ == "__main__":
    sys.exit(main())
