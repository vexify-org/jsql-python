"""Python client for JSQL-NEO.

The database engine stays in Node.js; this package provides a Python API
(``jsql_neo.Database``) over a stdio JSON bridge and a ``jsql`` CLI that
proxies to the Node CLI.

Install the Node side once with::

    curl -fsSL https://jsql.vexify.top/setup | bash
"""

from ._node import JSQLNotInstalled, SETUP_HINT, find_package_root
from .database import Database, JSQLException

__version__ = "6.8.4"

__all__ = [
    "Database",
    "JSQLException",
    "JSQLNotInstalled",
    "SETUP_HINT",
    "find_package_root",
    "__version__",
]
