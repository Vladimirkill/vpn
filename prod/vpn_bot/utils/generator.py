import subprocess
import os
import json
from datetime import datetime
import shlex
from config import GENERATION_PATHS, PYTHON_EXECUTABLE, PROJECT_ROOT

LOG_PATH = f"{PROJECT_ROOT}/vpn_bot/vpn_generator.log"
BUILD_SCRIPT = GENERATION_PATHS['build_config_script']

def log_output(stdout: str, stderr: str):
    with open(LOG_PATH, "a") as f:
        f.write(f"\n=== [{datetime.now()}] Генерация VPN ключа ===\n")
        f.write("STDOUT:\n" + stdout.strip() + "\n")
        f.write("STDERR:\n" + stderr.strip() + "\n")

def generate_vpn_link(client_name: str = "vpn") -> tuple:
    """Генерирует VPN ключ и возвращает (link, uuid)"""
    # 🔧 Шаг 1: Генерация ключа через run_generate.py
    try:
        result = subprocess.run(
            [PYTHON_EXECUTABLE, GENERATION_PATHS['run_generate_script'], client_name],
            capture_output=True,
            text=True,
            timeout=60  # Увеличиваем таймаут до 60 секунд
        )
    except subprocess.TimeoutExpired:
        return "❌ Таймаут при генерации ключа", None
    except Exception as e:
        return f"❌ Ошибка генерации: {e}", None

    # Логируем вывод
    log_output(result.stdout, result.stderr)

    # 🔍 Проверяем на ошибки в выводе
    if "❌ Ошибка создания ключа:" in result.stdout:
        # Не проталкиваем подробности stdout в сообщение пользователю.
        # Если у пользователя уже есть ключ, вернем существующую ссылку.
        try:
            from xray.generate_client import generate_vless_client
            existing_client_result = generate_vless_client(
                clients_dir=GENERATION_PATHS['xray_clients_dir'],
                flow="xtls-rprx-vision",
                host="146.103.125.210",
                port=443,
                sni="www.cloudflare.com",
                client_name=client_name,
                enforce_limits=False
            )
            if "error" not in existing_client_result and existing_client_result.get("link"):
                return existing_client_result.get("link"), existing_client_result.get("uuid")
        except Exception:
            pass
        # Фолбек: краткая ошибка без лишних деталей
        return "❌ Уже есть VPN ключ", None

    # 🔍 Поиск строки с VLESS-ссылкой и UUID
    vless_link = None
    uuid = None
    
    for line in result.stdout.splitlines():
        line = line.strip()
        if "UUID:" in line:
            uuid = line.split("UUID:", 1)[1].strip()
        elif "vless://" in line:
            # Извлекаем только саму ссылку, убирая префикс "Ссылка: "
            if "Ссылка: " in line:
                vless_link = line.split("Ссылка: ", 1)[1]
            else:
                vless_link = line

    if not vless_link:
        return "❌ Не удалось сгенерировать ключ.", None

    # 🔁 Шаг 2: Сборка финального конфига (с таймаутом)
    try:
        build_result = subprocess.run([PYTHON_EXECUTABLE, BUILD_SCRIPT], capture_output=True, text=True, timeout=15)
        if build_result.returncode != 0:
            log_output("", f"[Build Error] {build_result.stderr}")
            return "❌ Ошибка сборки конфига.", None
    except subprocess.TimeoutExpired:
        return "❌ Таймаут при сборке конфига", None
    except Exception as e:
        return f"❌ Ошибка сборки: {e}", None

    # 🔄 Шаг 3: Безопасный перезапуск Xray с защитой от утечки IP
    try:
        # Используем безопасный перезапуск для защиты IP пользователей
        safe_restart_script = GENERATION_PATHS['safe_restart_script']
        
        if os.path.exists(safe_restart_script):
            log_output("🛡️ Используем безопасный перезапуск Xray", "")
            log_output("🔒 IP пользователей защищены от утечки", "")
            
            restart_result = subprocess.run([
                PYTHON_EXECUTABLE, safe_restart_script, "restart"
            ], capture_output=True, text=True, timeout=30)  # Увеличиваем таймаут
            
            if restart_result.returncode == 0:
                log_output("✅ Xray безопасно перезапущен \\- клиент активен\\!", "")
                log_output("🛡️ IP пользователей защищены", "")
            else:
                log_output("", f"[Safe Restart Error] {restart_result.stderr}")
                # Fallback: обычный restart
                log_output("Fallback: используем обычный restart", "")
                fallback_restart()
        else:
            log_output("⚠️ Скрипт безопасного перезапуска не найден", "")
            log_output("Fallback: используем обычный restart", "")
            fallback_restart()
            
    except subprocess.TimeoutExpired:
        log_output("⏰ Timeout при безопасном перезапуске", "")
        log_output("Fallback: используем обычный restart", "")
        fallback_restart()
    except Exception as e:
        log_output("", f"[Safe Restart Error] {e}")
        log_output("Fallback: используем обычный restart", "")
        fallback_restart()

    return vless_link, uuid

def fallback_restart():
    """Fallback функция для обычного перезапуска"""
    try:
        restart_result = subprocess.run(["systemctl", "restart", "xray"], 
                                       capture_output=True, text=True)
        if restart_result.returncode == 0:
            log_output("✅ Xray перезапущен (fallback) \\- клиент активен\\!", "")
        else:
            log_output("", f"[Fallback Restart Error] {restart_result.stderr}")
    except Exception as e:
        log_output("", f"[Fallback Error] {e}")