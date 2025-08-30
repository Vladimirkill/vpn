#!/usr/bin/env python3
"""
Скрипт для управления лимитами пользователей:
- 1 ключ для одного пользователя
- Максимум 3 устройства для 1 ключа
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

CLIENTS_DIR = "/var/www/vpn/xray/clients"

# Типы пулов ключей
KEY_POOL_TYPES = {
    'weekly': {
        'name': 'Недельный',
        'duration_days': 7,
        'description': 'Ключ действует 7 дней'
    },
    'monthly': {
        'name': 'Месячный', 
        'duration_days': 30,
        'description': 'Ключ действует 30 дней'
    },
    'unlimited': {
        'name': 'Безлимитный',
        'duration_days': None,
        'description': 'Ключ без ограничения по времени'
    }
}

def calculate_expiry_date(pool_type: str) -> str:
    """Вычисляет дату истечения ключа"""
    if pool_type not in KEY_POOL_TYPES:
        pool_type = 'unlimited'
    
    pool_config = KEY_POOL_TYPES[pool_type]
    
    if pool_config['duration_days'] is None:
        return None  # Безлимитный ключ
    
    expiry_date = datetime.now() + timedelta(days=pool_config['duration_days'])
    return expiry_date.isoformat()

def is_key_expired(metadata: dict) -> bool:
    """Проверяет, истек ли ключ"""
    expires_at = metadata.get('expires_at')
    if not expires_at:
        return False  # Безлимитный ключ
    
    try:
        expiry_date = datetime.fromisoformat(expires_at)
        return datetime.now() > expiry_date
    except (ValueError, TypeError):
        return False

def get_key_status(metadata: dict) -> dict:
    """Получает статус ключа (активен/истек/дней осталось)"""
    expires_at = metadata.get('expires_at')
    pool_type = metadata.get('pool_type', 'unlimited')
    
    if not expires_at:
        return {
            'status': 'unlimited',
            'message': '♾️ Безлимитный',
            'days_left': None,
            'expired': False
        }
    
    try:
        expiry_date = datetime.fromisoformat(expires_at)
        now = datetime.now()
        
        if now > expiry_date:
            return {
                'status': 'expired',
                'message': '❌ Истек',
                'days_left': 0,
                'expired': True
            }
        
        days_left = (expiry_date - now).days
        pool_name = KEY_POOL_TYPES.get(pool_type, {}).get('name', 'Неизвестный')
        
        if days_left == 0:
            return {
                'status': 'expires_today',
                'message': f'⏰ {pool_name} (истекает сегодня)',
                'days_left': 0,
                'expired': False
            }
        else:
            return {
                'status': 'active',
                'message': f'✅ {pool_name} ({days_left} дн.)',
                'days_left': days_left,
                'expired': False
            }
            
    except (ValueError, TypeError):
        return {
            'status': 'unknown',
            'message': '❓ Неизвестно',
            'days_left': None,
            'expired': False
        }

def reload_xray_config():
    """Перестраивает конфигурацию и перезагружает Xray"""
    try:
        import subprocess
        
        # Перестраиваем конфигурацию (build_config.py уже делает reload)
        build_result = subprocess.run([
            "python3", "/var/www/vpn/xray/build_config.py"
        ], capture_output=True, text=True, timeout=30)
        
        if build_result.returncode == 0:
            print("✅ Конфигурация перестроена и Xray перезагружен")
            return True
        else:
            print(f"⚠️ Ошибка перестройки конфигурации: {build_result.stderr}")
            
            # Fallback: пытаемся перезапустить вручную
            print("🔄 Пытаемся перезапустить Xray вручную...")
            restart_result = subprocess.run([
                "systemctl", "restart", "xray"
            ], capture_output=True, text=True, timeout=30)
            
            if restart_result.returncode == 0:
                print("✅ Xray перезапущен вручную")
                return True
            else:
                print(f"❌ Ошибка перезапуска Xray: {restart_result.stderr}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка перезагрузки конфигурации: {e}")
        return False

def generate_vless_url(uuid, short_id, client_name):
    """Генерирует VLESS URL для ключа"""
    # Параметры сервера (из generate_vless_urls.py)
    server = "146.103.125.210:8443"
    public_key = "kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ"
    
    # Формируем VLESS URL (обновлено для iOS Safari совместимости)
    vless_url = f"vless://{uuid}@{server}?security=reality&sni=www.apple.com&fp=safari&pbk={public_key}&sid={short_id}&spx=/&type=tcp&flow=xtls-rprx-vision&encryption=none#{client_name}"
    
    return vless_url

def get_user_keys():
    """Получает список всех пользователей и их ключей"""
    users = {}
    
    if not os.path.exists(CLIENTS_DIR):
        return users
    
    for filename in os.listdir(CLIENTS_DIR):
        if filename.endswith('.json') and not filename.startswith('REMOVED_'):
            try:
                with open(os.path.join(CLIENTS_DIR, filename), 'r') as f:
                    client_data = json.load(f)
                    metadata = client_data.get('_metadata', {})
                    client_name = metadata.get('client_name', 'unknown')
                    
                    if client_name not in users:
                        users[client_name] = []
                    
                    uuid = client_data.get('id')
                    short_id = client_data.get('shortId', '')
                    
                    # Генерируем VLESS URL
                    vless_url = generate_vless_url(uuid, short_id, client_name) if uuid and short_id else None
                    
                    # Получаем статус ключа
                    key_status = get_key_status(metadata)
                    
                    users[client_name].append({
                        'id': uuid,
                        'uuid': uuid,
                        'filename': filename,
                        'created_at': metadata.get('created_at', 'unknown'),
                        'pool_type': metadata.get('pool_type', 'unlimited'),
                        'expires_at': metadata.get('expires_at'),
                        'status': key_status,
                        'max_connections': metadata.get('max_connections', 3),
                        'max_devices': metadata.get('max_devices', 3),
                        'enforce_limits': metadata.get('enforce_limits', True),
                        'vless_url': vless_url,
                        'metadata': metadata
                    })
            except Exception as e:
                print(f"⚠️ Ошибка чтения файла {filename}: {e}")
    
    return users

def count_active_connections():
    """Подсчитывает активные соединения по IP адресам"""
    try:
        result = subprocess.run(['ss', '-tn', 'state', 'established'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {}
        
        connections = {}
        for line in result.stdout.split('\n'):
            if ':8443' in line:
                parts = line.split()
                if len(parts) >= 4:
                    if parts[3].endswith(':8443'):
                        client_ip = parts[2].split(':')[0]
                        if client_ip not in connections:
                            connections[client_ip] = 0
                        connections[client_ip] += 1
        
        return connections
    except Exception as e:
        print(f"⚠️ Ошибка подсчета соединений: {e}")
        return {}

def analyze_user_usage():
    """Анализирует использование пользователями"""
    users = get_user_keys()
    connections = count_active_connections()
    
    print("🔍 Анализ использования пользователями")
    print("=" * 80)
    
    total_users = len(users)
    total_keys = sum(len(user_keys) for user_keys in users.values())
    
    print(f"📊 Общая статистика:")
    print(f"   Всего пользователей: {total_users}")
    print(f"   Всего ключей: {total_keys}")
    print(f"   Активных IP адресов: {len(connections)}")
    print()
    
    violations = []
    
    for client_name, keys in users.items():
        print(f"👤 Пользователь: {client_name}")
        print(f"   Ключей: {len(keys)}")
        
        # Проверяем лимит ключей (максимум 1)
        if len(keys) > 1:
            violations.append(f"❌ {client_name}: превышен лимит ключей ({len(keys)}/1)")
            print(f"   ⚠️ ПРЕВЫШЕН ЛИМИТ КЛЮЧЕЙ: {len(keys)}/1")
        
        for key in keys:
            print(f"   🔑 {key['uuid'][:8]}... | Создан: {key['created_at']}")
            print(f"      Лимиты: {key['max_connections']} соединений, {key['max_devices']} устройств")
            print(f"      Ограничения: {'Включены' if key['enforce_limits'] else 'Отключены'}")
        
        # Подсчитываем примерное количество устройств
        estimated_devices = len(connections) if connections else 0
        if estimated_devices > 3:
            violations.append(f"❌ {client_name}: превышен лимит устройств ({estimated_devices}/3)")
            print(f"   ⚠️ ПРЕВЫШЕН ЛИМИТ УСТРОЙСТВ: {estimated_devices}/3")
        else:
            print(f"   ✅ Устройств: {estimated_devices}/3")
        
        print()
    
    return violations

def enforce_user_limits():
    """Принудительно применяет лимиты пользователей"""
    print("🛡️ Применение лимитов пользователей")
    print("=" * 80)
    
    users = get_user_keys()
    actions_taken = []
    
    for client_name, keys in users.items():
        print(f"👤 Обработка пользователя: {client_name}")
        
        # Если у пользователя больше 1 ключа, оставляем только самый новый
        if len(keys) > 1:
            print(f"   ⚠️ Найдено {len(keys)} ключей (лимит: 1)")
            
            # Сортируем по времени создания
            keys.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Оставляем только первый (самый новый)
            keys_to_remove = keys[1:]
            
            for key in keys_to_remove:
                try:
                    old_filename = key['filename']
                    new_filename = f"REMOVED_{old_filename}"
                    old_path = os.path.join(CLIENTS_DIR, old_filename)
                    new_path = os.path.join(CLIENTS_DIR, new_filename)
                    
                    os.rename(old_path, new_path)
                    actions_taken.append(f"🗑️ Удален ключ {key['uuid'][:8]}... для {client_name}")
                    print(f"      🗑️ Удален ключ: {key['uuid'][:8]}...")
                except Exception as e:
                    print(f"      ❌ Ошибка удаления ключа: {e}")
        
        print(f"   ✅ Осталось ключей: {min(len(keys), 1)}")
        print()
    
    # Если были удалены ключи, перезагружаем конфигурацию
    if actions_taken:
        print(f"\n🔧 Применение изменений...")
        reload_success = reload_xray_config()
        if reload_success:
            print("✅ Все удаленные ключи деактивированы!")
        else:
            print("⚠️ Ключи удалены, но могут еще работать до перезапуска Xray")
    
    return actions_taken

def create_pool_key(client_name: str, pool_type: str = 'unlimited', enforce_limits: bool = True):
    """Создает ключ для пользователя с указанным типом пула"""
    if pool_type not in KEY_POOL_TYPES:
        print(f"❌ Неизвестный тип пула: {pool_type}")
        print(f"   Доступные типы: {', '.join(KEY_POOL_TYPES.keys())}")
        return False
    
    pool_config = KEY_POOL_TYPES[pool_type]
    print(f"🔑 Создание {pool_config['name'].lower()} ключа для: {client_name}")
    print(f"   {pool_config['description']}")
    print("=" * 80)
    
    # Проверяем существующие ключи
    users = get_user_keys()
    
    if client_name in users and len(users[client_name]) >= 1:
        print(f"❌ Пользователь {client_name} уже имеет ключ")
        print(f"   Существующие ключи:")
        for key in users[client_name]:
            status_msg = key['status']['message']
            print(f"   🔑 {key['uuid'][:8]}... | {status_msg} | Создан: {key['created_at']}")
        
        if enforce_limits:
            print(f"\n💡 Для создания нового ключа сначала удалите существующий")
            return False
        else:
            print(f"\n⚠️ Создание ключа без ограничений...")
    
    # Создаем ключ
    try:
        from xray.generate_client import generate_vless_client
        
        result = generate_vless_client(
            clients_dir=CLIENTS_DIR,
            flow="xtls-rprx-vision",
            host="146.103.125.210",
            port=443,
            sni="www.cloudflare.com",
            client_name=client_name,
            enforce_limits=enforce_limits
        )
        
        if "error" in result:
            print(f"❌ Ошибка создания ключа: {result['error']}")
            if "details" in result:
                print(f"   Детали: {result['details']}")
            return False
        
        # Добавляем метаданные пула
        client_file = result['file']
        expires_at = calculate_expiry_date(pool_type)
        
        # Обновляем файл ключа с метаданными пула
        try:
            with open(client_file, 'r') as f:
                client_data = json.load(f)
            
            if '_metadata' not in client_data:
                client_data['_metadata'] = {}
            
            client_data['_metadata']['pool_type'] = pool_type
            client_data['_metadata']['expires_at'] = expires_at
            client_data['_metadata']['updated_at'] = datetime.now().isoformat()
            
            with open(client_file, 'w') as f:
                json.dump(client_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Ошибка обновления метаданных: {e}")
        
        print(f"✅ {pool_config['name']} ключ успешно создан!")
        print(f"   UUID: {result['uuid']}")
        print(f"   Short ID: {result['shortId']}")
        print(f"   Файл: {result['file']}")
        print(f"   Тип пула: {pool_config['name']}")
        
        if expires_at:
            expiry_date = datetime.fromisoformat(expires_at)
            print(f"   Истекает: {expiry_date.strftime('%d.%m.%Y %H:%M')}")
        else:
            print(f"   Срок действия: Безлимитный")
            
        print(f"   Лимиты: {result['limits']}")
        print(f"\n🔗 VLESS ссылка:")
        print(f"   {result['link']}")
        
        # Перестраиваем конфигурацию и перезагружаем Xray
        print(f"\n🔧 Применение конфигурации...")
        reload_success = reload_xray_config()
        if reload_success:
            print("✅ Ключ активирован!")
        else:
            print("⚠️ Ключ создан, но может не работать до перезапуска Xray")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания ключа: {e}")
        return False

def create_user_key(client_name: str, enforce_limits: bool = True):
    """Создает ключ для пользователя с проверкой лимитов"""
    print(f"🔑 Создание ключа для пользователя: {client_name}")
    print("=" * 80)
    
    # Проверяем существующие ключи
    users = get_user_keys()
    
    if client_name in users and len(users[client_name]) >= 1:
        print(f"❌ Пользователь {client_name} уже имеет ключ")
        print(f"   Существующие ключи:")
        for key in users[client_name]:
            print(f"   🔑 {key['uuid'][:8]}... | Создан: {key['created_at']}")
        
        if enforce_limits:
            print(f"\n💡 Для создания нового ключа сначала удалите существующий")
            return False
        else:
            print(f"\n⚠️ Создание ключа без ограничений...")
    
    # Создаем ключ
    try:
        from xray.generate_client import generate_vless_client
        
        result = generate_vless_client(
            clients_dir=CLIENTS_DIR,
            flow="xtls-rprx-vision",
            host="146.103.125.210",
            port=443,
            sni="www.cloudflare.com",
            client_name=client_name,
            enforce_limits=enforce_limits
        )
        
        if "error" in result:
            print(f"❌ Ошибка создания ключа: {result['error']}")
            if "details" in result:
                print(f"   Детали: {result['details']}")
            return False
        
        print(f"✅ Ключ успешно создан!")
        print(f"   UUID: {result['uuid']}")
        print(f"   Short ID: {result['shortId']}")
        print(f"   Файл: {result['file']}")
        print(f"   Лимиты: {result['limits']}")
        print(f"\n🔗 VLESS ссылка:")
        print(f"   {result['link']}")
        
        # Перестраиваем конфигурацию и перезагружаем Xray
        print(f"\n🔧 Применение конфигурации...")
        reload_success = reload_xray_config()
        if reload_success:
            print("✅ Ключ активирован!")
        else:
            print("⚠️ Ключ создан, но может не работать до перезапуска Xray")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания ключа: {e}")
        return False

def cleanup_expired_keys():
    """Удаляет все просроченные ключи"""
    print("🧹 Очистка просроченных ключей")
    print("=" * 80)
    
    users = get_user_keys()
    expired_keys = []
    
    for client_name, keys in users.items():
        for key in keys:
            if key['status']['expired']:
                expired_keys.append({
                    'client_name': client_name,
                    'key': key
                })
    
    if not expired_keys:
        print("✅ Просроченных ключей не найдено")
        return []
    
    print(f"⚠️ Найдено {len(expired_keys)} просроченных ключей:")
    
    removed_keys = []
    for item in expired_keys:
        client_name = item['client_name']
        key = item['key']
        
        try:
            old_filename = key['filename']
            new_filename = f"EXPIRED_{old_filename}"
            old_path = os.path.join(CLIENTS_DIR, old_filename)
            new_path = os.path.join(CLIENTS_DIR, new_filename)
            
            os.rename(old_path, new_path)
            removed_keys.append(f"🗑️ {client_name}: {key['uuid'][:8]}... ({key['status']['message']})")
            print(f"   🗑️ Удален: {client_name} - {key['uuid'][:8]}... ({key['status']['message']})")
            
        except Exception as e:
            print(f"   ❌ Ошибка удаления {client_name} - {key['uuid'][:8]}...: {e}")
    
    if removed_keys:
        print(f"\n🔧 Применение изменений...")
        reload_success = reload_xray_config()
        if reload_success:
            print("✅ Просроченные ключи деактивированы!")
        else:
            print("⚠️ Ключи удалены, но могут еще работать до перезапуска Xray")
    
    return removed_keys

def show_key_pools():
    """Показывает статистику по пулам ключей"""
    print("📊 Статистика пулов ключей")
    print("=" * 80)
    
    users = get_user_keys()
    
    # Статистика по типам пулов
    pool_stats = {}
    total_keys = 0
    expired_count = 0
    expiring_soon = 0  # истекают в течение 3 дней
    
    for client_name, keys in users.items():
        for key in keys:
            pool_type = key['pool_type']
            status = key['status']
            
            if pool_type not in pool_stats:
                pool_stats[pool_type] = {
                    'count': 0,
                    'active': 0,
                    'expired': 0,
                    'expiring_soon': 0
                }
            
            pool_stats[pool_type]['count'] += 1
            total_keys += 1
            
            if status['expired']:
                pool_stats[pool_type]['expired'] += 1
                expired_count += 1
            elif status['days_left'] is not None and status['days_left'] <= 3:
                pool_stats[pool_type]['expiring_soon'] += 1
                expiring_soon += 1
            else:
                pool_stats[pool_type]['active'] += 1
    
    print(f"📈 Общая статистика:")
    print(f"   Всего ключей: {total_keys}")
    print(f"   Активных: {total_keys - expired_count}")
    print(f"   Просроченных: {expired_count}")
    print(f"   Истекают в течение 3 дней: {expiring_soon}")
    print()
    
    print(f"🏷️ По типам пулов:")
    for pool_type, stats in pool_stats.items():
        pool_name = KEY_POOL_TYPES.get(pool_type, {}).get('name', pool_type)
        print(f"   {pool_name}:")
        print(f"      Всего: {stats['count']}")
        print(f"      Активных: {stats['active']}")
        if stats['expired'] > 0:
            print(f"      Просроченных: {stats['expired']}")
        if stats['expiring_soon'] > 0:
            print(f"      Истекают скоро: {stats['expiring_soon']}")
        print()
    
    # Детальная информация по пользователям
    if users:
        print(f"👥 Детальная информация:")
        for client_name, keys in users.items():
            print(f"   👤 {client_name}:")
            for key in keys:
                pool_name = KEY_POOL_TYPES.get(key['pool_type'], {}).get('name', key['pool_type'])
                status_msg = key['status']['message']
                print(f"      🔑 {key['uuid'][:8]}... | {status_msg}")
            print()

def remove_user_key(client_name: str, uuid: str = None):
    """Удаляет ключ пользователя"""
    print(f"🗑️ Удаление ключа для пользователя: {client_name}")
    print("=" * 80)
    
    users = get_user_keys()
    
    if client_name not in users:
        print(f"❌ Пользователь {client_name} не найден")
        return False
    
    user_keys = users[client_name]
    
    if not user_keys:
        print(f"❌ У пользователя {client_name} нет ключей")
        return False
    
    if uuid:
        # Удаляем конкретный ключ
        key_to_remove = None
        for key in user_keys:
            if key['uuid'] == uuid:
                key_to_remove = key
                break
        
        if not key_to_remove:
            print(f"❌ Ключ {uuid} не найден у пользователя {client_name}")
            return False
    else:
        # Удаляем самый старый ключ
        key_to_remove = min(user_keys, key=lambda x: x['created_at'])
    
    try:
        old_filename = key_to_remove['filename']
        new_filename = f"REMOVED_{old_filename}"
        old_path = os.path.join(CLIENTS_DIR, old_filename)
        new_path = os.path.join(CLIENTS_DIR, new_filename)
        
        os.rename(old_path, new_path)
        print(f"✅ Ключ {key_to_remove['uuid'][:8]}... удален")
        print(f"   Файл переименован: {old_filename} → {new_filename}")
        
        # Перестраиваем конфигурацию и перезагружаем Xray
        print(f"\n🔧 Применение изменений...")
        reload_success = reload_xray_config()
        if reload_success:
            print("✅ Ключ деактивирован!")
        else:
            print("⚠️ Ключ удален, но может еще работать до перезапуска Xray")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка удаления ключа: {e}")
        return False

def reset_user_limits(client_name: str):
    """Сбрасывает лимиты конкретного пользователя (удаляет все ключи кроме самого нового)"""
    print(f"🔄 Сброс лимитов для пользователя: {client_name}")
    print("=" * 80)
    
    users = get_user_keys()
    
    if client_name not in users:
        print(f"❌ Пользователь {client_name} не найден")
        return False
    
    user_keys = users[client_name]
    
    if len(user_keys) <= 1:
        print(f"✅ У пользователя {client_name} только {len(user_keys)} ключ, сброс не требуется")
        return True
    
    print(f"⚠️ Найдено {len(user_keys)} ключей (лимит: 1)")
    
    # Сортируем по времени создания и оставляем только самый новый
    user_keys.sort(key=lambda x: x['created_at'], reverse=True)
    keys_to_remove = user_keys[1:]
    
    removed_count = 0
    for key in keys_to_remove:
        try:
            old_filename = key['filename']
            new_filename = f"REMOVED_{old_filename}"
            old_path = os.path.join(CLIENTS_DIR, old_filename)
            new_path = os.path.join(CLIENTS_DIR, new_filename)
            
            os.rename(old_path, new_path)
            removed_count += 1
            print(f"   🗑️ Удален ключ: {key['uuid'][:8]}...")
        except Exception as e:
            print(f"   ❌ Ошибка удаления ключа {key['uuid'][:8]}...: {e}")
    
    print(f"✅ Сброс завершен. Удалено {removed_count} ключей")
    print(f"✅ Осталось ключей: 1")
    
    # Если были удалены ключи, перезагружаем конфигурацию
    if removed_count > 0:
        print(f"\n🔧 Применение изменений...")
        reload_success = reload_xray_config()
        if reload_success:
            print("✅ Удаленные ключи деактивированы!")
        else:
            print("⚠️ Ключи удалены, но могут еще работать до перезапуска Xray")
    
    return removed_count > 0

def update_user_limits(client_name: str, max_connections: int = 3, max_devices: int = 3):
    """Обновляет лимиты для всех ключей пользователя"""
    print(f"⚙️ Обновление лимитов для пользователя: {client_name}")
    print(f"   Новые лимиты: {max_connections} соединений, {max_devices} устройств")
    print("=" * 80)
    
    users = get_user_keys()
    
    if client_name not in users:
        print(f"❌ Пользователь {client_name} не найден")
        return False
    
    user_keys = users[client_name]
    updated_count = 0
    
    for key in user_keys:
        try:
            file_path = os.path.join(CLIENTS_DIR, key['filename'])
            
            # Читаем файл ключа
            with open(file_path, 'r') as f:
                client_data = json.load(f)
            
            # Обновляем метаданные
            if '_metadata' not in client_data:
                client_data['_metadata'] = {}
            
            client_data['_metadata']['max_connections'] = max_connections
            client_data['_metadata']['max_devices'] = max_devices
            client_data['_metadata']['updated_at'] = datetime.now().isoformat()
            
            # Сохраняем обновленный файл
            with open(file_path, 'w') as f:
                json.dump(client_data, f, indent=2)
            
            updated_count += 1
            print(f"   ✅ Обновлен ключ: {key['uuid'][:8]}...")
            
        except Exception as e:
            print(f"   ❌ Ошибка обновления ключа {key['uuid'][:8]}...: {e}")
    
    print(f"✅ Обновление завершено. Обновлено {updated_count} ключей")
    
    return updated_count > 0

def reset_and_update_user_limits(client_name: str, max_connections: int = 3, max_devices: int = 3):
    """Комбинированная функция: сбрасывает лимиты и устанавливает новые"""
    print(f"🔄 Полный сброс и обновление лимитов для: {client_name}")
    print("=" * 80)
    
    # Сначала сбрасываем лимиты (удаляем лишние ключи)
    reset_success = reset_user_limits(client_name)
    
    if not reset_success:
        print("⚠️ Сброс не выполнен, но продолжаем обновление лимитов...")
    
    print()  # Пустая строка для разделения
    
    # Затем обновляем лимиты оставшихся ключей
    update_success = update_user_limits(client_name, max_connections, max_devices)
    
    return reset_success or update_success

def main():
    """Главная функция"""
    print("🛡️ Система управления пулами ключей VPN")
    print("=" * 80)
    
    while True:
        print("\n📋 Доступные действия:")
        print("1. 📊 Статистика пулов ключей")
        print("2. 🔑 Создать ключ (с выбором пула)")
        print("3. 🗑️ Удалить ключ пользователя")
        print("4. 🧹 Очистить просроченные ключи")
        print("5. 🛡️ Применить лимиты (удалить лишние ключи)")
        print("6. 🔍 Показать всех пользователей")
        print("7. 📈 Анализ использования (старый)")
        print("0. 🚪 Выход")
        
        choice = input("\nВыберите действие (0-7): ").strip()
        
        if choice == "0":
            print("👋 До свидания!")
            break
        elif choice == "1":
            show_key_pools()
        elif choice == "2":
            client_name = input("Введите имя пользователя: ").strip()
            if client_name:
                print("\n🏷️ Выберите тип пула:")
                for key, config in KEY_POOL_TYPES.items():
                    print(f"   {key}: {config['name']} - {config['description']}")
                
                pool_type = input("\nТип пула (weekly/monthly/unlimited): ").strip().lower()
                if pool_type not in KEY_POOL_TYPES:
                    pool_type = 'unlimited'
                    print(f"⚠️ Неизвестный тип, используется: unlimited")
                
                enforce = input("Применять лимиты? (y/n): ").strip().lower() != 'n'
                create_pool_key(client_name, pool_type, enforce)
        elif choice == "3":
            client_name = input("Введите имя пользователя: ").strip()
            if client_name:
                uuid = input("Введите UUID ключа (или Enter для удаления самого старого): ").strip()
                remove_user_key(client_name, uuid if uuid else None)
        elif choice == "4":
            cleanup_expired_keys()
        elif choice == "5":
            actions = enforce_user_limits()
            if actions:
                print("\n✅ Выполненные действия:")
                for action in actions:
                    print(f"   {action}")
            else:
                print("\n✅ Действия не требуются")
        elif choice == "6":
            users = get_user_keys()
            print(f"\n👥 Все пользователи ({len(users)}):")
            for client_name, keys in users.items():
                status_info = []
                for key in keys:
                    status_info.append(key['status']['message'])
                print(f"   👤 {client_name}: {len(keys)} ключей ({', '.join(status_info)})")
        elif choice == "7":
            violations = analyze_user_usage()
            if violations:
                print("\n🚨 Найдены нарушения:")
                for violation in violations:
                    print(f"   {violation}")
            else:
                print("\n✅ Нарушений не найдено")
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main() 