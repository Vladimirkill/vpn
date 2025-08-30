#!/usr/bin/env python3
"""
Модуль для генерации routing rules на основе исключений (bypass) из базы данных
"""

import sys
import os
import json

# Добавляем путь к модулям VPN бота
sys.path.append('/var/www/vpn')
sys.path.append('/var/www/vpn/vpn_bot')

try:
    from vpn_bot.db.models import session, VpnKey, VpnBypassRule, BypassSite, User
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    sys.exit(1)

def get_bypass_domains_for_user(user_tg_id):
    """Получает список доменов исключений для пользователя по Telegram ID"""
    try:
        user = session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            return []
        
        vpn_key = session.query(VpnKey).filter_by(user_id=user.id).first()
        if not vpn_key:
            return []
        
        # Получаем все исключения для ключа пользователя
        bypass_rules = session.query(VpnBypassRule, BypassSite).join(BypassSite).filter(
            VpnBypassRule.vpn_key_id == vpn_key.id
        ).all()
        
        domains = []
        for rule, site in bypass_rules:
            if site.is_verified:  # Только верифицированные домены
                # Нормализуем под формат Xray: domain:example.com
                domain_value = site.domain.strip()
                if not domain_value:
                    continue
                if not (domain_value.startswith("domain:") or domain_value.startswith("regexp:") or domain_value.startswith("keyword:")):
                    domain_value = f"domain:{domain_value}"
                domains.append(domain_value)
        
        return domains
    except Exception as e:
        print(f"❌ Ошибка получения доменов: {e}")
        return []

def generate_routing_rules():
    """Генерирует индивидуальные routing rules для каждого пользователя"""
    try:
        routing_rules = []
        
        # Получаем всех пользователей с VPN ключами
        users_with_keys = session.query(User, VpnKey).join(VpnKey).all()
        
        users_with_bypasses = []
        users_without_bypasses = []
        
        for user, vpn_key in users_with_keys:
            if not vpn_key.uuid:
                continue
                
            # Получаем исключения для этого пользователя
            bypass_rules = session.query(VpnBypassRule, BypassSite).join(BypassSite).filter(
                VpnBypassRule.vpn_key_id == vpn_key.id,
                BypassSite.is_verified == True
            ).all()
            
            if bypass_rules:
                # Пользователь с исключениями
                domains = []
                for rule, site in bypass_rules:
                    value = site.domain.strip()
                    if not value:
                        continue
                    if not (value.startswith("domain:") or value.startswith("regexp:") or value.startswith("keyword:")):
                        value = f"domain:{value}"
                    domains.append(value)
                
                # Правило 1: исключения идут напрямую (без VPN)
                # Таргетируем правило на конкретного клиента через поле user (совпадает с email клиента)
                bypass_rule = {
                    "type": "field",
                    "outboundTag": "direct",
                    "domain": domains,
                    "user": [vpn_key.uuid]
                }
                routing_rules.append(bypass_rule)
                users_with_bypasses.append(vpn_key.uuid)
                
                print(f"✅ {user.tg_id}: {len(domains)} исключений → direct")
            else:
                # Пользователь без исключений - весь трафик через VPN
                users_without_bypasses.append(vpn_key.uuid)
                print(f"✅ {user.tg_id}: все через VPN")
        
        # ВАЖНО: В VLESS конфигурации VPN работает по умолчанию
        # Исключения (direct) переопределяют поведение для конкретных доменов
        # Все остальное автоматически идет через VPN
        
        print(f"\\n📊 ИТОГО:")
        print(f"   👥 Пользователей с исключениями: {len(users_with_bypasses)}")
        print(f"   👥 Пользователей без исключений: {len(users_without_bypasses)}")
        print(f"   📋 Создано правил исключений: {len([r for r in routing_rules if 'domain' in r])}")
        print(f"\\n💡 Логика маршрутизации:")
        print(f"   🔀 Домены в исключениях → direct (без VPN)")
        print(f"   🔒 Все остальное → через VPN (по умолчанию)")
        
        return {
            "domainStrategy": "IPIfNonMatch",
            "rules": routing_rules
        }
        
    except Exception as e:
        print(f"❌ Ошибка генерации routing rules: {e}")
        return {"domainStrategy": "IPIfNonMatch", "rules": []}

def update_xray_config_with_routing():
    """Обновляет конфигурацию Xray, добавляя routing rules"""
    try:
        config_path = "/var/www/vpn/xray/final_config.json"
        
        # Читаем текущую конфигурацию
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Генерируем routing rules
        routing = generate_routing_rules()
        
        # Добавляем routing в конфигурацию
        config["routing"] = routing
        
        # Сохраняем обновленную конфигурацию
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Копируем в системную папку Xray
        import shutil
        shutil.copy(config_path, "/usr/local/etc/xray/config.json")
        
        print("✅ Конфигурация Xray обновлена с routing rules")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления конфигурации: {e}")
        return False

if __name__ == "__main__":
    print("🔧 ГЕНЕРАЦИЯ ROUTING RULES ДЛЯ ИСКЛЮЧЕНИЙ")
    print("=" * 50)
    
    # Обновляем конфигурацию
    success = update_xray_config_with_routing()
    
    if success:
        print("\n💡 Для применения изменений выполните:")
        print("   systemctl reload xray")
    else:
        print("\n❌ Ошибка генерации routing rules")