"""
Atualiza REGRAS DE PRECO MANDATORIAS no custom_knowledge dos tenants.

Uso:
    cd /root/fralib
    PYTHONPATH=/root/fralib python scripts/force_price_rules.py
"""
import os
import json
from backend.core.database import SessionLocal
from sqlalchemy import text

NEW_RULE = """

REGRAS DE PRECO MANDATORIAS (NAO PULE, NAO INVENTE OUTROS VALORES):

PRECO BASE:
- R$ 1.499 em 12x de R$ 124,92 sem juros     <- preco padrao quando lead pedir
- R$ 1.499 no Pix a vista (5% desc) = R$ 1.424,05

ESCALA DE OBJECAO (use em ordem, so descer se lead hesitar):
1. R$ 1.299 em 12x de R$ 108,25              <- 1a objecao "ta caro"
2. R$ 999 em 12x de R$ 83,25                 <- follow-up 72h sem resposta
3. R$ 549 em 12x de R$ 45,75                 <- lead muito resistente (PISO ABSOLUTO)
4. R$ 250 entrada + 12x de R$ 45 Pix recorrente  <- ultimo recurso absoluto

BONUS OBRIGATORIO MENCIONAR EM TODO PITCH:
- Dominio GRATIS por 1 ano
- Hospedagem GRATIS por 1 ano
- Cores, logo e fotos personalizados do jeito que o cliente decidir
- Site feito com base nos dados do Google Maps do lead
- O site JA ESTA PRONTO antes da conversa comecar

GARANTIA SEM RISCO (SEMPRE MENCIONAR):
- So paga DEPOIS que o site estiver 100% aprovado e no ar
- Se nao gostar, cancela sem custo

EXEMPLO CORRETO pra "ta caro":
Lead: "ta caro"
Franz: "Em 12x fica R$ 124,92 por mes, sem juros. Dominio e hospedagem gratis por 1 ano. E so paga DEPOIS de aprovar tudo. Faz sentido?"

EXEMPLO CORRETO pra "ta muito caro":
Lead: "ta muito caro"
Franz: "Blz. Tem opcao de R$ 549 em 12x de R$ 45,75. Dominio + hospedagem gratis no 1o ano. So paga depois que tiver no ar. Quer ver?"

EXEMPLO CORRETO pra "nao tenho esse valor":
Lead: "nao tenho esse valor agora"
Franz: "Entendo! Tem opcao de R$ 250 de entrada + 12x de R$ 45 no Pix. O site fica no ar hoje. So paga depois de aprovar. Topa?"

PROIBIDO:
- Inventar valores fora da tabela acima
- Cobrar antes de aprovacao
- Dar desconto maior que o PISO (R$ 549 / 12x R$ 45,75)
- Dizer "vamos fazer" ou "vamos criar" (o site JA ESTA PRONTO)"""


def main():
    db = SessionLocal()
    try:
        for tid in [2, 31]:
            row = db.execute(text("""
                SELECT config_value FROM user_configs
                WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
            """), {'uid': tid}).fetchone()

            if not row:
                print(f"user {tid}: sem registro sdr_settings_v1, pulando")
                continue

            settings = json.loads(row[0])
            ck = settings.get('custom_knowledge', '')

            # Remove versao anterior da regra de preco se existir
            marker = 'REGRAS DE PRECO MANDATORIAS'
            if marker in ck:
                idx = ck.find(marker)
                # Volta ate o \n\n anterior ao marker
                start = ck.rfind('\n\n', 0, idx)
                ck = ck[:start].rstrip() if start != -1 else ck[:idx].rstrip()

            settings['custom_knowledge'] = ck.rstrip() + NEW_RULE
            new_raw = json.dumps(settings, ensure_ascii=False)

            db.execute(text("""
                UPDATE user_configs
                SET config_value = :v, updated_at = NOW()
                WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
            """), {'v': new_raw, 'uid': tid})

            # Invalida cache em memoria se disponivel
            try:
                from backend.services.sdr_settings import invalidate_sdr_settings_cache
                invalidate_sdr_settings_cache(tid)
                print(f"user {tid}: cache invalidado")
            except Exception:
                pass

            print(f"user {tid}: REGRAS DE PRECO atualizadas, "
                  f"custom_knowledge total = {len(settings['custom_knowledge'])} chars")

        db.commit()
        print("Pronto. Commit feito.")
    finally:
        db.close()


if __name__ == '__main__':
    main()
