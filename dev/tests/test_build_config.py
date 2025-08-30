import json
import os
import shutil
import pytest
from pathlib import Path

from xray import build_config

@pytest.fixture
def setup_env(tmp_path):
    xray_dir = tmp_path / "xray"
    xray_dir.mkdir()
    clients_dir = xray_dir / "clients"
    clients_dir.mkdir()

    # Базовый конфиг
    base_config = {
        "inbounds": [{
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "xtls",
                "xtlsSettings": {
                    "alpn": ["http/1.1"],
                    "certificates": [{
                        "certificateFile": "/etc/ssl/certs/fullchain.pem",
                        "keyFile": "/etc/ssl/private/privkey.pem"
                    }]
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }

    with open(xray_dir / "base_config.json", "w") as f:
        json.dump(base_config, f)

    # Один клиент
    client = {"id": "uuid-test-123", "flow": "xtls-rprx-direct"}
    with open(clients_dir / "user1.json", "w") as f:
        json.dump(client, f)

    return {
        "base": xray_dir / "base_config.json",
        "clients": clients_dir,
        "output": xray_dir / "final_config.json",
        "expected_uuid": client["id"],
        "symlink": tmp_path / "config_link.json"
    }

def apply_paths(env):
    build_config.BASE_PATH = str(env["base"].parent)
    build_config.CLIENTS_PATH = str(env["clients"])
    build_config.OUTPUT_PATH = str(env["output"])
    build_config.TARGET_LINK = str(env["symlink"])

def test_final_config_created_correctly(setup_env):
    apply_paths(setup_env)
    build_config.build_config()

    assert setup_env["output"].exists(), "Финальный конфиг не создан"

    with open(setup_env["output"]) as f:
        data = json.load(f)

    clients = data["inbounds"][0]["settings"]["clients"]
    assert isinstance(clients, list)
    assert setup_env["expected_uuid"] in [c["id"] for c in clients]

def test_symlink_created(setup_env):
    apply_paths(setup_env)
    build_config.build_config()

    assert setup_env["symlink"].is_symlink()
    assert setup_env["symlink"].resolve() == setup_env["output"]

def test_empty_clients_list(setup_env):
    shutil.rmtree(setup_env["clients"])
    os.mkdir(setup_env["clients"])

    apply_paths(setup_env)
    build_config.build_config()

    with open(setup_env["output"]) as f:
        data = json.load(f)

    clients = data["inbounds"][0]["settings"]["clients"]
    assert clients == []

def test_missing_base_config(tmp_path):
    clients_path = tmp_path / "clients"
    clients_path.mkdir()

    build_config.BASE_PATH = str(tmp_path)  # без base_config.json
    build_config.CLIENTS_PATH = str(clients_path)
    build_config.OUTPUT_PATH = str(tmp_path / "out.json")
    build_config.TARGET_LINK = str(tmp_path / "link.json")

    with pytest.raises(FileNotFoundError):
        build_config.build_config()