import subprocess
import os
import tempfile
from datetime import datetime, timedelta
import shlex

class OpenVPNGenerator:
    def __init__(self, ca_path="/etc/openvpn/ca.crt", server_cert="/etc/openvpn/server.crt", server_key="/etc/openvpn/server.key"):
        self.ca_path = ca_path
        self.server_cert = server_cert
        self.server_key = server_key
        self.easy_rsa_path = "/usr/share/easy-rsa"
        
    def generate_client_cert(self, client_name: str) -> dict:
        """Генерирует сертификат клиента OpenVPN используя существующую PKI"""
        try:
            easy_rsa_dir = "/etc/openvpn/easy-rsa"
            cert_path = os.path.join(easy_rsa_dir, "pki", "issued", f"{client_name}.crt")
            key_path = os.path.join(easy_rsa_dir, "pki", "private", f"{client_name}.key")
            
            # Проверяем, существует ли уже сертификат
            if not os.path.exists(cert_path):
                # Генерируем клиентский сертификат
                subprocess.run([
                    "./easyrsa", "gen-req", client_name, "nopass"
                ], cwd=easy_rsa_dir, check=True, input="\n", text=True)
                
                # Подписываем сертификат
                subprocess.run([
                    "./easyrsa", "sign-req", "client", client_name
                ], cwd=easy_rsa_dir, check=True, input="yes\n", text=True)
            
            # Читаем сгенерированные файлы
            with open(cert_path, 'r') as f:
                client_cert = f.read()
            with open(key_path, 'r') as f:
                client_key = f.read()
                
            return {
                'cert': client_cert,
                'key': client_key,
                'ca': self._read_ca_cert(),
                'ta_key': self._read_ta_key()
            }
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ошибка генерации сертификата: {e}")
        except FileNotFoundError as e:
            raise Exception(f"Файл сертификата не найден: {e}")
    
    def _read_ca_cert(self) -> str:
        """Читает CA сертификат"""
        try:
            with open(self.ca_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def _generate_ta_key(self) -> str:
        """Генерирует TLS auth ключ"""
        try:
            result = subprocess.run([
                "openvpn", "--genkey", "secret"
            ], capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def _read_ta_key(self) -> str:
        """Читает TLS auth ключ"""
        try:
            with open("/etc/openvpn/ta.key", 'r') as f:
                return f.read()
        except FileNotFoundError:
            return self._generate_ta_key()
    
    def create_client_config(self, client_name: str, server_ip: str, server_port: int = 1194, protocol: str = "udp") -> str:
        """Создает конфигурацию клиента OpenVPN"""
        # Генерируем сертификат клиента один раз
        client_certs = self.generate_client_cert(client_name)
        
        config = f"""# OpenVPN Client Configuration for {client_name}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

client
dev tun
proto {protocol}
remote {server_ip} {server_port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-CBC
auth SHA256
key-direction 1
verb 3

# CA Certificate
<ca>
{client_certs['ca']}
</ca>

# Client Certificate
<cert>
{client_certs['cert']}
</cert>

# Client Key
<key>
{client_certs['key']}
</key>

# TLS Auth Key
<tls-auth>
{client_certs['ta_key']}
</tls-auth>
        """
        return config
    
    def save_client_config(self, client_name: str, config: str, output_dir: str = "/tmp") -> str:
        """Сохраняет конфигурацию клиента в файл"""
        filename = f"{client_name}.ovpn"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(config)
        
        return filepath 