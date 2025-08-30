#!/usr/bin/env python3
"""
Модуль для управления арендой IP-адресов через VDS провайдера
Интеграция с API для автоматической аренды/освобождения IP
"""

import json
import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RentedIP:
    """Класс для арендованного IP"""
    ip_address: str
    user_id: int
    rental_start: datetime
    rental_end: datetime
    cost_per_day: float
    provider_id: str
    status: str  # active, expired, pending

class VDSIPManager:
    def __init__(self):
        self.config_file = "/var/www/vpn/data/vds_config.json"
        self.rented_ips_file = "/var/www/vpn/data/rented_ips.json"
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Инициализируем конфигурацию
        self._init_config()
        self._load_config()
    
    def _init_config(self):
        """Инициализирует конфигурационные файлы"""
        if not os.path.exists(self.config_file):
            default_config = {
                "providers": {
                    "vdsina": {
                        "name": "VDSina.ru",
                        "api_url": "https://userapi.vdsina.ru/v1",
                        "api_key": "",
                        "cost_per_day": 50.0,  # рублей за день
                        "available_locations": [
                            {"id": "msk", "name": "🇷🇺 Москва", "country": "RU"},
                            {"id": "spb", "name": "🇷🇺 СПб", "country": "RU"},
                            {"id": "fra", "name": "🇩🇪 Франкфурт", "country": "DE"},
                            {"id": "ams", "name": "🇳🇱 Амстердам", "country": "NL"}
                        ]
                    },
                    "timeweb": {
                        "name": "Timeweb",
                        "api_url": "https://api.timeweb.cloud/api/v1",
                        "api_key": "",
                        "cost_per_day": 45.0,
                        "available_locations": [
                            {"id": "ru-1", "name": "🇷🇺 Москва", "country": "RU"},
                            {"id": "pl-1", "name": "🇵🇱 Польша", "country": "PL"},
                            {"id": "kz-1", "name": "🇰🇿 Казахстан", "country": "KZ"}
                        ]
                    }
                },
                "settings": {
                    "max_ips_per_user": 3,
                    "min_rental_days": 1,
                    "max_rental_days": 30,
                    "auto_renewal": True,
                    "payment_required": True
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        if not os.path.exists(self.rented_ips_file):
            with open(self.rented_ips_file, 'w') as f:
                json.dump({"rented_ips": []}, f, indent=2)
    
    def _load_config(self):
        """Загружает конфигурацию"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config = {"providers": {}, "settings": {}}
    
    def get_available_locations(self) -> List[Dict]:
        """Возвращает список доступных локаций для аренды IP"""
        locations = []
        
        for provider_id, provider in self.config.get("providers", {}).items():
            if not provider.get("api_key"):
                continue
                
            for location in provider.get("available_locations", []):
                locations.append({
                    "provider_id": provider_id,
                    "provider_name": provider["name"],
                    "location_id": location["id"],
                    "location_name": location["name"],
                    "country": location["country"],
                    "cost_per_day": provider["cost_per_day"]
                })
        
        return locations
    
    def rent_ip(self, user_id: int, provider_id: str, location_id: str, days: int) -> Dict:
        """Арендует IP-адрес для пользователя"""
        try:
            # Проверяем лимиты пользователя
            user_ips = self.get_user_ips(user_id)
            max_ips = self.config.get("settings", {}).get("max_ips_per_user", 3)
            
            if len(user_ips) >= max_ips:
                return {
                    "success": False,
                    "error": f"Превышен лимит IP ({max_ips})"
                }
            
            # Проверяем провайдера
            provider = self.config.get("providers", {}).get(provider_id)
            if not provider:
                return {
                    "success": False,
                    "error": "Провайдер не найден"
                }
            
            # Рассчитываем стоимость
            total_cost = provider["cost_per_day"] * days
            
            # Вызываем API провайдера для аренды IP
            ip_result = self._call_provider_api(provider_id, "rent_ip", {
                "location": location_id,
                "days": days
            })
            
            if not ip_result.get("success"):
                return {
                    "success": False,
                    "error": ip_result.get("error", "Ошибка API провайдера")
                }
            
            # Сохраняем информацию об аренде
            rented_ip = {
                "ip_address": ip_result["ip_address"],
                "user_id": user_id,
                "provider_id": provider_id,
                "location_id": location_id,
                "rental_start": datetime.now().isoformat(),
                "rental_end": (datetime.now() + timedelta(days=days)).isoformat(),
                "cost_per_day": provider["cost_per_day"],
                "total_cost": total_cost,
                "status": "active",
                "provider_resource_id": ip_result.get("resource_id")
            }
            
            self._save_rented_ip(rented_ip)
            
            # Добавляем IP в Xray конфигурацию
            self._add_ip_to_xray(rented_ip)
            
            return {
                "success": True,
                "ip_address": rented_ip["ip_address"],
                "cost": total_cost,
                "expires": rented_ip["rental_end"]
            }
            
        except Exception as e:
            logger.error(f"Ошибка аренды IP: {e}")
            return {
                "success": False,
                "error": f"Внутренняя ошибка: {e}"
            }
    
    def _call_provider_api(self, provider_id: str, action: str, params: Dict) -> Dict:
        """Вызывает API провайдера"""
        provider = self.config.get("providers", {}).get(provider_id)
        if not provider:
            return {"success": False, "error": "Провайдер не найден"}
        
        if provider_id == "vdsina":
            return self._call_vdsina_api(action, params, provider)
        elif provider_id == "timeweb":
            return self._call_timeweb_api(action, params, provider)
        else:
            # Заглушка для других провайдеров
            return self._mock_provider_api(action, params)
    
    def _call_vdsina_api(self, action: str, params: Dict, provider: Dict) -> Dict:
        """Вызывает API VDSina"""
        try:
            headers = {
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            }
            
            if action == "rent_ip":
                # Пример API вызова (нужно адаптировать под реальный API)
                url = f"{provider['api_url']}/floating-ips"
                data = {
                    "region": params["location"],
                    "name": f"vpn-ip-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 201:
                    result = response.json()
                    return {
                        "success": True,
                        "ip_address": result.get("ip", "192.168.1.100"),  # Заглушка
                        "resource_id": result.get("id")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API ошибка: {response.status_code}"
                    }
            
        except Exception as e:
            logger.error(f"Ошибка VDSina API: {e}")
            return {"success": False, "error": str(e)}
    
    def _call_timeweb_api(self, action: str, params: Dict, provider: Dict) -> Dict:
        """Вызывает API Timeweb"""
        # Аналогично VDSina, но для Timeweb API
        return self._mock_provider_api(action, params)
    
    def _mock_provider_api(self, action: str, params: Dict) -> Dict:
        """Заглушка API для тестирования"""
        if action == "rent_ip":
            # Генерируем случайный IP для теста
            import random
            ip = f"185.{random.randint(100,200)}.{random.randint(1,254)}.{random.randint(1,254)}"
            
            return {
                "success": True,
                "ip_address": ip,
                "resource_id": f"mock_{random.randint(1000,9999)}"
            }
        
        return {"success": False, "error": "Неизвестное действие"}
    
    def _save_rented_ip(self, rented_ip: Dict):
        """Сохраняет информацию об арендованном IP"""
        try:
            # Загружаем существующие IP
            rented_data = {"rented_ips": []}
            if os.path.exists(self.rented_ips_file):
                with open(self.rented_ips_file, 'r') as f:
                    rented_data = json.load(f)
            
            # Добавляем новый IP
            rented_data["rented_ips"].append(rented_ip)
            
            # Сохраняем
            with open(self.rented_ips_file, 'w') as f:
                json.dump(rented_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения IP: {e}")
    
    def _add_ip_to_xray(self, rented_ip: Dict):
        """Создает отдельный сервер Xray для арендованного IP"""
        try:
            from vpn_bot.utils.server_manager import ServerManager
            
            server_manager = ServerManager()
            
            # Создаем отдельный сервер для этого IP
            result = server_manager.create_server(
                ip_address=rented_ip['ip_address'],
                user_id=rented_ip['user_id'],
                location=rented_ip['location_id']
            )
            
            if result["success"]:
                # Обновляем информацию об аренде с данными сервера
                rented_ip['server_id'] = result['server_id']
                rented_ip['server_port'] = result['port']
                rented_ip['vless_key'] = result['vless_key']
                rented_ip['user_uuid'] = result['user_uuid']
                
                logger.info(f"Создан отдельный сервер для IP {rented_ip['ip_address']}")
            else:
                logger.error(f"Ошибка создания сервера для IP {rented_ip['ip_address']}: {result['error']}")
                
        except Exception as e:
            logger.error(f"Ошибка создания сервера для IP: {e}")
    
    def get_user_ips(self, user_id: int) -> List[Dict]:
        """Возвращает список IP пользователя"""
        try:
            if not os.path.exists(self.rented_ips_file):
                return []
            
            with open(self.rented_ips_file, 'r') as f:
                data = json.load(f)
            
            user_ips = []
            for ip_info in data.get("rented_ips", []):
                if ip_info["user_id"] == user_id:
                    # Проверяем не истек ли срок аренды
                    end_date = datetime.fromisoformat(ip_info["rental_end"])
                    if end_date > datetime.now():
                        ip_info["days_left"] = (end_date - datetime.now()).days
                        user_ips.append(ip_info)
                    else:
                        # IP истек, помечаем как expired
                        ip_info["status"] = "expired"
            
            return user_ips
            
        except Exception as e:
            logger.error(f"Ошибка получения IP пользователя: {e}")
            return []
    
    def release_ip(self, user_id: int, ip_address: str) -> bool:
        """Освобождает арендованный IP"""
        try:
            # Загружаем данные
            if not os.path.exists(self.rented_ips_file):
                return False
            
            with open(self.rented_ips_file, 'r') as f:
                data = json.load(f)
            
            # Находим и удаляем IP
            updated_ips = []
            found = False
            
            for ip_info in data.get("rented_ips", []):
                if ip_info["user_id"] == user_id and ip_info["ip_address"] == ip_address:
                    # Вызываем API провайдера для освобождения
                    self._call_provider_api(ip_info["provider_id"], "release_ip", {
                        "resource_id": ip_info.get("provider_resource_id")
                    })
                    found = True
                    # Не добавляем в updated_ips (удаляем)
                else:
                    updated_ips.append(ip_info)
            
            if found:
                # Сохраняем обновленный список
                data["rented_ips"] = updated_ips
                with open(self.rented_ips_file, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Удаляем из Xray
                self._remove_ip_from_xray(ip_address)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка освобождения IP: {e}")
            return False
    
    def _remove_ip_from_xray(self, ip_address: str):
        """Удаляет сервер Xray для IP"""
        try:
            from vpn_bot.utils.server_manager import ServerManager
            
            server_manager = ServerManager()
            server_id = f"xray_{ip_address.replace('.', '_')}"
            
            # Удаляем отдельный сервер
            success = server_manager.remove_server(server_id)
            
            if success:
                logger.info(f"Сервер для IP {ip_address} удален")
            else:
                logger.error(f"Ошибка удаления сервера для IP {ip_address}")
                
        except Exception as e:
            logger.error(f"Ошибка удаления сервера для IP: {e}")
    
    def check_expired_ips(self):
        """Проверяет и освобождает истекшие IP"""
        try:
            if not os.path.exists(self.rented_ips_file):
                return
            
            with open(self.rented_ips_file, 'r') as f:
                data = json.load(f)
            
            current_time = datetime.now()
            updated_ips = []
            
            for ip_info in data.get("rented_ips", []):
                end_date = datetime.fromisoformat(ip_info["rental_end"])
                
                if end_date <= current_time and ip_info["status"] == "active":
                    # IP истек, освобождаем
                    logger.info(f"Освобождение истекшего IP: {ip_info['ip_address']}")
                    
                    self._call_provider_api(ip_info["provider_id"], "release_ip", {
                        "resource_id": ip_info.get("provider_resource_id")
                    })
                    
                    self._remove_ip_from_xray(ip_info["ip_address"])
                    
                    # Не добавляем в updated_ips (удаляем)
                else:
                    updated_ips.append(ip_info)
            
            # Сохраняем обновленный список
            data["rented_ips"] = updated_ips
            with open(self.rented_ips_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Ошибка проверки истекших IP: {e}")
    
    def get_rental_cost(self, provider_id: str, days: int) -> float:
        """Рассчитывает стоимость аренды"""
        provider = self.config.get("providers", {}).get(provider_id)
        if not provider:
            return 0.0
        
        return provider["cost_per_day"] * days