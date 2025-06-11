import psycopg2 #pip install psycopg2-binary
from psycopg2 import sql
from getpass import getpass
import datetime
import csv
import os
import re
from tabulate import tabulate #pip install tabulate

# Configurações do banco de dados
DB_CONFIG = {
    "dbname": "labbd",
    "user": "fia_admin",
    "password": "labbd25",
    "host": "atomheartfoxer.gay",
    "port": "5432"
}

# Funções de validação e sanitização para prevenir SQL injection
def validate_input(input_string, input_type="general"):
    """Valida e sanitiza entradas do usuário"""
    if not input_string:
        return None
    
    # Remove caracteres perigosos
    input_string = input_string.strip()
    
    if input_type == "alphanumeric":
        # Permite apenas letras, números, espaços e hífens
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', input_string):
            raise ValueError("Entrada contém caracteres inválidos")
    elif input_type == "name":
        # Para nomes (permite acentos)
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\'\.]+$', input_string):
            raise ValueError("Nome contém caracteres inválidos")
    elif input_type == "date":
        print("OI")
        # Valida formato de data YYYY-MM-DD
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', input_string):
            raise ValueError("Data deve estar no formato YYYY-MM-DD")
    elif input_type == "url":
        # Validação básica de URL
        if not re.match(r'^https?://', input_string):
            input_string = "http://" + input_string
    
    return input_string

def safe_int_input(prompt, min_val=None, max_val=None):
    """Solicita entrada numérica com validação"""
    while True:
        try:
            value = input(prompt).strip()
            if not value:
                return None
            
            num = int(value)
            if min_val is not None and num < min_val:
                print(f"Valor deve ser maior que {min_val}")
                continue
            if max_val is not None and num > max_val:
                print(f"Valor deve ser menor que {max_val}")
                continue
            
            return num
        except ValueError:
            print("Por favor, digite um número válido")

class DatabaseManager:
    """Classe para gerenciar operações de banco com segurança"""
    
    @staticmethod
    def execute_query(query, params=None, fetch_type="all"):
        """Executa query com proteção contra SQL injection"""
        conn = connect_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                
                if fetch_type == "one":
                    return cursor.fetchone()
                elif fetch_type == "all":
                    return cursor.fetchall()
                elif fetch_type == "none":
                    conn.commit()
                    return True
                    
        except Exception as e:
            conn.rollback()
            print(f"Erro na consulta: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def check_views_exist():
        """Verifica se as views necessárias existem no banco"""
        required_views = [
            'admin_dashboard',
            'driver_performance',
            'constructor_performance'
        ]
        
        conn = connect_db()
        if not conn:
            return False
            
        try:
            with conn.cursor() as cursor:
                print("Investigando schemas e views disponíveis...")
                
                # Busca especificamente no schema LabBD25-Grupo7
                cursor.execute("""
                    SELECT table_schema, table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'LabBD25-Grupo7'
                    ORDER BY table_name
                """)
                all_views_in_schema = cursor.fetchall()
                
                print(f"Views encontradas no schema 'LabBD25-Grupo7':")
                found_views = set()
                for schema, view in all_views_in_schema:
                    print(f"  - {schema}.{view}")
                    if view in required_views:
                        found_views.add(view)
                
                # Também busca em todos os schemas como fallback
                cursor.execute("""
                    SELECT table_schema, table_name 
                    FROM information_schema.views 
                    WHERE table_name IN ('admin_dashboard', 'driver_performance', 'constructor_performance')
                    ORDER BY table_schema, table_name
                """)
                all_matching_views = cursor.fetchall()
                
                if all_matching_views:
                    print("\nTodas as views com nomes correspondentes encontradas:")
                    for schema, view in all_matching_views:
                        print(f"  - {schema}.{view}")
                        if view in required_views:
                            found_views.add(view)
                
                missing_views = set(required_views) - found_views
                
                if missing_views:
                    print(f"\nViews ainda faltando: {', '.join(missing_views)}")
                    
                    # Tenta uma busca mais específica para debug
                    for missing_view in missing_views:
                        cursor.execute("""
                            SELECT table_schema, table_name 
                            FROM information_schema.views 
                            WHERE LOWER(table_name) = LOWER(%s)
                        """, (missing_view,))
                        similar_views = cursor.fetchall()
                        
                        if similar_views:
                            print(f"Views similares a '{missing_view}':")
                            for schema, view in similar_views:
                                print(f"    - {schema}.{view}")
                    
                    return False
                else:
                    print(f"\n✓ Todas as views necessárias foram encontradas!")
                    return True
                
        except Exception as e:
            print(f"Erro ao verificar views: {e}")
            return False
        finally:
            conn.close()

class UserView:
    """Classe base para views de usuários"""
    
    def __init__(self, user_info):
        self.user_info = user_info
        self.db = DatabaseManager()
    
    def generate_reports_menu(self):
        """Menu base para relatórios - deve ser sobrescrito"""
        pass

class AdminView(UserView):
    """View específica para administradores"""
    
    def show_dashboard(self):
        return admin_dashboard(self.user_info)
    
    def get_admin_stats_from_view(self):
        """Usa a view específica para administradores"""
        # Primeiro tenta no schema conhecido
        stats = self.db.execute_query("""
            SELECT tabela, total_registros 
            FROM "LabBD25-Grupo7".admin_dashboard
        """)
        
        if stats:
            return stats
        
        # Se não funcionou, descobre em qual schema a view está
        schema_query = """
            SELECT table_schema 
            FROM information_schema.views 
            WHERE table_name = 'admin_dashboard'
            LIMIT 1
        """
        schema_result = self.db.execute_query(schema_query, fetch_type="one")
        
        if schema_result:
            schema_name = schema_result[0]
            stats = self.db.execute_query(f"""
                SELECT tabela, total_registros 
                FROM "{schema_name}".admin_dashboard
            """)
            return stats
        else:
            print("View admin_dashboard não encontrada!")
            return None
    
    def get_season_stats_from_view(self):
        """Usa a view de estatísticas de temporada"""
        stats = self.db.execute_query("""
            SELECT * FROM "LabBD25-Grupo7".season_stats_view
            LIMIT 10
        """)
        return stats
    
    def register_constructor_safe(self):
        """Cadastro seguro de escuderia"""
        print("\n" + "="*50)
        print("Cadastro de Nova Escuderia")
        print("="*50)

        try:
            constructor_ref = validate_input(input("ConstructorRef: "), "alphanumeric")
            name = validate_input(input("Name: "), "name")
            nationality = validate_input(input("Nationality: "), "name")
            url = validate_input(input("URL: "), "url")
            
            if not all([constructor_ref, name, nationality]):
                print("Todos os campos obrigatórios devem ser preenchidos!")
                return

            # Verifica se já existe
            existing = self.db.execute_query(
                'SELECT constructorid FROM "LabBD25-Grupo7".Constructors WHERE ConstructorRef = %s',
                (constructor_ref,),
                "one"
            )
            
            if existing:
                print("ConstructorRef já existe!")
                return

            # Busca próximo ID
            next_id_result = self.db.execute_query(
                'SELECT COALESCE(MAX("constructorid"), 0) + 1 FROM "LabBD25-Grupo7".Constructors',
                fetch_type="one"
            )
            next_id = next_id_result[0]

            # Insere escuderia
            success = self.db.execute_query("""
                INSERT INTO "LabBD25-Grupo7".Constructors 
                (constructorid, ConstructorRef, Name, Nationality, URL)
                VALUES (%s, %s, %s, %s, %s)
            """, (next_id, constructor_ref, name, nationality, url), "none")

            if success:
                # Cria usuário
                username = f"{constructor_ref}_c"
                self.db.execute_query("""
                    INSERT INTO "LabBD25-Grupo7".UserAccounts 
                    (Username, PasswordHash, UserType, constructorid)
                    VALUES (%s, %s, 'constructor', %s)
                """, (username, constructor_ref, next_id), "none")
                
                print(f"Escuderia cadastrada com sucesso! Usuário: {username}")
            else:
                print("Erro ao cadastrar escuderia!")

        except ValueError as e:
            print(f"Erro de validação: {e}")
        except Exception as e:
            print(f"Erro inesperado: {e}")

    def register_driver_safe(self):
        """Cadastro seguro de piloto"""
        print("\n" + "="*50)
        print("Cadastro de Novo Piloto")
        print("="*50)

        try:
            driver_ref = validate_input(input("DriverRef: "), "alphanumeric")
            number = safe_int_input("Number (opcional): ", 1, 999)
            code = validate_input(input("Code: "), "alphanumeric")
            forename = validate_input(input("Forename: "), "name")
            surname = validate_input(input("Surname: "), "name")
            dob = validate_input(input("Date of Birth (YYYY-MM-DD): "), "date")
            nationality = validate_input(input("Nationality: "), "name")
            
            if not all([driver_ref, code, forename, surname, dob, nationality]):
                print("Todos os campos obrigatórios devem ser preenchidos!")
                return

            # Verifica se já existe
            existing = self.db.execute_query(
                'SELECT driverid FROM "LabBD25-Grupo7".Drivers WHERE DriverRef = %s',
                (driver_ref,),
                "one"
            )
            
            if existing:
                print("DriverRef já existe!")
                return

            # Busca próximo ID
            next_id_result = self.db.execute_query(
                'SELECT COALESCE(MAX("driverid"), 0) + 1 FROM "LabBD25-Grupo7".Drivers',
                fetch_type="one"
            )
            next_id = next_id_result[0]

            # Insere piloto
            success = self.db.execute_query("""
                INSERT INTO "LabBD25-Grupo7".Drivers 
                (driverid, DriverRef, Number, Code, Forename, Surname, DateOfBirth, Nationality)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (next_id, driver_ref, number, code, forename, surname, dob, nationality), "none")

            if success:
                # Cria usuário
                username = f"{driver_ref}_d"
                self.db.execute_query("""
                    INSERT INTO "LabBD25-Grupo7".UserAccounts 
                    (Username, PasswordHash, UserType, driverid)
                    VALUES (%s, %s, 'driver', %s)
                """, (username, driver_ref, next_id), "none")
                
                print(f"Piloto cadastrado com sucesso! Usuário: {username}")
            else:
                print("Erro ao cadastrar piloto!")

        except ValueError as e:
            print(f"Erro de validação: {e}")
        except Exception as e:
            print(f"Erro inesperado: {e}")

class ConstructorView(UserView):
    """View específica para escuderias"""
    
    def show_dashboard(self):
        return constructor_dashboard(self.user_info)
    
    def generate_reports_menu(self):
        return generate_constructor_reports(self.user_info)
    
    def get_constructor_data_from_view(self):
        """Usa a view específica para escuderias - apenas dados da própria escuderia"""
        # Primeiro tenta no schema conhecido
        try:
            data = self.db.execute_query("""
                SELECT escuderia, Year, corrida, piloto, Position, Points
                FROM "LabBD25-Grupo7".constructor_performance
                WHERE ConstructorID = %s
                ORDER BY Year DESC, corrida
            """, (self.user_info['constructor_id'],))
            
            if data is not None:
                return data
        except:
            pass
        
        # Se não funcionou, descobre em qual schema a view está
        schema_query = """
            SELECT table_schema 
            FROM information_schema.views 
            WHERE table_name = 'constructor_performance'
            LIMIT 1
        """
        schema_result = self.db.execute_query(schema_query, fetch_type="one")
        
        if schema_result:
            schema_name = schema_result[0]
            data = self.db.execute_query(f"""
                SELECT escuderia, Year, corrida, piloto, Position, Points
                FROM "{schema_name}".constructor_performance
                WHERE ConstructorID = %s
                ORDER BY Year DESC, corrida
            """, (self.user_info['constructor_id'],))
            return data
        else:
            print("View constructor_performance não encontrada!")
            return None

class DriverView(UserView):
    """View específica para pilotos"""
    
    def show_dashboard(self):
        return driver_dashboard(self.user_info)
    
    def generate_reports_menu(self):
        return generate_driver_reports(self.user_info)
    
    def get_driver_data_from_view(self):
        """Usa a view específica para pilotos - apenas dados do próprio piloto"""
        # Primeiro tenta no schema conhecido
        try:
            data = self.db.execute_query("""
                SELECT nome_completo, Year, corrida, Position, Points, escuderia
                FROM "LabBD25-Grupo7".driver_performance
                WHERE DriverID = %s
                ORDER BY Year DESC, corrida
            """, (self.user_info['driver_id'],))
            
            if data is not None:
                return data
        except:
            pass
        
        # Se não funcionou, descobre em qual schema a view está
        schema_query = """
            SELECT table_schema 
            FROM information_schema.views 
            WHERE table_name = 'driver_performance'
            LIMIT 1
        """
        schema_result = self.db.execute_query(schema_query, fetch_type="one")
        
        if schema_result:
            schema_name = schema_result[0]
            data = self.db.execute_query(f"""
                SELECT nome_completo, Year, corrida, Position, Points, escuderia
                FROM "{schema_name}".driver_performance
                WHERE DriverID = %s
                ORDER BY Year DESC, corrida
            """, (self.user_info['driver_id'],))
            return data
        else:
            print("View driver_performance não encontrada!")
            return None

# Função para conectar ao banco de dados
def connect_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Função para autenticar usuário
def authenticate_user():
    username = input("Usuário: ")
    password = getpass("Senha: ")

    conn = connect_db()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            # Primeiro tenta verificar se a senha já está criptografada
            query = sql.SQL("""
                SELECT ua.UserID, ua.UserType, 
                    d.DriverID, d.Forename, d.Surname,
                    c.ConstructorID, c.Name
                FROM "LabBD25-Grupo7".UserAccounts ua
                LEFT JOIN "LabBD25-Grupo7".Drivers d ON ua.DriverID = d.DriverID
                LEFT JOIN "LabBD25-Grupo7".Constructors c ON ua.ConstructorID = c.ConstructorID
                WHERE ua.Username = %s 
                AND (ua.PasswordHash = "LabBD25-Grupo7".crypt(%s, ua.PasswordHash))
            """)
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            if user:
                # Registra o login na tabela de logs
                log_query = sql.SQL("""
                    INSERT INTO "LabBD25-Grupo7".Users_Log (UserID, LoginTime)
                    VALUES (%s, CURRENT_TIMESTAMP)
                """)
                cursor.execute(log_query, (user[0],))
                conn.commit()

                return {
                    'user_id': user[0],
                    'user_type': user[1],
                    'driver_id': user[2],
                    'driver_name': f"{user[3]} {user[4]}" if user[3] and user[4] else None,
                    'constructor_id': user[5],
                    'constructor_name': user[6]
                }
            else:
                print("Credenciais inválidas!")
                return None
    finally:
        conn.close()

# Dashboard para administradores
def admin_dashboard(user_info):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 1. Quantidade total de pilotos, escuderias e temporadas
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM "LabBD25-Grupo7".Drivers) AS total_pilotos,
                    (SELECT COUNT(*) FROM "LabBD25-Grupo7".Constructors) AS total_escuderias,
                    (SELECT COUNT(DISTINCT Year) FROM "LabBD25-Grupo7".Seasons) AS total_temporadas
            """)
            counts = cursor.fetchone()

            # Buscar o último ano com dados disponíveis
            cursor.execute("""
                SELECT MAX(Year) 
                FROM "LabBD25-Grupo7".Races 
                WHERE EXISTS (
                    SELECT 1 FROM "LabBD25-Grupo7".Results R 
                    WHERE R.RaceId = "LabBD25-Grupo7".Races.RaceId
                )
            """)
            latest_year_result = cursor.fetchone()
            latest_year = latest_year_result[0] if latest_year_result and latest_year_result[0] else datetime.datetime.now().year

            # 2. Corridas do último ano com dados
            cursor.execute("""
                SELECT R.Name, COUNT(L.Lap) AS total_voltas, 
                    MAX(L.Time) AS tempo_total
                FROM "LabBD25-Grupo7".Races R
                JOIN "LabBD25-Grupo7".LapTimes L ON R.RaceId = L.RaceId
                WHERE R.Year = %s
                GROUP BY R.RaceId, R.Name
                ORDER BY R.Date
                LIMIT 10
            """, (latest_year,))
            races = cursor.fetchall()

            # 3. Escuderias com pontos no último ano com dados
            cursor.execute("""
                SELECT C.Name, SUM(R.Points) AS total_pontos
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Constructors C ON R.ConstructorId = C.ConstructorId
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE RC.Year = %s
                GROUP BY C.ConstructorId, C.Name
                ORDER BY total_pontos DESC
                LIMIT 10
            """, (latest_year,))
            constructors = cursor.fetchall()

            # 4. Pilotos com pontos no último ano com dados
            cursor.execute("""
                SELECT D.Forename || ' ' || D.Surname AS piloto, SUM(R.Points) AS total_pontos
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Drivers D ON R.DriverId = D.DriverId
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE RC.Year = %s
                GROUP BY D.DriverId, piloto
                ORDER BY total_pontos DESC
                LIMIT 10
            """, (latest_year,))
            drivers = cursor.fetchall()

            # Exibição dos dados
            print("\n" + "="*50)
            print(f"Bem-vindo(a), Administrador!")
            print("="*50)

            print("\n[1] Estatísticas Gerais:")
            print(f"  - Total de Pilotos: {counts[0]}")
            print(f"  - Total de Escuderias: {counts[1]}")
            print(f"  - Total de Temporadas: {counts[2]}")

            print(f"\n[2] Corridas de {latest_year} (Últimas com dados):")
            if races:
                print(tabulate(races, headers=["Corrida", "Total Voltas", "Tempo Total"], tablefmt="pretty"))
            else:
                print("Nenhuma corrida encontrada com dados de voltas.")

            print(f"\n[3] Top 10 Escuderias (Pontos em {latest_year}):")
            if constructors:
                print(tabulate(constructors, headers=["Escuderia", "Pontos"], tablefmt="pretty"))
            else:
                print("Nenhuma escuderia encontrada com pontos.")

            print(f"\n[4] Top 10 Pilotos (Pontos em {latest_year}):")
            if drivers:
                print(tabulate(drivers, headers=["Piloto", "Pontos"], tablefmt="pretty"))
            else:
                print("Nenhum piloto encontrado com pontos.")

            print("\n" + "="*50)
            print("Opções:")
            print("1. Cadastrar Nova Escuderia")
            print("2. Cadastrar Novo Piloto")
            print("3. Consultar Piloto por Nome")
            print("4. Importar Pilotos de Arquivo")
            print("5. Gerar Relatórios")
            print("6. Verificar Views do Sistema")
            print("7. Sair")

            choice = input("Escolha uma opção: ")
            return choice

    finally:
        conn.close()

# Dashboard para escuderias
def constructor_dashboard(user_info):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 1. Quantidade de vitórias
            cursor.execute("""
                SELECT COUNT(*) 
                FROM "LabBD25-Grupo7".Results R
                WHERE R.Position = 1 
                AND R.ConstructorId = %s
            """, (user_info['constructor_id'],))
            wins = cursor.fetchone()[0]

            # 2. Quantidade de pilotos diferentes
            cursor.execute("""
                SELECT COUNT(DISTINCT R.DriverId)
                FROM "LabBD25-Grupo7".Results R
                WHERE R.ConstructorId = %s
            """, (user_info['constructor_id'],))
            drivers_count = cursor.fetchone()[0]

            # 3. Primeiro e último ano de participação
            cursor.execute("""
                SELECT MIN(Year), MAX(Year)
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.ConstructorId = %s
            """, (user_info['constructor_id'],))
            years = cursor.fetchone()

            # Exibição dos dados
            print("\n" + "="*50)
            print(f"Bem-vindo(a), {user_info['constructor_name']}!")
            print("="*50)

            print("\nDashboard da Escuderia:")
            print(f"  - Vitórias: {wins}")
            print(f"  - Pilotos Diferentes: {drivers_count}")
            print(f"  - Primeiro Ano: {years[0]} | Último Ano: {years[1]}")

            print("\n" + "="*50)
            print("Opções:")
            print("1. Gerar Relatórios")
            print("2. Sair")

            choice = input("Escolha uma opção: ")
            return choice

    finally:
        conn.close()

# Dashboard para pilotos
def driver_dashboard(user_info):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 1. Primeiro e último ano de participação
            cursor.execute("""
                SELECT MIN(RC.Year), MAX(RC.Year)
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.DriverId = %s
            """, (user_info['driver_id'],))
            years = cursor.fetchone()

            # 2. Estatísticas por ano
            cursor.execute("""
                SELECT RC.Year, 
                    SUM(R.Points) AS total_pontos,
                    COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                    COUNT(DISTINCT R.RaceId) AS corridas
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.DriverId = %s
                GROUP BY RC.Year
                ORDER BY RC.Year
            """, (user_info['driver_id'],))
            stats = cursor.fetchall()

            # Exibição dos dados
            print("\n" + "="*50)
            print(f"Bem-vindo(a), {user_info['driver_name']}!")
            print("="*50)

            print("\nDashboard do Piloto:")
            print(f"  - Primeiro Ano: {years[0]} | Último Ano: {years[1]}")

            print("\nEstatísticas por Ano:")
            print(tabulate(stats, headers=["Ano", "Pontos", "Vitórias", "Corridas"], tablefmt="pretty"))

            print("\n" + "="*50)
            print("Opções:")
            print("1. Gerar Relatórios")
            print("2. Sair")

            choice = input("Escolha uma opção: ")
            return choice

    finally:
        conn.close()

# Função para cadastrar nova escuderia
def register_constructor():
    print("\n" + "="*50)
    print("Cadastro de Nova Escuderia")
    print("="*50)

    constructor_ref = input("ConstructorRef: ")
    name = input("Name: ")
    nationality = input("Nationality: ")
    url = input("URL: ")

    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Busca o maior ConstructorID atual
            cursor.execute('SELECT COALESCE(MAX("constructorid"), 0) + 1 FROM "LabBD25-Grupo7".Constructors')
            next_id = cursor.fetchone()[0]

            # Insere na tabela de construtores com ID manual
            cursor.execute("""
                INSERT INTO "LabBD25-Grupo7".Constructors 
                (constructorid, ConstructorRef, Name, Nationality, URL)
                VALUES (%s, %s, %s, %s, %s)
            """, (next_id, constructor_ref, name, nationality, url))

            # Cria usuário associado
            username = f"{constructor_ref}_c"
            cursor.execute("""
                INSERT INTO "LabBD25-Grupo7".UserAccounts 
                (Username, PasswordHash, UserType, constructorid)
                VALUES (%s, %s, 'constructor', %s)
            """, (username, constructor_ref, next_id))

            conn.commit()
            print(f"Escuderia cadastrada com sucesso! Usuário: {username}")

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        print("Erro: ConstructorRef já existe!")
    finally:
        conn.close()


# Função para cadastrar novo piloto
def register_driver():
    print("\n" + "="*50)
    print("Cadastro de Novo Piloto")
    print("="*50)

    driver_ref = input("DriverRef: ")
    number = input("Number (opcional): ") or None
    code = input("Code: ")
    forename = input("Forename: ")
    surname = input("Surname: ")
    dob = input("Date of Birth (YYYY-MM-DD): ")
    nationality = input("Nationality: ")

    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Busca o próximo DriverID
            cursor.execute('SELECT COALESCE(MAX("driverid"), 0) + 1 FROM "LabBD25-Grupo7".Drivers')
            next_id = cursor.fetchone()[0]

            # Insere novo piloto com ID manual
            cursor.execute("""
                INSERT INTO "LabBD25-Grupo7".Drivers 
                (driverid, DriverRef, Number, Code, Forename, Surname, DateOfBirth, Nationality)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (next_id, driver_ref, number, code, forename, surname, dob, nationality))

            # Cria usuário associado (senha = driver_ref)
            username = f"{driver_ref}_d"
            cursor.execute("""
                INSERT INTO "LabBD25-Grupo7".UserAccounts 
                (Username, PasswordHash, UserType, driverid)
                VALUES (%s, %s, 'driver', %s)
            """, (username, driver_ref, next_id))

            conn.commit()
            print(f"Piloto cadastrado com sucesso! Usuário: {username}")

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        print("Erro: DriverRef já existe!")
    finally:
        conn.close()

# Função para consultar piloto por nome com validação
def search_driver_by_name():
    print("\n" + "="*50)
    print("Consulta de Piloto por Nome")
    print("="*50)

    try:
        search_name = input("Digite o nome do piloto (nome ou sobrenome): ").strip()
        
        # Valida entrada
        search_name = validate_input(search_name, "name")
        
        if not search_name or len(search_name) < 2:
            print("Nome deve ter pelo menos 2 caracteres!")
            return

        db = DatabaseManager()
        
        # Busca pilotos que contenham o nome digitado no nome ou sobrenome
        drivers = db.execute_query("""
            SELECT D.DriverId, D.DriverRef, D.Number, D.Code, 
                   D.Forename, D.Surname, D.DateOfBirth, D.Nationality
            FROM "LabBD25-Grupo7".Drivers D
            WHERE LOWER(D.Forename) LIKE LOWER(%s) 
               OR LOWER(D.Surname) LIKE LOWER(%s)
               OR LOWER(D.Forename || ' ' || D.Surname) LIKE LOWER(%s)
            ORDER BY D.Surname, D.Forename
        """, (f'%{search_name}%', f'%{search_name}%', f'%{search_name}%'))

        if not drivers:
            print(f"Nenhum piloto encontrado com o nome '{search_name}'.")
            return

        print(f"\nPilotos encontrados ({len(drivers)}):")
        print("="*80)

        # Exibe os pilotos encontrados
        headers = ["ID", "Ref", "Número", "Código", "Nome", "Sobrenome", "Nascimento", "Nacionalidade"]
        print(tabulate(drivers, headers=headers, tablefmt="pretty"))

        # Permite selecionar um piloto para ver detalhes
        print("\nDeseja ver detalhes de algum piloto? (Digite o ID ou 'n' para voltar)")
        choice = input("Opção: ").strip()

        if choice.lower() != 'n' and choice.isdigit():
            driver_id = int(choice)
            # Verifica se o ID existe na lista retornada
            valid_ids = [str(driver[0]) for driver in drivers]
            if choice in valid_ids:
                show_driver_details(driver_id)
            else:
                print("ID inválido!")

    except ValueError as e:
        print(f"Erro de validação: {e}")
    except Exception as e:
        print(f"Erro ao buscar piloto: {e}")

# Função para mostrar detalhes de um piloto específico
def show_driver_details(driver_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Informações básicas do piloto
            cursor.execute("""
                SELECT D.Forename, D.Surname, D.DateOfBirth, D.Nationality, D.DriverRef, D.Code
                FROM "LabBD25-Grupo7".Drivers D
                WHERE D.DriverId = %s
            """, (driver_id,))

            driver_info = cursor.fetchone()
            if not driver_info:
                print("Piloto não encontrado!")
                return

            print(f"\n" + "="*60)
            print(f"DETALHES DO PILOTO: {driver_info[0]} {driver_info[1]}")
            print("="*60)
            print(f"Data de Nascimento: {driver_info[2]}")
            print(f"Nacionalidade: {driver_info[3]}")
            print(f"Referência: {driver_info[4]}")
            print(f"Código: {driver_info[5]}")

            # Estatísticas de carreira
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT R.RaceId) as total_corridas,
                    SUM(R.Points) as total_pontos,
                    COUNT(CASE WHEN R.Position = 1 THEN 1 END) as vitorias,
                    COUNT(CASE WHEN R.Position <= 3 THEN 1 END) as podios,
                    MIN(RC.Year) as primeiro_ano,
                    MAX(RC.Year) as ultimo_ano
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.DriverId = %s
            """, (driver_id,))

            stats = cursor.fetchone()

            if stats[0] > 0:  # Se tem corridas
                print("\nEstatísticas de Carreira:")
                print(f"  - Total de Corridas: {stats[0]}")
                print(f"  - Total de Pontos: {stats[1] or 0}")
                print(f"  - Vitórias: {stats[2]}")
                print(f"  - Pódios: {stats[3]}")
                print(f"  - Período de Atividade: {stats[4]} - {stats[5]}")

                # Top 5 melhores resultados
                cursor.execute("""
                    SELECT RC.Name, RC.Year, R.Position, R.Points
                    FROM "LabBD25-Grupo7".Results R
                    JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                    WHERE R.DriverId = %s AND R.Position IS NOT NULL
                    ORDER BY R.Position ASC
                    LIMIT 5
                """, (driver_id,))

                best_results = cursor.fetchall()
                if best_results:
                    print("\nTop 5 Melhores Resultados:")
                    print(tabulate(best_results, headers=["Corrida", "Ano", "Posição", "Pontos"], tablefmt="pretty"))
            else:
                print("\nEste piloto não possui registros de corridas no banco de dados.")

            print("="*60)
            input("Pressione Enter para continuar...")

    except Exception as e:
        print(f"Erro ao buscar detalhes do piloto: {e}")
    finally:
        conn.close()

def import_drivers_from_file():
    file_path = input("Caminho do arquivo CSV: ")

    if not os.path.exists(file_path):
        print("Arquivo não encontrado!")
        return

    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            drivers = list(reader)
            print(f"Dados lidos: {drivers}")
                    
        conn = connect_db()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                for driver in drivers:
                    # Strip whitespace from values
                    driver = {k: v.strip() if v else None for k, v in driver.items()}
                    
                    # Verifica se piloto já existe
                    cursor.execute("""
                        SELECT DriverId 
                        FROM "LabBD25-Grupo7".Drivers
                        WHERE Forename = %s AND Surname = %s
                    """, (driver['forename'], driver['surname']))

                    if cursor.fetchone():
                        print(f"Piloto {driver['forename']} {driver['surname']} já existe. Pulando...")
                        continue
                    
                    # Busca próximo ID - CORREÇÃO AQUI
                    cursor.execute('SELECT COALESCE(MAX("driverid"), 0) + 1 FROM "LabBD25-Grupo7".Drivers')
                    next_id = cursor.fetchone()[0]

                    # Insere novo piloto - REMOVIDO O RETURNING
                    cursor.execute("""
                        INSERT INTO "LabBD25-Grupo7".Drivers 
                        (DriverID, DriverRef, Number, Code, Forename, Surname, DateOfBirth, Nationality)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        next_id,
                        driver['driverref'],
                        driver.get('number'),
                        driver['code'],
                        driver['forename'],
                        driver['surname'],
                        driver['dateofbirth'],
                        driver['nationality']
                    ))

                    # Cria usuário associado - CORREÇÃO AQUI
                    username = f"{driver['driverref']}_d"
                    cursor.execute("""
                        SET search_path TO "LabBD25-Grupo7";
                        INSERT INTO "LabBD25-Grupo7".UserAccounts 
                        (Username, PasswordHash, UserType, DriverID)
                        VALUES (%s, crypt(%s, gen_salt('bf')), %s, %s)
                    """, (username, driver['driverref'], 'driver', next_id))

                conn.commit()
                print(f"{len(drivers)} pilotos importados com sucesso!")

        except Exception as e:
            conn.rollback()
            print(f"Erro ao importar dados: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    except Exception as e:
        print(f"Erro ao processar arquivo: {e}")

# Função para gerar relatórios administrativos
def generate_admin_reports():
    print("\n" + "="*50)
    print("RELATÓRIOS ADMINISTRATIVOS")
    print("="*50)
    print("1. Top 10 Pilotos com Mais Vitórias")
    print("2. Top 10 Escuderias com Mais Pontos")
    print("3. Estatísticas por Temporada")
    print("4. Análise de Nacionalidades")
    print("5. Relatório de Atividade de Usuários")
    print("6. Voltar")

    choice = input("Escolha um relatório: ")

    if choice == '1':
        top_drivers_wins_report()
    elif choice == '2':
        top_constructors_points_report()
    elif choice == '3':
        season_statistics_report()
    elif choice == '4':
        nationality_analysis_report()
    elif choice == '5':
        user_activity_report()

def top_drivers_wins_report():
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT D.Forename || ' ' || D.Surname AS piloto,
                       D.Nationality,
                       COUNT(*) AS vitorias,
                       SUM(R.Points) AS total_pontos
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Drivers D ON R.DriverId = D.DriverId
                WHERE R.Position = 1
                GROUP BY D.DriverId, piloto, D.Nationality
                ORDER BY vitorias DESC
                LIMIT 10
            """)
            results = cursor.fetchall()

            print("\n" + "="*70)
            print("TOP 10 PILOTOS COM MAIS VITÓRIAS")
            print("="*70)
            print(tabulate(results, headers=["Piloto", "Nacionalidade", "Vitórias", "Total Pontos"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open('relatorios/top_drivers_wins.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Piloto", "Nacionalidade", "Vitórias", "Total Pontos"])
                writer.writerows(results)
            print("\nRelatório salvo em: top_drivers_wins.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def top_constructors_points_report():
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT C.Name,
                       C.Nationality,
                       SUM(R.Points) AS total_pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(DISTINCT RC.Year) AS anos_participacao
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Constructors C ON R.ConstructorId = C.ConstructorId
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                GROUP BY C.ConstructorId, C.Name, C.Nationality
                ORDER BY total_pontos DESC
                LIMIT 10
            """)
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("TOP 10 ESCUDERIAS COM MAIS PONTOS")
            print("="*80)
            print(tabulate(results, headers=["Escuderia", "Nacionalidade", "Pontos", "Vitórias", "Anos"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open('relatorios/top_constructors_points.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Escuderia", "Nacionalidade", "Pontos", "Vitórias", "Anos"])
                writer.writerows(results)
            print("\nRelatório salvo em: top_constructors_points.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def season_statistics_report():
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT RC.Year,
                       COUNT(DISTINCT RC.RaceId) AS corridas,
                       COUNT(DISTINCT R.DriverId) AS pilotos_participantes,
                       COUNT(DISTINCT R.ConstructorId) AS escuderias_participantes,
                       AVG(R.Points) AS media_pontos_por_corrida
                FROM "LabBD25-Grupo7".Races RC
                JOIN "LabBD25-Grupo7".Results R ON RC.RaceId = R.RaceId
                GROUP BY RC.Year
                ORDER BY RC.Year DESC
                LIMIT 20
            """)
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("ESTATÍSTICAS DAS ÚLTIMAS 20 TEMPORADAS")
            print("="*80)
            print(tabulate(results, headers=["Ano", "Corridas", "Pilotos", "Escuderias", "Média Pts"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open('relatorios/season_statistics.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Ano", "Corridas", "Pilotos", "Escuderias", "Média Pontos"])
                writer.writerows(results)
            print("\nRelatório salvo em: season_statistics.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def nationality_analysis_report():
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Análise de pilotos por nacionalidade
            cursor.execute("""
                SELECT D.Nationality,
                       COUNT(*) AS total_pilotos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       SUM(R.Points) AS total_pontos
                FROM "LabBD25-Grupo7".Drivers D
                LEFT JOIN "LabBD25-Grupo7".Results R ON D.DriverId = R.DriverId
                GROUP BY D.Nationality
                HAVING COUNT(*) > 5
                ORDER BY total_pontos DESC NULLS LAST
                LIMIT 15
            """)
            driver_results = cursor.fetchall()

            print("\n" + "="*80)
            print("ANÁLISE DE PILOTOS POR NACIONALIDADE (Países com 5+ pilotos)")
            print("="*80)
            print(tabulate(driver_results, headers=["Nacionalidade", "Pilotos", "Vitórias", "Pontos"], tablefmt="pretty"))

            # Análise de escuderias por nacionalidade
            cursor.execute("""
                SELECT C.Nationality,
                       COUNT(*) AS total_escuderias,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       SUM(R.Points) AS total_pontos
                FROM "LabBD25-Grupo7".Constructors C
                LEFT JOIN "LabBD25-Grupo7".Results R ON C.ConstructorId = R.ConstructorId
                GROUP BY C.Nationality
                HAVING COUNT(*) > 2
                ORDER BY total_pontos DESC NULLS LAST
                LIMIT 10
            """)
            constructor_results = cursor.fetchall()

            print("\n" + "="*80)
            print("ANÁLISE DE ESCUDERIAS POR NACIONALIDADE (Países com 2+ escuderias)")
            print("="*80)
            print(tabulate(constructor_results, headers=["Nacionalidade", "Escuderias", "Vitórias", "Pontos"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open('relatorios/nationality_analysis.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["=== PILOTOS ==="])
                writer.writerow(["Nacionalidade", "Pilotos", "Vitórias", "Pontos"])
                writer.writerows(driver_results)
                writer.writerow([])
                writer.writerow(["=== ESCUDERIAS ==="])
                writer.writerow(["Nacionalidade", "Escuderias", "Vitórias", "Pontos"])
                writer.writerows(constructor_results)
            print("\nRelatório salvo em: nationality_analysis.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def user_activity_report():
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ua.Username,
                       ua.UserType,
                       COALESCE(d.Forename || ' ' || d.Surname, c.Name, 'Admin') AS nome,
                       COUNT(ul.LoginTime) AS total_logins,
                       MAX(ul.LoginTime) AS ultimo_login
                FROM "LabBD25-Grupo7".UserAccounts ua
                LEFT JOIN "LabBD25-Grupo7".Users_Log ul ON ua.UserID = ul.UserID
                LEFT JOIN "LabBD25-Grupo7".Drivers d ON ua.DriverID = d.DriverID
                LEFT JOIN "LabBD25-Grupo7".Constructors c ON ua.ConstructorID = c.ConstructorID
                GROUP BY ua.UserID, ua.Username, ua.UserType, nome
                ORDER BY total_logins DESC, ultimo_login DESC
            """)
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("RELATÓRIO DE ATIVIDADE DE USUÁRIOS")
            print("="*80)
            print(tabulate(results, headers=["Usuário", "Tipo", "Nome", "Logins", "Último Login"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open('relatorios/user_activity.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Usuário", "Tipo", "Nome", "Logins", "Último Login"])
                writer.writerows(results)
            print("\nRelatório salvo em: user_activity.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

# Função para gerar relatórios de escuderias
def generate_constructor_reports(user_info):
    print("\n" + "="*50)
    print(f"RELATÓRIOS - {user_info['constructor_name']}")
    print("="*50)
    print("1. Histórico de Resultados por Ano")
    print("2. Performance de Pilotos da Escuderia")
    print("3. Comparação com Outras Escuderias")
    print("4. Análise de Circuitos")
    print("5. Voltar")

    choice = input("Escolha um relatório: ")

    if choice == '1':
        constructor_yearly_results(user_info['constructor_id'])
    elif choice == '2':
        constructor_drivers_performance(user_info['constructor_id'])
    elif choice == '3':
        constructor_comparison(user_info['constructor_id'], user_info['constructor_name'])
    elif choice == '4':
        constructor_circuits_analysis(user_info['constructor_id'])

def constructor_yearly_results(constructor_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT RC.Year,
                       COUNT(DISTINCT R.RaceId) AS corridas,
                       SUM(R.Points) AS pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(CASE WHEN R.Position <= 3 THEN 1 END) AS podios,
                       AVG(CAST(R.Position AS FLOAT)) AS posicao_media
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.ConstructorId = %s AND R.Position IS NOT NULL
                GROUP BY RC.Year
                ORDER BY RC.Year DESC
            """, (constructor_id,))
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("HISTÓRICO DE RESULTADOS POR ANO")
            print("="*80)
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                if formatted_row[5]:  # posição média
                    formatted_row[5] = f"{formatted_row[5]:.2f}"
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Ano", "Corridas", "Pontos", "Vitórias", "Pódios", "Pos. Média"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/constructor_{constructor_id}_yearly.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Ano", "Corridas", "Pontos", "Vitórias", "Pódios", "Posição Média"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: constructor_{constructor_id}_yearly.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def constructor_drivers_performance(constructor_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT D.Forename || ' ' || D.Surname AS piloto,
                       COUNT(DISTINCT R.RaceId) AS corridas,
                       SUM(R.Points) AS pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(CASE WHEN R.Position <= 3 THEN 1 END) AS podios,
                       AVG(CAST(R.Position AS FLOAT)) AS posicao_media,
                       MIN(RC.Year) AS primeiro_ano,
                       MAX(RC.Year) AS ultimo_ano
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Drivers D ON R.DriverId = D.DriverId
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.ConstructorId = %s AND R.Position IS NOT NULL
                GROUP BY D.DriverId, piloto
                ORDER BY pontos DESC
            """, (constructor_id,))
            results = cursor.fetchall()

            print("\n" + "="*90)
            print("PERFORMANCE DE PILOTOS DA ESCUDERIA")
            print("="*90)
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                if formatted_row[5]:  # posição média
                    formatted_row[5] = f"{formatted_row[5]:.2f}"
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Piloto", "Corridas", "Pontos", "Vitórias", "Pódios", "Pos. Média", "1º Ano", "Último"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/constructor_{constructor_id}_drivers.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Piloto", "Corridas", "Pontos", "Vitórias", "Pódios", "Posição Média", "Primeiro Ano", "Último Ano"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: constructor_{constructor_id}_drivers.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def constructor_comparison(constructor_id, constructor_name):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT C.Name,
                       SUM(R.Points) AS total_pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(CASE WHEN R.Position <= 3 THEN 1 END) AS podios,
                       COUNT(DISTINCT R.RaceId) AS corridas,
                       ROUND(CAST(AVG(R.Position) AS NUMERIC),2) AS posicao_media
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Constructors C ON R.ConstructorId = C.ConstructorId
                WHERE R.Position IS NOT NULL
                GROUP BY C.ConstructorId, C.Name
                HAVING SUM(R.Points) > 0
                ORDER BY total_pontos DESC
                LIMIT 20
            """)
            results = cursor.fetchall()

            print("\n" + "="*80)
            print(f"COMPARAÇÃO DE {constructor_name.upper()} COM OUTRAS ESCUDERIAS")
            print("="*80)
            
            # Destacar a escuderia atual
            highlighted_results = []
            for row in results:
                if row[0] == constructor_name:
                    highlighted_results.append([f">>> {row[0]} <<<"] + list(row[1:]))
                else:
                    highlighted_results.append(row)
            
            print(tabulate(highlighted_results, headers=["Escuderia", "Pontos", "Vitórias", "Pódios", "Corridas", "Pos. Média"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/constructor_{constructor_id}_comparison.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Escuderia", "Pontos", "Vitórias", "Pódios", "Corridas", "Posição Média"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: constructor_{constructor_id}_comparison.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def constructor_circuits_analysis(constructor_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT CI.Name AS circuito,
                       CI.Country,
                       COUNT(*) AS corridas,
                       SUM(R.Points) AS pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       AVG(CAST(R.Position AS FLOAT)) AS posicao_media
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                JOIN "LabBD25-Grupo7".Circuits CI ON RC.CircuitId = CI.CircuitId
                WHERE R.ConstructorId = %s AND R.Position IS NOT NULL
                GROUP BY CI.CircuitId, CI.Name, CI.Country
                HAVING COUNT(*) >= 3
                ORDER BY posicao_media ASC
            """, (constructor_id,))
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("ANÁLISE DE PERFORMANCE POR CIRCUITO (Mín. 3 corridas)")
            print("="*80)
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                if formatted_row[5]:  # posição média
                    formatted_row[5] = f"{formatted_row[5]:.2f}"
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Circuito", "País", "Corridas", "Pontos", "Vitórias", "Pos. Média"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/constructor_{constructor_id}_circuits.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Circuito", "País", "Corridas", "Pontos", "Vitórias", "Posição Média"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: constructor_{constructor_id}_circuits.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

# Função para gerar relatórios de pilotos
def generate_driver_reports(user_info):
    print("\n" + "="*50)
    print(f"RELATÓRIOS - {user_info['driver_name']}")
    print("="*50)
    print("1. Histórico de Resultados por Ano")
    print("2. Performance por Escuderia")
    print("3. Análise de Circuitos")
    print("4. Comparação com Outros Pilotos")
    print("5. Tempos de Volta")
    print("6. Voltar")

    choice = input("Escolha um relatório: ")

    if choice == '1':
        driver_yearly_results(user_info['driver_id'])
    elif choice == '2':
        driver_constructor_performance(user_info['driver_id'])
    elif choice == '3':
        driver_circuits_analysis(user_info['driver_id'])
    elif choice == '4':
        driver_comparison(user_info['driver_id'], user_info['driver_name'])
    elif choice == '5':
        driver_lap_times(user_info['driver_id'])

def driver_yearly_results(driver_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT RC.Year,
                       COUNT(DISTINCT R.RaceId) AS corridas,
                       SUM(R.Points) AS pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(CASE WHEN R.Position <= 3 THEN 1 END) AS podios,
                       AVG(CAST(R.Position AS FLOAT)) AS posicao_media,
                       C.Name AS escuderia_principal
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                JOIN "LabBD25-Grupo7".Constructors C ON R.ConstructorId = C.ConstructorId
                WHERE R.DriverId = %s AND R.Position IS NOT NULL
                GROUP BY RC.Year, C.ConstructorId, C.Name
                ORDER BY RC.Year DESC
            """, (driver_id,))
            results = cursor.fetchall()

            print("\n" + "="*90)
            print("HISTÓRICO DE RESULTADOS POR ANO")
            print("="*90)
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                if formatted_row[5]:  # posição média
                    formatted_row[5] = f"{formatted_row[5]:.2f}"
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Ano", "Corridas", "Pontos", "Vitórias", "Pódios", "Pos. Média", "Escuderia"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/driver_{driver_id}_yearly.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Ano", "Corridas", "Pontos", "Vitórias", "Pódios", "Posição Média", "Escuderia"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: driver_{driver_id}_yearly.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def driver_constructor_performance(driver_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT C.Name AS escuderia,
                       COUNT(DISTINCT R.RaceId) AS corridas,
                       SUM(R.Points) AS pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(CASE WHEN R.Position <= 3 THEN 1 END) AS podios,
                       AVG(CAST(R.Position AS FLOAT)) AS posicao_media,
                       MIN(RC.Year) AS primeiro_ano,
                       MAX(RC.Year) AS ultimo_ano
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Constructors C ON R.ConstructorId = C.ConstructorId
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                WHERE R.DriverId = %s AND R.Position IS NOT NULL
                GROUP BY C.ConstructorId, C.Name
                ORDER BY pontos DESC
            """, (driver_id,))
            results = cursor.fetchall()

            print("\n" + "="*90)
            print("PERFORMANCE POR ESCUDERIA")
            print("="*90)
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                if formatted_row[5]:  # posição média
                    formatted_row[5] = f"{formatted_row[5]:.2f}"
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Escuderia", "Corridas", "Pontos", "Vitórias", "Pódios", "Pos. Média", "1º Ano", "Último"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/driver_{driver_id}_constructors.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Escuderia", "Corridas", "Pontos", "Vitórias", "Pódios", "Posição Média", "Primeiro Ano", "Último Ano"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: driver_{driver_id}_constructors.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def driver_circuits_analysis(driver_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT CI.Name AS circuito,
                       CI.Country,
                       COUNT(*) AS corridas,
                       SUM(R.Points) AS pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       AVG(CAST(R.Position AS FLOAT)) AS posicao_media
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Races RC ON R.RaceId = RC.RaceId
                JOIN "LabBD25-Grupo7".Circuits CI ON RC.CircuitId = CI.CircuitId
                WHERE R.DriverId = %s AND R.Position IS NOT NULL
                GROUP BY CI.CircuitId, CI.Name, CI.Country
                HAVING COUNT(*) >= 2
                ORDER BY posicao_media ASC
            """, (driver_id,))
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("ANÁLISE DE PERFORMANCE POR CIRCUITO (Mín. 2 corridas)")
            print("="*80)
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                if formatted_row[5]:  # posição média
                    formatted_row[5] = f"{formatted_row[5]:.2f}"
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Circuito", "País", "Corridas", "Pontos", "Vitórias", "Pos. Média"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/driver_{driver_id}_circuits.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Circuito", "País", "Corridas", "Pontos", "Vitórias", "Posição Média"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: driver_{driver_id}_circuits.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def driver_comparison(driver_id, driver_name):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT D.Forename || ' ' || D.Surname AS piloto,
                       SUM(R.Points) AS total_pontos,
                       COUNT(CASE WHEN R.Position = 1 THEN 1 END) AS vitorias,
                       COUNT(CASE WHEN R.Position <= 3 THEN 1 END) AS podios,
                       COUNT(DISTINCT R.RaceId) AS corridas,
                       ROUND(AVG(CAST(R.Position AS FLOAT)), 2) AS posicao_media
                FROM "LabBD25-Grupo7".Results R
                JOIN "LabBD25-Grupo7".Drivers D ON R.DriverId = D.DriverId
                WHERE R.Position IS NOT NULL
                GROUP BY D.DriverId, piloto
                HAVING SUM(R.Points) > 0
                ORDER BY total_pontos DESC
                LIMIT 20
            """)
            results = cursor.fetchall()

            print("\n" + "="*80)
            print(f"COMPARAÇÃO DE {driver_name.upper()} COM OUTROS PILOTOS")
            print("="*80)
            
            # Destacar o piloto atual
            highlighted_results = []
            for row in results:
                if row[0] == driver_name:
                    highlighted_results.append([f">>> {row[0]} <<<"] + list(row[1:]))
                else:
                    highlighted_results.append(row)
            
            print(tabulate(highlighted_results, headers=["Piloto", "Pontos", "Vitórias", "Pódios", "Corridas", "Pos. Média"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/driver_{driver_id}_comparison.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Piloto", "Pontos", "Vitórias", "Pódios", "Corridas", "Posição Média"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: driver_{driver_id}_comparison.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def driver_lap_times(driver_id):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT RC.Name AS corrida,
                       RC.Year,
                       COUNT(LT.Lap) AS voltas_completadas,
                       MIN(LT.Milliseconds) AS melhor_volta_ms,
                       AVG(LT.Milliseconds) AS tempo_medio_ms
                FROM "LabBD25-Grupo7".LapTimes LT
                JOIN "LabBD25-Grupo7".Races RC ON LT.RaceId = RC.RaceId
                WHERE LT.DriverId = %s
                GROUP BY RC.RaceId, RC.Name, RC.Year
                ORDER BY RC.Year DESC, RC.Name
                LIMIT 20
            """, (driver_id,))
            results = cursor.fetchall()

            print("\n" + "="*80)
            print("ANÁLISE DE TEMPOS DE VOLTA (Últimas 20 corridas)")
            print("="*80)
            
            # Converter milissegundos para formato tempo
            formatted_results = []
            for row in results:
                formatted_row = list(row[:3])
                if row[3]:  # melhor volta
                    minutes = row[3] // 60000
                    seconds = (row[3] % 60000) / 1000
                    formatted_row.append(f"{minutes}:{seconds:06.3f}")
                else:
                    formatted_row.append("N/A")
                    
                if row[4]:  # tempo médio
                    minutes = row[4] // 60000
                    seconds = (row[4] % 60000) / 1000
                    formatted_row.append(f"{minutes}:{seconds:06.3f}")
                else:
                    formatted_row.append("N/A")
                    
                formatted_results.append(formatted_row)
            
            print(tabulate(formatted_results, headers=["Corrida", "Ano", "Voltas", "Melhor Volta", "Tempo Médio"], tablefmt="pretty"))
            
            # Salvar em CSV
            with open(f'relatorios/driver_{driver_id}_laptimes.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Corrida", "Ano", "Voltas", "Melhor Volta (ms)", "Tempo Médio (ms)"])
                writer.writerows(results)
            print(f"\nRelatório salvo em: driver_{driver_id}_laptimes.csv")
            
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        conn.close()
        input("Pressione Enter para continuar...")

def record_logout(user_id):
    # Abre conexão usando seu DB_CONFIG
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    logout_query = sql.SQL("""
        UPDATE "LabBD25-Grupo7".Users_Log
        SET LogoutTime = CURRENT_TIMESTAMP
        WHERE UserID = %s
          AND LoginTime = (
              SELECT MAX(LoginTime)
              FROM "LabBD25-Grupo7".Users_Log
              WHERE UserID = %s
          )
    """)
    cursor.execute(logout_query, (user_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

# Função principal com views separadas
def main():
    print("="*50)
    print("SISTEMA DE GERENCIAMENTO FÓRMULA 1")
    print("="*50)

    user_info = None
    while not user_info:
        print("\nTela de Login")
        user_info = authenticate_user()

    # Cria a view apropriada baseada no tipo de usuário
    if user_info['user_type'] == 'admin':
        user_view = AdminView(user_info)
    elif user_info['user_type'] == 'constructor':
        user_view = ConstructorView(user_info)
    elif user_info['user_type'] == 'driver':
        user_view = DriverView(user_info)
    else:
        print("Tipo de usuário inválido!")
        return

    while True:
        try:
            if user_info['user_type'] == 'admin':
                choice = user_view.show_dashboard()

                if choice == '1':
                    user_view.register_constructor_safe()
                elif choice == '2':
                    user_view.register_driver_safe()
                elif choice == '3':
                    search_driver_by_name()
                elif choice == '4':
                    import_drivers_from_file()
                elif choice == '5':
                    generate_admin_reports()
                elif choice == '6':
                    print("Verificando views do sistema...")
                    if DatabaseManager.check_views_exist():
                        print("Todas as views estão funcionando corretamente!")
                    else:
                        print("Algumas views podem estar faltando ou com problemas!")
                    input("Pressione Enter para continuar...")
                elif choice == '7':
                    break
                else:
                    print("Opção inválida!")

            elif user_info['user_type'] == 'constructor':
                choice = user_view.show_dashboard()

                if choice == '1':
                    user_view.generate_reports_menu()
                elif choice == '2':
                    break
                else:
                    print("Opção inválida!")

            elif user_info['user_type'] == 'driver':
                choice = user_view.show_dashboard()

                if choice == '1':
                    user_view.generate_reports_menu()
                elif choice == '2':
                    break
                else:
                    print("Opção inválida!")

        except KeyboardInterrupt:
            print("\n\nSaindo do sistema...")
            break
        except Exception as e:
            print(f"\nErro inesperado: {e}")
            print("Voltando ao menu principal...")

    record_logout(user_info['user_id'])

    print("\nSessão encerrada. Até logo!")

if __name__ == "__main__":
    main()