"""
Pipeline Credits Middleware - Integração com Sistema de Créditos
Desconta créditos antes de executar pipeline e mostra alertas
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from credits_manager import get_user_credits, use_credit, refund_credit
from credits_alerts import check_credits_alert

PAYMENT_LINK = "https://buy.stripe.com/5kQ5kvbtIgltgBFb24eAg00"

async def check_credits_before_pipeline(user_id: int) -> dict:
    """
    Verifica se usuário tem créditos antes de executar pipeline

    Returns:
        {
            'has_credits': bool,
            'creditos_disponiveis': int,
            'alert': dict (se aplicável)
        }
    """
    credits = get_user_credits(user_id)
    saldo = credits['creditos_disponiveis']

    # Verificar alertas
    alert = check_credits_alert(user_id)

    return {
        'has_credits': saldo > 0,
        'creditos_disponiveis': saldo,
        'alert': alert if alert['show_alert'] else None
    }

async def pipeline_credits_middleware(request: Request, call_next):
    """
    Middleware para verificar e descontar créditos no pipeline

    Aplica-se apenas às rotas de pipeline:
    - /api/pipeline/executar
    - /api/pipeline/iniciar
    - /maestro/executar
    """
    path = request.url.path

    # Verificar se é rota de pipeline
    is_pipeline_route = (
        path.startswith('/api/pipeline/executar') or
        path.startswith('/api/pipeline/iniciar') or
        path.startswith('/maestro/executar')
    )

    if not is_pipeline_route:
        # Não é rota de pipeline, continuar normalmente
        return await call_next(request)

    # Extrair user_id (assumindo que está no request.state após autenticação)
    user_id = getattr(request.state, 'user_id', None)

    if not user_id:
        # Tentar pegar do header (fallback)
        user_id = request.headers.get('X-User-ID')
        if user_id:
            user_id = int(user_id)

    if not user_id:
        # Sem autenticação, retornar erro
        return JSONResponse(
            status_code=401,
            content={
                'error': 'Usuário não autenticado',
                'message': 'Faça login para continuar'
            }
        )

    # Verificar créditos
    check = await check_credits_before_pipeline(user_id)

    if not check['has_credits']:
        # SEM CRÉDITOS - Retornar erro com link de pagamento
        return JSONResponse(
            status_code=402,  # Payment Required
            content={
                'error': 'Créditos insuficientes',
                'message': '🚨 Você não tem créditos suficientes para gerar sites. Recarregue sua conta para continuar!',
                'creditos_disponiveis': 0,
                'payment_link': PAYMENT_LINK,
                'action': 'buy_credits'
            }
        )

    # TEM CRÉDITOS - Descontar 1 crédito
    success = use_credit(user_id, f"Pipeline: {path}")

    if not success:
        return JSONResponse(
            status_code=402,
            content={
                'error': 'Erro ao descontar crédito',
                'message': 'Não foi possível descontar o crédito. Tente novamente.',
                'payment_link': PAYMENT_LINK
            }
        )

    # Adicionar info ao request
    request.state.credits_deducted = True
    request.state.credits_remaining = check['creditos_disponiveis'] - 1
    request.state.user_id = user_id

    # Executar pipeline
    try:
        response = await call_next(request)

        # Adicionar header com créditos restantes
        response.headers['X-Credits-Remaining'] = str(request.state.credits_remaining)

        # Se tiver alerta, adicionar no header
        if check['alert']:
            response.headers['X-Credits-Alert'] = check['alert']['level']

        return response

    except Exception as e:
        # ERRO NO PIPELINE - Devolver crédito (rollback)
        if hasattr(request.state, 'credits_deducted') and request.state.credits_deducted:
            refund_credit(user_id, f"Erro no pipeline: {str(e)[:100]}")
            print(f"↩️ Crédito devolvido para user_id={user_id} (erro: {str(e)[:50]})")

        # Re-lançar exceção
        raise

# Função para adicionar alerta no response JSON
def add_credits_alert_to_response(response_data: dict, user_id: int) -> dict:
    """
    Adiciona alerta de créditos ao response JSON
    """
    alert = check_credits_alert(user_id)

    if alert['show_alert']:
        response_data['credits_alert'] = {
            'level': alert['level'],
            'message': alert['message'],
            'creditos_restantes': alert['creditos_restantes'],
            'payment_link': alert['payment_link'],
            'color': alert['color'],
            'icon': alert['icon']
        }

    return response_data

# Endpoint para verificar créditos antes de iniciar pipeline
async def check_credits_endpoint(user_id: int):
    """
    Endpoint para frontend verificar créditos antes de iniciar pipeline

    GET /api/credits/check?user_id=1
    """
    check = await check_credits_before_pipeline(user_id)

    if not check['has_credits']:
        return {
            'can_proceed': False,
            'error': 'Créditos insuficientes',
            'message': '🚨 Você não tem créditos. Recarregue para continuar!',
            'creditos_disponiveis': 0,
            'payment_link': PAYMENT_LINK
        }

    return {
        'can_proceed': True,
        'creditos_disponiveis': check['creditos_disponiveis'],
        'alert': check['alert'],
        'payment_link': PAYMENT_LINK
    }
