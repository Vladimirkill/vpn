def generate_key_for_protocol(uuid, ip, port, encryption, region, protocol, obfuscation):
    if protocol == "vless":
        return (
            f"vless://{uuid}@{ip}:{port}"
            f"?encryption={encryption}&security=xtls&type=tcp&flow=xtls-rprx-direct#{region}"
        )
    raise ValueError(f"Unsupported protocol: {protocol}")