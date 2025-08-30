import os
import json
import re
import pytest
from pathlib import Path

from xray.generate_client import generate_vless_client

UUID_PATTERN = r"^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"

def test_generate_vless_client_creates_valid_uuid_and_file(tmp_path):
    result = generate_vless_client(clients_dir=tmp_path)

    uuid = result["uuid"]
    client_file = Path(result["file"])
    vless_link = result["link"]

    # UUID
    assert re.fullmatch(UUID_PATTERN, uuid), "UUID невалидный"

    # Файл клиента
    assert client_file.exists(), "Файл не создан"
    with open(client_file) as f:
        data = json.load(f)
    assert data["id"] == uuid
    assert data["flow"] == "xtls-rprx-direct"

    # Ссылка
    assert vless_link.startswith(f"vless://{uuid}@"), "Ссылка не начинается с правильного UUID"
    assert "security=xtls" in vless_link

def test_generate_vless_client_with_custom_flow(tmp_path):
    result = generate_vless_client(clients_dir=tmp_path, flow="custom-flow")
    with open(result["file"]) as f:
        data = json.load(f)
    assert data["flow"] == "custom-flow"

def test_multiple_client_generation_no_collision(tmp_path):
    uuids = set()
    for _ in range(5):
        result = generate_vless_client(clients_dir=tmp_path)
        assert result["uuid"] not in uuids
        uuids.add(result["uuid"])