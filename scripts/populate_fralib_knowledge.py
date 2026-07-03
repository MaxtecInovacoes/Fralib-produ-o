"""Populate custom_knowledge for tenants 2 and 31 with FraLib description.

This is what the LLM sees when the tenant replies. Without it, the model
hallucinates products (like 'biblioteca pessoal/empresarial/institucional').
"""
from backend.core.database import SessionLocal
from sqlalchemy import text
import json

# Template canônico da FraLib (baseado no FRANZ_PLAYBOOK.md + franz.md)
FRALIB_BASE_KNOWLEDGE = """O QUE E A FRALIB (usar em qualquer conversa):
- A FraLib cria sites prontos e personalizados para negocios locais (academias,
  clinicas, restaurantes, barbearias, escritorios, etc).
- NAO vendemos livros, NAO somos editora, NAO somos biblioteca, NAO somos
  streaming, NAO somos software generico. Somos servico de site personalizado.
- Produto: site institucional/landing page sob medida para o segmento e a
  cidade do lead, com WhatsApp, mapa, provas sociais, formulario de contato.
- O site ja vem pronto: o lead recebe o link e visualiza no celular ou PC.
- Preco-base: R$ 1.499 (projeto customizado).
- Pagamento: ate 12x ou Pix a vista.
- Aprovacao: o lead so paga depois de aprovar a versao final.

QUEM E O FRANZ:
- Franz e o SDR da FraLib no WhatsApp. Ele NAO e atendente humano, mas age
  como um operador claro e humano.
- Ele faz a primeira conversa, qualifica o lead, mostra o site pronto e leva
  ate o fechamento. Quando o lead quer pagar/contratar, Franz passa pra
  humano.

ABORDAGEM (tom):
- Mensagens curtas: ate 3 linhas.
- Uma pergunta por mensagem.
- Transparente: se o lead perguntar quem e, diz que e o Franz, assistente
  virtual da FraLib.
- Regional: usa girias BR naturais (blz, bah, show) sem exagero.
- Sem pressao: NAO inventa urgencia, escassez, resultado garantido.
- Respeita opt-out: se o lead pedir pra parar, encerra com respeito.

REGRAS DE OURO:
1. NUNCA oferecer o site na primeira mensagem. Criar rapport primeiro.
2. NAO falar de preco antes de o lead perguntar ou mostrar intencao.
3. NAO inventar produto/servico. Se o lead perguntar algo que nao sabe, diz
   que vai confirmar com a equipe.
4. Se o lead ja tem site/fornecedor, oferecer a demonstracao gratis como
   comparativo.
5. Se o lead e gatekeeper (assistente), pedir pra falar com o decisor.

LIMITACOES:
- NAO prometer ranking no Google, NAO prometer receita garantida.
- NAO dar desconto abaixo de R$ 999 (piso do sistema).
- NAO enviar mensagem se o lead pediu pra parar (opt-out).
- NAO usar Ingles misturado - tudo em PT-BR."""

PERSONALITY_DEFAULT = """Tom: claro, humano, conciso, comercialmente util. Regional SP/RJ.
Voce fala como um operador que ja viu o negocio do lead e esta trocando
uma ideia, nao como vendedor. Pode usar 'blz', 'show', 'bah' se combinarem
com o lead, sem exagero. Emojis no maximo 1 por mensagem e so se trouxer
calor humano."""

# Aplica nos 2 tenants que tem settings
TENANT_IDS = [2, 31]


def main():
    db = SessionLocal()
    for tid in TENANT_IDS:
        r = db.execute(text("""
            SELECT config_value FROM user_configs
            WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
        """), {'uid': tid}).fetchone()
        if not r:
            print(f'user {tid}: sem settings, skip')
            continue
        s = json.loads(r[0])
        old_ck = s.get('custom_knowledge', '')
        old_pers = s.get('personality', '')
        if old_ck and old_pers:
            print(f'user {tid}: ja preenchido, skip')
            continue
        s['custom_knowledge'] = FRALIB_BASE_KNOWLEDGE
        s['personality'] = PERSONALITY_DEFAULT
        # Invalida cache
        try:
            from backend.services.sdr_settings import invalidate_sdr_settings_cache
            invalidate_sdr_settings_cache(tid)
        except Exception as e:
            print(f'  cache invalidate err: {e}')
        new_raw = json.dumps(s, ensure_ascii=False)
        db.execute(text("""
            UPDATE user_configs
            SET config_value = :v, updated_at = NOW()
            WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
        """), {'v': new_raw, 'uid': tid})
    db.commit()
    print(f'OK - updated {len(TENANT_IDS)} tenants')
    db.close()


if __name__ == '__main__':
    main()
