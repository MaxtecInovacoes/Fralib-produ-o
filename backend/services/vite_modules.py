"""Vite/React module exports."""

try:
    from vite_config import (
        FIXED_PACKAGE_JSON,
        REQUIRED_PROJECT_FILES,
        BLOCKED_SOURCE_PATTERNS,
        SEGMENT_RULES,
        VITE_REACT_FILE_BATCHES,
        _env_int,
        _model_repair_attempts,
        _single_model_mode_enabled,
        _preview_fast_enabled,
        _batch_first_enabled,
        _batch_first_project_attempts,
        _batch_spacing_seconds,
        _transient_proxy_retry_delay_seconds,
    )
except ImportError:
    from backend.services.vite_config import (
        FIXED_PACKAGE_JSON,
        REQUIRED_PROJECT_FILES,
        BLOCKED_SOURCE_PATTERNS,
        SEGMENT_RULES,
        VITE_REACT_FILE_BATCHES,
        _env_int,
        _model_repair_attempts,
        _single_model_mode_enabled,
        _preview_fast_enabled,
        _batch_first_enabled,
        _batch_first_project_attempts,
        _batch_spacing_seconds,
        _transient_proxy_retry_delay_seconds,
    )

try:
    from vite_prompts import (
        VITE_REACT_SYSTEM_PROMPT,
        VITE_REACT_BATCH_SYSTEM_PROMPT,
        _compose_vite_user_prompt,
        _compose_vite_file_batch_prompt,
        _summarize_builder_facts,
        _segment_contamination_guard,
        _safe_project_path,
        _meta_escape,
    )
except ImportError:
    from backend.services.vite_prompts import (
        VITE_REACT_SYSTEM_PROMPT,
        VITE_REACT_BATCH_SYSTEM_PROMPT,
        _compose_vite_user_prompt,
        _compose_vite_file_batch_prompt,
        _summarize_builder_facts,
        _segment_contamination_guard,
        _safe_project_path,
        _meta_escape,
    )

try:
    from vite_facts import (
        _segment_key_for_business,
        _segment_key_from_facts,
        _validate_segment_specificity,
        _facts_business,
        _facts_publication_url,
        _facts_theme_color,
        _facts_local_keywords,
        _facts_meta_description,
        _facts_og_image,
        _facts_json_ld,
        _visual_business_payload,
        _visual_media_urls,
    )
except ImportError:
    from backend.services.vite_facts import (
        _segment_key_for_business,
        _segment_key_from_facts,
        _validate_segment_specificity,
        _facts_business,
        _facts_publication_url,
        _facts_theme_color,
        _facts_local_keywords,
        _facts_meta_description,
        _facts_og_image,
        _facts_json_ld,
        _visual_business_payload,
        _visual_media_urls,
    )

try:
    from vite_file_extractor import (
        extract_vite_project_files,
        _clean_json_block,
        _normalize_text,
        _normalize_model_alias,
    )
except ImportError:
    from backend.services.vite_file_extractor import (
        extract_vite_project_files,
        _clean_json_block,
        _normalize_text,
        _normalize_model_alias,
    )

try:
    from vite_validator import (
        validate_vite_project_files,
        validate_vite_dist,
    )
except ImportError:
    from backend.services.vite_validator import (
        validate_vite_project_files,
        validate_vite_dist,
    )

try:
    from vite_build_executor import (
        write_vite_project,
        build_vite_project,
        _node_bin,
        _npm_bin,
    )
except ImportError:
    from backend.services.vite_build_executor import (
        write_vite_project,
        build_vite_project,
        _node_bin,
        _npm_bin,
    )

__all__ = [
    # config
    "FIXED_PACKAGE_JSON",
    "REQUIRED_PROJECT_FILES",
    "BLOCKED_SOURCE_PATTERNS",
    "SEGMENT_RULES",
    "VITE_REACT_FILE_BATCHES",
    # prompts
    "VITE_REACT_SYSTEM_PROMPT",
    "VITE_REACT_BATCH_SYSTEM_PROMPT",
    # facts
    "_facts_business",
    "_facts_publication_url",
    "_facts_theme_color",
    "_facts_meta_description",
    # file extraction
    "extract_vite_project_files",
    # validation
    "validate_vite_project_files",
    "validate_vite_dist",
    # build
    "write_vite_project",
    "build_vite_project",
]
