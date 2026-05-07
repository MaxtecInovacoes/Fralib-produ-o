from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
import os

class BrainLearner:
    def __init__(self):
        self.scores_file = "scores_variacoes.json"
        self.aprendizados_file = "docs/BRAIN-APRENDIZADOS.md"
        self._criar_arquivos_iniciais()
    
    def _criar_arquivos_iniciais(self):
        if not os.path.exists(self.scores_file):
            self._criar_scores_inicial()
        if not os.path.exists(self.aprendizados_file):
            Path("docs").mkdir(exist_ok=True)
            with open(self.aprendizados_file, "w", encoding="utf-8") as f:
                f.write("# Brain Aprendizados\n\n")
    
    def _criar_scores_inicial(self):
        scores = {"academia": {"hero": {"A": 0.5, "B": 0.3, "C": 0.2}}}
        with open(self.scores_file, "w") as f:
            json.dump(scores, f, indent=2)
    
    def processar_feedback_dashboard(self, site_id: str, aprovado: bool, mudancas: List[str] = None):
        peso = 1.0
        print(f"[Brain] Dashboard feedback peso {peso}x")
    
    def processar_feedback_cliente(self, site_id: str, mensagem: str):
        peso = 3.0
        print(f"[Brain] Cliente feedback peso {peso}x")
    
    def carregar_scores(self, segmento: str) -> Dict:
        try:
            with open(self.scores_file, "r") as f:
                return json.load(f).get(segmento, {})
        except:
            return {}

brain_learner = BrainLearner()

def get_scores(segmento: str) -> Dict:
    return brain_learner.carregar_scores(segmento)

def feedback_dashboard(site_id: str, aprovado: bool, mudancas: List[str] = None):
    brain_learner.processar_feedback_dashboard(site_id, aprovado, mudancas)

def feedback_cliente(site_id: str, mensagem: str):
    brain_learner.processar_feedback_cliente(site_id, mensagem)
