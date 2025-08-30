import subprocess
from datetime import datetime
import os
from typing import Dict, Any, Optional
from .generator import generate_vpn_link
from .openvpn_generator import OpenVPNGenerator
from .wireguard_generator import WireGuardGenerator

class UniversalVPNGenerator:
    """Универсальный генератор для всех типов VPN"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.openvpn_gen = OpenVPNGenerator(
            ca_path=config.get('openvpn_ca_path', '/etc/openvpn/ca.crt'),
            server_cert=config.get('openvpn_server_cert', '/etc/openvpn/server.crt'),
            server_key=config.get('openvpn_server_key', '/etc/openvpn/server.key')
        )
        self.wireguard_gen = WireGuardGenerator(
            server_public_key=config.get('wireguard_server_public_key'),
            server_endpoint=config.get('wireguard_server_endpoint'),
            server_port=config.get('wireguard_server_port', 51820)
        )
        
    def generate_vpn(self, vpn_type: str, client_name: str, **kwargs) -> Dict[str, Any]:
        """
        Генерирует VPN конфигурацию указанного типа
        
        Args:
            vpn_type: Тип VPN ('xray', 'openvpn', 'wireguard')
            client_name: Имя клиента
            **kwargs: Дополнительные параметры
            
        Returns:
            Словарь с результатами генерации
        """
        try:
            if vpn_type.lower() == 'xray':
                return self._generate_xray(client_name)
            elif vpn_type.lower() == 'openvpn':
                return self._generate_openvpn(client_name, **kwargs)
            elif vpn_type.lower() == 'wireguard':
                return self._generate_wireguard(client_name, **kwargs)
            else:
                raise ValueError(f"Неподдерживаемый тип VPN: {vpn_type}")
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'vpn_type': vpn_type,
                'client_name': client_name
            }
    
    def _generate_xray(self, client_name: str) -> Dict[str, Any]:
        """Генерирует Xray конфигурацию"""
        try:
            vless_link, client_uuid = generate_vpn_link(client_name)
            if "❌" in vless_link:
                return {
                    'success': False,
                    'error': vless_link,
                    'vpn_type': 'xray',
                    'client_name': client_name
                }
            
            return {
                'success': True,
                'vpn_type': 'xray',
                'client_name': client_name,
                'config': vless_link,
                'uuid': client_uuid,
                'config_type': 'link',
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'vpn_type': 'xray',
                'client_name': client_name
            }
    
    def _generate_openvpn(self, client_name: str, **kwargs) -> Dict[str, Any]:
        """Генерирует OpenVPN конфигурацию"""
        try:
            server_ip = kwargs.get('server_ip', self.config.get('openvpn_server_ip', '127.0.0.1'))
            server_port = kwargs.get('server_port', self.config.get('openvpn_server_port', 1194))
            protocol = kwargs.get('protocol', 'udp')
            
            # Генерируем сертификаты
            certs = self.openvpn_gen.generate_client_cert(client_name)
            
            # Создаем конфигурацию
            config = self.openvpn_gen.create_client_config(
                client_name, server_ip, server_port, protocol
            )
            
            # Сохраняем файл
            output_dir = kwargs.get('output_dir', '/tmp')
            filepath = self.openvpn_gen.save_client_config(client_name, config, output_dir)
            
            return {
                'success': True,
                'vpn_type': 'openvpn',
                'client_name': client_name,
                'config': config,
                'config_type': 'file',
                'filepath': filepath,
                'certificates': certs,
                'server_info': {
                    'ip': server_ip,
                    'port': server_port,
                    'protocol': protocol
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'vpn_type': 'openvpn',
                'client_name': client_name
            }
    
    def _generate_wireguard(self, client_name: str, **kwargs) -> Dict[str, Any]:
        """Генерирует WireGuard конфигурацию"""
        try:
            # Генерируем ключи
            keypair = self.wireguard_gen.generate_keypair()
            preshared_key = kwargs.get('use_preshared', True) and self.wireguard_gen.generate_preshared_key()
            
            # Определяем IP клиента
            existing_ips = kwargs.get('existing_ips', [])
            client_ip = self.wireguard_gen.get_next_client_ip(existing_ips=existing_ips)
            
            # Создаем конфигурацию клиента
            config = self.wireguard_gen.create_client_config(
                client_name, keypair['private_key'], client_ip
            )
            
            # Создаем фрагмент для сервера
            server_snippet = self.wireguard_gen.create_server_config_snippet(
                client_name, keypair['public_key'], client_ip, preshared_key
            )
            
            # Сохраняем файл
            output_dir = kwargs.get('output_dir', '/tmp')
            filepath = self.wireguard_gen.save_client_config(client_name, config, output_dir)
            
            # Генерируем QR-код если возможно
            qr_path = None
            if kwargs.get('generate_qr', True):
                qr_filename = f"{client_name}_qr.png"
                qr_path = os.path.join(output_dir, qr_filename)
                qr_path = self.wireguard_gen.create_qr_code(config, qr_path)
            
            return {
                'success': True,
                'vpn_type': 'wireguard',
                'client_name': client_name,
                'config': config,
                'config_type': 'file',
                'filepath': filepath,
                'qr_path': qr_path,
                'keys': {
                    'private_key': keypair['private_key'],
                    'public_key': keypair['public_key'],
                    'preshared_key': preshared_key
                },
                'network': {
                    'client_ip': client_ip,
                    'server_public_key': self.wireguard_gen.server_public_key,
                    'server_endpoint': self.wireguard_gen.server_endpoint,
                    'server_port': self.wireguard_gen.server_port
                },
                'server_snippet': server_snippet,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'vpn_type': 'wireguard',
                'client_name': client_name
            }
    
    def get_supported_types(self) -> list:
        """Возвращает список поддерживаемых типов VPN"""
        return ['xray', 'openvpn', 'wireguard']
    
    def get_vpn_info(self, vpn_type: str) -> Dict[str, Any]:
        """Возвращает информацию о типе VPN"""
        info = {
            'xray': {
                'name': 'Xray (VLESS)',
                'description': 'Современный прокси-сервер с поддержкой VLESS протокола',
                'config_type': 'link',
                'file_extension': None,
                'features': ['Высокая производительность', 'Поддержка TLS', 'Множество протоколов']
            },
            'openvpn': {
                'name': 'OpenVPN',
                'description': 'Классический VPN протокол с открытым исходным кодом',
                'config_type': 'file',
                'file_extension': '.ovpn',
                'features': ['Высокая безопасность', 'Широкое распространение', 'Поддержка сертификатов']
            },
            'wireguard': {
                'name': 'WireGuard',
                'description': 'Современный и быстрый VPN протокол',
                'config_type': 'file',
                'file_extension': '.conf',
                'features': ['Высокая скорость', 'Простая настройка', 'Встроенная криптография']
            }
        }
        
        return info.get(vpn_type.lower(), {}) 