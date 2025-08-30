#!/usr/bin/env python3
"""
Скрипт для включения gRPC API в конфигурации Xray
Позволяет динамически добавлять/удалять пользователей без перезапуска
"""

import json
import os
import shutil

CONFIG_PATH = "/var/www/vpn/xray/final_config.json"
SYSTEM_CONFIG_PATH = "/usr/local/etc/xray/config.json"

def enable_xray_api():
    """Включает gRPC API в конфигурации Xray"""
    try:
        # Читаем текущую конфигурацию
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Добавляем API конфигурацию
        config["api"] = {
            "tag": "api",
            "listen": "127.0.0.1:8080",
            "services": ["HandlerService", "LoggerService", "StatsService"]
        }
        
        # Добавляем inbound для API
        api_inbound = {
            "listen": "127.0.0.1",
            "port": 10085,
            "protocol": "dokodemo-door",
            "settings": {
                "address": "127.0.0.1"
            },
            "tag": "api"
        }
        
        # Проверяем, не добавлен ли уже API inbound
        api_exists = any(inbound.get("tag") == "api" for inbound in config.get("inbounds", []))
        if not api_exists:
            config["inbounds"].append(api_inbound)
        
        # Добавляем routing rules для API
        if "routing" not in config:
            config["routing"] = {"domainStrategy": "IPIfNonMatch", "rules": []}
        
        # Проверяем, не добавлено ли уже правило для API
        api_rule_exists = any(
            rule.get("inboundTag") == ["api"] 
            for rule in config["routing"].get("rules", [])
        )
        
        if not api_rule_exists:
            api_rule = {
                "inboundTag": ["api"],
                "outboundTag": "api",
                "type": "field"
            }
            config["routing"]["rules"].insert(0, api_rule)
        
        # Сохраняем обновленную конфигурацию
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Не копируем, так как это симлинк
        # shutil.copy(CONFIG_PATH, SYSTEM_CONFIG_PATH)
        
        print("✅ API успешно включен в конфигурации Xray")
        print("🔧 Перезапустите Xray: systemctl restart xray")
        print("🌐 API доступен на: 127.0.0.1:8080")
        print("📡 Management port: 10085")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка включения API: {e}")
        return False

if __name__ == "__main__":
    enable_xray_api()