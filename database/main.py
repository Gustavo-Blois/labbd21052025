import psycopg2

conn = psycopg2.connect(database="labbd",
                        host="atomheartfoxer.gay",
                        user="a13688162",
                        password="a13688162",
                        port="5432")

cursor = conn.cursor()
cursor.execute("SELECT * FROM information_schema.tables")
print(cursor.fetchall())

