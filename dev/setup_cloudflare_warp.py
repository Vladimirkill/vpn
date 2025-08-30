#!/usr/bin/env python3
"""
Скрипт для настройки Cloudflare WARP как дополнительного IP
"""

import subprocess
import json
import os
import sys
from vpn_bot.utils.ip_manager import IPManager

def install_warp():
    """Устанавливает Cloudflare WARP"""
    print("📦 Установка Cloudflare WARP...")
    
    try:
        # Добавляем репозиторий Cloudflare
        commands = [
            "curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg",
            'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflare-client.list',
            "apt update",
            "apt install -y cloudflare-warp"
        ]
        
        for cmd in commands:
            print(f"Выполняю: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Ошибка: {result.stderr}")
                return False
        
        print("✅ Cloudflare WARP установлен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка установки WARP: {e}")
        return False

def configure_warp():
    """Настраивает WARP"""
    print("⚙️ Настройка WARP...")
    
    try:
        # Регистрируем WARP
        result = subprocess.run(["warp-cli", "register"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ Регистрация: {result.stderr}")
        
        # Устанавливаем режим прокси
        result = subprocess.run(["warp-cli", "set-mode", "proxy"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Ошибка настройки прокси режима: {result.stderr}")
            return False
        
        # Подключаемся
        result = subprocess.run(["warp-cli", "connect"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Ошибка подключения: {result.stderr}")
            return False
        
        print("✅ WARP настроен и подключен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настройки WARP: {e}")
        return False

def check_warp_status():
    """Проверяет статус WARP"""
    try:
        result = subprocess.run(["warp-cli", "status"], capture_output=True, text=True)
        print(f"📊 Статус WARP: {result.stdout}")
        return "Connected" in result.stdout
    except Exception as e:
        print(f"❌ Ошибка проверки статуса: {e}")
        return False

def add_warp_to_ip_manager():
    """Добавляет WARP в IP Manager"""
    print("🔧 Добавление WARP в систему IP...")
    
    try:
        ip_manager = IPManager()
        
        # Конфигурация WARP сервера
        warp_config = {
            "id": "cloudflare_warp",
            "name": "🌐 Cloudflare WARP (США)",
            "country": "US",
            "type": "socks",
            "address": "127.0.0.1",
            "port": 40000,
            "description": "Cloudflare WARP прокси для смены IP"
        }
        
        # Проверяем, не добавлен ли уже
        servers = ip_manager.get_available_servers()
        if any(s['id'] == 'cloudflare_warp' for s in servers):
            print("ℹ️ WARP уже добавлен в систему")
            return True
        
        # Добавляем сервер
        success = ip_manager.add_server(warp_config)
        if success:
            print("✅ WARP добавлен в систему IP")
            return True
        else:
            print("❌ Ошибка добавления WARP")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка добавления в IP Manager: {e}")
        return False

def add_additional_servers():
    """Добавляет дополнительные IP серверы"""
    print("🌍 Добавление дополнительных IP серверов...")
    
    try:
        ip_manager = IPManager()
        
        # Дополнительные серверы (примеры)
        additional_servers = [
            {
                "id": "netherlands",
                "name": "🇳🇱 Нидерланды",
                "country": "NL", 
                "type": "direct",
                "description": "Прямое подключение (IP сервера)"
            },
            {
                "id": "germany", 
                "name": "🇩🇪 Германия",
                "country": "DE",
                "type": "direct", 
                "description": "Прямое подключение (IP сервера)"
            }
        ]
        
        for server in additional_servers:
            servers = ip_manager.get_available_servers()
            if not any(s['id'] == server['id'] for s in servers):
                ip_manager.add_server(server)
                print(f"✅ Добавлен: {server['name']}")
            else:
                print(f"ℹ️ Уже существует: {server['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка добавления серверов: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 НАСТРОЙКА СИСТЕМЫ СМЕНЫ IP")
    print("=" * 50)
    
    # Проверяем права root
    if os.geteuid() != 0:
        print("❌ Скрипт должен запускаться от root")
        sys.exit(1)
    
    # 1. Устанавливаем WARP
    if not install_warp():
        print("❌ Не удалось установить WARP")
        return
    
    # 2. Настраиваем WARP
    if not configure_warp():
        print("❌ Не удалось настроить WARP")
        return
    
    # 3. Проверяем статус
    if not check_warp_status():
        print("⚠️ WARP не подключен, но продолжаем...")
    
    # 4. Добавляем в IP Manager
    if not add_warp_to_ip_manager():
        print("❌ Не удалось добавить WARP в систему")
        return
    
    # 5. Добавляем дополнительные серверы
    add_additional_servers()
    
    print("\n" + "=" * 50)
    print("✅ Система смены IP настроена!")
    print("\n📋 Доступные функции:")
    print("   • /ip - меню смены IP в боте")
    print("   • 🌍 Смена IP - кнопка в VPN меню")
    print("   • Cloudflare WARP для США IP")
    print("   • Прямые подключения")
    
    print("\n💡 Для использования:")
    print("   1. Перезапустите VPN бота")
    print("   2. Откройте VPN меню")
    print("   3. Нажмите '🌍 Смена IP'")
    print("   4. Выберите нужный IP")

if __name__ == "__main__":
    main()