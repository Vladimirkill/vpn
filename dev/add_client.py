import os
import qrcode
import io
import subprocess
from xray.generate_client import generate_vless_client

BASE_PATH = "/var/www/vpn"
BUILD_SCRIPT = os.path.join(BASE_PATH, "xray", "build_config.py")

def generate_client_with_qr(host: str = "146.103.125.210", port: int = 443, client_name: str = "vpn"):
    result = generate_vless_client(
        clients_dir=os.path.join(BASE_PATH, "xray", "clients"),
        host=host,
        port=port,
        client_name=client_name
    )

    if "error" in result:
        return {"error": result["error"]}

    link = result["link"]
    uuid = result["uuid"]
    file = result["file"]

    # Генерация QR-кода в ASCII для терминала
    qr_terminal = io.StringIO()
    qr = qrcode.QRCode(border=1)
    qr.add_data(link)
    qr.make(fit=True)
    qr.print_ascii(out=qr_terminal, invert=True)
    qr_ascii = qr_terminal.getvalue()
    qr_terminal.close()

    # Сборка конфига
    build = subprocess.run(["python3", BUILD_SCRIPT], capture_output=True, text=True)
    if build.returncode != 0:
        return {"error": f"❌ Сборка конфига не удалась:\n{build.stderr}"}

    # Горячая перезагрузка Xray (без обрыва клиентов)
    try:
        # Сначала пробуем systemctl reload
        reload_result = subprocess.run(["systemctl", "reload", "xray"], 
                                     capture_output=True, text=True)
        if reload_result.returncode == 0:
            xray_restarted = True
        else:
            # Если reload не сработал, пробуем HUP signal
            pids = subprocess.check_output(["pidof", "xray"]).decode().strip().split()
            for pid in pids:
                subprocess.run(["kill", "-HUP", pid])
            xray_restarted = True
    except subprocess.CalledProcessError:
        xray_restarted = False

    return {
        "uuid": uuid,
        "file": file,
        "link": link,
        "qr_ascii": qr_ascii,
        "xray_restarted": xray_restarted
    }

if __name__ == "__main__":
    data = generate_client_with_qr()

    if "error" in data:
        print("❌ Ошибка:", data["error"])
    else:
        print("\n✅ Новый клиент создан:")
        print(f"🔑 UUID: {data['uuid']}")
        print(f"📁 Файл: {data['file']}")
        print(f"🔗 VLESS-ссылка:\n{data['link']}")
        print("\n📱 QR-код:\n" + data["qr_ascii"])
        if data["xray_restarted"]:
            print("✅ Xray горячо перезагружен (SIGHUP).")
        else:
            print("⚠️ Не удалось выполнить hot-reload Xray.")