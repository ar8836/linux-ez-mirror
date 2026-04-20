#!/usr/bin/env python3
import sys
import subprocess
from utils import check_root, get_linux_distro, get_local_ip
from mysql_handler import MySQLHandler
from psql_handler import PostgreSQLHandler

def print_banner():
    banner = """
    ==========================================
    Linux EZ Mirror - Maestro-Esclavo
    ==========================================
    """
    print(banner)

def main():
    print_banner()

    # Verificar ejecución como root
    if not check_root():
        print("Error: Este script debe ejecutarse como root.")
        sys.exit(1)

    # Detectar distribución de Linux
    distro = get_linux_distro()
    print(f"Distribución detectada: {distro}")

    # Obtener IP local
    local_ip = get_local_ip()
    print(f"IP local: {local_ip}")

    # Menú para seleccionar SGBD
    print("\nSeleccione el Sistema Gestor de Base de Datos:")
    print("1. MySQL/MariaDB")
    print("2. PostgreSQL")
    db_choice = input("Ingrese su opción (1/2): ").strip()

    if db_choice == '1':
        db_handler = MySQLHandler()
    elif db_choice == '2':
        db_handler = PostgreSQLHandler()
    else:
        print("Opción no válida.")
        sys.exit(1)

    # Menú para seleccionar rol
    print("\nSeleccione el rol en la replicación:")
    print("1. Maestro")
    print("2. Esclavo")
    role_choice = input("Ingrese su opción (1/2): ").strip()

    if role_choice == '1':
        role = 'master'
    elif role_choice == '2':
        role = 'slave'
    else:
        print("Opción no válida.")
        sys.exit(1)

    # Solicitar datos al usuario
    print("\n--- Configuración de Replicación ---")
    other_ip = input("Ingrese la IP de la otra máquina: ").strip()
    db_password = input("Ingrese la contraseña de root de la BD: ").strip()
    repl_user = input("Ingrese el nombre de usuario para replicación: ").strip()
    repl_password = input("Ingrese la contraseña para el usuario de replicación: ").strip()

    # Ejecutar la configuración según el rol
    if role == 'master':
        db_handler.setup_master(other_ip, db_password, repl_user, repl_password)
    else:
        db_handler.setup_slave(other_ip, db_password, repl_user, repl_password)

if __name__ == "__main__":
    main()