#!/usr/bin/env python3
"""
Мониторинг изменений в директории клиентов Xray
Автоматически перезапускает Xray при появлении новых клиентов
"""

import os
import time
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import hashlib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/xray-monitor.log'),
        logging.StreamHandler()
    ]
)

class XrayClientMonitor:
    def __init__(self):
        self.clients_dir = "/var/www/vpn/xray/clients"
        self.config_file = "/var/www/vpn/xray/final_config.json"
        self.safe_restart_script = "/var/www/vpn/xray/safe_restart.py"
        self.build_script = "/var/www/vpn/xray/build_config.py"
        
        # Хеши файлов для отслеживания изменений
        self.file_hashes = {}
        self.last_config_hash = None
        
        # Флаг для предотвращения множественных перезапусков
        self.restart_in_progress = False
        
        logging.info("🚀 Xray Client Monitor запущен")
        logging.info(f"📁 Мониторинг директории: {self.clients_dir}")
        
    def get_file_hash(self, filepath: str) -> str:
        """Вычисляет MD5 хеш файла"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logging.error(f"❌ Ошибка вычисления хеша {filepath}: {e}")
            return ""
    
    def scan_clients_directory(self) -> dict:
        """Сканирует директорию клиентов и возвращает хеши файлов"""
        file_hashes = {}
        
        if not os.path.exists(self.clients_dir):
            logging.warning(f"⚠️ Директория клиентов не существует: {self.clients_dir}")
            return file_hashes
        
        try:
            for filename in os.listdir(self.clients_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.clients_dir, filename)
                    file_hashes[filepath] = self.get_file_hash(filepath)
        except Exception as e:
            logging.error(f"❌ Ошибка сканирования директории: {e}")
        
        return file_hashes
    
    def check_config_changes(self) -> bool:
        """Проверяет изменения в конфигурации клиентов"""
        current_hashes = self.scan_clients_directory()
        
        # Проверяем новые файлы
        new_files = []
        modified_files = []
        removed_files = []
        
        for filepath, current_hash in current_hashes.items():
            if filepath not in self.file_hashes:
                new_files.append(filepath)
                logging.info(f"🆕 Новый клиент обнаружен: {os.path.basename(filepath)}")
            elif self.file_hashes[filepath] != current_hash:
                modified_files.append(filepath)
                logging.info(f"📝 Клиент изменен: {os.path.basename(filepath)}")
        
        # Проверяем удаленные файлы
        for filepath in self.file_hashes:
            if filepath not in current_hashes:
                removed_files.append(filepath)
                logging.info(f"🗑️ Клиент удален: {os.path.basename(filepath)}")
        
        # Обновляем хеши
        self.file_hashes = current_hashes
        
        # Возвращаем True если есть изменения
        return bool(new_files or modified_files or removed_files)
    
    def rebuild_config(self) -> bool:
        """Пересобирает конфигурацию Xray"""
        try:
            logging.info("🔧 Пересборка конфигурации Xray...")
            
            result = subprocess.run(
                ["python3", self.build_script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logging.info("✅ Конфигурация успешно пересобрана")
                return True
            else:
                logging.error(f"❌ Ошибка пересборки конфигурации: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("⏰ Timeout при пересборке конфигурации")
            return False
        except Exception as e:
            logging.error(f"❌ Ошибка пересборки: {e}")
            return False
    
    def safe_restart_xray(self) -> bool:
        """Безопасно перезапускает Xray"""
        if self.restart_in_progress:
            logging.warning("⚠️ Перезапуск уже выполняется, пропускаем")
            return False
        
        self.restart_in_progress = True
        
        try:
            logging.info("🔄 Безопасный перезапуск Xray...")
            
            if os.path.exists(self.safe_restart_script):
                result = subprocess.run(
                    ["python3", self.safe_restart_script, "restart"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    logging.info("✅ Xray успешно перезапущен")
                    return True
                else:
                    logging.error(f"❌ Ошибка безопасного перезапуска: {result.stderr}")
                    # Fallback на обычный restart
                    return self.fallback_restart_xray()
            else:
                logging.warning("⚠️ Скрипт безопасного перезапуска не найден, используем fallback")
                return self.fallback_restart_xray()
                
        except subprocess.TimeoutExpired:
            logging.error("⏰ Timeout при безопасном перезапуске")
            return self.fallback_restart_xray()
        except Exception as e:
            logging.error(f"❌ Ошибка безопасного перезапуска: {e}")
            return self.fallback_restart_xray()
        finally:
            self.restart_in_progress = False
    
    def fallback_restart_xray(self) -> bool:
        """Fallback перезапуск Xray через systemctl"""
        try:
            logging.info("🔄 Fallback перезапуск Xray через systemctl...")
            
            result = subprocess.run(
                ["systemctl", "restart", "xray"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logging.info("✅ Xray перезапущен через systemctl")
                return True
            else:
                logging.error(f"❌ Ошибка fallback перезапуска: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("⏰ Timeout при fallback перезапуске")
            return False
        except Exception as e:
            logging.error(f"❌ Ошибка fallback перезапуска: {e}")
            return False
    
    def check_xray_status(self) -> bool:
        """Проверяет статус Xray"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "xray"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.stdout.strip() == "active"
        except Exception as e:
            logging.error(f"❌ Ошибка проверки статуса Xray: {e}")
            return False
    
    def process_changes(self):
        """Обрабатывает изменения в конфигурации"""
        try:
            # Проверяем изменения
            if not self.check_config_changes():
                return
            
            logging.info("🔄 Обнаружены изменения в конфигурации клиентов")
            
            # Пересобираем конфигурацию
            if not self.rebuild_config():
                logging.error("❌ Не удалось пересобрать конфигурацию")
                return
            
            # Проверяем статус Xray
            if not self.check_xray_status():
                logging.warning("⚠️ Xray не активен, запускаем...")
                subprocess.run(["systemctl", "start", "xray"], capture_output=True)
                time.sleep(5)  # Ждем запуска
            
            # Перезапускаем Xray
            if self.safe_restart_xray():
                logging.info("🎉 Обработка изменений завершена успешно")
            else:
                logging.error("❌ Не удалось перезапустить Xray")
                
        except Exception as e:
            logging.error(f"❌ Ошибка обработки изменений: {e}")
    
    def run(self):
        """Основной цикл мониторинга"""
        logging.info("🚀 Запуск мониторинга...")
        
        # Инициализация - сканируем текущее состояние
        self.file_hashes = self.scan_clients_directory()
        logging.info(f"📊 Найдено {len(self.file_hashes)} клиентов")
        
        while True:
            try:
                # Обрабатываем изменения
                self.process_changes()
                
                # Ждем перед следующей проверкой
                time.sleep(5)
                
            except KeyboardInterrupt:
                logging.info("🛑 Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logging.error(f"❌ Критическая ошибка в цикле мониторинга: {e}")
                time.sleep(10)  # Ждем дольше при ошибке

def main():
    """Главная функция"""
    monitor = XrayClientMonitor()
    monitor.run()

if __name__ == "__main__":
    main() 