import sys, asyncio
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
sys.path.insert(0, '/root/fralib/backend/agents')
sys.path.insert(0, '/root/fralib/backend/utils')
sys.path.insert(0, '/root/fralib/backend/endpoints')
from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')

from backend.endpoints.pipeline_endpoints import executar_pipeline_completo

config = {
    'segmento': 'academia',
    'cidade': 'Campina Grande do Sul',
    'quantidade': 1,
}

print('=== PIPELINE COMPLETO ===')
print(f'Config: {config}')
print()

async def main():
    result = await executar_pipeline_completo(config, tenant_id=1)
    print(f'Resultado: {result}')

asyncio.run(main())
