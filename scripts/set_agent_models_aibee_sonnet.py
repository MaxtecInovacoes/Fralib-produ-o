"""Deprecated compatibility wrapper for the old Aibee/Sonnet script.

The canonical production route is now the FraLib LiteLLM proxy pool. Keeping
this filename avoids breaking old runbooks while preventing rollback to legacy
single-model routing.
"""

from __future__ import annotations

from set_agent_models_proxy_pool import main


if __name__ == "__main__":
    main()
