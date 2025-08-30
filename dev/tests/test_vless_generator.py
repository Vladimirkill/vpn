import pytest
from utils.generate_key_for_protocol import generate_key_for_protocol

@pytest.fixture
def sample_input():
    return {
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "ip": "192.168.1.100",  # IPv4
        "port": 443,
        "encryption": "none",
        "region": "test-region",
        "protocol": "vless",
        "obfuscation": "none"
    }

def test_generate_vless_url_with_ipv4(sample_input):
    url = generate_key_for_protocol(**sample_input)
    assert url.startswith("vless://"), "URL должен начинаться с 'vless://'"
    assert sample_input["uuid"] in url, "UUID должен быть в URL"
    assert sample_input["ip"] in url, "IPv4 должен быть в URL"
    assert f":{sample_input['port']}" in url, "Порт должен быть в URL"
    assert f"encryption={sample_input['encryption']}" in url, "Encryption должен быть указан"
    assert f"#" in url, "Имя должно быть в ссылке"

def test_invalid_protocol():
    with pytest.raises(ValueError):
        generate_key_for_protocol(
            uuid="abc",
            ip="1.2.3.4",
            port=443,
            encryption="none",
            region="none",
            protocol="not_supported",
            obfuscation="none"
        )
