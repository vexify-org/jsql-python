"""Python Database wrapper around the JSQL-NEO Node.js engine."""

import base64
import datetime
import decimal
import json
import os
import queue
import subprocess
import threading

from ._node import find_package_root, node_executable

_BRIDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bridge.js")


class JSQLException(RuntimeError):
    """Error raised by the JSQL engine."""

    def __init__(self, message, code=None, name="Error"):
        super().__init__(message)
        self.code = code
        self.name = name


def _json_default(value):
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (set, frozenset)):
        return list(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    raise TypeError("Object of type %s is not JSON serializable" % type(value).__name__)


class Database:
    """A JSQL-NEO database backed by a Node.js child process.

    Parameters
    ----------
    path:
        Database file path, a data directory, or ``":memory:"``.
    options:
        Options forwarded to the JSQL ``Database`` constructor.
    """

    def __init__(self, path=":memory:", options=None, **kwargs):
        opts = dict(options or {})
        opts.update(kwargs)
        self.path = path
        self.options = opts
        self._proc = None
        self._lock = threading.Lock()
        self._next_id = 0
        self._closed = False
        self._stderr = []
        self._stderr_lock = threading.Lock()
        self._lines = queue.Queue()
        self._start()

    # -- process lifecycle -------------------------------------------------

    def _start(self):
        node = node_executable()
        root = find_package_root()
        env = os.environ.copy()
        env["JSQL_NEO_JS_ROOT"] = str(root)
        self._proc = subprocess.Popen(
            [node, _BRIDGE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self._call("__init", self.path, self.options, timeout=60)

    def _read_stdout(self):
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _read_stderr(self):
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        for line in proc.stderr:
            with self._stderr_lock:
                self._stderr.append(line.rstrip())
                if len(self._stderr) > 50:
                    del self._stderr[0]

    def _stderr_tail(self):
        with self._stderr_lock:
            return "\n".join(self._stderr[-10:])

    # -- RPC ---------------------------------------------------------------

    def _call(self, method, *args, **kwargs):
        timeout = kwargs.pop("timeout", None)
        if kwargs:
            raise TypeError("Unexpected keyword arguments: %s" % ", ".join(kwargs))
        with self._lock:
            if self._closed:
                raise JSQLException("Database is closed")
            if self._proc is None or self._proc.poll() is not None:
                raise JSQLException(
                    "JSQL bridge is not running" + self._suffix()
                )
            self._next_id += 1
            request = json.dumps(
                {"id": self._next_id, "method": method, "args": list(args)},
                default=_json_default,
            )
            try:
                self._proc.stdin.write(request + "\n")
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise JSQLException("Failed to write to JSQL bridge: %s%s" % (exc, self._suffix()))
            try:
                line = self._lines.get(timeout=timeout) if timeout else self._lines.get()
            except queue.Empty:
                raise JSQLException("JSQL call timed out: %s" % method)
            if line is None:
                raise JSQLException("JSQL bridge exited unexpectedly" + self._suffix())
            response = json.loads(line)
            if response.get("ok"):
                return response.get("result")
            error = response.get("error") or {}
            raise JSQLException(
                error.get("message", "Unknown JSQL error"),
                code=error.get("code"),
                name=error.get("name", "Error"),
            )

    def _suffix(self):
        tail = self._stderr_tail()
        return (":\n" + tail) if tail else ""

    def _call_opt(self, method, *args):
        values = list(args)
        while values and values[-1] is None:
            values.pop()
        return self._call(method, *values)

    # -- convenience API ---------------------------------------------------

    def createTable(self, name, schema=None):
        return self._call_opt("createTable", name, schema)

    def dropTable(self, name):
        return self._call("dropTable", name)

    def hasTable(self, name):
        return self._call("hasTable", name)

    def getTables(self):
        return self._call("getTables")

    def getTableSchema(self, name):
        return self._call("getTableSchema", name)

    def insert(self, table, data):
        return self._call("insert", table, data)

    def insertMany(self, table, items):
        return self._call("insertMany", table, items)

    def find(self, table, filter=None, opts=None):
        return self._call("find", table, filter if filter is not None else {}, opts or {})

    def findById(self, table, id):
        return self._call("findById", table, id)

    def count(self, table):
        return self._call("count", table)

    def update(self, table, query, updates):
        return self._call("update", table, query, updates)

    def delete(self, table, query=None):
        return self._call("delete", table, query if query is not None else {})

    def removeWhere(self, table, filter):
        return self._call("removeWhere", table, filter)

    def truncate(self, table):
        return self._call("truncate", table)

    def query(self, sql, params=None, opts=None):
        return self._call_opt("query", sql, params, opts)

    def begin(self):
        return self._call("begin")

    def commit(self):
        return self._call("commit")

    def rollback(self):
        return self._call("rollback")

    def save(self):
        return self._call("save")

    def stats(self):
        return self._call("stats")

    def close(self):
        if self._closed:
            return
        try:
            self._call("close", timeout=10)
        except JSQLException:
            pass
        finally:
            self._closed = True
            proc = self._proc
            if proc is not None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    try:
                        stream.close()
                    except Exception:
                        pass

    # -- dynamic proxy -----------------------------------------------------

    def __getattr__(self, name):
        if name.startswith("_") or name in ("path", "options"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            if kwargs:
                raise TypeError(
                    "%s() does not accept keyword arguments; pass an options "
                    "object as the last positional argument" % name
                )
            return self._call(name, *args)

        call.__name__ = name
        return call

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self):
        return "<jsql_neo.Database path=%r%s>" % (
            self.path,
            " closed" if self._closed else "",
        )
