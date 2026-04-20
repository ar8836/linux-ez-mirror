#!/usr/bin/env python3
import os
import subprocess
import re
from utils import check_root
from pathlib import Path


class MySQLHandler:
    """Handle MySQL/MariaDB master/slave replication setup."""

    DEFAULTS_DIRS = [
        "/etc/mysql",
        "/etc/mysql/mysql.conf.d",
        "/etc",
        "/etc/mysql/mysql.conf.d"
    ]

    CONFIG_FILES = ["my.cnf", "mysqld.cnf", "mysql.conf.d/mysql.conf"]

    def __init__(self):
        self.distro = self._detect_distro()
        self.config_path = self._find_config_file()
        self.is_master = False

    def _detect_distro(self) -> str:
        """Detect Linux distribution."""
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                content = f.read().lower()
                if "rhel" in content or "centos" in content or "fedora" in content:
                    return "RHEL"
                if "arch" in content:
                    return "Arch"
                if "debian" in content or "ubuntu" in content:
                    return "Debian"
        except FileNotFoundError:
            pass
        return "Unknown"

    def _find_config_file(self) -> Path:
        """Search for my.cnf or equivalent config file in known directories."""
        for dir_path in self.DEFAULTS_DIRS:
            for cfg in self.CONFIG_FILES:
                full_path = os.path.join(dir_path, cfg)
                if os.path.exists(full_path):
                    return Path(full_path)
        return None

    def _find_service_name(self) -> str:
        """Determine the systemd service name for MySQL."""
        # Common service names across distributions
        for name in ["mysql", "mysqld", "mariadb"]:
            result = subprocess.run(
                ["systemctl", "list-units", "--type=service", name],
                capture_output=True,
                text=True,
            )
            if "mysql.service" in result.stdout or f"{name}.service" in result.stdout:
                return name
        return "mysql"

    def _backup_file(self, path: Path) -> None:
        """Create a backup of a configuration file."""
        if not path.exists():
            return
        backup_path = path.with_suffix(path.suffix + ".bak")
        backup_path.write_text(path.read_text())
        # Note: Real implementation should preserve permissions and timestamps

    def _replace_or_append_line(self, file_path: Path, match_regex: str, new_line: str):
        """Replace a line matching regex or append it to the file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        content_lines = file_path.read_text().splitlines()
        updated = False
        for i, line in enumerate(content_lines):
            if re.search(match_regex, line, re.IGNORECASE):
                content_lines[i] = new_line
                updated = True
                break

        if not updated:
            content_lines.append(new_line)
        file_path.write_text("\n".join(content_lines))

    def setup_master(self, other_ip: str, root_pwd: str, repl_user: str, repl_pwd: str) -> None:
        """Configure this instance as MySQL master."""
        self.is_master = True

        if not self.config_path:
            # Prompt user for custom config path if not found
            file_path = input(
                "MySQL config file not found. Enter absolute path to my.cnf or similar: "
            )
            self.config_path = Path(file_path)
            if not self.config_path.exists():
                raise FileNotFoundError("Specified config file does not exist.")

        self._backup_file(self.config_path)

        # Add/replace [mysqld] block with replication settings
        self._replace_or_append_line(
            self.config_path,
            r"^\s*\[mysqld\]",
            "[mysqld]\nserver-id=1\nlog-bin=mysql-bin\ninnodb_flush_logs_at_trx_commit=1\nsync_binlog=1"
        )

        # Ensure binlog directory exists
        binlog_dir = "/var/log/mysql"
        if not os.path.isdir(binlog_dir):
            os.makedirs(binlog_dir, exist_ok=True)

        # Restart MySQL service
        service_name = self._find_service_name()
        subprocess.run(
            ["systemctl", "restart", service_name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Create replication user and grant privileges
        cmd = [
            "mysql",
            "-u", "root",
            "-p" + root_pwd,
            "-e",
            f"""
            CREATE USER IF NOT EXISTS '{repl_user}'@'%' IDENTIFIED BY '{repl_pwd}';
            GRANT REPLICATION SLAVE ON *.* TO '{repl_user}'@'%';
            FLUSH PRIVILEGES;
            SHOW MASTER STATUS;
            """
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
        print(result.stdout)

    def setup_slave(self, master_ip: str, master_pwd: str, repl_user: str, repl_pwd: str) -> None:
        """Configure this instance as MySQL slave."""
        self.is_master = False

        if not self.config_path:
            file_path = input(
                "MySQL config file not found. Enter absolute path to my.cnf or similar: "
            )
            self.config_path = Path(file_path)
            if not self.config_path.exists():
                raise FileNotFoundError("Specified config file does not exist.")

        self._backup_file(self.config_path)

        # Add/replace [mysqld] block with server-id
        self._replace_or_append_line(
            self.config_path,
            r"^\s*\[mysqld\]",
            "[mysqld]\nserver-id=2\nlog-bin=mysql-bin"
        )

        service_name = self._find_service_name()
        subprocess.run(
            ["systemctl", "restart", service_name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Prompt for master status details if not provided
        print("Please provide binary log file and position from master.")
        file_name = input("Binlog file name: ").strip()
        file_pos = input("Binlog position: ").strip()

        # Configure slave replication
        cmd = [
            "mysql",
            "-u", "root",
            "-p" + master_pwd,
            "-e",
            f"""
            CHANGE MASTER TO
                MASTER_HOST='{master_ip}',
                MASTER_USER='{repl_user}',
                MASTER_PASSWORD='{repl_pwd}',
                MASTER_LOG_FILE='{file_name}',
                MASTER_LOG_POS={file_pos},
                MASTER_CONNECT_RETRY=30;
            START SLAVE;
            """
        ]
        subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )