#!/usr/bin/env python3
"""
Модуль управления IP-адресами для VPN пользователей
Позволяет пользователям выбирать разные IP для выхода в интернет
"""

import json
import os
import subprocess
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class IPManager:
    def __init__(self):
        self.config_path = "/usr/local/etc/xray/config.json"
        self.ip_servers_file = "/var/www/vpn/data/ip_servers.json"
        self.user_ip_mapping_file = "/var/www/vpn/data/user_ip_mapping.json"
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(self.ip_servers_file), exist_ok=True)
        
        # Инициализируем файлы если не существуют
        self._init_files()
    
    def _init_files(self):
        """Инициализирует файлы конфигурации"""
        # Список доступных IP серверов
        if not os.path.exists(self.ip_servers_file):
            default_servers = {
                "servers": [
                    {
                        "id": "direct",
                        "name": "🇷🇺 Россия (прямое)",
                        "country": "RU",
                        "type": "direct",
                        "description": "Прямое подключение без прокси"
                    },
                    {
                        "id": "cloudflare_warp",
                        "name": "🌐 Cloudflare WARP",
                        "country": "US",
                        "type": "socks",
                        "address": "127.0.0.1",
                        "port": 40000,
                        "description": "Cloudflare WARP прокси"
                    }
                ]
            }
            with open(self.ip_servers_file, 'w') as f:
                json.dump(default_servers, f, indent=2, ensure_ascii=False)
        
        # Маппинг пользователей к IP серверам
        if not os.path.exists(self.user_ip_mapping_file):
            with open(self.user_ip_mapping_file, 'w') as f:
                json.dump({}, f, indent=2)
    
    def get_available_servers(self) -> List[Dict]:
        """Возвращает список доступных IP серверов"""
        try:
            with open(self.ip_servers_file, 'r') as f:
                data = json.load(f)
            return data.get('servers', [])
        except Exception as e:
            logger.error(f"Ошибка чтения серверов: {e}")
            return []
    
    def add_server(self, server_config: Dict) -> bool:
        """Добавляет новый IP сервер"""
        try:
            servers_data = {"servers": []}
            if os.path.exists(self.ip_servers_file):
                with open(self.ip_servers_file, 'r') as f:
                    servers_data = json.load(f)
            
            servers_data['servers'].append(server_config)
            
            with open(self.ip_servers_file, 'w') as f:
                json.dump(servers_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Добавлен сервер: {server_config['name']}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления сервера: {e}")
            return False
    
    def set_user_ip(self, user_uuid: str, server_id: str) -> bool:
        """Устанавливает IP сервер для пользователя"""
        try:
            # Загружаем текущий маппинг
            user_mapping = {}
            if os.path.exists(self.user_ip_mapping_file):
                with open(self.user_ip_mapping_file, 'r') as f:
                    user_mapping = json.load(f)
            
            # Обновляем маппинг
            user_mapping[user_uuid] = server_id
            
            # Сохраняем
            with open(self.user_ip_mapping_file, 'w') as f:
                json.dump(user_mapping, f, indent=2)
            
            # Обновляем конфигурацию Xray
            return self._update_xray_config()
            
        except Exception as e:
            logger.error(f"Ошибка установки IP для пользователя: {e}")
            return False
    
    def get_user_ip(self, user_uuid: str) -> Optional[str]:
        """Возвращает текущий IP сервер пользователя"""
        try:
            if os.path.exists(self.user_ip_mapping_file):
                with open(self.user_ip_mapping_file, 'r') as f:
                    user_mapping = json.load(f)
                return user_mapping.get(user_uuid, "direct")
            return "direct"
        except Exception as e:
            logger.error(f"Ошибка получения IP пользователя: {e}")
            return "direct"
    
    def _update_xray_config(self) -> bool:
        """Обновляет конфигурацию Xray с новыми outbound'ами"""
        try:
            # Загружаем текущую конфигурацию
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Загружаем серверы и маппинг
            servers = self.get_available_servers()
            with open(self.user_ip_mapping_file, 'r') as f:
                user_mapping = json.load(f)
            
            # Обновляем outbounds
            self._update_outbounds(config, servers)
            
            # Обновляем routing rules
            self._update_routing_rules(config, servers, user_mapping)
            
            # Сохраняем конфигурацию
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Конфигурация Xray обновлена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации Xray: {e}")
            return False
    
    def _update_outbounds(self, config: Dict, servers: List[Dict]):
        """Обновляет секцию outbounds"""
        # Сохраняем существующие системные outbound'ы
        existing_outbounds = []
        for outbound in config.get('outbounds', []):
            tag = outbound.get('tag', '')
            if tag in ['direct', 'blocked', 'block']:
                existing_outbounds.append(outbound)
        
        # Добавляем outbound'ы для каждого IP сервера
        for server in servers:
            if server['type'] == 'direct':
                # Прямое подключение уже есть
                continue
            elif server['type'] == 'socks':
                outbound = {
                    "tag": f"ip_{server['id']}",
                    "protocol": "socks",
                    "settings": {
                        "servers": [{
                            "address": server['address'],
                            "port": server['port']
                        }]
                    }
                }
                existing_outbounds.append(outbound)
            elif server['type'] == 'http':
                outbound = {
                    "tag": f"ip_{server['id']}",
                    "protocol": "http",
                    "settings": {
                        "servers": [{
                            "address": server['address'],
                            "port": server['port']
                        }]
                    }
                }
                existing_outbounds.append(outbound)
        
        config['outbounds'] = existing_outbounds
    
    def _update_routing_rules(self, config: Dict, servers: List[Dict], user_mapping: Dict):
        """Обновляет routing rules для пользователей"""
        routing = config.get('routing', {'domainStrategy': 'IPIfNonMatch', 'rules': []})
        
        # Сохраняем существующие правила (блокировка рекламы, bypass и т.д.)
        existing_rules = []
        for rule in routing.get('rules', []):
            # Пропускаем старые правила IP маршрутизации
            if rule.get('outboundTag', '').startswith('ip_'):
                continue
            existing_rules.append(rule)
        
        # Добавляем правила для каждого пользователя с кастомным IP
        for user_uuid, server_id in user_mapping.items():
            if server_id != 'direct':
                # Правило для конкретного пользователя
                rule = {
                    "type": "field",
                    "user": [user_uuid],
                    "outboundTag": f"ip_{server_id}"
                }
                existing_rules.append(rule)
        
        routing['rules'] = existing_rules
        config['routing'] = routing
    
    def restart_xray(self) -> bool:
        """Перезапускает Xray для применения изменений"""
        try:
            result = subprocess.run(['systemctl', 'restart', 'xray'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Xray перезапущен успешно")
                return True
            else:
                logger.error(f"Ошибка перезапуска Xray: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Ошибка перезапуска Xray: {e}")
            return False
    
    def get_current_ip(self) -> Optional[str]:
        """Получает текущий внешний IP сервера"""
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            return response.text.strip()
        except:
            try:
                response = requests.get('https://ifconfig.me', timeout=5)
                return response.text.strip()
            except:
                return None
    
    def test_server_connection(self, server_config: Dict) -> bool:
        """Тестирует подключение к IP серверу"""
        if server_config['type'] == 'direct':
            return True
        
        # Для прокси серверов можно добавить тестирование
        # Пока возвращаем True
        return True