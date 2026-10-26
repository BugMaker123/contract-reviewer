"""Database boundary for the existing repository's small SQL vocabulary.

SQLite remains available for desktop use and migration sources. Production uses
MySQL 8.0. Serializing short writes on one database row preserves the repository's
BEGIN IMMEDIATE semantics, including cross-object checks and version snapshots.
No model call is made inside these transactions.
"""
import re
import sqlite3
from contextlib import contextmanager

from sqlalchemy import create_engine, text


def mysql_sql(sql):
    sql = sql.replace("coalesce(json_extract(i.value,'$.title'),'') || ' ' || coalesce(json_extract(i.value,'$.requirement'),'')",
                      "CONCAT(coalesce(json_extract(i.value,'$.title'),''),' ',coalesce(json_extract(i.value,'$.requirement'),''))")
    # The only table-valued JSON search in the catalog.
    sql = sql.replace("json_each(o.data,'$.items') i",
                      "JSON_TABLE(o.data,'$.items[*]' COLUMNS(value JSON PATH '$')) i")
    # Rewrite nested JSON functions with balanced parentheses, respecting strings.
    def convert(expression, raw=False):
        result, i = '', 0
        while i < len(expression):
            if expression[i] == "'":
                j = i + 1
                while j < len(expression):
                    if expression[j] == "'":
                        if j + 1 < len(expression) and expression[j + 1] == "'":
                            j += 2
                            continue
                        break
                    j += 1
                result += expression[i:j + 1]
                i = j + 1
                continue
            match = re.match(r'(json_extract|json_array_length|json_object)\(', expression[i:], re.I)
            if not match:
                result += expression[i]
                i += 1
                continue
            start = i + len(match[0])
            j, depth, quoted = start, 1, False
            while depth:
                char = expression[j]
                if char == "'":
                    quoted = not quoted
                elif not quoted:
                    depth += (char == '(') - (char == ')')
                j += 1
            function = match[1].lower()
            original_args = expression[start:j - 1]
            args = convert(original_args, raw=function == 'json_object' or raw)
            if function == 'json_object':
                result += 'JSON_OBJECT(' + args + ')'
            elif function == 'json_extract':
                # SQL NULL, rather than the JSON string "null", is essential
                # for existing COALESCE filters and LEFT JOINs.
                extracted = 'JSON_EXTRACT(' + args + ')'
                scalar = "NULLIF(JSON_UNQUOTE(" + extracted + "), 'null')"
                if raw:
                    result += extracted
                elif re.search(r"\.(archived|published)'$", original_args):
                    result += "CASE " + scalar + " WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE CAST(" + scalar + ' AS SIGNED) END'
                elif re.search(r"\.(number|sort_order|compliance_score)'$", original_args):
                    result += 'CAST(' + scalar + ' AS SIGNED)'
                else:
                    result += scalar
            else:
                result += 'JSON_LENGTH(' + args + ')'
            i = j
        return result
    return convert(sql)


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Result:
    def __init__(self, result):
        self.result = result
        self.rowcount = result.rowcount

    def fetchone(self):
        row = self.result.mappings().fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return [Row(row) for row in self.result.mappings().fetchall()]

    def __iter__(self):
        for row in self.result.mappings():
            yield Row(row)


class MySQLConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        if sql == 'BEGIN IMMEDIATE':
            return Result(self.connection.execute(text('SELECT id FROM repository_lock WHERE id=1 FOR UPDATE')))
        sql = mysql_sql(sql)
        if sql.startswith('DELETE FROM review_events WHERE run_id='):
            # MySQL disallows modifying a table also selected directly by a
            # subquery. Materializing the bounded ID list avoids error 1093.
            sql = sql.replace('id NOT IN (SELECT id FROM review_events',
                              'id NOT IN (SELECT id FROM (SELECT id FROM review_events')
            sql = sql.replace('ORDER BY id DESC LIMIT 256)', 'ORDER BY id DESC LIMIT 256) retained)')
        # Bind qmark parameters without changing literal question marks.
        pieces = re.split(r"('(?:''|[^'])*')", sql)
        index = 0
        for part in range(0, len(pieces), 2):
            def bind(_):
                nonlocal index
                name = ':p' + str(index)
                index += 1
                return name
            pieces[part] = re.sub(r'\?', bind, pieces[part])
        if index != len(params):
            raise ValueError('SQL parameter count mismatch')
        return Result(self.connection.execute(text(''.join(pieces)),
                      {'p' + str(i): value for i, value in enumerate(params)}))


class Database:
    def __init__(self, path, url=None):
        self.mysql = bool(url)
        if url and not url.startswith('mysql+pymysql://'):
            raise ValueError('LEXIS_DATABASE_URL must use mysql+pymysql://')
        self.engine = create_engine(url or 'sqlite:///' + path,
            pool_pre_ping=True, hide_parameters=True, **({'connect_args': {'charset': 'utf8mb4'}} if url else
                                 {'connect_args': {'timeout': 15, 'check_same_thread': False}}))

    @contextmanager
    def connect(self):
        if self.mysql:
            with self.engine.begin() as connection:
                yield MySQLConnection(connection)
        else:
            connection = self.engine.raw_connection()
            connection.driver_connection.row_factory = sqlite3.Row
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()

    def initialize_mysql(self):
        # Versioned migrations are applied explicitly by the deployment CLI.
        from .schema import migrate
        migrate(self.engine)
