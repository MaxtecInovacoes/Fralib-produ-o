"""LGPD Banner personalizado por negócio.

Contorna o bug de sintaxe em vite_templates.py criando a versão
personalizada em arquivo separado.
"""

from typing import Any
import re


def _slugify(text: str) -> str:
    text = str(text or "").lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:20] or "default"


def build_personalized_lgpd(facts: dict[str, Any]) -> str:
    """Gera código TSX do LgpdBanner personalizado por negócio."""
    business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
    nome = business.get("name") or "Este site"
    cidade = business.get("city") or ""
    segment = business.get("segment") or "negócio local"

    consent_key = "lgpd_consent_" + _slugify(nome)

    if segment in ("restaurante", "pizzaria", "lanchonete", "churrascaria"):
        servico = "pedidos, reservas e entrega de alimentos"
    elif segment in ("clinica", "odontologia", "nutricionista", "psicologia"):
        servico = "agendamento de consultas e atendimento"
    elif segment in ("academia", "crossfit"):
        servico = "matriculas e acompanhamento fitness"
    elif segment in ("barbearia", "estetica", "salao_beleza"):
        servico = "agendamento de horarios e servicos de beleza"
    elif segment in ("advocacia", "contabilidade"):
        servico = "atendimento juridico e contabil"
    else:
        servico = "atendimento e prestacao de servicos"

    cidade_text = (" em " + cidade) if cidade else ""
    copy = (
        "Seus dados sao usados apenas para " + servico + cidade_text +
        ", nunca compartilhados com terceiros sem consentimento."
    )

    # Usar string regular, NAO f-string, para evitar problemas com {{ }}
    return '''import { useEffect, useState } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { motion } from 'motion/react';

const CONSENT_KEY = "''' + consent_key + '''";

interface LgpdBannerProps {
  businessName?: string;
  city?: string;
  customMessage?: string;
}

export function LgpdBanner({ businessName, city, customMessage }: LgpdBannerProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    try {
      if (localStorage.getItem(CONSENT_KEY) === "1") setVisible(false);
    } catch {}
  }, []);

  const accept = () => {
    try {
      localStorage.setItem(CONSENT_KEY, "1");
    } catch {}
    setVisible(false);
  };

  if (!visible) return null;

  const message = customMessage || "''' + copy + '''";

  return (
    <motion.div
      data-lgpd-banner
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed inset-x-4 bottom-4 z-[9999] mx-auto grid max-w-3xl grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border border-white/15 bg-zinc-950/94 p-4 text-white shadow-2xl backdrop-blur"
      role="dialog"
      aria-label="Aviso de privacidade"
    >
      <ShieldCheck className="h-5 w-5 text-emerald-300" />
      <p className="text-sm leading-5 text-zinc-200">{message}</p>
      <div className="flex items-center gap-2">
        <button type="button" data-lgpd-accept onClick={accept} className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-semibold text-zinc-950">
          Aceitar
        </button>
        <button type="button" aria-label="Fechar aviso de privacidade" onClick={accept} className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 text-white">
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}

export default LgpdBanner;
'''


if __name__ == "__main__":
    test_facts = {"business": {"name": "Pizzaria Napoli", "city": "Sao Paulo", "segment": "pizzaria"}}
    code = build_personalized_lgpd(test_facts)
    assert "Pizzaria-Napoli" in code or "lgpd_consent_pizzaria" in code, "Consent key not found"
    assert "pedidos" in code, "Custom copy not found"
    print("[OK] LGPD personalized works")
