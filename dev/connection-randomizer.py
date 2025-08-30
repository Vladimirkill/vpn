#!/usr/bin/env python3
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
            print("\n🛑 Остановка рандомизатора...")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(300)  # Пауза при ошибке

if __name__ == "__main__":
    randomize_connections()
