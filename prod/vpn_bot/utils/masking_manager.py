#!/usr/bin/env python3
"""
🎭 Интегрированный менеджер маскировки VPN
Встроенные функции маскировки для Telegram бота
"""

import json
import random
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class IntegratedMaskingManager:
    """Менеджер маскировки, интегрированный в бота"""
    
    def __init__(self):
        self.xray_config_path = "/usr/local/etc/xray/config.json"
        self.reality_config_path = "/var/www/vpn/xray/reality.json"
        self.last_rotation = None
        self.masking_active = False
        
    async def start_masking(self):
        """Запускает интегрированную маскировку"""
        if self.masking_active:
            logger.info("🎭 Маскировка уже активна")
            return
            
        logger.info("🎭 Запуск интегрированной маскировки VPN")
        
        # Сначала применяем все улучшения
        await self._apply_initial_enhancements()
        
        self.masking_active = True
        
        # Запускаем фоновые задачи маскировки
        asyncio.create_task(self._rotation_task())
        asyncio.create_task(self._traffic_noise_task())
        
        logger.info("✅ Интегрированная маскировка VPN активирована")
        logger.info("📊 Активные техники: Reality enhancement, Dynamic rotation, Traffic noise, Geo routing")
        
    async def stop_masking(self):
        """Останавливает маскировку"""
        logger.info("🛑 Остановка маскировки VPN")
        self.masking_active = False
    
    async def _apply_initial_enhancements(self):
        """Применяет начальные улучшения маскировки"""
        logger.info("🔧 Применение начальных улучшений маскировки...")
        
        # 1. Улучшаем Reality конфигурацию
        enhanced_reality = await self.enhance_reality_config()
        if enhanced_reality:
            logger.info("✅ Reality конфигурация улучшена")
        else:
            logger.info("ℹ️ Reality конфигурация уже оптимальна")
        
        # 2. Применяем географическую маршрутизацию
        applied_geo = await self.apply_geo_routing()
        if applied_geo:
            logger.info("✅ Географическая маршрутизация настроена")
        else:
            logger.info("ℹ️ Географическая маршрутизация уже настроена")
        
        # 3. Перезагружаем Xray если были изменения
        if enhanced_reality or applied_geo:
            logger.info("🔄 Перезагрузка Xray для применения изменений...")
            await self._reload_xray()
        
        logger.info("🎯 Начальные улучшения маскировки применены")
        
    async def enhance_reality_config(self):
        """Улучшает конфигурацию Reality для лучшей маскировки"""
        try:
            with open(self.xray_config_path, 'r') as f:
                config = json.load(f)
            
            reality_settings = config['inbounds'][0]['streamSettings']['realitySettings']
            
            # Расширенный список популярных доменов с акцентом на iOS совместимость
            enhanced_domains = [
                # Apple экосистема (приоритет для iOS)
                "www.apple.com",
                "www.icloud.com",
                "itunes.apple.com", 
                "apps.apple.com",
                "developer.apple.com",
                
                # Основные CDN и облачные сервисы
                "www.microsoft.com",
                "discord.com",
                "www.github.com",
                "api.github.com",
                
                # Популярные сервисы (выглядят как обычный трафик)
                "www.youtube.com",
                "fonts.googleapis.com",
                "ajax.googleapis.com",
                "www.wikipedia.org",
                "www.reddit.com",
                
                # Образовательные и новостные (менее подозрительные)
                "stackoverflow.com",
                "news.ycombinator.com",
                "medium.com"
            ]
            
            # Обновляем только если список отличается
            current_domains = set(reality_settings.get('serverNames', []))
            new_domains = set(enhanced_domains)
            
            if current_domains != new_domains:
                reality_settings['serverNames'] = enhanced_domains
                
                # Сохраняем конфигурацию
                with open(self.xray_config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logger.info("✅ Обновлен список serverNames для лучшей маскировки")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка улучшения Reality: {e}")
            return False
    
    async def _rotation_task(self):
        """Фоновая задача ротации параметров"""
        logger.info("🔄 Запуск задачи динамической ротации (каждые 6 часов)")
        
        while self.masking_active:
            try:
                # Ротация раз в 6 часов
                if (not self.last_rotation or 
                    datetime.now() - self.last_rotation > timedelta(hours=6)):
                    
                    logger.info("🔄 Время ротации dest сервера...")
                    await self._rotate_dest_server()
                    self.last_rotation = datetime.now()
                    logger.info(f"✅ Ротация завершена. Следующая ротация: {(self.last_rotation + timedelta(hours=6)).strftime('%H:%M %d.%m')}")
                
                # Проверяем каждые 30 минут
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в задаче ротации: {e}")
                await asyncio.sleep(300)  # Пауза при ошибке
    
    async def _rotate_dest_server(self):
        """Ротирует dest сервер для усложнения обнаружения"""
        # Приоритет Apple серверам для лучшей iOS совместимости
        dest_servers = [
            "www.apple.com:8443",      # Приоритет для iOS
            "www.icloud.com:8443",     # Apple сервисы
            "www.microsoft.com:8443",  # Альтернативный
            "discord.com:8443",        # Популярный сервис
            "www.github.com:8443"      # Разработчики
        ]
        
        try:
            with open(self.xray_config_path, 'r') as f:
                config = json.load(f)
            
            reality_settings = config['inbounds'][0]['streamSettings']['realitySettings']
            current_dest = reality_settings.get('dest', '')
            
            # Выбираем новый dest (отличный от текущего)
            available_servers = [s for s in dest_servers if s != current_dest]
            if available_servers:
                new_dest = random.choice(available_servers)
                reality_settings['dest'] = new_dest
                
                # Обновляем основной serverName
                main_server = new_dest.split(':')[0]
                server_names = reality_settings.get('serverNames', [])
                if main_server not in server_names:
                    server_names.insert(0, main_server)
                    reality_settings['serverNames'] = server_names
                
                # Сохраняем конфигурацию
                with open(self.xray_config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                # Мягкая перезагрузка Xray
                await self._reload_xray()
                
                logger.info(f"🔄 Dest сервер изменен на: {new_dest}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка ротации dest сервера: {e}")
    
    async def _traffic_noise_task(self):
        """Создает фоновый шум трафика"""
        domains = [
            "www.google.com",
            "www.github.com", 
            "www.wikipedia.org",
            "stackoverflow.com"
        ]
        
        logger.info("📊 Запуск задачи фонового трафика (имитация обычного пользователя)")
        
        while self.masking_active:
            try:
                # Случайная пауза (имитация человеческого поведения)
                pause = random.randint(300, 1800)  # 5-30 минут
                logger.debug(f"📊 Пауза перед следующим DNS запросом: {pause//60} мин")
                await asyncio.sleep(pause)
                
                # Случайный домен
                domain = random.choice(domains)
                logger.debug(f"📊 DNS запрос к {domain}")
                
                # Асинхронный DNS запрос (минимальный трафик)
                process = await asyncio.create_subprocess_exec(
                    'nslookup', domain,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
                
                if process.returncode == 0:
                    logger.debug(f"✅ DNS запрос к {domain} успешен")
                else:
                    logger.debug(f"⚠️ DNS запрос к {domain} неудачен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка в генерации трафика: {e}")
                await asyncio.sleep(600)  # Пауза при ошибке
    
    async def _reload_xray(self):
        """Мягкая перезагрузка Xray"""
        try:
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'reload', 'xray',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("✅ Xray успешно перезагружен")
            else:
                logger.error(f"❌ Ошибка перезагрузки Xray: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Ошибка перезагрузки Xray: {e}")
    
    def get_masking_status(self):
        """Возвращает статус маскировки"""
        return {
            'active': self.masking_active,
            'last_rotation': self.last_rotation.isoformat() if self.last_rotation else None,
            'techniques': [
                'Reality protocol masking',
                'Dynamic dest rotation', 
                'Background traffic noise',
                'Enhanced serverNames list'
            ]
        }
    
    async def apply_geo_routing(self):
        """Применяет географическую маршрутизацию"""
        try:
            with open(self.xray_config_path, 'r') as f:
                config = json.load(f)
            
            # Проверяем, есть ли уже routing
            if 'routing' in config:
                return False  # Уже настроено
            
            # Добавляем умную маршрутизацию
            config['routing'] = {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {
                        "type": "field",
                        "domain": ["geosite:category-ads-all"],
                        "outboundTag": "block"
                    },
                    {
                        "type": "field", 
                        "domain": ["geosite:cn", "geosite:ru"],
                        "outboundTag": "direct"
                    },
                    {
                        "type": "field",
                        "ip": ["geoip:private", "geoip:cn", "geoip:ru"],
                        "outboundTag": "direct"
                    }
                ]
            }
            
            # Добавляем outbounds если их нет
            existing_tags = {ob.get('tag') for ob in config.get('outbounds', [])}
            
            if 'direct' not in existing_tags:
                config.setdefault('outbounds', []).append({
                    "protocol": "freedom",
                    "tag": "direct"
                })
            
            if 'block' not in existing_tags:
                config.setdefault('outbounds', []).append({
                    "protocol": "blackhole", 
                    "tag": "block"
                })
            
            # Сохраняем конфигурацию
            with open(self.xray_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("✅ Применена географическая маршрутизация")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения гео-маршрутизации: {e}")
            return False

# Глобальный экземпляр менеджера
masking_manager = IntegratedMaskingManager()

async def start_integrated_masking():
    """Запускает интегрированную маскировку"""
    await masking_manager.start_masking()

async def stop_integrated_masking():
    """Останавливает интегрированную маскировку"""
    await masking_manager.stop_masking()

def get_masking_status():
    """Получает статус маскировки"""
    return masking_manager.get_masking_status()