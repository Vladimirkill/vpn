#!/usr/bin/env python3
"""
Веб-админка для управления VPN пользователями и лимитами
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import json
import os
import subprocess
from datetime import datetime
import hashlib
import secrets

# Импортируем функции из существующего скрипта
from manage_user_limits import (
    get_user_keys, analyze_user_usage, enforce_user_limits,
    create_user_key, remove_user_key, count_active_connections,
    CLIENTS_DIR
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Конфигурация админки
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # "admin"
ADMIN_PORT = 5000
ADMIN_HOST = "0.0.0.0"

def hash_password(password):
    """Хеширует пароль"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_auth():
    """Проверяет аутентификацию"""
    return session.get('authenticated') == True

def require_auth(f):
    """Декоратор для проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_auth():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH:
            session['authenticated'] = True
            flash('Успешный вход в систему!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные учетные данные!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/')
@require_auth
def dashboard():
    """Главная страница админки"""
    try:
        users = get_user_keys()
        connections = count_active_connections()
        
        # Статистика
        total_users = len(users)
        total_keys = sum(len(user_keys) for user_keys in users.values())
        active_connections = len(connections)
        
        # Нарушения лимитов
        violations = []
        for client_name, keys in users.items():
            if len(keys) > 1:
                violations.append({
                    'type': 'keys',
                    'user': client_name,
                    'current': len(keys),
                    'limit': 1,
                    'message': f'Превышен лимит ключей: {len(keys)}/1'
                })
        
        return render_template('dashboard.html', 
                             users=users,
                             connections=connections,
                             stats={
                                 'total_users': total_users,
                                 'total_keys': total_keys,
                                 'active_connections': active_connections,
                                 'violations': len(violations)
                             },
                             violations=violations)
    except Exception as e:
        flash(f'Ошибка загрузки данных: {str(e)}', 'error')
        return render_template('dashboard.html', users={}, connections={}, stats={}, violations=[])

@app.route('/users')
@require_auth
def users_list():
    """Список пользователей"""
    try:
        users = get_user_keys()
        return render_template('users.html', users=users)
    except Exception as e:
        flash(f'Ошибка загрузки пользователей: {str(e)}', 'error')
        return render_template('users.html', users={})

@app.route('/user/<client_name>')
@require_auth
def user_detail(client_name):
    """Детали пользователя"""
    try:
        users = get_user_keys()
        if client_name not in users:
            flash('Пользователь не найден', 'error')
            return redirect(url_for('users_list'))
        
        user_keys = users[client_name]
        return render_template('user_detail.html', 
                             client_name=client_name, 
                             user_keys=user_keys)
    except Exception as e:
        flash(f'Ошибка загрузки данных пользователя: {str(e)}', 'error')
        return redirect(url_for('users_list'))

@app.route('/api/reset_limits/<client_name>', methods=['POST'])
@require_auth
def reset_user_limits(client_name):
    """API: Сброс лимитов для пользователя"""
    try:
        users = get_user_keys()
        if client_name not in users:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})
        
        user_keys = users[client_name]
        
        # Если у пользователя больше 1 ключа, удаляем все кроме самого нового
        if len(user_keys) > 1:
            # Сортируем по времени создания
            user_keys.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Удаляем все кроме первого (самого нового)
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
                except Exception as e:
                    print(f"Ошибка удаления ключа {key['uuid']}: {e}")
            
            return jsonify({
                'success': True, 
                'message': f'Лимиты сброшены. Удалено {removed_count} ключей',
                'removed_keys': removed_count
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'У пользователя только 1 ключ, сброс не требуется',
                'removed_keys': 0
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove_key/<client_name>/<uuid>', methods=['POST'])
@require_auth
def remove_key(client_name, uuid):
    """API: Удаление конкретного ключа"""
    try:
        success = remove_user_key(client_name, uuid)
        if success:
            return jsonify({'success': True, 'message': 'Ключ успешно удален'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось удалить ключ'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create_key/<client_name>', methods=['POST'])
@require_auth
def create_key(client_name):
    """API: Создание ключа для пользователя"""
    try:
        enforce_limits = request.json.get('enforce_limits', True)
        success = create_user_key(client_name, enforce_limits)
        
        if success:
            return jsonify({'success': True, 'message': 'Ключ успешно создан'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось создать ключ'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/enforce_limits', methods=['POST'])
@require_auth
def api_enforce_limits():
    """API: Принудительное применение лимитов"""
    try:
        actions = enforce_user_limits()
        return jsonify({
            'success': True, 
            'message': f'Выполнено действий: {len(actions)}',
            'actions': actions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
@require_auth
def api_stats():
    """API: Получение статистики"""
    try:
        users = get_user_keys()
        connections = count_active_connections()
        
        return jsonify({
            'total_users': len(users),
            'total_keys': sum(len(user_keys) for user_keys in users.values()),
            'active_connections': len(connections),
            'users': users,
            'connections': connections
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# HTML шаблоны встроены в код для простоты развертывания
@app.route('/templates/<template_name>')
def serve_template(template_name):
    """Служебный роут для шаблонов (не используется в продакшене)"""
    return "Template serving disabled"

if __name__ == '__main__':
    # Создаем директорию для шаблонов если её нет
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    print("🚀 Запуск VPN Admin Panel")
    print(f"📍 URL: http://{ADMIN_HOST}:{ADMIN_PORT}")
    print(f"👤 Логин: {ADMIN_USERNAME}")
    print(f"🔑 Пароль: admin")
    print("=" * 50)
    
    app.run(host=ADMIN_HOST, port=ADMIN_PORT, debug=True)