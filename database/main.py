import psycopg2
import getpass
import django
user = input("iniciando conexão\nInsira Usuário:")
password = getpass.getpass(prompt="Senha (você não é capaz de ver sua senha enquanto digita):")
conn = psycopg2.connect(database="labbd",
                        host="atomheartfoxer.gay",
                        user=user,
                        password=password,
                        port="5432")

cursor = conn.cursor()
cursor.execute("SELECT * FROM information_schema.tables")
print(cursor.fetchall())

