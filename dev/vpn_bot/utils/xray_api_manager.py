#!/usr/bin/env python3
"""
Менеджер для управления Xray через API
Поддерживает динамическое добавление/удаление inbound'ов и клиентов
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from config import GENERATION_PATHS, PROJECT_ROOT

logger = logging.getLogger(__name__)

class XrayAPIManager:
    def __init__(self, api_host: str = "127.0.0.1", api_port: int = 10085):
        """
        Инициализация менеджера Xray API
        
        Args:
            api_host: Хост API сервера (по умолчанию localhost)
            api_port: Порт API сервера (по умолчанию 10085)
        """
        self.api_host = api_host
        self.api_port = api_port
        self.base_url = f"http://{api_host}:{api_port}"
        
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Выполняет HTTP запрос к Xray API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.error(f"API Error {response.status}: {await response.text()}")
                            return None
                            
                elif method.upper() == "POST":
                    async with session.post(url, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.error(f"API Error {response.status}: {await response.text()}")
                            return None
                            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    async def add_inbound(self, tag: str, port: int, protocol: str = "vless", 
                         reality_settings: Optional[Dict] = None) -> bool:
        """
        Добавляет новый inbound
        
        Args:
            tag: Уникальный тег для inbound
            port: Порт для прослушивания  
            protocol: Протокол (vless, vmess, etc.)
            reality_settings: Настройки Reality для TLS
            
        Returns:
            bool: True если успешно добавлен
        """
        
        # Базовая конфигурация inbound
        inbound_config = {
            "tag": tag,
            "port": port,
            "protocol": protocol,
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality" if reality_settings else "none",
                "tcpSettings": {
                    "header": {"type": "none"}
                }
            }
        }
        
        # Добавляем Reality настройки если указаны
        if reality_settings:
            inbound_config["streamSettings"]["realitySettings"] = reality_settings
            
        # Отправляем запрос
        result = await self._make_request("POST", "add/inbound", inbound_config)
        
        if result and result.get("success"):
            logger.info(f"✅ Inbound {tag} добавлен на порт {port}")
            return True
        else:
            logger.error(f"❌ Не удалось добавить inbound {tag}")
            return False
    
    async def remove_inbound(self, tag: str) -> bool:
        """
        Удаляет inbound по тегу
        
        Args:
            tag: Тег inbound для удаления
            
        Returns:
            bool: True если успешно удален
        """
        result = await self._make_request("POST", f"remove/inbound/{tag}")
        
        if result and result.get("success"):
            logger.info(f"✅ Inbound {tag} удален")
            return True
        else:
            logger.error(f"❌ Не удалось удалить inbound {tag}")
            return False
    
    async def add_client_to_inbound(self, inbound_tag: str, client_uuid: str, 
                                  client_email: str, flow: str = "xtls-rprx-vision") -> bool:
        """
        Добавляет клиента к существующему inbound
        
        Args:
            inbound_tag: Тег inbound
            client_uuid: UUID клиента
            client_email: Email клиента (обычно username)
            flow: Тип потока для VLESS
            
        Returns:
            bool: True если успешно добавлен
        """
        client_config = {
            "id": client_uuid,
            "flow": flow,
            "level": 0,
            "email": client_email
        }
        
        result = await self._make_request("POST", f"add/inbound/{inbound_tag}/client", client_config)
        
        if result and result.get("success"):
            logger.info(f"✅ Клиент {client_email} добавлен в inbound {inbound_tag}")
            return True
        else:
            logger.error(f"❌ Не удалось добавить клиента {client_email}")
            return False
    
    async def remove_client_from_inbound(self, inbound_tag: str, client_email: str) -> bool:
        """
        Удаляет клиента из inbound
        
        Args:
            inbound_tag: Тег inbound
            client_email: Email клиента для удаления
            
        Returns:
            bool: True если успешно удален
        """
        result = await self._make_request("POST", f"remove/inbound/{inbound_tag}/client/{client_email}")
        
        if result and result.get("success"):
            logger.info(f"✅ Клиент {client_email} удален из inbound {inbound_tag}")
            return True
        else:
            logger.error(f"❌ Не удалось удалить клиента {client_email}")
            return False
    
    async def get_inbound_stats(self, inbound_tag: str) -> Optional[Dict]:
        """
        Получает статистику inbound
        
        Args:
            inbound_tag: Тег inbound
            
        Returns:
            Dict: Статистика или None если ошибка
        """
        result = await self._make_request("GET", f"stats/inbound/{inbound_tag}")
        return result
    
    async def get_client_stats(self, client_email: str) -> Optional[Dict]:
        """
        Получает статистику клиента
        
        Args:
            client_email: Email клиента
            
        Returns:
            Dict: Статистика или None если ошибка
        """
        result = await self._make_request("GET", f"stats/user/{client_email}")
        return result
    
    async def list_inbounds(self) -> List[Dict]:
        """
        Получает список всех inbound'ов
        
        Returns:
            List[Dict]: Список inbound'ов
        """
        result = await self._make_request("GET", "list/inbounds")
        return result.get("inbounds", []) if result else []
    
    async def create_user_inbound(self, user_id: int, user_uuid: str, username: str) -> Dict[str, Any]:
        """
        Создает персональный inbound для пользователя
        
        Args:
            user_id: ID пользователя
            user_uuid: UUID для VLESS ключа
            username: Имя пользователя
            
        Returns:
            Dict: Информация о созданном inbound и ключе
        """
        
        # Генерируем уникальный порт для пользователя (начиная с 20000)
        user_port = 20000 + (user_id % 10000)  # Ограничиваем диапазон портов
        inbound_tag = f"user_{user_id}"
        
        # Reality настройки (используем текущие)
        reality_settings = {
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
        
        # Создаем inbound
        success = await self.add_inbound(
            tag=inbound_tag,
            port=user_port,
            protocol="vless",
            reality_settings=reality_settings
        )
        
        if not success:
            return {"error": "Не удалось создать inbound"}
        
        # Добавляем клиента к inbound
        client_success = await self.add_client_to_inbound(
            inbound_tag=inbound_tag,
            client_uuid=user_uuid,
            client_email=username,
            flow="xtls-rprx-vision"
        )
        
        if not client_success:
            # Если не удалось добавить клиента, удаляем inbound
            await self.remove_inbound(inbound_tag)
            return {"error": "Не удалось добавить клиента"}
        
        # Формируем VLESS ссылку
        vless_url = self._generate_vless_url(
            uuid=user_uuid,
            host="146.103.125.210",
            port=443,  # Внешний порт (через Nginx)
            username=username,
            reality_settings=reality_settings
        )
        
        return {
            "success": True,
            "vless_url": vless_url,
            "inbound_tag": inbound_tag,
            "internal_port": user_port,
            "external_port": 443,
            "uuid": user_uuid
        }
    
    def _generate_vless_url(self, uuid: str, host: str, port: int, username: str, 
                          reality_settings: Dict) -> str:
        """Генерирует VLESS URL для клиента"""
        
        # Извлекаем параметры из Reality настроек
        sni = reality_settings.get("serverNames", ["www.apple.com"])[0]
        fp = reality_settings.get("fingerprint", "safari")
        pbk = reality_settings.get("publicKey", "kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ")
        sid = reality_settings.get("shortIds", ["60e35ba6"])[0]
        
        # Формируем URL
        vless_url = (
            f"vless://{uuid}@{host}:{port}"
            f"?security=reality"
            f"&sni={sni}"
            f"&fp={fp}"
            f"&pbk={pbk}"
            f"&sid={sid}"
            f"&spx=/"
            f"&type=tcp"
            f"&flow=xtls-rprx-vision"
            f"&encryption=none"
            f"#{username}"
        )
        
        return vless_url
    
    async def test_api_connection(self) -> bool:
        """Тестирует подключение к Xray API"""
        try:
            result = await self._make_request("GET", "stats/sys")
            return result is not None
        except:
            return False