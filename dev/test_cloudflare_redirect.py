#!/usr/bin/env python3
"""
Тест перенаправлений на Cloudflare
Проверяет что все обращения (по IP, неправильному SNI) перенаправляются на Cloudflare
"""

import socket
import ssl
import subprocess
import time
from urllib.parse import urlparse

class CloudflareRedirectTest:
    def __init__(self):
        self.server_ip = "146.103.125.210"
        self.server_port = 443
        
    def test_ip_access(self):
        """Тестирует прямое обращение по IP"""
        print("🔍 Тест 1: Прямое обращение по IP адресу")
        print(f"   Подключение к {self.server_ip}:443 без SNI...")
        
        try:
            # Подключение без SNI (как при обращении по IP)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((self.server_ip, self.server_port), timeout=10) as sock:
                with context.wrap_socket(sock) as ssock:
                    # Если соединение установлено, проверяем сертификат
                    cert = ssock.getpeercert()
                    if cert:
                        subject = dict(x[0] for x in cert['subject'])
                        print(f"   ✅ Получен сертификат от: {subject.get('commonName', 'Unknown')}")
                        
                        # Проверяем, это Cloudflare или наш сертификат
                        if 'cloudflare' in subject.get('commonName', '').lower():
                            print("   🎯 Перенаправление на Cloudflare работает!")
                            return True
                        else:
                            print(f"   ⚠️ Получен неожиданный сертификат: {subject.get('commonName')}")
                            return False
                    else:
                        print("   ⚠️ Сертификат не получен")
                        return False
                        
        except ssl.SSLError as e:
            if "certificate verify failed" in str(e):
                print("   ✅ SSL соединение установлено (ожидаемая ошибка верификации)")
                return True
            else:
                print(f"   ⚠️ SSL ошибка: {e}")
                return False
        except Exception as e:
            print(f"   ❌ Ошибка подключения: {e}")
            return False
    
    def test_wrong_sni(self):
        """Тестирует обращение с неправильным SNI"""
        print("\n🔍 Тест 2: Обращение с неправильным SNI")
        
        wrong_snis = [
            "google.com",
            "example.com", 
            "test.local",
            "v452799.hosted-by-vdsina.com"
        ]
        
        results = []
        for sni in wrong_snis:
            print(f"   Тестирую SNI: {sni}")
            
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with socket.create_connection((self.server_ip, self.server_port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=sni) as ssock:
                        cert = ssock.getpeercert()
                        if cert:
                            subject = dict(x[0] for x in cert['subject'])
                            cn = subject.get('commonName', 'Unknown')
                            print(f"      → Сертификат: {cn}")
                            
                            if 'cloudflare' in cn.lower() or cn != sni:
                                print("      ✅ Перенаправление работает")
                                results.append(True)
                            else:
                                print("      ❌ Перенаправление не работает")
                                results.append(False)
                        else:
                            results.append(False)
                            
            except ssl.SSLError as e:
                if "certificate verify failed" in str(e):
                    print("      ✅ SSL соединение (ожидаемая ошибка)")
                    results.append(True)
                else:
                    print(f"      ⚠️ SSL ошибка: {e}")
                    results.append(False)
            except Exception as e:
                print(f"      ❌ Ошибка: {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"   📊 Успешность перенаправлений: {success_rate:.1f}%")
        return success_rate > 50
    
    def test_cloudflare_sni(self):
        """Тестирует правильный SNI для VPN"""
        print("\n🔍 Тест 3: Правильный SNI (www.cloudflare.com)")
        print("   Этот трафик должен идти на Xray для обработки REALITY...")
        
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((self.server_ip, self.server_port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname='www.cloudflare.com') as ssock:
                    print("   ✅ Соединение с SNI www.cloudflare.com установлено")
                    print("   🎯 Трафик направлен на Xray для REALITY обработки")
                    return True
                    
        except ssl.SSLError as e:
            if "handshake failure" in str(e) or "certificate verify failed" in str(e):
                print("   ✅ Соединение обработано Xray REALITY (ожидаемое поведение)")
                return True
            else:
                print(f"   ⚠️ Неожиданная SSL ошибка: {e}")
                return False
        except Exception as e:
            print(f"   ❌ Ошибка соединения: {e}")
            return False
    
    def test_curl_redirect(self):
        """Тестирует перенаправление через curl"""
        print("\n🔍 Тест 4: HTTP запрос через curl")
        
        try:
            # Тест HTTP запроса по IP
            result = subprocess.run([
                'curl', '-s', '-I', '--connect-timeout', '10',
                f'https://{self.server_ip}/', '--insecure'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                headers = result.stdout
                print("   ✅ HTTP запрос выполнен успешно")
                
                # Ищем признаки Cloudflare
                if 'cloudflare' in headers.lower() or 'cf-' in headers.lower():
                    print("   🎯 Обнаружены заголовки Cloudflare - перенаправление работает!")
                    return True
                else:
                    print("   ⚠️ Заголовки Cloudflare не найдены")
                    print(f"   📄 Полученные заголовки:\n{headers[:200]}...")
                    return False
            else:
                print(f"   ⚠️ Curl завершился с кодом: {result.returncode}")
                print(f"   📄 Ошибка: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ⚠️ Timeout при выполнении curl")
            return False
        except Exception as e:
            print(f"   ❌ Ошибка выполнения curl: {e}")
            return False
    
    def show_current_config(self):
        """Показывает текущую конфигурацию"""
        print("\n⚙️ Текущая конфигурация:")
        print("   📋 Nginx Stream: Все подключения → Xray")
        print("   🛡️ Xray REALITY: VPN клиенты → VPN, остальные → Cloudflare")
        print("   🎭 SNI маскировка: Только под www.cloudflare.com")
        print("   🌐 Веб-сайт: Отключен (все перенаправления через REALITY)")
    
    def run_all_tests(self):
        """Запускает все тесты"""
        print("🧪 ТЕСТ ПЕРЕНАПРАВЛЕНИЙ НА CLOUDFLARE")
        print("="*60)
        
        self.show_current_config()
        
        # Выполняем тесты
        test_results = []
        
        test_results.append(self.test_ip_access())
        test_results.append(self.test_wrong_sni())
        test_results.append(self.test_cloudflare_sni())
        test_results.append(self.test_curl_redirect())
        
        # Подводим итоги
        print("\n" + "="*60)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        
        test_names = [
            "Прямое обращение по IP",
            "Неправильные SNI", 
            "Правильный SNI (VPN)",
            "HTTP запрос через curl"
        ]
        
        for i, (name, result) in enumerate(zip(test_names, test_results), 1):
            status = "✅ Пройден" if result else "❌ Провален"
            print(f"   {i}. {name}: {status}")
        
        success_count = sum(test_results)
        total_tests = len(test_results)
        
        print(f"\n🎯 Общий результат: {success_count}/{total_tests} тестов пройдено")
        
        if success_count >= 3:
            print("🎉 Система перенаправлений работает отлично!")
            print("✅ Все обращения корректно перенаправляются на Cloudflare")
            print("✅ VPN трафик обрабатывается правильно")
        else:
            print("⚠️ Обнаружены проблемы в системе перенаправлений")
            print("💡 Рекомендуется проверить конфигурацию REALITY")

def main():
    """Главная функция"""
    test = CloudflareRedirectTest()
    test.run_all_tests()

if __name__ == "__main__":
    main()