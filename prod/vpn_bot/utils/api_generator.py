#!/usr/bin/env python3
"""
Генератор VPN ключей через Xray API
Заменяет файловую систему на API управление
"""

import asyncio
import uuid as uuid_lib
import logging
from datetime import datetime
from typing import Tuple, Optional
from .xray_api_manager import XrayAPIManager
from db.models import session, User, VpnKey

logger = logging.getLogger(__name__)

class APIVPNGenerator:
    def __init__(self):
        """Инициализация API генератора"""
        self.api_manager = XrayAPIManager()
        
    async def generate_vpn_key(self, client_name: str, user_id: int) -> Tuple[str, Optional[str]]:
        """
        Генерирует VPN ключ через API
        
        Args:
            client_name: Имя клиента
            user_id: ID пользователя в Telegram
            
        Returns:
            Tuple[str, Optional[str]]: (vless_url или ошибка, uuid)
        """
        
        try:
            # Проверяем подключение к API
            if not await self.api_manager.test_api_connection():
                return "❌ Xray API недоступен. Проверьте конфигурацию.", None
            
            # Получаем пользователя из базы данных
            db_user = session.query(User).filter_by(tg_id=user_id).first()
            if not db_user:
                return "❌ Пользователь не найден в базе данных", None
            
            # Проверяем есть ли уже ключ у пользователя
            existing_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
            
            if existing_key:
                # Если ключ уже есть, генерируем URL на основе существующих данных
                return await self._generate_url_for_existing_key(existing_key, client_name)
            
            # Генерируем новый UUID для клиента
            client_uuid = str(uuid_lib.uuid4())
            
            # Используем один main inbound вместо создания отдельных
            # Это более эффективно для больших количеств пользователей
            success = await self.api_manager.add_client_to_inbound(
                inbound_tag="main",
                client_uuid=client_uuid,
                client_email=f"{client_name}_{user_id}",
                flow="xtls-rprx-vision"
            )
            
            if not success:
                return "❌ Не удалось добавить клиента через API", None
            
            # Генерируем VLESS URL
            vless_url = self._generate_vless_url(client_uuid, client_name)
            
            # Сохраняем в базу данных
            new_key = VpnKey(
                user_id=db_user.id,
                uuid=client_uuid,
                vpn_link=vless_url,
                created_at=datetime.now()
            )
            
            session.add(new_key)
            session.commit()
            
            logger.info(f"✅ Создан ключ для {client_name} (API режим)")
            return vless_url, client_uuid
            
        except Exception as e:
            logger.error(f"Ошибка генерации через API: {e}")
            session.rollback()
            return f"❌ Ошибка генерации: {str(e)}", None
    
    async def _generate_url_for_existing_key(self, existing_key: VpnKey, client_name: str) -> Tuple[str, str]:
        """Генерирует URL для существующего ключа"""
        
        if existing_key.vpn_link:
            # Если ссылка уже есть, возвращаем её
            return existing_key.vpn_link, existing_key.uuid
        
        # Если ссылки нет, генерируем новую
        vless_url = self._generate_vless_url(existing_key.uuid, client_name)
        
        # Обновляем в базе
        existing_key.vpn_link = vless_url
        session.commit()
        
        return vless_url, existing_key.uuid
    
    def _generate_vless_url(self, client_uuid: str, client_name: str) -> str:
        """Генерирует VLESS URL для клиента"""
        
        # Параметры Reality (используем актуальные)
        reality_params = {
            "sni": "www.apple.com",
            "fp": "safari", 
            "pbk": "kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ",
            "sid": "60e35ba6"
        }
        
        # Формируем VLESS URL
        vless_url = (
            f"vless://{client_uuid}@146.103.125.210:443"
            f"?security=reality"
            f"&sni={reality_params['sni']}"
            f"&fp={reality_params['fp']}"
            f"&pbk={reality_params['pbk']}" 
            f"&sid={reality_params['sid']}"
            f"&spx=/"
            f"&type=tcp"
            f"&flow=xtls-rprx-vision"
            f"&encryption=none"
            f"#{client_name}"
        )
        
        return vless_url
    
    async def remove_user_key(self, user_id: int) -> bool:
        """
        Удаляет ключ пользователя через API
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            bool: True если успешно удален
        """
        
        try:
            # Получаем пользователя и его ключ
            db_user = session.query(User).filter_by(tg_id=user_id).first()
            if not db_user:
                return False
                
            vpn_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
            if not vpn_key:
                return False
            
            # Удаляем клиента из main inbound через API
            client_email = f"user_{user_id}_{vpn_key.uuid[:8]}"
            success = await self.api_manager.remove_client_from_inbound("main", client_email)
            
            if success:
                # Удаляем из базы данных
                session.delete(vpn_key)
                session.commit()
                logger.info(f"✅ Ключ пользователя {user_id} удален через API")
                return True
            else:
                logger.error(f"❌ Не удалось удалить клиента {user_id} через API")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка удаления ключа через API: {e}")
            session.rollback()
            return False
    
    async def get_user_stats(self, user_id: int) -> Optional[dict]:
        """
        Получает статистику пользователя через API
        
        Args:
            user_id: ID пользователя
            
        Returns:
            dict: Статистика или None
        """
        
        try:
            db_user = session.query(User).filter_by(tg_id=user_id).first()
            if not db_user:
                return None
                
            vpn_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
            if not vpn_key:
                return None
            
            client_email = f"user_{user_id}_{vpn_key.uuid[:8]}"
            stats = await self.api_manager.get_client_stats(client_email)
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None

# Глобальный экземпляр для использования в боте
api_generator = APIVPNGenerator()