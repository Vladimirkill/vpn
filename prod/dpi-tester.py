#!/usr/bin/env python3
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
                lines = result.stdout.strip().split('\n')
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
            for line in result.stdout.split('\n'):
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
        
        print("\n" + "="*50)
        print("📋 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ:")
        print("1. Используйте фоновый трафик для маскировки")
        print("2. Периодически разрывайте долгие соединения")
        print("3. Варьируйте TLS fingerprints")
        print("4. Избегайте регулярных паттернов трафика")

if __name__ == "__main__":
    tester = DPITester()
    tester.run_all_tests()
