#!/usr/bin/env python3
"""
Скачивает внешние списки рекламы (OISD/Hagezi и т.п.),
нормализует в формат Xray (domain:example.com), дедуплицирует
и сохраняет в adblock_domains.txt, затем пересобирает конфиг Xray.
"""

import os
import sys
import urllib.request
import ssl
from typing import Iterable, Set

BASE_DIR = "/var/www/vpn/xray"
OUTPUT_FILE = os.path.join(BASE_DIR, "adblock_domains.txt")
GEO_DIR = "/usr/local/share/xray"
GEO_SITE_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"
GEO_IP_URL = "https://github.com/Loyalsoldier/geoip/releases/latest/download/geoip.dat"

# Источники (микс доменных и hosts-форматов)
SOURCES = [
    # OISD small (умеренный размер)
    "https://small.oisd.nl/domains",          # чистые домены
    "https://small.oisd.nl/domainswild",      # wildcard/поддомены
    # Hagezi (pro список)
    "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/pro.txt",
]


def fetch_url(url: str) -> Iterable[str]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=60) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
            for line in data.splitlines():
                yield line.strip()
    except Exception as e:
        print(f"⚠️ Не удалось скачать {url}: {e}")
        return []


def normalize_to_domains(lines: Iterable[str]) -> Set[str]:
    domains: Set[str] = set()
    for raw in lines:
        if not raw:
            continue
        if raw.startswith(("#", ";", "!")):
            continue
        # hosts: 0.0.0.0 domain.com или 127.0.0.1 domain
        if raw.startswith("0.0.0.0 ") or raw.startswith("127.0.0.1 "):
            parts = raw.split()
            if len(parts) >= 2:
                d = parts[1].strip().lower()
            else:
                continue
        else:
            # чистый домен
            d = raw.strip().lower()

        # фильтруем мусор
        if not d or d.startswith(":"):
            continue
        if d.startswith("localhost"):
            continue
        if "/" in d or d.startswith("["):
            # явно не домен
            continue
        # уберем начальные точки
        while d.startswith("."):
            d = d[1:]
        # простейшая валидация
        if "." not in d:
            continue
        domains.add(d)
    return domains


def write_xray_domains(domains: Set[str]) -> None:
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("# Сгенерировано update_adlists.py\n")
        for d in sorted(domains):
            f.write(f"domain:{d}\n")
    print(f"✅ Записано доменов: {len(domains)} → {OUTPUT_FILE}")


def ensure_geodata() -> None:
    """Скачивает/обновляет geosite.dat и geoip.dat в стандартный путь Xray."""
    os.makedirs(GEO_DIR, exist_ok=True)
    for url, name in ((GEO_SITE_URL, "geosite.dat"), (GEO_IP_URL, "geoip.dat")):
        dst = os.path.join(GEO_DIR, name)
        try:
            print(f"⬇️  {name}: {url}")
            urllib.request.urlretrieve(url, dst)
            # Права на чтение всем
            os.chmod(dst, 0o644)
            print(f"✅ Обновлено: {dst}")
        except Exception as e:
            print(f"⚠️ Не удалось обновить {name}: {e}")


def main() -> int:
    all_domains: Set[str] = set()
    for url in SOURCES:
        print(f"⬇️  Загружаю: {url}")
        lines = list(fetch_url(url))
        ds = normalize_to_domains(lines)
        print(f"   ➕ {len(ds)} доменов")
        all_domains |= ds

    if not all_domains:
        print("❌ Не получено доменов — пропускаю обновление")
        return 1

    write_xray_domains(all_domains)

    # Обновляем geosite/geoip, чтобы работали geosite правила
    ensure_geodata()

    # Пересобираем конфиг Xray
    try:
        sys.path.append(BASE_DIR)
        from build_config import build_config  # type: ignore
        build_config()
    except Exception as e:
        print(f"⚠️ Не удалось пересобрать конфиг через импорт: {e}")
        # fallback на subprocess
        try:
            import subprocess
            subprocess.run(["/usr/bin/python3", os.path.join(BASE_DIR, "build_config.py")], check=False)
        except Exception as e2:
            print(f"❌ Ошибка пересборки конфигурации: {e2}")
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

