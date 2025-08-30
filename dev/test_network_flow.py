#!/usr/bin/env python3
"""
Визуализация сетевого потока VPN трафика
Показывает детальную схему прохождения пакетов
"""

import subprocess
import json
import time
from datetime import datetime

class NetworkFlowVisualizer:
    def __init__(self):
        self.server_ip = "146.103.125.210"
        
    def show_network_topology(self):
        """Показывает сетевую топологию"""
        print("🌐 СЕТЕВАЯ ТОПОЛОГИЯ VPN СИСТЕМЫ")
        print("="*60)
        print("""
    Интернет
        │
        ▼
    ┌─────────────────────────────────────┐
    │     146.103.125.210:443             │
    │     (Nginx Stream)                  │
    │                                     │
    │  ┌─────────────────────────────────┐│
    │  │ SNI Analysis                    ││
    │  │ if (sni == "www.cloudflare.com")││
    │  └─────────────────────────────────┘│
    └─────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
    ┌─────────┐         ┌─────────┐
    │Xray:8443│         │Nginx:8444│
    │(VPN)    │         │(Website) │
    └─────────┘         └─────────┘
        │
        ▼
    ┌─────────────────┐
    │ REALITY Check   │
    │ Short ID Valid? │
    └─────────────────┘
        │
    ┌───┴───┐
    ▼       ▼
┌─────┐ ┌─────────────┐
│ VPN │ │ Redirect to │
│     │ │ Cloudflare  │
└─────┘ └─────────────┘
        """)
    
    def show_packet_flow(self):
        """Показывает поток пакетов"""
        print("\n📦 ПОТОК ПАКЕТОВ ЧЕРЕЗ СИСТЕМУ")
        print("="*60)
        
        steps = [
            ("1", "TCP SYN", "Клиент → 146.103.125.210:443", "Установка соединения"),
            ("2", "TLS Hello", "SNI: www.cloudflare.com", "Nginx читает SNI"),
            ("3", "Routing", "Nginx → 127.0.0.1:8443", "Перенаправление на Xray"),
            ("4", "REALITY", "Анализ Short ID", "Проверка валидности"),
            ("5", "Decision", "Valid → VPN / Invalid → Cloudflare", "Принятие решения"),
            ("6", "Tunnel", "VLESS + XTLS-RPRX-Vision", "Установка VPN туннеля")
        ]
        
        for step, packet_type, route, description in steps:
            print(f"   {step}️⃣ {packet_type:12} │ {route:25} │ {description}")
        
        print("\n" + "="*60)
    
    def monitor_connections(self):
        """Мониторит активные соединения"""
        print("\n🔍 МОНИТОРИНГ АКТИВНЫХ СОЕДИНЕНИЙ")
        print("="*60)
        
        try:
            # Проверяем соединения на порту 443
            result = subprocess.run(
                ['netstat', '-an'], 
                capture_output=True, text=True, timeout=10
            )
            
            connections_443 = []
            for line in result.stdout.split('\n'):
                if ':443 ' in line and 'LISTEN' not in line:
                    connections_443.append(line.strip())
            
            if connections_443:
                print("   📊 Активные соединения на порту 443:")
                for conn in connections_443[:5]:  # Показываем первые 5
                    print(f"      {conn}")
            else:
                print("   📊 Нет активных соединений на порту 443")
                
        except Exception as e:
            print(f"   ❌ Ошибка мониторинга: {e}")
    
    def show_traffic_statistics(self):
        """Показывает статистику трафика"""
        print("\n📈 СТАТИСТИКА ТРАФИКА")
        print("="*60)
        
        try:
            # Статистика по портам
            ports_info = {
                443: "Основной порт (Nginx Stream)",
                8443: "Xray VPN сервер", 
                8444: "Nginx веб-сайт"
            }
            
            for port, description in ports_info.items():
                result = subprocess.run(
                    ['netstat', '-an'], 
                    capture_output=True, text=True, timeout=5
                )
                
                listening = f":{port} " in result.stdout and "LISTEN" in result.stdout
                status = "🟢 Слушает" if listening else "🔴 Не слушает"
                print(f"   Порт {port:4} │ {status:12} │ {description}")
                
        except Exception as e:
            print(f"   ❌ Ошибка получения статистики: {e}")
    
    def simulate_real_traffic(self):
        """Симулирует реальный трафик"""
        print("\n🚀 СИМУЛЯЦИЯ РЕАЛЬНОГО ТРАФИКА")
        print("="*60)
        
        scenarios = [
            {
                "name": "VPN Клиент (правильный ключ)",
                "sni": "www.cloudflare.com",
                "short_id": "ddc322f2",
                "result": "✅ VPN туннель установлен",
                "path": "Nginx:443 → Xray:8443 → VPN"
            },
            {
                "name": "Обычный браузер на Cloudflare", 
                "sni": "www.cloudflare.com",
                "short_id": "отсутствует",
                "result": "🔄 Перенаправление на настоящий Cloudflare",
                "path": "Nginx:443 → Xray:8443 → www.cloudflare.com:443"
            },
            {
                "name": "Посетитель нашего сайта",
                "sni": "v452799.hosted-by-vdsina.com", 
                "short_id": "не применимо",
                "result": "🌐 Корпоративный веб-сайт",
                "path": "Nginx:443 → Nginx:8444 → TechCorp Site"
            },
            {
                "name": "Сканер портов",
                "sni": "неизвестный домен",
                "short_id": "не применимо", 
                "result": "🌐 Корпоративный веб-сайт (маскировка)",
                "path": "Nginx:443 → Nginx:8444 → TechCorp Site"
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n   📋 Сценарий {i}: {scenario['name']}")
            print(f"      SNI: {scenario['sni']}")
            print(f"      Short ID: {scenario['short_id']}")
            print(f"      Путь: {scenario['path']}")
            print(f"      Результат: {scenario['result']}")
    
    def show_security_analysis(self):
        """Показывает анализ безопасности"""
        print("\n🛡️ АНАЛИЗ БЕЗОПАСНОСТИ")
        print("="*60)
        
        security_features = [
            ("SNI Маскировка", "✅", "VPN трафик маскируется под Cloudflare"),
            ("REALITY Перенаправления", "✅", "Неправильные клиенты → настоящий Cloudflare"),
            ("Корпоративная маскировка", "✅", "Сервер выглядит как IT-компания"),
            ("SSL/TLS шифрование", "✅", "Весь трафик зашифрован"),
            ("Порт 443", "✅", "Стандартный HTTPS порт"),
            ("DPI устойчивость", "✅", "Неотличим от обычного HTTPS"),
            ("Скрытие Xray", "✅", "Сканеры видят только nginx")
        ]
        
        for feature, status, description in security_features:
            print(f"   {status} {feature:25} │ {description}")
    
    def run_visualization(self):
        """Запускает полную визуализацию"""
        print("🎯 ВИЗУАЛИЗАЦИЯ СЕТЕВОГО ПОТОКА VPN")
        print("="*70)
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Показываем топологию
        self.show_network_topology()
        
        # Показываем поток пакетов
        self.show_packet_flow()
        
        # Мониторим соединения
        self.monitor_connections()
        
        # Статистика трафика
        self.show_traffic_statistics()
        
        # Симулируем трафик
        self.simulate_real_traffic()
        
        # Анализ безопасности
        self.show_security_analysis()
        
        print("\n" + "="*70)
        print("🎉 ЗАКЛЮЧЕНИЕ:")
        print("🔄 Трафик проходит через многоуровневую систему маскировки")
        print("🛡️ REALITY обеспечивает автоматическое перенаправление")
        print("🎭 Nginx обеспечивает SNI маршрутизацию и корпоративную маскировку")
        print("✅ VPN полностью скрыт от обнаружения")

def main():
    """Главная функция"""
    visualizer = NetworkFlowVisualizer()
    visualizer.run_visualization()

if __name__ == "__main__":
    main()