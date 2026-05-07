"""
Credits Alerts - Sistema de Alertas de Saldo Baixo
Notifica usuário quando créditos estão acabando
"""
from credits_manager import get_user_credits

# Thresholds de alerta
ALERT_THRESHOLDS = {
    'critical': 5,   # Saldo crítico: 5 créditos
    'warning': 20,   # Aviso: 20 créditos
    'low': 50        # Saldo baixo: 50 créditos
}

def check_credits_alert(user_id: int) -> dict:
    """
    Verifica se usuário precisa de alerta de saldo

    Returns:
        {
            'show_alert': bool,
            'level': 'critical' | 'warning' | 'low' | None,
            'message': str,
            'creditos_restantes': int,
            'payment_link': str
        }
    """
    credits = get_user_credits(user_id)
    saldo = credits['creditos_disponiveis']

    payment_link = "https://buy.stripe.com/5kQ5kvbtIgltgBFb24eAg00"

    # Saldo crítico (< 5)
    if saldo < ALERT_THRESHOLDS['critical']:
        return {
            'show_alert': True,
            'level': 'critical',
            'message': f'🚨 CRÉDITOS ESGOTANDO! Você tem apenas {saldo} créditos. Recarregue agora para continuar gerando sites.',
            'creditos_restantes': saldo,
            'payment_link': payment_link,
            'color': '#ef4444',  # vermelho
            'icon': '🚨'
        }

    # Aviso (< 20)
    elif saldo < ALERT_THRESHOLDS['warning']:
        return {
            'show_alert': True,
            'level': 'warning',
            'message': f'⚠️ Saldo baixo! Você tem {saldo} créditos restantes. Considere recarregar em breve.',
            'creditos_restantes': saldo,
            'payment_link': payment_link,
            'color': '#f59e0b',  # laranja
            'icon': '⚠️'
        }

    # Saldo baixo (< 50)
    elif saldo < ALERT_THRESHOLDS['low']:
        return {
            'show_alert': True,
            'level': 'low',
            'message': f'💡 Você tem {saldo} créditos. Aproveite para recarregar e ganhar bônus!',
            'creditos_restantes': saldo,
            'payment_link': payment_link,
            'color': '#38bdf8',  # azul
            'icon': '💡'
        }

    # Saldo OK
    else:
        return {
            'show_alert': False,
            'level': None,
            'message': None,
            'creditos_restantes': saldo,
            'payment_link': payment_link
        }

def get_alert_html(user_id: int) -> str:
    """
    Retorna HTML do alerta para inserir no dashboard
    """
    alert = check_credits_alert(user_id)

    if not alert['show_alert']:
        return ''

    return f"""
    <div style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        max-width: 400px;
        background: var(--fl-bg-card);
        border: 2px solid {alert['color']};
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        z-index: 9998;
        animation: slideIn 0.3s ease-out;
    ">
        <div style="display:flex;align-items:start;gap:12px">
            <div style="font-size:32px">{alert['icon']}</div>
            <div style="flex:1">
                <div style="font-size:14px;color:var(--fl-text);margin-bottom:12px;line-height:1.5">
                    {alert['message']}
                </div>
                <button onclick="window.open('{alert['payment_link']}', '_blank')" style="
                    width:100%;
                    padding:12px;
                    background:{alert['color']};
                    color:white;
                    border:none;
                    border-radius:8px;
                    font-size:14px;
                    font-weight:700;
                    cursor:pointer;
                    transition:transform 0.2s;
                " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                    💳 COMPRAR CRÉDITOS AGORA
                </button>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" style="
                background:none;
                border:none;
                color:var(--fl-text-muted);
                font-size:20px;
                cursor:pointer;
                padding:0;
                width:24px;
                height:24px;
            ">×</button>
        </div>
    </div>

    <style>
    @keyframes slideIn {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}
    </style>
    """

# Teste
if __name__ == "__main__":
    print("🧪 Testando sistema de alertas...")

    # Simular diferentes saldos
    test_cases = [
        (1, 3),    # Crítico
        (2, 15),   # Warning
        (3, 40),   # Low
        (4, 100),  # OK
    ]

    for user_id, saldo_simulado in test_cases:
        # Simular saldo
        from credits_manager import get_db
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_credits (user_id, creditos_disponiveis) VALUES (?, ?)",
                (user_id, saldo_simulado)
            )

        alert = check_credits_alert(user_id)
        print(f"\nUser {user_id} (saldo: {saldo_simulado}):")
        print(f"  Level: {alert['level']}")
        print(f"  Show: {alert['show_alert']}")
        if alert['message']:
            print(f"  Message: {alert['message']}")

    print("\n✅ Testes concluídos!")
