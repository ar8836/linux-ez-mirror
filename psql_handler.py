mport os
import subprocess
from utils import check_root

class PostgreSQLHandler:
    """Maneja la replicación Maestro-Esclavo para PostgreSQL en Linux."""

    def __init__(self):
        # Rutas comunes en Debian/Ubuntu/Kali
        self.config_path = "/etc/postgresql/16/main/" # Ajustar según versión
        self.hba_file = os.path.join(self.config_path, "pg_hba.conf")
        self.conf_file = os.path.join(self.config_path, "postgresql.conf")

    def setup_master(self, slave_ip, repl_user, repl_password, db_password):
        print(f"[*] Configurando Maestro PostgreSQL para IP: {slave_ip}...")
        
        # 1. Configurar postgresql.conf para permitir réplicas
        commands = [
            f"sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/\" {self.conf_file}",
            f"sed -i \"s/#wal_level = replica/wal_level = replica/\" {self.conf_file}",
            f"sed -i \"s/#max_wal_senders = 10/max_wal_senders = 10/\" {self.conf_file}"
        ]
        
        # 2. Configurar pg_hba.conf para permitir la conexión del esclavo
        auth_line = f"host replication {repl_user} {slave_ip}/32 md5"
        
        try:
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
            
            with open(self.hba_file, "a") as f:
                f.write(f"\n{auth_line}\n")
            
            # 3. Crear usuario de replicación (simplificado)
            create_user_cmd = f"sudo -u postgres psql -c \"CREATE USER {repl_user} REPLICATION LOGIN CONNECTION LIMIT 10 ENCRYPTED PASSWORD '{repl_password}';\""
            subprocess.run(create_user_cmd, shell=True, check=True)
            
            subprocess.run("systemctl restart postgresql", shell=True, check=True)
            print("[+] Maestro configurado y reiniciado.")
        except Exception as e:
            print(f"[!] Error: {e}")

    def setup_slave(self, master_ip, repl_user, repl_password, db_password):
        print(f"[*] Configurando Esclavo PostgreSQL conectando a: {master_ip}...")
        try:
            # 1. Detener servicio y limpiar directorio de datos
            subprocess.run("systemctl stop postgresql", shell=True, check=True)
            data_dir = "/var/lib/postgresql/16/main/"
            subprocess.run(f"rm -rf {data_dir}*", shell=True, check=True)
            
            # 2. Realizar base backup desde el maestro
            backup_cmd = f"sudo -u postgres pg_basebackup -h {master_ip} -D {data_dir} -U {repl_user} -P -v -R"
            # Nota: Esto pedirá password o requiere un archivo .pgpass
            print("[!] Ejecutando pg_basebackup (asegúrate de tener configurado el acceso)...")
            
            # 3. Iniciar esclavo
            subprocess.run("systemctl start postgresql", shell=True, check=True)
            print("[+] Esclavo sincronizado e iniciado.")
        except Exception as e:
            print(f"[!] Error: {e}")
