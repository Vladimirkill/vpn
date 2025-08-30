#!/usr/bin/env python3
"""
Менеджер групповых inbound'ов для Xray
Создает отдельные inbound'ы для групп пользователей (10-20 на группу)
"""

import json
import subprocess
import uuid as uuid_lib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from config import GENERATION_PATHS, PYTHON_EXECUTABLE, PROJECT_ROOT
from db.models import session, User, VpnKey

logger = logging.getLogger(__name__)

class GroupInboundManager:
    def __init__(self, users_per_group: int = 15, base_port: int = 20000):
        """
        Инициализация менеджера групповых inbound'ов
        
        Args:
            users_per_group: Количество пользователей в одной группе (по умолчанию 15)
            base_port: Базовый порт для групп (20000, 20001, 20002...)
        """
        self.users_per_group = users_per_group
        self.base_port = base_port
        self.config_path = f"{PROJECT_ROOT}/xray/final_config.json"
        
    def get_user_group_id(self, user_id: int) -> int:
        """Определяет ID группы для пользователя"""
        return (user_id % 1000) // self.users_per_group  # Группы 0-66 для 1000 пользователей
    
    def get_group_port(self, group_id: int) -> int:
        """Получает порт для группы"""
        return self.base_port + group_id
    
    def get_group_tag(self, group_id: int) -> str:
        """Получает тег для группы"""
        return f"group_{group_id}"
    
    def load_current_config(self) -> dict:
        """Загружает текущую конфигурацию Xray"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфига: {e}")
            return None
    
    def save_config(self, config: dict) -> bool:
        """Сохраняет конфигурацию Xray"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения конфига: {e}")
            return False
    
    def create_group_inbound(self, group_id: int) -> dict:
        """Создает конфигурацию inbound для группы"""
        
        group_port = self.get_group_port(group_id)
        group_tag = self.get_group_tag(group_id)
        
        inbound_config = {
            "tag": group_tag,
            "listen": "0.0.0.0",
            "port": group_port,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "tcpSettings": {
                    "header": {"type": "none"}
                },
                "realitySettings": {
                    "show": False,
                    "dest": "itunes.apple.com:443",
                    "xver": 0,
                    "serverNames": ["www.apple.com", "itunes.apple.com"],
                    "privateKey": "kJMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ",
                    "minClientVer": "1.8.0",
                    "maxTimeDiff": 30000,
                    "shortIds": ["60e35ba6", "3c6f96ff"],
                    "fingerprint": "safari"
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls", "quic"]
            }
        }
        
        return inbound_config
    
    def ensure_group_exists(self, group_id: int) -> bool:
        """Убеждается что группа существует в конфигурации"""
        
        config = self.load_current_config()
        if not config:
            return False
        
        group_tag = self.get_group_tag(group_id)
        
        # Проверяем есть ли уже такая группа
        for inbound in config.get("inbounds", []):
            if inbound.get("tag") == group_tag:
                logger.info(f"Группа {group_id} уже существует")
                return True
        
        # Создаем новую группу
        group_inbound = self.create_group_inbound(group_id)
        config["inbounds"].append(group_inbound)
        
        # Добавляем routing rule для группы
        if "routing" not in config:
            config["routing"] = {"rules": []}
        
        # Добавляем правило роутинга для новой группы
        group_rule = {
            "type": "field",
            "inboundTag": [group_tag],
            "outboundTag": "direct"
        }
        
        # Вставляем правило перед последним (обычно это default rule)
        if config["routing"]["rules"]:
            config["routing"]["rules"].insert(-1, group_rule)
        else:
            config["routing"]["rules"].append(group_rule)
        
        # Сохраняем конфигурацию
        if self.save_config(config):
            logger.info(f"✅ Группа {group_id} создана (порт {self.get_group_port(group_id)})")
            return True
        else:
            logger.error(f"❌ Не удалось создать группу {group_id}")
            return False
    
    def add_user_to_group(self, user_id: int, username: str) -> Tuple[bool, str, Optional[str]]:
        """
        Добавляет пользователя в соответствующую группу
        
        Returns:
            Tuple[bool, str, Optional[str]]: (success, message, vless_url)
        """
        
        try:
            # Определяем группу пользователя
            group_id = self.get_user_group_id(user_id)
            
            # Убеждаемся что группа существует
            if not self.ensure_group_exists(group_id):
                return False, f"Не удалось создать группу {group_id}", None
            
            # Генерируем UUID для пользователя
            user_uuid = str(uuid_lib.uuid4())
            
            # Загружаем конфиг
            config = self.load_current_config()
            if not config:
                return False, "Не удалось загрузить конфигурацию", None
            
            # Находим нужную группу и добавляем клиента
            group_tag = self.get_group_tag(group_id)
            group_found = False
            
            for inbound in config["inbounds"]:
                if inbound.get("tag") == group_tag:
                    # Проверяем не превышен ли лимит группы
                    current_clients = len(inbound["settings"]["clients"])
                    if current_clients >= self.users_per_group:
                        return False, f"Группа {group_id} переполнена ({current_clients}/{self.users_per_group})", None
                    
                    # Добавляем клиента
                    new_client = {
                        "id": user_uuid,
                        "flow": "xtls-rprx-vision",
                        "level": 0,
                        "email": f"{username}_{user_id}"
                    }
                    
                    inbound["settings"]["clients"].append(new_client)
                    group_found = True
                    break
            
            if not group_found:
                return False, f"Группа {group_tag} не найдена", None
            
            # Сохраняем конфигурацию
            if not self.save_config(config):
                return False, "Не удалось сохранить конфигурацию", None
            
            # Перезагружаем только эту группу (без полного перезапуска Xray)
            success = self.reload_xray_config()
            
            if success:
                # Генерируем VLESS URL
                vless_url = self.generate_vless_url(user_uuid, username, group_id)
                
                # Сохраняем в базу данных
                self.save_to_database(user_id, user_uuid, vless_url)
                
                logger.info(f"✅ Пользователь {username} добавлен в группу {group_id}")
                return True, f"Пользователь добавлен в группу {group_id}", vless_url
            else:
                return False, "Не удалось перезагрузить конфигурацию", None
                
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            return False, f"Ошибка: {str(e)}", None
    
    def remove_user_from_group(self, user_id: int) -> bool:
        """Удаляет пользователя из группы"""
        
        try:
            group_id = self.get_user_group_id(user_id)
            group_tag = self.get_group_tag(group_id)
            
            config = self.load_current_config()
            if not config:
                return False
            
            # Получаем информацию о пользователе из базы
            db_user = session.query(User).filter_by(tg_id=user_id).first()
            if not db_user:
                return False
                
            vpn_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
            if not vpn_key:
                return False
            
            user_email = f"{db_user.username or f'user_{user_id}'}_{user_id}"
            
            # Находим группу и удаляем клиента
            for inbound in config["inbounds"]:
                if inbound.get("tag") == group_tag:
                    clients = inbound["settings"]["clients"]
                    
                    # Ищем клиента по email или UUID
                    for i, client in enumerate(clients):
                        if (client.get("email") == user_email or 
                            client.get("id") == vpn_key.uuid):
                            
                            clients.pop(i)
                            logger.info(f"🗑️ Пользователь {user_email} удален из группы {group_id}")
                            break
                    break
            
            # Сохраняем конфигурацию
            if self.save_config(config):
                # Удаляем из базы данных
                session.delete(vpn_key)
                session.commit()
                
                # Перезагружаем конфигурацию
                self.reload_xray_config()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя: {e}")
            session.rollback()
            return False
    
    def get_group_stats(self, group_id: int) -> Dict:
        """Получает статистику группы"""
        
        try:
            config = self.load_current_config()
            if not config:
                return {}
            
            group_tag = self.get_group_tag(group_id)
            
            for inbound in config["inbounds"]:
                if inbound.get("tag") == group_tag:
                    clients = inbound["settings"]["clients"]
                    return {
                        "group_id": group_id,
                        "port": self.get_group_port(group_id),
                        "tag": group_tag,
                        "users_count": len(clients),
                        "max_users": self.users_per_group,
                        "usage_percent": (len(clients) / self.users_per_group) * 100,
                        "available_slots": self.users_per_group - len(clients)
                    }
            
            return {"group_id": group_id, "exists": False}
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики группы: {e}")
            return {}
    
    def get_all_groups_stats(self) -> List[Dict]:
        """Получает статистику всех групп"""
        
        config = self.load_current_config()
        if not config:
            return []
        
        groups = []
        for inbound in config.get("inbounds", []):
            tag = inbound.get("tag", "")
            if tag.startswith("group_"):
                try:
                    group_id = int(tag.replace("group_", ""))
                    stats = self.get_group_stats(group_id)
                    if stats:
                        groups.append(stats)
                except:
                    continue
        
        return sorted(groups, key=lambda x: x.get("group_id", 0))
    
    def generate_vless_url(self, user_uuid: str, username: str, group_id: int) -> str:
        """Генерирует VLESS URL для пользователя"""
        
        # Внешний порт всегда 443 (через Nginx), но можем добавить группу в комментарий
        vless_url = (
            f"vless://{user_uuid}@146.103.125.210:443"
            f"?security=reality"
            f"&sni=www.apple.com"
            f"&fp=safari"
            f"&pbk=kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ"
            f"&sid=60e35ba6"
            f"&spx=/"
            f"&type=tcp"
            f"&flow=xtls-rprx-vision"
            f"&encryption=none"
            f"#{username}_group{group_id}"
        )
        
        return vless_url
    
    def save_to_database(self, user_id: int, user_uuid: str, vless_url: str):
        """Сохраняет ключ в базу данных"""
        
        try:
            db_user = session.query(User).filter_by(tg_id=user_id).first()
            if not db_user:
                logger.error(f"Пользователь {user_id} не найден в базе")
                return
            
            # Проверяем есть ли уже ключ
            existing_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
            if existing_key:
                # Обновляем существующий
                existing_key.uuid = user_uuid
                existing_key.vpn_link = vless_url
            else:
                # Создаем новый
                new_key = VpnKey(
                    user_id=db_user.id,
                    uuid=user_uuid,
                    vpn_link=vless_url,
                    created_at=datetime.now()
                )
                session.add(new_key)
            
            session.commit()
            logger.info(f"💾 Ключ сохранен в базу для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в базу: {e}")
            session.rollback()
    
    def reload_xray_config(self) -> bool:
        """Перезагружает конфигурацию Xray"""
        
        try:
            # Используем reload вместо restart для минимизации downtime
            result = subprocess.run([
                '/usr/bin/systemctl', 'reload', 'xray'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("✅ Xray конфигурация перезагружена")
                return True
            else:
                # Если reload не поддерживается, используем restart
                logger.warning("Reload не поддерживается, используем restart")
                result = subprocess.run([
                    '/usr/bin/systemctl', 'restart', 'xray'
                ], capture_output=True, text=True, timeout=15)
                
                return result.returncode == 0
                
        except Exception as e:
            logger.error(f"Ошибка перезагрузки Xray: {e}")
            return False
    
    def find_available_group(self) -> Optional[int]:
        """Находит группу с доступными слотами"""
        
        all_groups = self.get_all_groups_stats()
        
        # Ищем группу с свободными местами
        for group in all_groups:
            if group.get("available_slots", 0) > 0:
                return group["group_id"]
        
        # Если свободных групп нет, создаем новую
        max_group_id = max([g.get("group_id", -1) for g in all_groups], default=-1)
        return max_group_id + 1
    
    def create_user_key(self, user_id: int, username: str) -> Tuple[bool, str, Optional[str]]:
        """
        Создает ключ для пользователя в подходящей группе
        
        Returns:
            Tuple[bool, str, Optional[str]]: (success, message, vless_url)
        """
        
        # Проверяем есть ли уже ключ у пользователя
        db_user = session.query(User).filter_by(tg_id=user_id).first()
        if db_user:
            existing_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
            if existing_key and existing_key.vpn_link:
                return True, "Ключ уже существует", existing_key.vpn_link
        
        # Определяем группу пользователя
        user_group_id = self.get_user_group_id(user_id)
        
        # Проверяем доступность группы
        group_stats = self.get_group_stats(user_group_id)
        if group_stats.get("available_slots", 0) <= 0:
            # Группа переполнена, ищем другую
            available_group = self.find_available_group()
            if available_group is not None:
                user_group_id = available_group
                logger.info(f"Пользователь {user_id} перенаправлен в группу {user_group_id}")
        
        # Добавляем пользователя в группу
        return self.add_user_to_group(user_id, username)
    
    def setup_nginx_routing(self) -> bool:
        """Настраивает Nginx для роутинга групп"""
        
        try:
            # Создаем конфиг Nginx для групповой маршрутизации
            nginx_config = """
# Групповая маршрутизация для Xray inbound'ов
# Nginx проксирует 443 -> группы по SNI

map $ssl_preread_server_name $group_backend {
    ~^group(\d+)\..*$ 127.0.0.1:2000$1;  # group0.domain -> 20000, group1.domain -> 20001
    default 127.0.0.1:10443;              # Основной inbound
}

server {
    listen 443;
    listen [::]:443;
    proxy_pass $group_backend;
    ssl_preread on;
}
"""
            
            with open("/etc/nginx/conf.d/xray-groups.conf", "w") as f:
                f.write(nginx_config)
            
            # Перезагружаем Nginx
            result = subprocess.run([
                '/usr/bin/systemctl', 'reload', 'nginx'
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Ошибка настройки Nginx: {e}")
            return False

# Глобальный экземпляр
group_manager = GroupInboundManager(users_per_group=15, base_port=20000)