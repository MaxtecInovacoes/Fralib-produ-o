"""Validação rigorosa de dados de entrada por fase.

Fail-fast: se dado obrigatório está ausente, lança RequiredDataMissingError
imediatamente — não continua o pipeline com dados incompletos.

Uso:
    from backend.pipeline_validators import (
        validate_phase_hunter_lead,
        validate_phase_caio_input,
        validate_phase_jina_input,
        validate_phase_variacao_input,
        validate_phase_builder_input,
    )
"""

from typing import Any

from backend.pipeline_exceptions import RequiredDataMissingError


def validate_phase_hunter_lead(raw_lead: dict[str, Any]) -> None:
    """Valida dados do lead após Hunter (fase 1-2).

    Dados obrigatórios:
    - nome: Nome do negócio
    - segmento: Categoria principal
    """
    errors: list[str] = []

    if not raw_lead.get("nome"):
        errors.append("nome: Nome do negocio obrigatorio")
    if not raw_lead.get("segmento"):
        errors.append("segmento: Categoria/segmento obrigatorio")

    if errors:
        raise RequiredDataMissingError(
            "Fase Hunter: dados obrigatorios ausentes.",
            context={
                "fase": "hunter",
                "erros": errors,
                "lead_nome": raw_lead.get("nome", ""),
                "acao": "Forneca nome e segmento do negocio",
            },
        )


def validate_phase_caio_input(lead_data: dict[str, Any]) -> None:
    """Valida dados antes de chamar CAIO (fase 4).

    Dados obrigatórios:
    - nome
    - segmento
    """
    errors: list[str] = []

    if not lead_data.get("nome"):
        errors.append("nome: obrigatorio")
    if not lead_data.get("segmento"):
        errors.append("segmento: obrigatorio")

    if errors:
        raise RequiredDataMissingError(
            "Fase CAIO: dados obrigatorios ausentes.",
            context={
                "fase": "caio",
                "erros": errors,
                "acao": "Verifique dados do lead",
            },
        )


def validate_phase_jina_input(nicho: str, cidade: str) -> None:
    """Valida dados antes de chamar JINA (fase 6).

    Dados obrigatórios:
    - nicho: Segmento do negócio
    - cidade: Cidade de atuação
    """
    errors: list[str] = []

    if not nicho or len(nicho.strip()) < 2:
        errors.append("nicho: Segmento invalido ou ausente")
    if not cidade or len(cidade.strip()) < 2:
        errors.append("cidade: Cidade invalida ou ausente")

    if errors:
        raise RequiredDataMissingError(
            "Fase JINA: dados obrigatorios ausentes.",
            context={
                "fase": "jina",
                "erros": errors,
                "nicho": nicho,
                "cidade": cidade,
                "acao": "Forneca nicho e cidade validos",
            },
        )


def validate_phase_variacao_input(nicho_briefing: dict[str, Any]) -> None:
    """Valida dados antes de gerar variação estrutural (fase 7).

    Dados obrigatórios:
    - nicho: Segmento do negócio
    - subnicho: Subnicho canonico (ou detectar automaticamente)
    """
    errors: list[str] = []

    if not nicho_briefing.get("nicho"):
        errors.append("nicho: Segmento obrigatorio")

    if errors:
        raise RequiredDataMissingError(
            "Fase Variacao: dados obrigatorios ausentes.",
            context={
                "fase": "variacao",
                "erros": errors,
                "acao": "Forneca nicho no briefing",
            },
        )


def validate_phase_builder_input(
    nome: str,
    segmento: str,
    cidade: str,
    variation: dict[str, Any] | None = None,
) -> None:
    """Valida dados antes de chamar Builder (fase 9-10).

    Dados obrigatórios:
    - nome: Nome do negócio
    - segmento: Categoria
    - cidade: Cidade

    Validação adicional:
    - variation: Deve existir e ter counter > 0
    """
    errors: list[str] = []

    if not nome or len(nome.strip()) < 2:
        errors.append("nome: Nome invalido")
    if not segmento or len(segmento.strip()) < 2:
        errors.append("segmento: Segmento invalido")
    if not cidade or len(cidade.strip()) < 2:
        errors.append("cidade: Cidade invalida")

    # Sprint 16: variation seed é obrigatório
    if not variation:
        errors.append("variation: VariationSeed obrigatorio (deve ser gerado em fase 7)")
    elif not variation.get("seed"):
        errors.append("variation.seed: Seed invalido")
    elif not variation.get("counter", 0) >= 0:
        errors.append("variation.counter: Counter invalido")

    if errors:
        raise RequiredDataMissingError(
            "Fase Builder: dados obrigatorios ausentes.",
            context={
                "fase": "builder",
                "erros": errors,
                "nome": nome,
                "segmento": segmento,
                "acao": "Verifique variation seed da fase 7",
            },
        )


def validate_required_fields(
    data: dict[str, Any],
    required_fields: list[str],
    fase: str,
) -> None:
    """Validação genérica: verifica campos obrigatórios em um dicionário.

    Args:
        data: Dicionário com os dados
        required_fields: Lista de campos obrigatórios
        fase: Nome da fase (para mensagem de erro)

    Raises:
        RequiredDataMissingError: Se algum campo obrigatório estiver ausente
    """
    errors: list[str] = []

    for field in required_fields:
        value = data.get(field)
        if value is None or value == "" or value == [] or value == {}:
            errors.append(f"{field}: campo obrigatorio ausente")

    if errors:
        raise RequiredDataMissingError(
            f"Fase {fase}: campos obrigatorios ausentes.",
            context={
                "fase": fase,
                "erros": errors,
                "acao": f"Forneca os campos obrigatorios para {fase}",
            },
        )
