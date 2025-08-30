# VPN Bot с поддержкой OpenVPN и WireGuard

Этот проект расширяет функциональность VPN бота, добавляя поддержку OpenVPN и WireGuard помимо существующего Xray.

## 🚀 Возможности

- **Xray (VLESS)** - современный прокси-сервер
- **OpenVPN** - классический VPN протокол с сертификатами
- **WireGuard** - быстрый и современный VPN протокол
- Автоматическая генерация конфигураций
- Поддержка QR-кодов для WireGuard
- Система управления клиентами

## 📋 Требования

- Ubuntu/Debian сервер
- Python 3.8+
- Root права для установки VPN сервисов

## 🔧 Установка

### 1. Установка VPN сервисов

```bash
# Сделать скрипт исполняемым
chmod +x setup_vpn_services.sh

# Запустить установку (требует root прав)
sudo ./setup_vpn_services.sh
```

### 2. Настройка Python окружения

```bash
cd vpn_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Скопируйте `env_example.txt` в `.env` и заполните необходимые значения:

```bash
cp env_example.txt .env
nano .env
```

### 4. Запуск бота

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите бота
python bot.py
```

## 📁 Структура проекта

```
vpn_bot/
├── utils/
│   ├── generator.py          # Генератор Xray
│   ├── openvpn_generator.py # Генератор OpenVPN
│   ├── wireguard_generator.py # Генератор WireGuard
│   └── vpn_generator.py     # Универсальный генератор
├── config.py                 # Конфигурация
├── bot.py                    # Основной файл бота
└── requirements.txt          # Зависимости Python
```

## 🔐 Использование

### Генерация VPN конфигураций

```python
from utils.vpn_generator import UniversalVPNGenerator
from config import VPN_CONFIG

# Создаем генератор
generator = UniversalVPNGenerator(VPN_CONFIG)

# Генерируем Xray
result = generator.generate_vpn('xray', 'client1')

# Генерируем OpenVPN
result = generator.generate_vpn('openvpn', 'client1', 
                               server_ip='your_server_ip')

# Генерируем WireGuard
result = generator.generate_vpn('wireguard', 'client1',
                               generate_qr=True)
```

### Управление сервисами

```bash
# Статус OpenVPN
sudo systemctl status openvpn@server

# Статус WireGuard
sudo systemctl status wg-quick@wg0

# Добавление клиентов
sudo add-wg-client client_name
sudo add-ovpn-client client_name

# Просмотр активных клиентов WireGuard
sudo wg show wg0
```

## 📊 Мониторинг

### Логи OpenVPN
```bash
tail -f /var/log/openvpn/openvpn-status.log
```

### Логи WireGuard
```bash
sudo wg show wg0
```

### Системные логи
```bash
journalctl -u openvpn@server -f
journalctl -u wg-quick@wg0 -f
```

## 🔒 Безопасность

- Все сертификаты генерируются с использованием strong cryptography
- WireGuard использует современные криптографические алгоритмы
- OpenVPN настроен с TLS auth и strong ciphers
- Автоматическое управление firewall правилами

## 🛠️ Устранение неполадок

### OpenVPN не запускается
```bash
# Проверить конфигурацию
sudo openvpn --config /etc/openvpn/server.conf --test-crypto

# Проверить права доступа к сертификатам
sudo chown -R nobody:nogroup /etc/openvpn/
```

### WireGuard не подключается
```bash
# Проверить статус интерфейса
sudo ip link show wg0

# Проверить маршрутизацию
sudo ip route show table all
```

### Проблемы с сертификатами
```bash
# Пересоздать CA
cd /etc/openvpn/easy-rsa
./easyrsa clean-all
./easyrsa init-pki
./easyrsa build-ca nopass
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи сервисов
2. Убедитесь в корректности конфигурации
3. Проверьте сетевые настройки
4. Убедитесь в наличии всех зависимостей

## 📝 Лицензия

Проект распространяется под лицензией MIT. 