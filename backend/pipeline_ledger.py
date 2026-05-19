"""
Pipeline Ledger — Documento vivo do pipeline run (PRD #6)
Padrão: Ledger Pattern (Magentic-One, Microsoft)
Registra Facts, Plan, Progress, Assignments, Decisões.
"""

import time
import json
import uuid
import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class FaseStatus(Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    FALHOU = "falhou"
    PULADA = "pulada"


@dataclass
class Ledger:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: float = field(default_factory=time.time)

    facts: dict = field(default_factory=lambda: {
        "lead_nome": None,
        "lead_telefone": None,
        "lead_endereco": None,
        "nicho": None,
        "segmento": None,
        "tier": None,
        "cidade": None,
        "tem_reviews": False,
        "qtd_reviews": 0,
        "tem_site": False,
        "score_qualificacao": 0,
        "keywords": [],
        "referencias_jina": None,
        "design_direction": None,
        "fotos_disponiveis": 0,
    })

    plan: list = field(default_factory=lambda: [
        {"fase": 1, "nome": "hunter_kw", "desc": "Buscar lead + keywords", "obrigatoria": True},
        {"fase": 2, "nome": "caio", "desc": "Qualificar lead", "obrigatoria": True},
        {"fase": 3, "nome": "jina", "desc": "Pesquisar referências", "obrigatoria": False},
        {"fase": 4, "nome": "theo", "desc": "Briefing estratégico", "obrigatoria": False},
        {"fase": 5, "nome": "unsplash", "desc": "Buscar fotos", "obrigatoria": True},
        {"fase": 6, "nome": "arquiteto", "desc": "Gerar PRD", "obrigatoria": True},
        {"fase": 7, "nome": "liam", "desc": "Gerar HTML", "obrigatoria": True},
        {"fase": 8, "nome": "liz", "desc": "Auditar qualidade", "obrigatoria": True},
        {"fase": 9, "nome": "deploy", "desc": "Publicar site", "obrigatoria": True},
        {"fase": 10, "nome": "bryan", "desc": "Enviar WhatsApp", "obrigatoria": False},
    ])

    progress: list = field(default_factory=list)
    assignments: dict = field(default_factory=lambda: {
        "fase_atual": 0,
        "agente_ativo": None,
        "modelo": None,
        "proxima_acao": "iniciar_pipeline",
        "bloqueado_por": None,
    })
    decisoes: list = field(default_factory=list)

    def registrar_inicio_fase(self, fase: int, nome: str, modelo: str = None):
        self.assignments["fase_atual"] = fase
        self.assignments["agente_ativo"] = nome
        self.assignments["modelo"] = modelo
        self.progress.append({
            "fase": fase,
            "nome": nome,
            "status": FaseStatus.EM_ANDAMENTO.value,
            "inicio": time.time(),
            "fim": None,
            "duracao_s": None,
            "resultado": None,
            "erro": None,
            "tentativas": self.tentativas_fase(fase) + 1,
            "decisao": None,
        })

    def registrar_fim_fase(self, fase: int, status: FaseStatus, resultado: str = None, erro: str = None):
        for p in reversed(self.progress):
            if p["fase"] == fase and p["status"] == FaseStatus.EM_ANDAMENTO.value:
                p["status"] = status.value
                p["fim"] = time.time()
                p["duracao_s"] = round(p["fim"] - p["inicio"], 1)
                p["resultado"] = resultado
                p["erro"] = erro
                break
        self.assignments["agente_ativo"] = None
        self.assignments["modelo"] = None
        self.assignments["proxima_acao"] = self._determinar_proxima_acao(fase, status)

    def registrar_decisao(self, fase: int, decisao: str, motivo: str):
        self.decisoes.append({
            "timestamp": time.time(),
            "fase": fase,
            "decisao": decisao,
            "motivo": motivo,
        })

    def atualizar_fact(self, chave: str, valor):
        self.facts[chave] = valor

    def fase_falhou(self, fase: int) -> bool:
        return any(p["fase"] == fase and p["status"] == FaseStatus.FALHOU.value for p in self.progress)

    def tentativas_fase(self, fase: int) -> int:
        return sum(1 for p in self.progress if p["fase"] == fase)

    def _determinar_proxima_acao(self, fase_atual: int, status: FaseStatus) -> str:
        if status == FaseStatus.CONCLUIDA:
            proxima = fase_atual + 1
            if proxima > 10:
                return "pipeline_completo"
            return f"executar_fase_{proxima}"
        elif status == FaseStatus.FALHOU:
            fase_info = next((p for p in self.plan if p["fase"] == fase_atual), None)
            if fase_info and not fase_info["obrigatoria"]:
                return f"pular_para_fase_{fase_atual + 1}"
            return f"retry_fase_{fase_atual}"
        return "aguardando"

    def snapshot(self) -> str:
        status_map = {"concluida": "✓", "falhou": "✗", "em_andamento": "⏳", "pulada": "⊘", "pendente": "○"}
        fases_status = " → ".join([
            f"{p['nome']}({status_map.get(p['status'], '?')})"
            for p in self.progress
        ]) or "nenhuma fase executada"
        return (
            f"[LEDGER] Run {self.run_id} | {self.facts.get('lead_nome', '?')} | {self.facts.get('nicho', '?')}\n"
            f"[LEDGER] Progress: {fases_status}\n"
            f"[LEDGER] Atual: fase {self.assignments['fase_atual']} | agente: {self.assignments['agente_ativo']} | próxima: {self.assignments['proxima_acao']}\n"
            f"[LEDGER] Decisões: {len(self.decisoes)} | Erros: {sum(1 for p in self.progress if p['status'] == 'falhou')}"
        )

    def to_json(self) -> str:
        return json.dumps({
            "run_id": self.run_id,
            "created_at": self.created_at,
            "facts": self.facts,
            "plan": self.plan,
            "progress": self.progress,
            "assignments": self.assignments,
            "decisoes": self.decisoes,
        }, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "Ledger":
        d = json.loads(data)
        ledger = cls()
        ledger.run_id = d["run_id"]
        ledger.created_at = d["created_at"]
        ledger.facts = d["facts"]
        ledger.plan = d["plan"]
        ledger.progress = d["progress"]
        ledger.assignments = d["assignments"]
        ledger.decisoes = d["decisoes"]
        return ledger


LEDGER_DIR = "/tmp/fralib_ledgers"


def salvar_ledger(ledger: Ledger):
    try:
        os.makedirs(LEDGER_DIR, exist_ok=True)
        path = f"{LEDGER_DIR}/{ledger.run_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(ledger.to_json())
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO pipeline_ledgers (run_id, lead_nome, nicho, ledger_json, created_at)
                VALUES (:run_id, :lead_nome, :nicho, :ledger_json, NOW())
                ON CONFLICT (run_id) DO UPDATE SET ledger_json = EXCLUDED.ledger_json
            """), {
                "run_id": ledger.run_id,
                "lead_nome": ledger.facts.get("lead_nome"),
                "nicho": ledger.facts.get("nicho"),
                "ledger_json": ledger.to_json(),
            })
            conn.commit()
    except Exception as e:
        print(f"[LEDGER][WARN] Falha ao salvar: {e}")


def carregar_ledger(run_id: str) -> Optional[Ledger]:
    path = f"{LEDGER_DIR}/{run_id}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return Ledger.from_json(f.read())
    return None
