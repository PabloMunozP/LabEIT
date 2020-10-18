import mysql.connector as mysqlcn

class DB:
    def __init__(self, user, passwd, host, port, database, autocommit=True):
        self.user=user
        self.passwd=passwd
        self.host=host
        self.port=port
        self.database=database
        self.autocommit=autocommit

        self.db = self.connect()
        self.cursor = self.db.cursor(dictionary=True, buffered=True)
        self.cursor.execute("SET NAMES utf8mb4;")

    def connect(self):
        return mysqlcn.connect(
            user=self.user,
            passwd=self.passwd,
            host=self.host,
            port=self.port,
            database=self.database,
            autocommit=self.autocommit
        )

    def query(self, query, values):
        try:
            self._query(query, values)
        except (mysqlcn.errors.InterfaceError, mysqlcn.errors.OperationalError):
            self.db = self.connect()
            self.cursor = self.db.cursor(dictionary=True, buffered=True)
            self.cursor.execute("SET NAMES utf8mb4;")
            self._query(query, values)

        return self.cursor

    def _query(self, query, values):
        if values:
            self.cursor.execute(query, values)
        else:
            self.cursor.execute(query)
