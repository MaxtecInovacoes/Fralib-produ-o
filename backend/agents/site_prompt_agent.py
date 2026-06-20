"""Prompt Agent: turns FraLib research data into the only Builder request.

This module is a thin wrapper re-exporting all public symbols from:
- backend.agents.prompt_agent_builder: build_prompt_agent_payload, render_builder_prompt
- backend.agents.prompt_agent_helpers: utility, parsing, extraction, formatting functions
- backend.agents.prompt_agent_context: business, qualification, research, SEO, content, media, design, publication context functions
"""

from __future__ import annotations

from backend.agents.prompt_agent_builder import (
    build_prompt_agent_payload,
    render_builder_prompt,
)
from backend.agents.prompt_agent_context import (
    _business_context,
    _content_context,
    _design_context,
    _direction_for_archetype,
    _fmt_visual_direction,
    _ideal_customer_context,
    _infer_prompt_archetype,
    _market_intelligence_context,
    _media_context,
    _normalize_target,
    _premium_delivery_contract,
    _publication_context,
    _qualification_context,
    _research_context,
    _runtime_site_skill_pack,
    _section_request,
    _section_sequence_for_niche,
    _seo_context,
    _visual_direction_contract,
    _visual_section_order,
    _VALID_TARGETS,
)
from backend.agents.prompt_agent_helpers import (
    _allowed_numeric_claims,
    _as_dict,
    _as_list,
    _clean_dict,
    _compact,
    _dict,
    _dump_compact,
    _extract_keyword_candidates,
    _first,
    _fmt_contract_facts,
    _fmt_list,
    _fmt_missing_contract_fields,
    _fmt_research,
    _fmt_sections,
    _fmt_value,
    _infer_subniche,
    _media_urls,
    _normalize,
    _qualification_summary,
    _sanitize_primary_term,
    _section_name,
    _strip_legacy_control_text,
)

__all__ = [
    # Builder functions
    "build_prompt_agent_payload",
    "render_builder_prompt",
    # Context functions
    "_business_context",
    "_content_context",
    "_design_context",
    "_direction_for_archetype",
    "_fmt_visual_direction",
    "_ideal_customer_context",
    "_infer_prompt_archetype",
    "_market_intelligence_context",
    "_media_context",
    "_normalize_target",
    "_premium_delivery_contract",
    "_publication_context",
    "_qualification_context",
    "_research_context",
    "_runtime_site_skill_pack",
    "_section_request",
    "_section_sequence_for_niche",
    "_seo_context",
    "_visual_direction_contract",
    "_visual_section_order",
    "_VALID_TARGETS",
    # Helper functions
    "_allowed_numeric_claims",
    "_as_dict",
    "_as_list",
    "_clean_dict",
    "_compact",
    "_dict",
    "_dump_compact",
    "_extract_keyword_candidates",
    "_first",
    "_fmt_contract_facts",
    "_fmt_list",
    "_fmt_missing_contract_fields",
    "_fmt_research",
    "_fmt_sections",
    "_fmt_value",
    "_infer_subniche",
    "_media_urls",
    "_normalize",
    "_qualification_summary",
    "_sanitize_primary_term",
    "_section_name",
    "_strip_legacy_control_text",
]
