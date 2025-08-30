#!/usr/bin/env python3
"""
🔧 Тестирование VPN ключей на работоспособность
Проверяет подключение и функциональность созданных ключей
"""

import json
import os
import sys
import subprocess
import time
import requests
from pathlib import Path
import tempfile
import socket
from urllib.parse import urlparse

# Добавляем путь к проекту
sys.path.append('/var/www/vpn')
from manage_user_limits import get_user_keys, CLIENTS_DIR

class VPNKeyTester:
    def __init__(self):
        self.clients_dir = Path(CLIENTS_DIR)
        self.test_results = {}
        
    def get_external_ip(self, timeout=10):
        """Получает внешний IP адрес"""
        try:
            response = requests.get('https://httpbin.org/ip', timeout=timeout)
            return response.json().get('origin', 'Unknown')
        except Exception as e:
            try:
                # Альтернативный сервис
                response = requests.get('https://api.ipify.org?format=json', timeout=timeout)
                return response.json().get('ip', 'Unknown')
            except:
                return f"Error: {str(e)}"

    def test_port_connectivity(self, host, port, timeout=5):
        """Тестирует подключение к порту"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            return False

    def parse_vless_url(self, vless_url):
        """Парсит VLESS URL и извлекает параметры подключения"""
        try:
            if not vless_url.startswith('vless://'):
                return None
                
            # Убираем префикс vless://
            url_part = vless_url[8:]
            
            # Разделяем на части
            if '@' not in url_part:
                return None
                
            uuid_part, rest = url_part.split('@', 1)
            
            if '?' not in rest:
                host_port = rest
                params = {}
            else:
                host_port, query = rest.split('?', 1)
                # Парсим параметры
                params = {}
                for param in query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
            
            if ':' in host_port:
                host, port = host_port.split(':', 1)
                port = int(port)
            else:
                host = host_port
                port = 443  # По умолчанию для VLESS
                
            return {
                'uuid': uuid_part,
                'host': host,
                'port': port,
                'params': params
            }
        except Exception as e:
            return None

    def test_key_connectivity(self, client_name, key_data):
        """Тестирует подключение конкретного ключа"""
        print(f"\n🔍 Тестирование ключа для {client_name}")
        print("=" * 60)
        
        results = {
            'client_name': client_name,
            'key_id': key_data.get('id', 'Unknown'),
            'tests': {}
        }
        
        # 1. Проверяем наличие конфигурации
        vless_url = key_data.get('vless_url')
        if not vless_url:
            results['tests']['config_exists'] = {
                'status': 'FAIL',
                'message': 'VLESS URL не найден в конфигурации'
            }
            print("❌ VLESS URL не найден")
            return results
        
        results['tests']['config_exists'] = {
            'status': 'PASS',
            'message': 'Конфигурация найдена'
        }
        print("✅ Конфигурация найдена")
        
        # 2. Парсим параметры подключения
        connection_params = self.parse_vless_url(vless_url)
        if not connection_params:
            results['tests']['url_parsing'] = {
                'status': 'FAIL',
                'message': 'Не удалось распарсить VLESS URL'
            }
            print("❌ Не удалось распарсить VLESS URL")
            return results
            
        results['tests']['url_parsing'] = {
            'status': 'PASS',
            'message': f"URL распарсен: {connection_params['host']}:{connection_params['port']}"
        }
        print(f"✅ URL распарсен: {connection_params['host']}:{connection_params['port']}")
        
        # 3. Тестируем подключение к серверу
        host = connection_params['host']
        port = connection_params['port']
        
        print(f"🔌 Тестирование подключения к {host}:{port}...")
        is_reachable = self.test_port_connectivity(host, port)
        
        if is_reachable:
            results['tests']['server_reachable'] = {
                'status': 'PASS',
                'message': f'Сервер {host}:{port} доступен'
            }
            print(f"✅ Сервер {host}:{port} доступен")
        else:
            results['tests']['server_reachable'] = {
                'status': 'FAIL',
                'message': f'Сервер {host}:{port} недоступен'
            }
            print(f"❌ Сервер {host}:{port} недоступен")
        
        # 4. Проверяем метаданные ключа
        metadata = key_data.get('metadata', {})
        max_connections = metadata.get('max_connections', 'не задано')
        max_devices = metadata.get('max_devices', 'не задано')
        
        results['tests']['metadata'] = {
            'status': 'PASS',
            'message': f'Лимиты: {max_connections} соединений, {max_devices} устройств'
        }
        print(f"📊 Лимиты: {max_connections} соединений, {max_devices} устройств")
        
        # 5. Проверяем активные подключения (если доступно)
        active_connections = key_data.get('active_connections', 0)
        results['tests']['active_connections'] = {
            'status': 'INFO',
            'message': f'Активных подключений: {active_connections}'
        }
        print(f"🔗 Активных подключений: {active_connections}")
        
        return results

    def test_xray_service(self):
        """Проверяет статус сервиса Xray"""
        print("\n🚀 Проверка сервиса Xray")
        print("=" * 40)
        
        try:
            # Проверяем статус systemd сервиса
            result = subprocess.run(['systemctl', 'is-active', 'xray'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip() == 'active':
                print("✅ Сервис Xray активен")
                return True
            else:
                print("❌ Сервис Xray неактивен")
                
                # Пробуем получить статус
                status_result = subprocess.run(['systemctl', 'status', 'xray'], 
                                             capture_output=True, text=True)
                print(f"📋 Статус: {status_result.stdout}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки Xray: {str(e)}")
            return False

    def test_xray_config(self):
        """Проверяет конфигурацию Xray"""
        print("\n⚙️ Проверка конфигурации Xray")
        print("=" * 40)
        
        config_paths = [
            '/usr/local/etc/xray/config.json',
            '/etc/xray/config.json',
            '/var/www/vpn/xray/config.json'
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                print(f"✅ Найден конфиг: {config_path}")
                
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Проверяем основные секции
                    if 'inbounds' in config:
                        inbounds_count = len(config['inbounds'])
                        print(f"📥 Входящих подключений: {inbounds_count}")
                        
                        for i, inbound in enumerate(config['inbounds']):
                            port = inbound.get('port', 'не указан')
                            protocol = inbound.get('protocol', 'не указан')
                            print(f"   {i+1}. Протокол: {protocol}, Порт: {port}")
                    
                    if 'outbounds' in config:
                        outbounds_count = len(config['outbounds'])
                        print(f"📤 Исходящих подключений: {outbounds_count}")
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ Ошибка чтения конфига: {str(e)}")
                    return False
        
        print("❌ Конфигурация Xray не найдена")
        return False

    def run_comprehensive_test(self):
        """Запускает полное тестирование"""
        print("🧪 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ VPN КЛЮЧЕЙ")
        print("=" * 60)
        
        # Получаем текущий IP
        print("🌐 Проверка текущего IP адреса...")
        current_ip = self.get_external_ip()
        print(f"📍 Текущий IP: {current_ip}")
        
        # Проверяем Xray сервис
        xray_running = self.test_xray_service()
        
        # Проверяем конфигурацию
        config_valid = self.test_xray_config()
        
        # Получаем всех пользователей
        print(f"\n👥 Получение списка пользователей...")
        users = get_user_keys()
        
        if not users:
            print("❌ Пользователи не найдены")
            return
        
        print(f"✅ Найдено пользователей: {len(users)}")
        
        # Тестируем каждого пользователя
        all_results = []
        
        for client_name, keys in users.items():
            print(f"\n👤 Пользователь: {client_name}")
            print(f"🔑 Количество ключей: {len(keys)}")
            
            for i, key_data in enumerate(keys, 1):
                print(f"\n🔍 Тестирование ключа #{i}")
                result = self.test_key_connectivity(client_name, key_data)
                all_results.append(result)
        
        # Выводим итоговый отчет
        self.print_summary_report(all_results, xray_running, config_valid, current_ip)
        
        return all_results

    def print_summary_report(self, results, xray_running, config_valid, current_ip):
        """Выводит итоговый отчет"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        print(f"🌐 Текущий IP сервера: {current_ip}")
        print(f"🚀 Сервис Xray: {'✅ Работает' if xray_running else '❌ Не работает'}")
        print(f"⚙️ Конфигурация Xray: {'✅ Валидна' if config_valid else '❌ Проблемы'}")
        
        print(f"\n🔑 Протестировано ключей: {len(results)}")
        
        # Статистика по тестам
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for result in results:
            for test_name, test_result in result['tests'].items():
                total_tests += 1
                if test_result['status'] == 'PASS':
                    passed_tests += 1
                elif test_result['status'] == 'FAIL':
                    failed_tests += 1
        
        print(f"📈 Статистика тестов:")
        print(f"   ✅ Пройдено: {passed_tests}")
        print(f"   ❌ Провалено: {failed_tests}")
        print(f"   📊 Всего: {total_tests}")
        
        # Детали по каждому ключу
        print(f"\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        print("-" * 80)
        
        for result in results:
            client_name = result['client_name']
            key_id = result['key_id']
            
            print(f"\n👤 {client_name} (Ключ: {key_id})")
            
            for test_name, test_result in result['tests'].items():
                status_icon = {
                    'PASS': '✅',
                    'FAIL': '❌',
                    'INFO': 'ℹ️'
                }.get(test_result['status'], '❓')
                
                print(f"   {status_icon} {test_name}: {test_result['message']}")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        print("-" * 40)
        
        if not xray_running:
            print("🔧 Запустите сервис Xray: sudo systemctl start xray")
        
        if not config_valid:
            print("🔧 Проверьте конфигурацию Xray")
        
        if failed_tests > 0:
            print("🔧 Есть проблемы с подключением к серверу")
            print("   - Проверьте файрвол")
            print("   - Проверьте DNS настройки")
            print("   - Проверьте сетевое подключение")
        
        if passed_tests == total_tests and xray_running and config_valid:
            print("🎉 Все тесты пройдены! VPN работает корректно!")

def main():
    """Главная функция"""
    if os.geteuid() != 0:
        print("⚠️ Рекомендуется запускать от root для полного доступа к системе")
    
    tester = VPNKeyTester()
    
    try:
        results = tester.run_comprehensive_test()
        
        # Сохраняем результаты в файл
        timestamp = int(time.time())
        results_file = f"/var/www/vpn/test_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'results': results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Результаты сохранены в: {results_file}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()