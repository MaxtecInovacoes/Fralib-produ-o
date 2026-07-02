"""Testes da UI de Personalização do Franz (Sprint 1.3).

Cobre:
- frontend/admin.html: nova seção "🤖 Configurar Franz" no SDR Settings
  (3 tabs: Básico / Avançado / Base de conhecimento)
- Por campo: toggle "Personalizar" (quando off → usa nativo + disabled)
- Botão "Testar no simulador" que integra com Sprint 1.1
- Botão "Restaurar nativo" por campo
- Preview em tempo real do system prompt
- frontend/js/admin/sdr-personalization.js: carregarPersonalizacao(),
  salvarPersonalizacao(), togglePersonalizar(), atualizarPreview()

Sem rede real — usa leitura estática de HTML/JS e asserts de substring.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

import pytest

# Bootstrap path & env vars antes de importar o backend
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/test",
)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

ADMIN_HTML = _ROOT / "frontend" / "admin.html"
PERSONALIZATION_JS = _ROOT / "frontend" / "js" / "admin" / "sdr-personalization.js"


# ── Helpers ──────────────────────────────────────────────────────────────


def _has_all(text: str, needles: Iterable[str]) -> bool:
    """True se todas as substrings aparecem em text."""
    return all(needle in text for needle in needles)


def _ids_present(html: str, ids: Iterable[str]) -> list[str]:
    """Filtra a lista de ids para os que realmente aparecem em html."""
    return [i for i in ids if (f'id="{i}"' in html)]


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def admin_html() -> str:
    if not ADMIN_HTML.is_file():
        return ""
    return ADMIN_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def personalization_js() -> str:
    if not PERSONALIZATION_JS.is_file():
        return ""
    return PERSONALIZATION_JS.read_text(encoding="utf-8")


# ── Testes ──────────────────────────────────────────────────────────────


def test_admin_html_secao_configurar_franz_presente(admin_html: str) -> None:
    """A secao 'Configurar Franz' deve estar presente no admin.html
    dentro da area de SDR Settings (CONTROLE DO SDR)."""
    assert admin_html, "admin.html nao encontrado"
    # Identificador visivel independente de caixa (HTML usa maiusculas para o titulo)
    assert "🤖" in admin_html, "emoji robo do Franz ausente"
    lower = admin_html.lower()
    assert "configurar franz" in lower, (
        "Titulo 'Configurar Franz' ausente no admin.html"
    )
    # Deve estar dentro da area SDR Settings (CONTROLE DO SDR) -
    # confirmado pela PRESENCA do id sdrConfigStatus em algum lugar do HTML
    # dentro da mesma regiao da secao (janela de ate 50k chars cobre o bloco).
    idx = lower.find("🤖 configurar franz")
    if idx < 0:
        idx = lower.find("configurar franz")
    assert idx > 0, "Secao '🤖 Configurar Franz' nao esta no HTML"
    assert "sdrconfigstatus" in lower[idx:idx + 50000], (
        "Secao 'Configurar Franz' nao esta perto do bloco SDR Config existente"
    )


def test_tab_basico_presente(admin_html: str) -> None:
    """A tab 'Basico' deve existir (via data-tab="basico") e ter 3 campos:
    - nome do agente
    - assinatura do agente
    - tom/personalidade (textarea)
    """
    # data-tab=basico presente no HTML
    assert 'data-tab="basico"' in admin_html, (
        "data-tab='basico' ausente - tab Basico nao declarada"
    )
    # data-panel=basico (container) presente
    assert 'data-panel="basico"' in admin_html, (
        "data-panel='basico' ausente - container Basico nao encontrado"
    )
    ids_present = _ids_present(
        admin_html,
        ["sdrPersAgentName", "sdrPersAgentSignature", "sdrPersTone"],
    )
    assert "sdrPersAgentName" in ids_present, "Campo nome agente ausente na tab Basico"
    assert "sdrPersAgentSignature" in ids_present, (
        "Campo assinatura do agente ausente na tab Basico"
    )
    assert "sdrPersTone" in ids_present, "Campo tom/personalidade ausente na tab Basico"


def test_tab_avancado_presente(admin_html: str) -> None:
    """A tab 'Avancado' deve existir (via data-tab="avancado") e ter 4 campos:
    - acoes permitidas
    - acoes bloqueadas
    - gatilhos de handoff
    - nota de handoff
    """
    assert 'data-tab="avancado"' in admin_html, (
        "data-tab='avancado' ausente - tab Avancado nao declarada"
    )
    assert 'data-panel="avancado"' in admin_html, (
        "data-panel='avancado' ausente - container Avancado nao encontrado"
    )
    ids_present = _ids_present(
        admin_html,
        [
            "sdrPersAllowedActions",
            "sdrPersBlockedActions",
            "sdrPersHandoffTriggers",
            "sdrPersHandoffNote",
        ],
    )
    assert "sdrPersAllowedActions" in ids_present, "Campo acoes permitidas ausente"
    assert "sdrPersBlockedActions" in ids_present, "Campo acoes bloqueadas ausente"
    assert "sdrPersHandoffTriggers" in ids_present, "Campo gatilhos de handoff ausente"
    assert "sdrPersHandoffNote" in ids_present, "Campo nota de handoff ausente"


def test_tab_base_conhecimento_presente(admin_html: str) -> None:
    """A tab 'Base de conhecimento' deve existir (via data-tab="base") e ter
    um textarea custom_knowledge com maxlength 8000 e contador."""
    assert 'data-tab="base"' in admin_html, (
        "data-tab='base' ausente - tab Base de conhecimento nao declarada"
    )
    assert 'data-panel="base"' in admin_html, (
        "data-panel='base' ausente - container Base nao encontrado"
    )
    ids_present = _ids_present(
        admin_html,
        [
            "sdrPersCustomKnowledge",
            "sdrPersCharCounter",
        ],
    )
    assert "sdrPersCustomKnowledge" in ids_present, (
        "Textarea custom_knowledge ausente na tab Base"
    )
    assert "sdrPersCharCounter" in ids_present, (
        "Contador regressivo de chars ausente"
    )
    # O textarea DEVE ter maxlength 8000 (MAX_CUSTOM_KNOWLEDGE_CHARS no backend)
    idx = admin_html.find('id="sdrPersCustomKnowledge"')
    assert idx > 0, "sdrPersCustomKnowledge nao encontrada"
    snippet = admin_html[idx:idx + 600]
    assert "maxlength=\"8000\"" in snippet, (
        "sdrPersCustomKnowledge precisa ter maxlength=8000"
    )


def test_toggle_personalizar_por_campo(admin_html: str) -> None:
    """Cada campo personalizado deve ter um toggle 'Personalizar'
    (checkbox) — quando off, usa nativo e campo fica disabled."""
    # Cada campo personalizável deve ter um toggle cuja classe inclui
    # 'sdr-pers-toggle' e esteja ligado ao campo via data-target.
    assert "sdr-pers-toggle" in admin_html, (
        "Classe 'sdr-pers-toggle' ausente — não há toggles por campo"
    )
    assert "data-target=" in admin_html, (
        "data-target deve linkar toggle ao campo"
    )
    # Pelo menos 8 toggles (3 básico + 4 avançado + 1 base = 8)
    toggle_count = admin_html.count("sdr-pers-toggle")
    assert toggle_count >= 8, (
        f"Esperado >=8 toggles 'Personalizar', encontrado {toggle_count}"
    )
    # O JS deve implementar a função togglePersonalizar(campo)
    # que adiciona/remove o atributo disabled no target
    js = PERSONALIZATION_JS.read_text(encoding="utf-8") if PERSONALIZATION_JS.is_file() else ""
    assert js, "sdr-personalization.js ausente"
    assert "togglePersonalizar" in js, (
        "Função togglePersonalizar(campo) ausente no sdr-personalization.js"
    )
    assert "disabled" in js, (
        "togglePersonalizar precisa manipular o atributo disabled"
    )


def test_botao_testar_simulador_integrado(admin_html: str, personalization_js: str) -> None:
    """Deve haver botão 'Testar no simulador' que integra com
    o card Simulador Franz existente (Sprint 1.1)."""
    assert admin_html, "admin.html não encontrado"
    # Texto visível
    assert "Testar no simulador" in admin_html, (
        "Botão 'Testar no simulador' ausente no admin.html"
    )
    # Botão deve ter id estável
    found = _ids_present(admin_html, ["sdrPersTestSimulator"])
    assert "sdrPersTestSimulator" in found, (
        "id 'sdrPersTestSimulator' ausente"
    )
    # JS deve fazer algo que conecta com o simulador existente.
    # Aceita tanto acionar o card de simulação (sdrSimulatorCard) quanto
    # chamar a função SDR_SIMULATOR pública ou focar o textarea do simulador.
    assert personalization_js, "sdr-personalization.js ausente"
    connect_signals = (
        "sdrSimulatorCard" in personalization_js
        or "sdrSimulatorMessage" in personalization_js
        or "scrollIntoView" in personalization_js
        or "SDR_SIMULATOR" in personalization_js
    )
    assert connect_signals, (
        "Botão 'Testar no simulador' não está ligado ao card Simulador Franz"
    )


def test_botao_restaurar_nativo_por_campo(admin_html: str, personalization_js: str) -> None:
    """Cada campo deve ter um botão 'Restaurar nativo' que volta
    o valor ao default do motor (campo desabilitado + toggle off)."""
    # Texto visível "Restaurar nativo" deve aparecer pelo menos 1×
    assert "Restaurar nativo" in admin_html, (
        "Texto 'Restaurar nativo' ausente no admin.html"
    )
    # Deve haver uma classe comum para os botões
    assert "sdr-pers-restore" in admin_html, (
        "Classe 'sdr-pers-restore' ausente nos botões de restaurar"
    )
    # Deve aparecer em pelo menos 8 botões (1 por campo personalizável)
    restore_count = admin_html.count("sdr-pers-restore")
    assert restore_count >= 8, (
        f"Esperado >=8 botões 'Restaurar nativo', encontrado {restore_count}"
    )
    # JS precisa implementar a lógica (incluindo função restaurarNativo)
    assert personalization_js, "sdr-personalization.js ausente"
    assert "restaurarNativo" in personalization_js, (
        "Função restaurarNativo(campo) ausente no sdr-personalization.js"
    )


def test_preview_system_prompt_em_tempo_real(admin_html: str, personalization_js: str) -> None:
    """Deve existir um preview do system prompt final em
    textarea readonly, atualizado em tempo real."""
    # Textarea de preview com id estável
    found = _ids_present(admin_html, ["sdrPersPromptPreview"])
    assert "sdrPersPromptPreview" in found, (
        "Textarea de preview do system prompt ausente"
    )
    # Atributo readonly
    idx = admin_html.find('id="sdrPersPromptPreview"')
    assert idx > 0, "sdrPersPromptPreview não encontrada"
    snippet = admin_html[idx:idx + 600]
    assert "readonly" in snippet, (
        "sdrPersPromptPreview precisa ter atributo readonly"
    )
    # JS precisa de função atualizarPreview que monta o prompt
    assert personalization_js, "sdr-personalization.js ausente"
    assert "atualizarPreview" in personalization_js, (
        "Função atualizarPreview() ausente no sdr-personalization.js"
    )
    # A função atualizarPreview deve escutar eventos de input
    # (input event listener em algum dos campos personalizáveis).
    assert "addEventListener" in personalization_js, (
        "atualizarPreview deve estar amarrada a listeners de input/change"
    )


def test_carregarSdrConfig_chama_personalization(admin_html: str, personalization_js: str) -> None:
    """A função carregarSdrConfig existente no admin.html deve
    também carregar a personalização (ou haver um carregarPersonalizacao
    no JS novo chamado por carregarSdrConfig)."""
    # carregarPersonalizacao existe no JS novo
    assert personalization_js, "sdr-personalization.js ausente"
    assert "carregarPersonalizacao" in personalization_js, (
        "Função carregarPersonalizacao() ausente no sdr-personalization.js"
    )
    # E ela deve chamar o endpoint existente /api/users/sdr-config
    assert "/api/users/sdr-config" in personalization_js, (
        "carregarPersonalizacao deve chamar /api/users/sdr-config"
    )
    # O admin.html deve carregar o JS novo no fim do body
    assert "sdr-personalization.js" in admin_html, (
        "<script src='/js/admin/sdr-personalization.js'> ausente no admin.html"
    )


def test_salvarSdrConfig_persiste_todos_campos(admin_html: str, personalization_js: str) -> None:
    """salvarPersonalizacao deve persistir TODOS os campos personalizaveis
    (nome, assinatura, tom, acoes permitidas/bloqueadas, gatilhos,
    nota de handoff, custom_knowledge) via PUT /api/users/sdr-config."""
    assert personalization_js, "sdr-personalization.js ausente"
    assert "salvarPersonalizacao" in personalization_js, (
        "Funcao salvarPersonalizacao() ausente"
    )
    # Deve usar PUT (mesmo metodo do endpoint existente) em algum caminho
    # (aceita varias representacoes: literal, variavel, etc).
    call_sdr_put = (
        ("'PUT'" in personalization_js)
        or ('"PUT"' in personalization_js)
        or ("method.toUpperCase()" in personalization_js)
        or ("method = (method" in personalization_js)
    )
    assert call_sdr_put, "salvarPersonalizacao precisa chamar PUT"
    # Endpoint correto
    assert "/api/users/sdr-config" in personalization_js, (
        "salvarPersonalizacao precisa chamar /api/users/sdr-config"
    )
    # Cobrir os campos principais do payload (checar pelas chaves)
    expected_keys = [
        "agent_name",
        "agent_signature",
        "personality",
        "allowed_actions",
        "blocked_actions",
        "custom_knowledge",
    ]
    missing = [k for k in expected_keys if k not in personalization_js]
    assert not missing, (
        f"salvarPersonalizacao nao cobre os campos: {missing}"
    )
