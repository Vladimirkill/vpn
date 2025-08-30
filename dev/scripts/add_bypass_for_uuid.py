#!/usr/bin/env python3
import sys
import os

sys.path.append('/var/www/vpn')
sys.path.append('/var/www/vpn/vpn_bot')

from vpn_bot.db.models import session, VpnKey, BypassSite, VpnBypassRule


def add_bypass(uuid: str, domains: list[str]) -> None:
    key = session.query(VpnKey).filter_by(uuid=uuid).first()
    if not key:
        print(f"❌ VpnKey с UUID {uuid} не найден")
        sys.exit(1)

    created_sites = 0
    created_rules = 0

    for domain in domains:
        d = domain.strip().lower()
        if not d:
            continue

        site = session.query(BypassSite).filter_by(domain=d).first()
        if not site:
            site = BypassSite(domain=d, name=d, category="custom", is_verified=True)
            session.add(site)
            session.flush()
            created_sites += 1

        # Проверяем, нет ли уже правила
        existing = session.query(VpnBypassRule).filter_by(vpn_key_id=key.id, bypass_site_id=site.id).first()
        if not existing:
            rule = VpnBypassRule(vpn_key_id=key.id, bypass_site_id=site.id)
            session.add(rule)
            created_rules += 1

    session.commit()
    print(f"✅ Сайтов добавлено: {created_sites}, правил исключений создано: {created_rules}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: add_bypass_for_uuid.py <UUID> <domain1> [domain2 ...]")
        sys.exit(1)
    uuid = sys.argv[1]
    domains = sys.argv[2:]
    add_bypass(uuid, domains)

