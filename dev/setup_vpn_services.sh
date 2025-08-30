#!/bin/bash

# Скрипт для установки и настройки OpenVPN и WireGuard серверов
# Запускать с правами root

set -e

echo "🚀 Начинаем установку VPN сервисов..."

# Обновляем систему
echo "📦 Обновляем систему..."
apt update && apt upgrade -y

# Устанавливаем необходимые пакеты
echo "📦 Устанавливаем необходимые пакеты..."
apt install -y openvpn easy-rsa wireguard qrencode iptables-persistent

# Создаем директории для VPN
echo "📁 Создаем директории..."
mkdir -p /etc/openvpn
mkdir -p /etc/wireguard
mkdir -p /var/log/vpn

# Настройка OpenVPN
echo "🔐 Настраиваем OpenVPN..."

# Копируем easy-rsa
cp -r /usr/share/easy-rsa /etc/openvpn/
cd /etc/openvpn/easy-rsa

# Создаем файл vars
cat > vars << EOF
export EASYRSA_REQ_COUNTRY="RU"
export EASYRSA_REQ_PROVINCE="Moscow"
export EASYRSA_REQ_CITY="Moscow"
export EASYRSA_REQ_ORG="VPN Organization"
export EASYRSA_REQ_EMAIL="admin@example.com"
export EASYRSA_REQ_OU="VPN OU"
export EASYRSA_KEY_SIZE=2048
export EASYRSA_ALGO=rsa
export EASYRSA_CA_EXPIRE=3650
export EASYRSA_CERT_EXPIRE=3650
EOF

# Инициализируем PKI
./easyrsa init-pki
./easyrsa build-ca nopass

# Генерируем сертификат сервера
./easyrsa gen-req server nopass
./easyrsa sign-req server server

# Генерируем Diffie-Hellman параметры
./easyrsa gen-dh

# Генерируем TLS auth ключ
openvpn --genkey secret /etc/openvpn/ta.key

# Копируем сертификаты
cp pki/ca.crt /etc/openvpn/
cp pki/issued/server.crt /etc/openvpn/
cp pki/private/server.key /etc/openvpn/
cp pki/dh.pem /etc/openvpn/

# Создаем конфигурацию сервера OpenVPN
cat > /etc/openvpn/server.conf << EOF
port 1194
proto udp
dev tun
ca ca.crt
cert server.crt
key server.key
dh dh.pem
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 8.8.8.8"
keepalive 10 120
tls-auth ta.key 0
cipher AES-256-CBC
auth SHA256
user nobody
group nogroup
persist-key
persist-tun
status openvpn-status.log
verb 3
explicit-exit-notify 1
EOF

# Настройка WireGuard
echo "🔒 Настраиваем WireGuard..."

# Генерируем ключи сервера
cd /etc/wireguard
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Создаем конфигурацию сервера WireGuard
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = \$(cat server_private.key)
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
SaveConfig = true
EOF

# Включаем IP forwarding
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Создаем systemd сервисы
echo "🔧 Создаем systemd сервисы..."

# OpenVPN сервис
cat > /etc/systemd/system/openvpn@server.service << EOF
[Unit]
Description=OpenVPN service for %I
After=network.target

[Service]
Type=notify
PrivateTmp=true
ExecStart=/usr/sbin/openvpn --config /etc/openvpn/%i.conf
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# WireGuard сервис
cat > /etc/systemd/system/wg-quick@wg0.service << EOF
[Unit]
Description=WireGuard VPN - wg0 interface
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/wg-quick up wg0
ExecStop=/usr/bin/wg-quick down wg0

[Install]
WantedBy=multi-user.target
EOF

# Включаем и запускаем сервисы
echo "🚀 Запускаем сервисы..."
systemctl daemon-reload
systemctl enable openvpn@server
systemctl enable wg-quick@wg0
systemctl start openvpn@server
systemctl start wg-quick@wg0

# Создаем скрипт для добавления клиентов WireGuard
cat > /usr/local/bin/add-wg-client << 'EOF'
#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Использование: $0 <client_name>"
    exit 1
fi

CLIENT_NAME=$1
CLIENT_IP=$(wg show wg0 endpoints | grep -v "none" | wc -l)
CLIENT_IP=$((CLIENT_IP + 2))

# Генерируем ключи клиента
wg genkey | tee /tmp/${CLIENT_NAME}_private.key | wg pubkey > /tmp/${CLIENT_NAME}_public.key

# Добавляем клиента в конфигурацию сервера
echo "" >> /etc/wireguard/wg0.conf
echo "# Client: ${CLIENT_NAME}" >> /etc/wireguard/wg0.conf
echo "[Peer]" >> /etc/wireguard/wg0.conf
echo "PublicKey = $(cat /tmp/${CLIENT_NAME}_public.key)" >> /etc/wireguard/wg0.conf
echo "AllowedIPs = 10.0.0.${CLIENT_IP}/32" >> /etc/wireguard/wg0.conf

# Создаем конфигурацию клиента
cat > /tmp/${CLIENT_NAME}.conf << CLIENT_CONFIG
[Interface]
PrivateKey = $(cat /tmp/${CLIENT_NAME}_private.key)
Address = 10.0.0.${CLIENT_IP}/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = $(cat /etc/wireguard/server_public.key)
Endpoint = $(curl -s ifconfig.me):51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
CLIENT_CONFIG

# Перезапускаем WireGuard
systemctl restart wg-quick@wg0

echo "Клиент ${CLIENT_NAME} добавлен с IP 10.0.0.${CLIENT_IP}"
echo "Конфигурация сохранена в /tmp/${CLIENT_NAME}.conf"
EOF

chmod +x /usr/local/bin/add-wg-client

# Создаем скрипт для добавления клиентов OpenVPN
cat > /usr/local/bin/add-ovpn-client << 'EOF'
#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Использование: $0 <client_name>"
    exit 1
fi

CLIENT_NAME=$1
cd /etc/openvpn/easy-rsa

# Генерируем сертификат клиента
./easyrsa gen-req ${CLIENT_NAME} nopass
./easyrsa sign-req client ${CLIENT_NAME}

# Создаем конфигурацию клиента
cat > /tmp/${CLIENT_NAME}.ovpn << CLIENT_CONFIG
client
dev tun
proto udp
remote $(curl -s ifconfig.me) 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-CBC
auth SHA256
key-direction 1
verb 3

<ca>
$(cat /etc/openvpn/ca.crt)
</ca>

<cert>
$(cat pki/issued/${CLIENT_NAME}.crt)
</cert>

<key>
$(cat pki/private/${CLIENT_NAME}.key)
</key>

<tls-auth>
$(cat /etc/openvpn/ta.key)
</tls-auth>
CLIENT_CONFIG

echo "Клиент ${CLIENT_NAME} добавлен"
echo "Конфигурация сохранена в /tmp/${CLIENT_NAME}.ovpn"
EOF

chmod +x /usr/local/bin/add-ovpn-client

echo "✅ Установка завершена!"
echo ""
echo "📋 Полезные команды:"
echo "  Добавить клиента WireGuard: add-wg-client <имя>"
echo "  Добавить клиента OpenVPN: add-ovpn-client <имя>"
echo "  Статус OpenVPN: systemctl status openvpn@server"
echo "  Статус WireGuard: systemctl status wg-quick@wg0"
echo "  Просмотр клиентов WireGuard: wg show wg0"
echo ""
echo "🔑 Ключи сервера:"
echo "  OpenVPN CA: /etc/openvpn/ca.crt"
echo "  WireGuard Public Key: $(cat /etc/wireguard/server_public.key)"
echo ""
echo "📁 Конфигурации:"
echo "  OpenVPN: /etc/openvpn/server.conf"
echo "  WireGuard: /etc/wireguard/wg0.conf" 