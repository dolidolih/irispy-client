import sqlite3
import json
import threading

class PyKV:
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PyKV, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.filename = "iris.db"
            self._initialized = True

    def _get_db(self):
        if not hasattr(self._local, 'db') or self._local.db is None:
            if self.filename is None:
                 raise RuntimeError("Database filename not set. Call open() first.")
            self._local.db = sqlite3.connect(self.filename, check_same_thread=False)
            cursor = self._local.db.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS kv_pairs (key TEXT PRIMARY KEY, value TEXT)")
            self._local.db.commit()
            cursor.close()
        return self._local.db

    def open(self, filename):
        if self.filename is None:
            self.filename = filename

    def close(self):
        if hasattr(self._local, 'db') and self._local.db is not None:
            self._local.db.close()
            self._local.db = None

    def get(self, key):
        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT value FROM kv_pairs WHERE key = ?", (key,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return False
        else:
            return False

    def get_kv(self, key):
        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT value FROM kv_pairs WHERE key = ?", (key,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            try:
                return {"key": key, "value": json.loads(row[0])}
            except json.JSONDecodeError:
                return False
        else:
            return False

    def put(self, key, value):
        db = self._get_db()
        value_str = json.dumps(value)
        cursor = db.cursor()
        cursor.execute("INSERT OR REPLACE INTO kv_pairs (key, value) VALUES (?, ?)", (key, value_str))
        db.commit()
        cursor.close()

    def search(self, searchString):
        db = self._get_db()
        results = []
        cursor = db.cursor()
        cursor.execute("SELECT key, value FROM kv_pairs WHERE value LIKE ?", ('%' + searchString + '%',))
        rows = cursor.fetchall()
        for row in rows:
            key, value_str = row
            try:
                results.append({"key": key, "value": json.loads(value_str)})
            except json.JSONDecodeError:
                pass
        cursor.close()
        return results

    def search_json(self, valueKey, searchString):
        db = self._get_db()
        results = []
        cursor = db.cursor()
        cursor.execute("SELECT key, value FROM kv_pairs")
        rows = cursor.fetchall()
        for row in rows:
            key, value_str = row
            try:
                value = json.loads(value_str)
                value_key_components = valueKey.split('.')
                curr_value = value
                for value_key_component in value_key_components:
                    if isinstance(curr_value, dict) and value_key_component in curr_value:
                        curr_value = curr_value[value_key_component]
                    else:
                        curr_value = None
                        break
                if curr_value is not None and searchString in str(curr_value):
                    results.append({"key": key, "value": value})
            except json.JSONDecodeError:
                pass
        cursor.close()
        return results

    def search_key(self, searchString):
        db = self._get_db()
        results = []
        cursor = db.cursor()
        cursor.execute("SELECT key, value FROM kv_pairs WHERE key LIKE ?", ('%' + searchString + '%',))
        rows = cursor.fetchall()
        for row in rows:
            key, value_str = row
            try:
                results.append({"key": key, "value": json.loads(value_str)})
            except json.JSONDecodeError:
                pass
        cursor.close()
        return results

    def list_keys(self):
        db = self._get_db()
        results = []
        cursor = db.cursor()
        cursor.execute("SELECT key FROM kv_pairs")
        rows = cursor.fetchall()
        for row in rows:
            results.append(row[0])
        cursor.close()
        return results

    def delete(self, key):
        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM kv_pairs WHERE key = ?", (key,))
        db.commit()
        cursor.close()
