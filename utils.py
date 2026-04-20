import os
import subprocess
import platform
import socket


def check_root() -> bool:
    """Return True if the current user is root.
    """
    try:
        uid = os.geteuid()
        return uid == 0
    except AttributeError:  # Windows system, not expected in this repo
        return False


def get_linux_distro() -> str:
    """Detect the Linux distribution by parsing /etc/os-release.
    Returns a string like "Ubuntu", "Debian", "Arch", "RHEL", etc.
    """
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            info = f.read().lower()
            if "ubuntu" in info:
                return "Ubuntu"
            if "debian" in info:
                return "Debian"
            if "arch" in info:
                return "Arch"
            if "rhel" in info or "centos" in info or "fedora" in info:
                return "RHEL"
            return "Unknown"
    except FileNotFoundError:
        return "Unknown"


def get_local_ip() -> str:
    """Return the primary local IP address (non-loopback)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # connect to external IP; doesn't require actual route
        s.connect(("8.8.8.8", 53))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()
