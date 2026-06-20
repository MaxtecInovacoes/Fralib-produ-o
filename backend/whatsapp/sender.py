"""Helpers de envio HTTP para o Meowhats."""


def send_presence_composing(http_client, base_url: str, api_key: str, tenant_id: str, jid: str):
    """Envia presence=typing; falhas daqui não devem derrubar o fluxo."""
    return http_client.post(
        f"{base_url}/api/sessions/{tenant_id}/presence",
        headers={"X-API-Key": api_key},
        json={"jid": jid, "type": "composing"},
    )


def send_text_parts(http_client, base_url: str, api_key: str, tenant_id: str, jid: str, parts, before_send=None):
    """Envia uma resposta em múltiplas partes, abortando no primeiro erro."""
    last_error = ""
    for idx, part in enumerate(parts):
        if before_send is not None:
            before_send(idx, part)
        response = http_client.post(
            f"{base_url}/api/sessions/{tenant_id}/send",
            headers={"X-API-Key": api_key},
            json={"jid": jid, "type": "text", "text": part},
        )
        if response.status_code != 200:
            last_error = (response.text or "")[:80]
            return False, last_error
    return True, last_error


def send_handoff_notification(
    http_client,
    base_url: str,
    api_key: str,
    tenant_id: str,
    closer_number: str,
    text: str,
):
    """Notifica o closer humano pelo mesmo device do tenant."""
    closer_jid = f"{closer_number}@s.whatsapp.net"
    return http_client.post(
        f"{base_url}/api/sessions/{tenant_id}/send",
        headers={"X-API-Key": api_key},
        json={"jid": closer_jid, "type": "text", "text": text},
    )
