"""Update price objection rule to be MANDATORY (DEVE, not PODE)."""
import os
from backend.core.database import SessionLocal
from sqlalchemy import text
import json

# Reescrever a regra "QUANDO LEAD FALAR 'TA CARO'" pra ser obrigatória
NEW_RULE = """

REGRAS DE PRECO (OBRIGATORIAS - NAO PULE):
- Se o lead perguntar preco: responda IMEDIATAMENTE com R$ 1.499.
- SEMPRE adicione: "Parcelado em 12x de R$ 124,92 sem juros. Ou R$ 1.424,05 a vista no Pix."
- SEMPRE adicione: "E so paga DEPOIS de aprovar o site final."
- Se o lead falar "ta caro" / "caro" / "nao tenho esse valor": NAO espalhe duvida. Responda com o parcelamento:
  "Em 12x fica R$ 124,92 por mes. Sem juros. E so paga depois de aprovar tudo. Faz sentido?"
- Se o lead hesitar ainda: "Se nao for agora, quer que eu siga daqui a 30 dias? Sem compromisso."

EXEMPLO CORRETO pra 'ta caro':
Lead: "ta caro"
Franz: "Em 12x fica R$ 124,92 por mes, sem juros. E so paga DEPOIS de aprovar o site final. Quer que eu te explique o que vem junto?"

EXEMPLO ERRADO pra 'ta caro' (NAO FACA ASSIM):
Lead: "ta caro"
Franz: "Voce ja chegou a ver o servico? As vezes o que parece caro muda quando ve o resultado."  <- ESPALHANDO DUVIDA, NAO VENDE

LICÕES MEMORIZADAS (CALCULOS):
- R$ 1.499 / 12 = R$ 124,92/mes (sem juros)
- R$ 1.499 Pix a vista: 5% desconto = R$ 1.424,05
- R$ 1.299 (follow-up 24h): R$ 108,25/mes
- R$ 999 (follow-up 72h): R$ 83,25/mes"""


def main():
    db = SessionLocal()
    for tid in [2, 31]:
        r = db.execute(text("""
            SELECT config_value FROM user_configs
            WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
        """), {'uid': tid}).fetchone()
        if not r:
            continue
        s = json.loads(r[0])
        ck = s.get('custom_knowledge', '')
        # Remove regra antiga se existir
        if 'REGRAS DE PRECO (OBRIGATORIAS' in ck:
            idx = ck.find('REGRAS DE PRECO (OBRIGATORIAS')
            ck = ck[:idx].rstrip() + '\n'
        s['custom_knowledge'] = ck.rstrip() + NEW_RULE
        new_raw = json.dumps(s, ensure_ascii=False)
        db.execute(text("""
            UPDATE user_configs
            SET config_value = :v, updated_at = NOW()
            WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
        """), {'v': new_raw, 'uid': tid})
        # Invalida cache
        try:
            from backend.services.sdr_settings import invalidate_sdr_settings_cache
            invalidate_sdr_settings_cache(tid)
        except Exception:
            pass
        print(f'user {tid}: REGRAS DE PRECO mandatory added, total ck={len(s["custom_knowledge"])}')
    db.commit()
    db.close()


if __name__ == '__main__':
    main()
