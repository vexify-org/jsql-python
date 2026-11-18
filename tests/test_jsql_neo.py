import subprocess
import sys
import unittest

from jsql_neo import Database, JSQLException
from jsql_neo._node import JSQLNotInstalled, find_package_root


def available():
    try:
        find_package_root()
        return True
    except JSQLNotInstalled:
        return False


SCHEMA = {
    "id": {"type": "integer", "primaryKey": True, "autoIncrement": True},
    "name": {"type": "string"},
    "age": {"type": "integer"},
}


@unittest.skipUnless(available(), "jsql-neo npm package is not installed")
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.close()

    def test_crud(self):
        self.db.createTable("users", SCHEMA)
        self.assertTrue(self.db.hasTable("users"))

        self.db.insert("users", {"name": "alice", "age": 30})
        self.db.insertMany(
            "users",
            [{"name": "bob", "age": 25}, {"name": "carol", "age": 35}],
        )

        rows = self.db.find("users", {"age": {"$gt": 26}}, {"sort": {"age": 1}})
        self.assertEqual([row["name"] for row in rows], ["alice", "carol"])
        self.assertEqual(self.db.count("users"), 3)

        self.db.update("users", {"name": "bob"}, {"age": 26})
        bob = self.db.find("users", {"name": "bob"})[0]
        self.assertEqual(bob["age"], 26)

        self.db.removeWhere("users", {"name": "carol"})
        self.assertEqual(self.db.count("users"), 2)

        self.db.delete("users", {"name": "alice"})
        self.assertEqual(self.db.count("users"), 1)

    def test_query(self):
        self.db.createTable("users", SCHEMA)
        self.db.insertMany(
            "users",
            [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}],
        )
        result = self.db.query("SELECT name FROM users ORDER BY name")
        self.assertEqual(result["columns"], ["name"])
        self.assertEqual([row["name"] for row in result["raw"]], ["alice", "bob"])
        self.assertEqual(result["rows"], [["alice"], ["bob"]])

    def test_generic_proxy(self):
        self.db.createTable("notes", {"id": {"type": "integer", "primaryKey": True}, "body": {"type": "string"}})
        self.db.insert("notes", {"id": 1, "body": "hello"})
        self.assertIn("notes", self.db.getTables())
        self.assertIsInstance(self.db.stats(), dict)

    def test_error(self):
        with self.assertRaises(JSQLException):
            self.db._call("definitelyNotAMethod")

    def test_closed(self):
        self.db.close()
        with self.assertRaises(JSQLException):
            self.db.getTables()


@unittest.skipUnless(available(), "jsql-neo npm package is not installed")
class CliTests(unittest.TestCase):
    def test_version(self):
        out = subprocess.run(
            [sys.executable, "-m", "jsql_neo", "version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertRegex(out.stdout.strip(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
