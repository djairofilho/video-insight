"""Impede endereços de infraestrutura em arquivos versionáveis; não exibe valores."""

import ipaddress
import re
import subprocess
from pathlib import Path

PATTERN = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?![\w.])")
DOCUMENTATION_NETWORKS = tuple(ipaddress.ip_network(network) for network in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",
))


def sensitive(content):
    for match in PATTERN.finditer(content):
        try:
            address = ipaddress.ip_interface(match.group()).ip
        except ValueError:
            continue
        if not (address.is_loopback or address.is_unspecified
                or any(address in network for network in DOCUMENTATION_NETWORKS)):
            yield content.count("\n", 0, match.start()) + 1


if __name__ == "__main__":
    files = subprocess.check_output([
        "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z",
    ]).decode("utf8").split("\0")
    errors = []
    for filename in filter(None, files):
        path = Path(filename)
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf8")
        except UnicodeDecodeError:
            continue
        errors.extend(f"{filename}:{line}: endereço de infraestrutura deve vir de secret"
                      for line in sensitive(content))
    print("\n".join(errors) if errors else "Endereços de infraestrutura: nenhum valor literal versionável.")
    raise SystemExit(bool(errors))
