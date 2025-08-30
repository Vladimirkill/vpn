#!/usr/bin/env python3
"""
Тест блокировки рекламы в Xray Reality VPN
"""

import json
import subprocess
import requests
import time

def check_xray_config():
    """Проверяет конфигурацию блокировки в Xray"""
    try:
        with open('/usr/local/etc/xray/config.json', 'r') as f:
            config = json.load(f)
        
        # Проверяем routing rules
        rules = config.get('routing', {}).get('rules', [])
        block_rules = [r for r in rules if r.get('outboundTag') == 'block']
        
        # Проверяем outbounds
        outbounds = config.get('outbounds', [])
        block_outbound = next((o for o in outbounds if o.get('tag') == 'block'), None)
        
        print("🔍 Анализ конфигурации блокировки:")
        print(f"   📋 Правил блокировки: {len(block_rules)}")
        
        if block_rules:
            rule = block_rules[0]
            if 'domain' in rule:
                if isinstance(rule['domain'], list) and rule['domain']:
                    first_domain = rule['domain'][0]
                    if first_domain.startswith('geosite:'):
                        print(f"   🌍 Используется geosite: {first_domain}")
                    else:
                        print(f"   📝 Доменные правила: {len(rule['domain'])} доменов")
        
        if block_outbound:
            protocol = block_outbound.get('protocol', 'unknown')
            print(f"   🚫 Block outbound: {protocol}")
            return True
        else:
            print("   ❌ Block outbound не найден!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации: {e}")
        return False

def test_known_ad_domains():
    """Тестирует известные рекламные домены"""
    ad_domains = [
        "googleads.g.doubleclick.net",
        "googlesyndication.com", 
        "googleadservices.com",
        "facebook.com/tr",
        "analytics.google.com"
    ]
    
    print("\n🧪 Тест известных рекламных доменов:")
    
    for domain in ad_domains:
        try:
            # Простой DNS lookup
            result = subprocess.run(['nslookup', domain], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   🟡 {domain}: DNS разрешается")
            else:
                print(f"   🔴 {domain}: DNS не разрешается")
        except:
            print(f"   ❓ {domain}: Ошибка проверки")

def check_geosite_data():
    """Проверяет наличие и актуальность geosite.dat"""
    import os
    from datetime import datetime
    
    geosite_path = "/usr/local/share/xray/geosite.dat"
    
    print("\n📊 Проверка geosite.dat:")
    
    if os.path.exists(geosite_path):
        stat = os.stat(geosite_path)
        size_mb = stat.st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        
        print(f"   ✅ Файл существует: {size_mb:.1f} MB")
        print(f"   📅 Обновлен: {mod_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Проверяем возраст файла
        age_days = (datetime.now() - mod_time).days
        if age_days > 7:
            print(f"   ⚠️ Файл устарел ({age_days} дней)")
        else:
            print(f"   ✅ Файл актуален ({age_days} дней)")
    else:
        print("   ❌ Файл geosite.dat не найден!")

def main():
    print("🛡️ ТЕСТ БЛОКИРОВКИ РЕКЛАМЫ В XRAY VPN")
    print("=" * 50)
    
    # 1. Проверяем конфигурацию
    config_ok = check_xray_config()
    
    # 2. Проверяем geosite данные  
    check_geosite_data()
    
    # 3. Тестируем домены
    test_known_ad_domains()
    
    print("\n" + "=" * 50)
    if config_ok:
        print("✅ Блокировка рекламы настроена и должна работать")
        print("💡 Для полной проверки подключитесь через VPN клиент")
    else:
        print("❌ Проблемы с конфигурацией блокировки")

if __name__ == "__main__":
    main()