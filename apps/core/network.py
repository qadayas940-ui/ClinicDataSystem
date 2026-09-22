"""Network address discovery shared by the desktop launcher and settings UI."""
import ipaddress
import socket
from urllib.parse import urlparse


def public_hostname(url):
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def discover_lan_addresses():
    """Return usable private IPv4 addresses with the default-route address first."""
    candidates = []
    for target in (("1.1.1.1", 53), ("8.8.8.8", 53), ("192.0.2.1", 80)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(target)
            candidates.append(sock.getsockname()[0])
        except OSError:
            pass
        finally:
            sock.close()
    try:
        candidates.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    result = []
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.version == 4 and address.is_private and not address.is_loopback and not address.is_link_local:
            if candidate not in result:
                result.append(candidate)
    return result


def preferred_lan_url(port):
    addresses = discover_lan_addresses()
    return f"http://{addresses[0]}:{port}" if addresses else f"http://127.0.0.1:{port}"
