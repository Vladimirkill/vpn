#!/usr/bin/env python3
"""
Модуль для управления отдельными серверами Xray для арендованных IP
Каждый арендованный IP получает свой сервер с отдельной конфигурацией
"""

import json
import os
import subprocess
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import shutil

logger = logging.getLogger(__name__)

class ServerManager:
    def __init__(self):
        self.servers_dir = "/var/www/vpn/servers"
        self.systemd_dir = "/etc/systemd/system"
        self.base_port = 20000  # Начальный порт для новых серверов
        
        # Создаем директории
        os.makedirs(self.servers_dir, exist_ok=True)
        os.makedirs(f"{self.servers_dir}/configs", exist_ok=True)
        os.makedirs(f"{self.servers_dir}/keys", exist_ok=True)
        
        self.servers_registry = f"{self.servers_dir}/servers_registry.json"
        self._init_registry()
    
    def _init_registry(self):
        """Инициализирует реестр серверов"""
        if not os.path.exists(self.servers_registry):
            registry = {
                "servers": {},
                "next_port": self.base_port,
                "created": datetime.now().isoformat()
            }
            with open(self.servers_registry, 'w') as f:
                json.dump(registry, f, indent=2)
    
    def _load_registry(self) -> Dict:
        """Загружает реестр серверов"""
        try:
            with open(self.servers_registry, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки реестра: {e}")
            return {"servers": {}, "next_port": self.base_port}
    
    def _save_registry(self, registry: Dict):
        """Сохраняет реестр серверов"""
        try:
            with open(self.servers_registry, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения реестра: {e}")
    
    def create_server(self, ip_address: str, user_id: int, location: str) -> Dict:
        """Создает новый сервер Xray для арендованного IP"""
        try:
            registry = self._load_registry()
            
            # Генерируем уникальный ID сервера
            server_id = f"xray_{ip_address.replace('.', '_')}"
            
            # Проверяем, не существует ли уже сервер для этого IP
            if server_id in registry["servers"]:
                return {
                    "success": False,
                    "error": f"Сервер для IP {ip_address} уже существует"
                }
            
            # Выделяем порт
            port = registry["next_port"]
            registry["next_port"] += 1
            
            # Создаем конфигурацию сервера
            server_config = self._create_server_config(ip_address, port, user_id, location)
            
            # Создаем ключи Reality
            reality_keys = self._generate_reality_keys()
            
            # Генерируем UUID для пользователя
            user_uuid = str(uuid.uuid4())
            
            # Создаем Xray конфигурацию
            xray_config = self._create_xray_config(
                port=port,
                bind_ip=ip_address,
                user_uuid=user_uuid,
                reality_keys=reality_keys
            )
            
            # Сохраняем конфигурацию
            config_path = f"{self.servers_dir}/configs/{server_id}.json"
            with open(config_path, 'w') as f:
                json.dump(xray_config, f, indent=2)
            
            # Создаем systemd сервис
            service_created = self._create_systemd_service(server_id, config_path)
            
            if not service_created:
                return {
                    "success": False,
                    "error": "Ошибка создания systemd сервиса"
                }
            
            # Запускаем сервер
            start_result = self._start_server(server_id)
            
            if not start_result:
                return {
                    "success": False,
                    "error": "Ошибка запуска сервера"
                }
            
            # Генерируем VLESS ключ для пользователя
            vless_key = self._generate_vless_key(
                ip_address=ip_address,
                port=port,
                user_uuid=user_uuid,
                reality_keys=reality_keys,
                user_id=user_id
            )
            
            # Сохраняем информацию о сервере в реестр
            server_info = {
                "server_id": server_id,
                "ip_address": ip_address,
                "port": port,
                "user_id": user_id,
                "user_uuid": user_uuid,
                "location": location,
                "created": datetime.now().isoformat(),
                "status": "active",
                "config_path": config_path,
                "vless_key": vless_key,
                "reality_keys": reality_keys
            }
            
            registry["servers"][server_id] = server_info
            self._save_registry(registry)
            
            logger.info(f"Создан сервер {server_id} для IP {ip_address}")
            
            return {
                "success": True,
                "server_id": server_id,
                "ip_address": ip_address,
                "port": port,
                "vless_key": vless_key,
                "user_uuid": user_uuid
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания сервера: {e}")
            return {
                "success": False,
                "error": f"Внутренняя ошибка: {e}"
            }
    
    def _create_server_config(self, ip_address: str, port: int, user_id: int, location: str) -> Dict:
        """Создает базовую конфигурацию сервера"""
        return {
            "ip_address": ip_address,
            "port": port,
            "user_id": user_id,
            "location": location,
            "created": datetime.now().isoformat()
        }
    
    def _generate_reality_keys(self) -> Dict:
        """Генерирует ключи Reality"""
        try:
            # Используем xray для генерации ключей
            result = subprocess.run(
                ["/usr/local/bin/xray", "x25519"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                private_key = lines[0].split(': ')[1]
                public_key = lines[1].split(': ')[1]
                
                # Генерируем short IDs
                short_ids = [
                    os.urandom(8).hex(),
                    os.urandom(8).hex()
                ]
                
                return {
                    "private_key": private_key,
                    "public_key": public_key,
                    "short_ids": short_ids
                }
            else:
                logger.error(f"Ошибка генерации ключей: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка генерации Reality ключей: {e}")
            return None
    
    def _create_xray_config(self, port: int, bind_ip: str, user_uuid: str, reality_keys: Dict) -> Dict:
        """Создает конфигурацию Xray для отдельного сервера"""
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": [
                {
                    "port": port,
                    "listen": bind_ip,
                    "protocol": "vless",
                    "settings": {
                        "clients": [
                            {
                                "id": user_uuid,
                                "flow": "xtls-rprx-vision"
                            }
                        ],
                        "decryption": "none"
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "tcpSettings": {
                            "header": {
                                "type": "none"
                            }
                        },
                        "realitySettings": {
                            "show": False,
                            "fingerprint": "safari",
                            "serverNames": [
                                "www.apple.com",
                                "www.icloud.com",
                                "itunes.apple.com"
                            ],
                            "shortIds": reality_keys["short_ids"],
                            "privateKey": reality_keys["private_key"],
                            "dest": "www.apple.com:443"
                        }
                    }
                }
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "tag": "direct",
                    "settings": {
                        "domainStrategy": "UseIP"
                    }
                },
                {
                    "protocol": "blackhole",
                    "tag": "block"
                }
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {
                        "type": "field",
                        "domain": ["geosite:category-ads-all"],
                        "outboundTag": "block"
                    }
                ]
            }
        }
        
        return config
    
    def _create_systemd_service(self, server_id: str, config_path: str) -> bool:
        """Создает systemd сервис для сервера"""
        try:
            service_content = f"""[Unit]
Description=Xray Server {server_id}
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/xray run -config {config_path}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
            
            service_path = f"{self.systemd_dir}/{server_id}.service"
            
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            # Перезагружаем systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            
            # Включаем сервис
            subprocess.run(["systemctl", "enable", server_id], check=True)
            
            logger.info(f"Создан systemd сервис: {service_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания systemd сервиса: {e}")
            return False
    
    def _start_server(self, server_id: str) -> bool:
        """Запускает сервер"""
        try:
            result = subprocess.run(
                ["systemctl", "start", server_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Сервер {server_id} запущен")
                return True
            else:
                logger.error(f"Ошибка запуска сервера {server_id}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка запуска сервера {server_id}: {e}")
            return False
    
    def _generate_vless_key(self, ip_address: str, port: int, user_uuid: str, reality_keys: Dict, user_id: int) -> str:
        """Генерирует VLESS ключ для пользователя"""
        try:
            # Формируем VLESS URL
            vless_url = (
                f"vless://{user_uuid}@{ip_address}:{port}"
                f"?type=tcp"
                f"&security=reality"
                f"&encryption=none"
                f"&flow=xtls-rprx-vision"
                f"&sni=www.apple.com"
                f"&fp=safari"
                f"&pbk={reality_keys['public_key']}"
                f"&sid={reality_keys['short_ids'][0]}"
                f"&spx=/"
                f"#VPNBot_Rented_{ip_address.replace('.', '_')}_User_{user_id}"
            )
            
            return vless_url
            
        except Exception as e:
            logger.error(f"Ошибка генерации VLESS ключа: {e}")
            return ""
    
    def stop_server(self, server_id: str) -> bool:
        """Останавливает сервер"""
        try:
            result = subprocess.run(
                ["systemctl", "stop", server_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Сервер {server_id} остановлен")
                return True
            else:
                logger.error(f"Ошибка остановки сервера {server_id}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка остановки сервера {server_id}: {e}")
            return False
    
    def remove_server(self, server_id: str) -> bool:
        """Полностью удаляет сервер"""
        try:
            registry = self._load_registry()
            
            if server_id not in registry["servers"]:
                logger.warning(f"Сервер {server_id} не найден в реестре")
                return False
            
            server_info = registry["servers"][server_id]
            
            # Останавливаем сервер
            self.stop_server(server_id)
            
            # Отключаем и удаляем systemd сервис
            subprocess.run(["systemctl", "disable", server_id], capture_output=True)
            
            service_path = f"{self.systemd_dir}/{server_id}.service"
            if os.path.exists(service_path):
                os.remove(service_path)
            
            # Удаляем конфигурацию
            config_path = server_info.get("config_path")
            if config_path and os.path.exists(config_path):
                os.remove(config_path)
            
            # Удаляем из реестра
            del registry["servers"][server_id]
            self._save_registry(registry)
            
            # Перезагружаем systemd
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
            
            logger.info(f"Сервер {server_id} полностью удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления сервера {server_id}: {e}")
            return False
    
    def get_server_info(self, server_id: str) -> Optional[Dict]:
        """Возвращает информацию о сервере"""
        registry = self._load_registry()
        return registry["servers"].get(server_id)
    
    def get_user_servers(self, user_id: int) -> List[Dict]:
        """Возвращает список серверов пользователя"""
        registry = self._load_registry()
        user_servers = []
        
        for server_id, server_info in registry["servers"].items():
            if server_info["user_id"] == user_id:
                user_servers.append(server_info)
        
        return user_servers
    
    def get_all_servers(self) -> Dict:
        """Возвращает информацию о всех серверах"""
        registry = self._load_registry()
        return registry["servers"]
    
    def get_server_status(self, server_id: str) -> str:
        """Проверяет статус сервера"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", server_id],
                capture_output=True,
                text=True
            )
            
            return result.stdout.strip()
            
        except Exception as e:
            logger.error(f"Ошибка проверки статуса сервера {server_id}: {e}")
            return "unknown"
    
    def restart_server(self, server_id: str) -> bool:
        """Перезапускает сервер"""
        try:
            result = subprocess.run(
                ["systemctl", "restart", server_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Сервер {server_id} перезапущен")
                return True
            else:
                logger.error(f"Ошибка перезапуска сервера {server_id}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка перезапуска сервера {server_id}: {e}")
            return False