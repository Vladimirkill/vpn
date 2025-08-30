import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Определяем окружение
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
IS_DEV = ENVIRONMENT == "development"
IS_PROD = ENVIRONMENT == "production"

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Кошелёк для оплаты
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")

# Строка подключения к базе данных PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

# Админы бота (Telegram ID)
ADMIN_IDS = [
    int(os.getenv("ADMIN_ID_1", "0")),  # Основной админ
    int(os.getenv("ADMIN_ID_2", "0")),  # Дополнительный админ
]
# Удаляем нули из списка
ADMIN_IDS = [admin_id for admin_id in ADMIN_IDS if admin_id != 0]

# Конфигурация OpenVPN
OPENVPN_CONFIG = {
    'server_ip': os.getenv("OPENVPN_SERVER_IP", "146.103.125.210"),
    'server_port': int(os.getenv("OPENVPN_SERVER_PORT", "1195" if IS_DEV else "1194")),
    'ca_path': os.getenv("OPENVPN_CA_PATH", "/etc/openvpn/ca.crt"),
    'server_cert': os.getenv("OPENVPN_SERVER_CERT", "/etc/openvpn/server.crt"),
    'server_key': os.getenv("OPENVPN_SERVER_KEY", "/etc/openvpn/server.key"),
    'protocol': os.getenv("OPENVPN_PROTOCOL", "udp")
}

# Конфигурация WireGuard
WIREGUARD_CONFIG = {
    'server_public_key': os.getenv("WIREGUARD_SERVER_PUBLIC_KEY", "mzu+t3V6cDUVw6tCMt9qBv7oIUHdEuuFyxeVDrKmDFc="),
    'server_endpoint': os.getenv("WIREGUARD_SERVER_ENDPOINT", "146.103.125.210"),
    'server_port': int(os.getenv("WIREGUARD_SERVER_PORT", "51821" if IS_DEV else "51820")),
    'base_subnet': os.getenv("WIREGUARD_BASE_SUBNET", "10.1.0.0/24" if IS_DEV else "10.0.0.0/24")
}

# Конфигурация Xray для разных окружений
XRAY_CONFIG = {
    'port': 11443 if IS_DEV else 10443,
    'config_path': '/usr/local/etc/xray/dev_config.json' if IS_DEV else '/usr/local/etc/xray/config.json'
}

# Пути для генерации ключей (зависят от окружения)
PROJECT_ROOT = "/var/www/vpn/dev" if IS_DEV else "/var/www/vpn/prod"
PYTHON_EXECUTABLE = "/var/www/vpn/venv/bin/python"

GENERATION_PATHS = {
    'run_generate_script': f"{PROJECT_ROOT}/run_generate.py",
    'build_config_script': f"{PROJECT_ROOT}/xray/build_config.py",
    'xray_clients_dir': f"{PROJECT_ROOT}/xray/clients",
    'safe_restart_script': f"{PROJECT_ROOT}/safe_restart.py"
}

# Объединяем все конфигурации
VPN_CONFIG = {
    'openvpn_server_ip': OPENVPN_CONFIG['server_ip'],
    'openvpn_server_port': OPENVPN_CONFIG['server_port'],
    'openvpn_ca_path': OPENVPN_CONFIG['ca_path'],
    'openvpn_server_cert': OPENVPN_CONFIG['server_cert'],
    'openvpn_server_key': OPENVPN_CONFIG['server_key'],
    'openvpn_protocol': OPENVPN_CONFIG['protocol'],
    'wireguard_server_public_key': WIREGUARD_CONFIG['server_public_key'],
    'wireguard_server_endpoint': WIREGUARD_CONFIG['server_endpoint'],
    'wireguard_server_port': WIREGUARD_CONFIG['server_port'],
    'wireguard_base_subnet': WIREGUARD_CONFIG['base_subnet']
}