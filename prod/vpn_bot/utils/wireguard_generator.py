import subprocess
import os
import tempfile
from datetime import datetime
import secrets
import base64

class WireGuardGenerator:
    def __init__(self, server_public_key: str = None, server_endpoint: str = None, server_port: int = 51820):
        self.server_public_key = server_public_key
        self.server_endpoint = server_endpoint
        self.server_port = server_port
        
    def generate_keypair(self) -> dict:
        """Генерирует пару ключей WireGuard"""
        try:
            # Генерируем приватный ключ
            private_key = subprocess.check_output([
                "wg", "genkey"
            ], text=True).strip()
            
            # Генерируем публичный ключ из приватного
            public_key = subprocess.check_output([
                "wg", "pubkey"
            ], text=True, input=private_key).strip()
            
            return {
                'private_key': private_key,
                'public_key': public_key
            }
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ошибка генерации ключей WireGuard: {e}")
    
    def generate_preshared_key(self) -> str:
        """Генерирует preshared ключ"""
        try:
            return subprocess.check_output([
                "wg", "genpsk"
            ], text=True).strip()
        except subprocess.CalledProcessError:
            # Fallback к Python генерации
            return base64.b64encode(secrets.token_bytes(32)).decode()
    
    def create_client_config(self, client_name: str, client_private_key: str, 
                           client_ip: str, dns_servers: list = None) -> str:
        """Создает конфигурацию клиента WireGuard"""
        if dns_servers is None:
            dns_servers = ["1.1.1.1", "8.8.8.8"]
        
        config = f"""[Interface]
# Client: {client_name}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
PrivateKey = {client_private_key}
Address = {client_ip}/32
DNS = {', '.join(dns_servers)}

[Peer]
# Server
PublicKey = {self.server_public_key or 'YOUR_SERVER_PUBLIC_KEY'}
Endpoint = {self.server_endpoint or 'YOUR_SERVER_IP'}:{self.server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        return config
    
    def create_server_config_snippet(self, client_name: str, client_public_key: str, 
                                   client_ip: str, preshared_key: str = None) -> str:
        """Создает фрагмент конфигурации сервера для добавления клиента"""
        config = f"""
# Client: {client_name}
[Peer]
PublicKey = {client_public_key}
AllowedIPs = {client_ip}/32
"""
        
        if preshared_key:
            config += f"PresharedKey = {preshared_key}\n"
        
        return config
    
    def save_client_config(self, client_name: str, config: str, output_dir: str = "/tmp") -> str:
        """Сохраняет конфигурацию клиента в файл"""
        filename = f"{client_name}.conf"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(config)
        
        return filepath
    
    def get_next_client_ip(self, base_subnet: str = "10.0.0.0/24", 
                          existing_ips: list = None) -> str:
        """Определяет следующий доступный IP для клиента"""
        if existing_ips is None:
            existing_ips = []
        
        # Простая логика для определения следующего IP
        # В реальном проекте лучше использовать более сложную логику
        base_ip = "10.0.0"
        for i in range(2, 255):  # Пропускаем .1 (сервер)
            candidate_ip = f"{base_ip}.{i}"
            if candidate_ip not in existing_ips:
                return candidate_ip
        
        raise Exception("Нет доступных IP адресов в подсети")
    
    def create_qr_code(self, config: str, output_path: str) -> str:
        """Создает QR-код для конфигурации WireGuard"""
        try:
            # Создаем временный файл с конфигурацией
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(config)
                temp_config = f.name
            
            # Генерируем QR-код
            qr_output = subprocess.check_output([
                "qrencode", "-t", "PNG", "-o", output_path, temp_config
            ], stderr=subprocess.PIPE)
            
            # Удаляем временный файл
            os.unlink(temp_config)
            
            return output_path
        except subprocess.CalledProcessError:
            # Fallback - возвращаем путь к конфигурации
            return temp_config
        except FileNotFoundError:
            # qrencode не установлен
            return None 