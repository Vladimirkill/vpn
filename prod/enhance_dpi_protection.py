#!/usr/bin/env python3
"""
Улучшение защиты от DPI
Добавляет дополнительные меры маскировки VPN трафика
"""

import json
import random
import time
import subprocess
from pathlib import Path

class DPIProtectionEnhancer:
    def __init__(self):
        self.xray_config_path = "/var/www/vpn/xray/final_config.json"
        
    def add_traffic_obfuscation(self):
        """Добавляет обфускацию трафика в Xray"""
        print("🔧 Улучшение защиты от DPI в Xray...")
        
        try:
            with open(self.xray_config_path, 'r') as f:
                config = json.load(f)
            
            # Добавляем дополнительные домены для маскировки
            reality_settings = config['inbounds'][0]['streamSettings']['realitySettings']
            
            # Расширяем список доменов
            additional_domains = [
                "www.cloudflare.com",
                "cdnjs.cloudflare.com", 
                "ajax.cloudflare.com",
                "api.cloudflare.com"
            ]
            
            reality_settings['serverNames'] = additional_domains
            
            # Добавляем случайные fingerprints
            fingerprints = ["chrome", "firefox", "safari", "edge", "random"]
            reality_settings['fingerprint'] = random.choice(fingerprints)
            
            # Сохраняем конфигурацию
            with open(self.xray_config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            print("   ✅ Добавлены дополнительные домены для маскировки")
            print("   ✅ Настроены случайные TLS fingerprints")
            
        except Exception as e:
            print(f"   ❌ Ошибка обновления конфигурации: {e}")
    
    def create_traffic_mixer(self):
        """Создает скрипт для генерации фонового трафика"""
        print("🌐 Создание генератора фонового трафика...")
        
        script_content = '''#!/bin/bash
# Генератор фонового веб-трафика для маскировки VPN
# Имитирует обычную активность пользователя

DOMAINS=(
    "www.google.com"
    "www.youtube.com" 
    "www.github.com"
    "www.stackoverflow.com"
    "www.wikipedia.org"
    "www.reddit.com"
    "news.ycombinator.com"
    "www.cloudflare.com"
)

USER_AGENTS=(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
)

generate_background_traffic() {
    while true; do
        # Случайная пауза между запросами (1-30 минут)
        sleep $((RANDOM % 1800 + 60))
        
        # Выбираем случайный домен и User-Agent
        domain=${DOMAINS[$RANDOM % ${#DOMAINS[@]}]}
        ua=${USER_AGENTS[$RANDOM % ${#USER_AGENTS[@]}]}
        
        # Делаем несколько запросов для имитации браузера
        for i in {1..3}; do
            curl -s -A "$ua" -H "Accept: text/html,application/xhtml+xml" \\
                 -H "Accept-Language: en-US,en;q=0.9" \\
                 -H "Cache-Control: no-cache" \\
                 --connect-timeout 10 --max-time 30 \\
                 "https://$domain/" > /dev/null 2>&1
            
            # Пауза между запросами в сессии
            sleep $((RANDOM % 5 + 1))
        done
        
        echo "$(date): Generated background traffic to $domain"
    done
}

# Запуск в фоне
if [ "$1" = "start" ]; then
    echo "Запуск генератора фонового трафика..."
    generate_background_traffic &
    echo $! > /var/run/traffic-mixer.pid
    echo "PID: $(cat /var/run/traffic-mixer.pid)"
elif [ "$1" = "stop" ]; then
    if [ -f /var/run/traffic-mixer.pid ]; then
        kill $(cat /var/run/traffic-mixer.pid) 2>/dev/null
        rm /var/run/traffic-mixer.pid
        echo "Генератор фонового трафика остановлен"
    fi
elif [ "$1" = "status" ]; then
    if [ -f /var/run/traffic-mixer.pid ] && kill -0 $(cat /var/run/traffic-mixer.pid) 2>/dev/null; then
        echo "Генератор работает (PID: $(cat /var/run/traffic-mixer.pid))"
    else
        echo "Генератор не запущен"
    fi
else
    echo "Использование: $0 {start|stop|status}"
fi
'''
        
        with open('/var/www/vpn/traffic-mixer.sh', 'w') as f:
            f.write(script_content)
        
        subprocess.run(['chmod', '+x', '/var/www/vpn/traffic-mixer.sh'])
        print("   ✅ Создан скрипт генерации фонового трафика")
        print("   📝 Использование: ./traffic-mixer.sh {start|stop|status}")
    
    def create_connection_randomizer(self):
        """Создает скрипт для рандомизации соединений"""
        print("🔀 Создание рандомизатора соединений...")
        
        script_content = '''#!/usr/bin/env python3
"""
Рандомизатор TCP соединений
Периодически разрывает и пересоздает соединения для маскировки
"""

import time
import random
import subprocess
import psutil

def get_xray_connections():
    """Получает список соединений Xray"""
    connections = []
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'xray':
                proc_obj = psutil.Process(proc.info['pid'])
                connections.extend(proc_obj.connections())
    except:
        pass
    return connections

def randomize_connections():
    """Периодически сбрасывает долгоживущие соединения"""
    print("🔀 Запуск рандомизатора соединений...")
    
    while True:
        try:
            # Пауза 30-120 минут
            sleep_time = random.randint(1800, 7200)
            print(f"⏰ Следующая проверка через {sleep_time//60} минут")
            time.sleep(sleep_time)
            
            connections = get_xray_connections()
            long_lived = [c for c in connections if hasattr(c, 'create_time') 
                         and time.time() - c.create_time > 3600]  # > 1 час
            
            if long_lived:
                print(f"🔄 Найдено {len(long_lived)} долгоживущих соединений")
                
                # Сбрасываем случайные соединения (не все сразу)
                to_reset = random.sample(long_lived, min(3, len(long_lived)))
                
                for conn in to_reset:
                    try:
                        # Мягкий сброс через iptables (временный блок)
                        subprocess.run([
                            'iptables', '-I', 'OUTPUT', '-p', 'tcp',
                            '--dport', str(conn.raddr.port),
                            '-d', conn.raddr.ip, '-j', 'DROP'
                        ], timeout=5)
                        
                        time.sleep(5)  # Ждем сброса
                        
                        # Убираем блок
                        subprocess.run([
                            'iptables', '-D', 'OUTPUT', '-p', 'tcp', 
                            '--dport', str(conn.raddr.port),
                            '-d', conn.raddr.ip, '-j', 'DROP'
                        ], timeout=5)
                        
                        print(f"   ✅ Сброшено соединение {conn.raddr.ip}:{conn.raddr.port}")
                        
                    except Exception as e:
                        print(f"   ⚠️ Ошибка сброса соединения: {e}")
                        
        except KeyboardInterrupt:
            print("\\n🛑 Остановка рандомизатора...")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(300)  # Пауза при ошибке

if __name__ == "__main__":
    randomize_connections()
'''
        
        with open('/var/www/vpn/connection-randomizer.py', 'w') as f:
            f.write(script_content)
        
        subprocess.run(['chmod', '+x', '/var/www/vpn/connection-randomizer.py'])
        print("   ✅ Создан рандомизатор соединений")
    
    def create_dpi_test_script(self):
        """Создает скрипт для тестирования защиты от DPI"""
        print("🧪 Создание тестера защиты от DPI...")
        
        script_content = '''#!/usr/bin/env python3
"""
Тестер защиты от DPI
Анализирует трафик на предмет DPI-детектируемых паттернов
"""

import subprocess
import time
import statistics
from collections import defaultdict

class DPITester:
    def __init__(self):
        self.server_ip = "146.103.125.210"
        
    def test_tls_fingerprint(self):
        """Тестирует TLS fingerprint"""
        print("🔍 Тест TLS fingerprint...")
        
        # Несколько подключений для анализа вариативности
        fingerprints = []
        for i in range(5):
            try:
                result = subprocess.run([
                    'openssl', 's_client', '-connect', f'{self.server_ip}:443',
                    '-servername', 'www.cloudflare.com', '-brief'
                ], input='', text=True, capture_output=True, timeout=10)
                
                if 'Verification error' in result.stderr or 'Verify return code' in result.stderr:
                    fingerprints.append("varied")
                    
            except:
                pass
                
        if len(set(fingerprints)) > 1:
            print("   ✅ TLS fingerprints варьируются")
        else:
            print("   ⚠️ TLS fingerprints могут быть предсказуемыми")
    
    def test_packet_timing(self):
        """Анализирует временные паттерны пакетов"""
        print("🕐 Тест временных паттернов...")
        
        try:
            # Захватываем трафик на короткое время
            result = subprocess.run([
                'timeout', '30', 'tcpdump', '-i', 'any', '-c', '100',
                f'host {self.server_ip} and port 443', '-tt'
            ], capture_output=True, text=True)
            
            if result.stdout:
                lines = result.stdout.strip().split('\\n')
                timestamps = []
                
                for line in lines:
                    if self.server_ip in line:
                        parts = line.split()
                        if len(parts) > 0:
                            try:
                                ts = float(parts[0])
                                timestamps.append(ts)
                            except:
                                pass
                
                if len(timestamps) > 10:
                    intervals = [timestamps[i+1] - timestamps[i] 
                               for i in range(len(timestamps)-1)]
                    
                    avg_interval = statistics.mean(intervals)
                    std_interval = statistics.stdev(intervals)
                    
                    # Проверяем на слишком регулярные интервалы
                    regularity = std_interval / avg_interval if avg_interval > 0 else 0
                    
                    if regularity > 0.5:
                        print("   ✅ Временные паттерны нерегулярные")
                    else:
                        print("   ⚠️ Слишком регулярные временные паттерны")
                else:
                    print("   ℹ️ Недостаточно данных для анализа")
            else:
                print("   ℹ️ Нет трафика для анализа")
                
        except Exception as e:
            print(f"   ❌ Ошибка анализа: {e}")
    
    def test_connection_behavior(self):
        """Анализирует поведение соединений"""
        print("🔗 Тест поведения соединений...")
        
        try:
            result = subprocess.run([
                'netstat', '-tn'
            ], capture_output=True, text=True)
            
            connections = []
            for line in result.stdout.split('\\n'):
                if self.server_ip in line and ':443' in line:
                    connections.append(line)
            
            if connections:
                print(f"   📊 Активных соединений: {len(connections)}")
                
                # Проверяем на слишком много долгоживущих соединений
                if len(connections) > 10:
                    print("   ⚠️ Много одновременных соединений (подозрительно)")
                else:
                    print("   ✅ Нормальное количество соединений")
            else:
                print("   ℹ️ Нет активных соединений")
                
        except Exception as e:
            print(f"   ❌ Ошибка анализа: {e}")
    
    def run_all_tests(self):
        """Запускает все тесты DPI защиты"""
        print("🛡️ ТЕСТИРОВАНИЕ ЗАЩИТЫ ОТ DPI")
        print("="*50)
        
        self.test_tls_fingerprint()
        self.test_packet_timing()
        self.test_connection_behavior()
        
        print("\\n" + "="*50)
        print("📋 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ:")
        print("1. Используйте фоновый трафик для маскировки")
        print("2. Периодически разрывайте долгие соединения")
        print("3. Варьируйте TLS fingerprints")
        print("4. Избегайте регулярных паттернов трафика")

if __name__ == "__main__":
    tester = DPITester()
    tester.run_all_tests()
'''
        
        with open('/var/www/vpn/dpi-tester.py', 'w') as f:
            f.write(script_content)
        
        subprocess.run(['chmod', '+x', '/var/www/vpn/dpi-tester.py'])
        print("   ✅ Создан тестер защиты от DPI")
    
    def enhance_protection(self):
        """Применяет все улучшения защиты от DPI"""
        print("🛡️ УЛУЧШЕНИЕ ЗАЩИТЫ ОТ DPI")
        print("="*50)
        
        self.add_traffic_obfuscation()
        self.create_traffic_mixer()
        self.create_connection_randomizer()
        self.create_dpi_test_script()
        
        print("\n" + "="*50)
        print("✅ Все улучшения применены!")
        print("\n📋 Следующие шаги:")
        print("1. Перезапустите Xray: systemctl restart xray")
        print("2. Запустите фоновый трафик: ./traffic-mixer.sh start")
        print("3. Протестируйте защиту: python3 dpi-tester.py")

def main():
    enhancer = DPIProtectionEnhancer()
    enhancer.enhance_protection()

if __name__ == "__main__":
    main()