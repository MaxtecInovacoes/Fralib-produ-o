#!/usr/bin/env python3
"""
WhatsApp Listener - Conecta ao WebSocket do WhatsAppMeow e encaminha mensagens para o webhook
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime

WHATSAPP_WS_URL = 'ws://localhost:8080/ws?tenantId=fralib_user_3'
WHATSAPP_API_KEY = 'f218ccd4d2345fb2ec8cb6385be26d76e945e4cf4dd92ca99965509c45545200'
WEBHOOK_URL = 'http://localhost:8000/api/whatsapp/webhook'

async def listen_whatsapp():
    """Conecta ao WebSocket e processa mensagens"""
    print(f'[{datetime.now()}] Conectando ao WhatsApp WebSocket...')
    
    try:
        async with websockets.connect(
            WHATSAPP_WS_URL,
            additional_headers={'X-API-Key': WHATSAPP_API_KEY}
        ) as websocket:
            print(f'[{datetime.now()}] Conectado! Aguardando mensagens...')
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event_type = data.get('type')
                    
                    print(f'[{datetime.now()}] Evento recebido: {event_type}')
                    
                    # Encaminhar para webhook
                    response = requests.post(
                        WEBHOOK_URL,
                        json=data,
                        timeout=10
                    )
                    
                    print(f'[{datetime.now()}] Webhook response: {response.status_code}')
                    print(f'[{datetime.now()}] {response.json()}')
                    
                except json.JSONDecodeError:
                    print(f'[{datetime.now()}] Erro ao decodificar JSON: {message}')
                except Exception as e:
                    print(f'[{datetime.now()}] Erro ao processar mensagem: {e}')
                    
    except Exception as e:
        print(f'[{datetime.now()}] Erro na conexão WebSocket: {e}')
        print(f'[{datetime.now()}] Tentando reconectar em 5 segundos...')
        await asyncio.sleep(5)
        await listen_whatsapp()

if __name__ == '__main__':
    print('=== WhatsApp Listener - FraLib ===')
    print(f'WebSocket: {WHATSAPP_WS_URL}')
    print(f'Webhook: {WEBHOOK_URL}')
    print('===================================')
    
    asyncio.run(listen_whatsapp())
