# jsql-neo (Python)

Python client and CLI for [JSQL-NEO](https://github.com/vexify-org/JSQL-neo).
The engine stays in Node.js: this package ships a thin Python API over a
stdio JSON bridge and a `jsql` command that proxies to the Node CLI.

## Install

Install Node.js and the `jsql-neo` npm package first:

```bash
curl -fsSL https://jsql.vexify.top/setup | bash
```

Then install the Python package:

```bash
pip install jsql-neo
```

Requires Node.js 18+ and `jsql-neo` >= 6.8.4.

## CLI

The `jsql` command is the Node CLI, proxied:

```bash
jsql serve --port 3306 --data-dir ./data
jsql plugin search xql
jsql plugin install xql
jsql version
```

Exit codes, stdin/stdout and TTY behaviour are preserved (the process is
replaced with `node bin/jsql` on POSIX).

## Python API

```python
from jsql_neo import Database

db = Database(":memory:")  # or Database("./data/app.json")

db.createTable("users", {
    "id": {"type": "integer", "primaryKey": True, "autoIncrement": True},
    "name": {"type": "string"},
    "age": {"type": "integer"},
})

db.insert("users", {"name": "alice", "age": 30})
db.insertMany("users", [{"name": "bob", "age": 25}])

rows = db.find("users", {"age": {"$gt": 26}}, {"sort": {"age": 1}})
print(rows)

db.update("users", {"name": "bob"}, {"age": 26})
db.removeWhere("users", {"name": "bob"})

for row in db.query("SELECT name FROM users ORDER BY name"):
    print(row)

db.close()
```

Use it as a context manager:

```python
with Database("./data/app.json") as db:
    print(db.getTables())
```

Any method on the Node `Database` object is reachable through the bridge:

```python
db.save()
db.stats()
db.begin()
db.commit()
db.backup("./backup.json")
```

Errors from the engine raise `jsql_neo.JSQLException`.

## Configuration

| Variable | Purpose |
| --- | --- |
| `JSQL_NEO_JS` | Path to the `jsql-neo` npm package directory |
| `JSQL_NODE` | Path to the Node.js executable |

The package locates the npm package from the current directory
(`node_modules/jsql-neo`), the global npm root, or the `jsql` executable on
`PATH`. If nothing is found it raises `JSQLNotInstalled` with the setup command.

## Versioning

The Python package version mirrors the npm package (`6.8.4`). The Python
wrapper only needs `jsql-neo >= 6.8.4`.

## License

Apache-2.0
