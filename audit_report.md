# Audit de Codebase

Total de achados: 682

## Resumo por severidade

- CRÍTICO: 288
- MÉDIO: 283
- BAIXO: 111

## BAIXO — duplicate_import

- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 102 -> duplicate_import - Import duplicado de `agents.llm_direct._invalidar_agent_config_cache`; primeira ocorrência na linha 256
- [C:\fralib\backend\endpoints\api_usage_endpoints.py](C:\fralib\backend\endpoints\api_usage_endpoints.py) -> linha 43 -> duplicate_import - Import duplicado de `datetime.timezone`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 112 -> duplicate_import - Import duplicado de `sqlalchemy.text`; primeira ocorrência na linha 3
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 134 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 119
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 247 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 119
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 294 -> duplicate_import - Import duplicado de `pydantic.BaseModel`; primeira ocorrência na linha 104
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 378 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 119
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 387 -> duplicate_import - Import duplicado de `datetime.datetime`; primeira ocorrência na linha 309
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 389 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 105
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 589 -> duplicate_import - Import duplicado de `pydantic.BaseModel`; primeira ocorrência na linha 104
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 590 -> duplicate_import - Import duplicado de `typing.Optional`; primeira ocorrência na linha 295
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 798 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 105
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 798 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 119
- [C:\fralib\backend\endpoints\pipeline_edit_endpoints.py](C:\fralib\backend\endpoints\pipeline_edit_endpoints.py) -> linha 68 -> duplicate_import - Import duplicado de `agents.liz.listar_secoes`; primeira ocorrência na linha 29
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 19 -> duplicate_import - Import duplicado de `logging`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 116 -> duplicate_import - Import duplicado de `datetime.datetime`; primeira ocorrência na linha 5
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 116 -> duplicate_import - Import duplicado de `datetime.timedelta`; primeira ocorrência na linha 5
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 290 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 365 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 379 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 450 -> duplicate_import - Import duplicado de `hashlib`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 481 -> duplicate_import - Import duplicado de `concurrent.futures.ThreadPoolExecutor`; primeira ocorrência na linha 6
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 507 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 648 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 763 -> duplicate_import - Import duplicado de `agents.caio.CaioOutput`; primeira ocorrência na linha 378
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 810 -> duplicate_import - Import duplicado de `agents.caio.qualificar_lead`; primeira ocorrência na linha 2371
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 810 -> duplicate_import - Import duplicado de `agents.caio.LeadInput`; primeira ocorrência na linha 2371
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 837 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1150 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1202 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1387 -> duplicate_import - Import duplicado de `job_queue`; primeira ocorrência na linha 1938
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1416 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1476 -> duplicate_import - Import duplicado de `agents.token_tracker.set_tracker`; primeira ocorrência na linha 318
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1486 -> duplicate_import - Import duplicado de `agent_router.set_router`; primeira ocorrência na linha 866
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1551 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1822 -> duplicate_import - Import duplicado de `datetime.datetime`; primeira ocorrência na linha 5
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1822 -> duplicate_import - Import duplicado de `datetime.timezone`; primeira ocorrência na linha 116
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1822 -> duplicate_import - Import duplicado de `datetime.timedelta`; primeira ocorrência na linha 5
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2044 -> duplicate_import - Import duplicado de `datetime.datetime`; primeira ocorrência na linha 5
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2044 -> duplicate_import - Import duplicado de `datetime.timezone`; primeira ocorrência na linha 116
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2044 -> duplicate_import - Import duplicado de `datetime.timedelta`; primeira ocorrência na linha 5
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2233 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 153
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2329 -> duplicate_import - Import duplicado de `asyncio`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2344 -> duplicate_import - Import duplicado de `hashlib`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2344 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2370 -> duplicate_import - Import duplicado de `asyncio`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2370 -> duplicate_import - Import duplicado de `hashlib`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2370 -> duplicate_import - Import duplicado de `random`; primeira ocorrência na linha 4
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 120 -> duplicate_import - Import duplicado de `httpx`; primeira ocorrência na linha 8
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 120 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 7
- [C:\fralib\backend\services\pipeline_state.py](C:\fralib\backend\services\pipeline_state.py) -> linha 93 -> duplicate_import - Import duplicado de `agents.pipeline_checkpoint.gerar_pipeline_id`; primeira ocorrência na linha 36
- [C:\fralib\backend\agents\design_context.py](C:\fralib\backend\agents\design_context.py) -> linha 550 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 562
- [C:\fralib\backend\agents\design_context.py](C:\fralib\backend\agents\design_context.py) -> linha 1061 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 562
- [C:\fralib\backend\agents\design_prompts.py](C:\fralib\backend\agents\design_prompts.py) -> linha 34 -> duplicate_import - Import duplicado de `design_context.get_design_context`; primeira ocorrência na linha 11
- [C:\fralib\backend\agents\html_builder_repair.py](C:\fralib\backend\agents\html_builder_repair.py) -> linha 267 -> duplicate_import - Import duplicado de `backend.agents.html_phase6_repair.publication_page_title`; primeira ocorrência na linha 195
- [C:\fralib\backend\agents\html_builder_repair.py](C:\fralib\backend\agents\html_builder_repair.py) -> linha 273 -> duplicate_import - Import duplicado de `backend.agents.html_phase6_repair.publication_page_description`; primeira ocorrência na linha 195
- [C:\fralib\backend\agents\jina_research.py](C:\fralib\backend\agents\jina_research.py) -> linha 7 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 1
- [C:\fralib\backend\agents\liz.py](C:\fralib\backend\agents\liz.py) -> linha 73 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 7
- [C:\fralib\backend\agents\liz.py](C:\fralib\backend\agents\liz.py) -> linha 144 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 7
- [C:\fralib\backend\agents\liz.py](C:\fralib\backend\agents\liz.py) -> linha 162 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 7
- [C:\fralib\backend\agents\liz.py](C:\fralib\backend\agents\liz.py) -> linha 222 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 7
- [C:\fralib\backend\agents\llm_agent_config.py](C:\fralib\backend\agents\llm_agent_config.py) -> linha 56 -> duplicate_import - Import duplicado de `backend.agents.llm_config`; primeira ocorrência na linha 9
- [C:\fralib\backend\agents\llm_config.py](C:\fralib\backend\agents\llm_config.py) -> linha 63 -> duplicate_import - Import duplicado de `backend.core.proxy_models.PROXY_BUILDER_MODEL`; primeira ocorrência na linha 55
- [C:\fralib\backend\agents\llm_config.py](C:\fralib\backend\agents\llm_config.py) -> linha 63 -> duplicate_import - Import duplicado de `backend.core.proxy_models.PROXY_DEFAULT_MODEL`; primeira ocorrência na linha 55
- [C:\fralib\backend\agents\llm_config.py](C:\fralib\backend\agents\llm_config.py) -> linha 63 -> duplicate_import - Import duplicado de `backend.core.proxy_models.PROXY_LIGHT_MODEL`; primeira ocorrência na linha 55
- [C:\fralib\backend\agents\llm_config.py](C:\fralib\backend\agents\llm_config.py) -> linha 63 -> duplicate_import - Import duplicado de `backend.core.proxy_models.PROXY_PROVIDER`; primeira ocorrência na linha 55
- [C:\fralib\backend\agents\llm_config.py](C:\fralib\backend\agents\llm_config.py) -> linha 63 -> duplicate_import - Import duplicado de `backend.core.proxy_models.is_proxy_model`; primeira ocorrência na linha 55
- [C:\fralib\backend\agents\llm_context.py](C:\fralib\backend\agents\llm_context.py) -> linha 245 -> duplicate_import - Import duplicado de `ia_manager`; primeira ocorrência na linha 121
- [C:\fralib\backend\agents\llm_direct.py](C:\fralib\backend\agents\llm_direct.py) -> linha 402 -> duplicate_import - Import duplicado de `time`; primeira ocorrência na linha 26
- [C:\fralib\backend\agents\llm_direct.py](C:\fralib\backend\agents\llm_direct.py) -> linha 672 -> duplicate_import - Import duplicado de `ia_manager`; primeira ocorrência na linha 349
- [C:\fralib\backend\agents\llm_direct.py](C:\fralib\backend\agents\llm_direct.py) -> linha 942 -> duplicate_import - Import duplicado de `ia_manager`; primeira ocorrência na linha 349
- [C:\fralib\backend\agents\llm_tracking.py](C:\fralib\backend\agents\llm_tracking.py) -> linha 81 -> duplicate_import - Import duplicado de `agents.token_tracker.get_tracker`; primeira ocorrência na linha 30
- [C:\fralib\backend\agents\llm_tracking.py](C:\fralib\backend\agents\llm_tracking.py) -> linha 83 -> duplicate_import - Import duplicado de `token_tracker.get_tracker`; primeira ocorrência na linha 32
- [C:\fralib\backend\agents\pipeline_learning.py](C:\fralib\backend\agents\pipeline_learning.py) -> linha 106 -> duplicate_import - Import duplicado de `agent_memory.MemoryEntry`; primeira ocorrência na linha 46
- [C:\fralib\backend\agents\pipeline_learning.py](C:\fralib\backend\agents\pipeline_learning.py) -> linha 108 -> duplicate_import - Import duplicado de `agents.agent_memory.MemoryEntry`; primeira ocorrência na linha 48
- [C:\fralib\backend\agents\prompt_agent_context.py](C:\fralib\backend\agents\prompt_agent_context.py) -> linha 205 -> duplicate_import - Import duplicado de `backend.agents.prompt_agent_helpers._as_list`; primeira ocorrência na linha 7
- [C:\fralib\backend\agents\sdr_langgraph\compat.py](C:\fralib\backend\agents\sdr_langgraph\compat.py) -> linha 120 -> duplicate_import - Import duplicado de `agents.memory.carregar_memoria`; primeira ocorrência na linha 88
- [C:\fralib\backend\agents\sdr_langgraph\compat.py](C:\fralib\backend\agents\sdr_langgraph\compat.py) -> linha 225 -> duplicate_import - Import duplicado de `agents.memory.carregar_memoria`; primeira ocorrência na linha 88
- [C:\fralib\backend\agents\theo.py](C:\fralib\backend\agents\theo.py) -> linha 17 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 6
- [C:\fralib\backend\agents\theo.py](C:\fralib\backend\agents\theo.py) -> linha 79 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 4
- [C:\fralib\backend\agents\theo.py](C:\fralib\backend\agents\theo.py) -> linha 236 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 5
- [C:\fralib\backend\agents\theo.py](C:\fralib\backend\agents\theo.py) -> linha 470 -> duplicate_import - Import duplicado de `time`; primeira ocorrência na linha 79
- [C:\fralib\backend\agents\theo.py](C:\fralib\backend\agents\theo.py) -> linha 737 -> duplicate_import - Import duplicado de `typing.Optional`; primeira ocorrência na linha 9
- [C:\fralib\backend\agents\theo.py](C:\fralib\backend\agents\theo.py) -> linha 738 -> duplicate_import - Import duplicado de `pydantic.BaseModel`; primeira ocorrência na linha 8
- [C:\fralib\backend\core\database.py](C:\fralib\backend\core\database.py) -> linha 17 -> duplicate_import - Import duplicado de `proxy_models.ALLOWED_PROXY_MODELS`; primeira ocorrência na linha 9
- [C:\fralib\backend\core\database.py](C:\fralib\backend\core\database.py) -> linha 17 -> duplicate_import - Import duplicado de `proxy_models.PROXY_BUILDER_MODEL`; primeira ocorrência na linha 9
- [C:\fralib\backend\core\database.py](C:\fralib\backend\core\database.py) -> linha 17 -> duplicate_import - Import duplicado de `proxy_models.PROXY_DEFAULT_MODEL`; primeira ocorrência na linha 9
- [C:\fralib\backend\core\database.py](C:\fralib\backend\core\database.py) -> linha 17 -> duplicate_import - Import duplicado de `proxy_models.PROXY_LIGHT_MODEL`; primeira ocorrência na linha 9
- [C:\fralib\backend\core\database.py](C:\fralib\backend\core\database.py) -> linha 17 -> duplicate_import - Import duplicado de `proxy_models.PROXY_PROVIDER`; primeira ocorrência na linha 9
- [C:\fralib\backend\utils\agente1_hunter_v2.py](C:\fralib\backend\utils\agente1_hunter_v2.py) -> linha 623 -> duplicate_import - Import duplicado de `agents.caio.LeadInput`; primeira ocorrência na linha 570
- [C:\fralib\backend\utils\agente1_hunter_v2.py](C:\fralib\backend\utils\agente1_hunter_v2.py) -> linha 623 -> duplicate_import - Import duplicado de `agents.caio.qualificar_lead`; primeira ocorrência na linha 570
- [C:\fralib\backend\utils\google_scraper_core.py](C:\fralib\backend\utils\google_scraper_core.py) -> linha 82 -> duplicate_import - Import duplicado de `asyncio`; primeira ocorrência na linha 4
- [C:\fralib\backend\utils\google_scraper_core.py](C:\fralib\backend\utils\google_scraper_core.py) -> linha 198 -> duplicate_import - Import duplicado de `asyncio`; primeira ocorrência na linha 4
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 64 -> duplicate_import - Import duplicado de `time`; primeira ocorrência na linha 12
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 82 -> duplicate_import - Import duplicado de `datetime.date`; primeira ocorrência na linha 13
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 203 -> duplicate_import - Import duplicado de `sqlalchemy.text`; primeira ocorrência na linha 18
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 430 -> duplicate_import - Import duplicado de `sqlalchemy.create_engine`; primeira ocorrência na linha 18
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 430 -> duplicate_import - Import duplicado de `sqlalchemy.text`; primeira ocorrência na linha 18
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 734 -> duplicate_import - Import duplicado de `re`; primeira ocorrência na linha 9
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 784 -> duplicate_import - Import duplicado de `datetime.datetime`; primeira ocorrência na linha 13
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 913 -> duplicate_import - Import duplicado de `json`; primeira ocorrência na linha 7
- [C:\fralib\frontend\build.py](C:\fralib\frontend\build.py) -> linha 17 -> duplicate_import - Import duplicado de `shutil`; primeira ocorrência na linha 85
- [C:\fralib\frontend\build.py](C:\fralib\frontend\build.py) -> linha 85 -> duplicate_import - Import duplicado de `os`; primeira ocorrência na linha 6
- [C:\fralib\prime-agent\packages\coding-agent\skills\attach-image\src\attach_image\attach_image.py](C:\fralib\prime-agent\packages\coding-agent\skills\attach-image\src\attach_image\attach_image.py) -> linha 40 -> duplicate_import - Import duplicado de `PIL.Image`; primeira ocorrência na linha 107
- [C:\fralib\prime-agent\packages\coding-agent\skills\attach-image\src\attach_image\attach_image.py](C:\fralib\prime-agent\packages\coding-agent\skills\attach-image\src\attach_image\attach_image.py) -> linha 57 -> duplicate_import - Import duplicado de `PIL.Image`; primeira ocorrência na linha 107
- [C:\fralib\prime-agent\packages\coding-agent\skills\attach-image\src\attach_image\attach_image.py](C:\fralib\prime-agent\packages\coding-agent\skills\attach-image\src\attach_image\attach_image.py) -> linha 148 -> duplicate_import - Import duplicado de `PIL.Image`; primeira ocorrência na linha 107
- [C:\fralib\server.py](C:\fralib\server.py) -> linha 198 -> duplicate_import - Import duplicado de `sys`; primeira ocorrência na linha 20
- [C:\fralib\server.py](C:\fralib\server.py) -> linha 329 -> duplicate_import - Import duplicado de `backend.core.observability_setup.deep_health_check`; primeira ocorrência na linha 5

## BAIXO — syntax_error

- [C:\fralib\backend\services\credits_manager.py](C:\fralib\backend\services\credits_manager.py) -> linha 1 -> syntax_error - invalid non-printable character U+FEFF
- [C:\fralib\backend\agents\color_enforcer.py](C:\fralib\backend\agents\color_enforcer.py) -> linha 1 -> syntax_error - invalid non-printable character U+FEFF
- [C:\fralib\scripts\fixes\worker_patched.py](C:\fralib\scripts\fixes\worker_patched.py) -> linha 200 -> syntax_error - expected 'except' or 'finally' block

## CRÍTICO — async_endpoint_uses_sync_db_method

- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 34 -> async_endpoint_uses_sync_db_method - Endpoint async `register_ab_event` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 41 -> async_endpoint_uses_sync_db_method - Endpoint async `register_ab_event` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 57 -> async_endpoint_uses_sync_db_method - Endpoint async `convert_ab_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 65 -> async_endpoint_uses_sync_db_method - Endpoint async `convert_ab_lead` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 80 -> async_endpoint_uses_sync_db_method - Endpoint async `get_ab_report` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 50 -> async_endpoint_uses_sync_db_method - Endpoint async `list_configs` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 85 -> async_endpoint_uses_sync_db_method - Endpoint async `update_config` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 92 -> async_endpoint_uses_sync_db_method - Endpoint async `update_config` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 97 -> async_endpoint_uses_sync_db_method - Endpoint async `update_config` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 98 -> async_endpoint_uses_sync_db_method - Endpoint async `update_config` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 162 -> async_endpoint_uses_sync_db_method - Endpoint async `run_playground` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 173 -> async_endpoint_uses_sync_db_method - Endpoint async `run_playground` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 191 -> async_endpoint_uses_sync_db_method - Endpoint async `playground_history` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 264 -> async_endpoint_uses_sync_db_method - Endpoint async `run_pipeline_sandbox` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 270 -> async_endpoint_uses_sync_db_method - Endpoint async `run_pipeline_sandbox` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 276 -> async_endpoint_uses_sync_db_method - Endpoint async `run_pipeline_sandbox` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 286 -> async_endpoint_uses_sync_db_method - Endpoint async `run_pipeline_sandbox` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 122 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 131 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 135 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.rollback()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 143 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 148 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 152 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 155 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 158 -> async_endpoint_uses_sync_db_method - Endpoint async `train_agent` usa chamada síncrona `db.rollback()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 171 -> async_endpoint_uses_sync_db_method - Endpoint async `list_training` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 200 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_training` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 209 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_training` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 234 -> async_endpoint_uses_sync_db_method - Endpoint async `list_sales_axes` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 273 -> async_endpoint_uses_sync_db_method - Endpoint async `toggle_sales_axis` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 279 -> async_endpoint_uses_sync_db_method - Endpoint async `toggle_sales_axis` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 284 -> async_endpoint_uses_sync_db_method - Endpoint async `toggle_sales_axis` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 288 -> async_endpoint_uses_sync_db_method - Endpoint async `toggle_sales_axis` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 291 -> async_endpoint_uses_sync_db_method - Endpoint async `toggle_sales_axis` usa chamada síncrona `db.rollback()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 143 -> async_endpoint_uses_sync_db_method - Endpoint async `register` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 150 -> async_endpoint_uses_sync_db_method - Endpoint async `register` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 173 -> async_endpoint_uses_sync_db_method - Endpoint async `register` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 176 -> async_endpoint_uses_sync_db_method - Endpoint async `register` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 179 -> async_endpoint_uses_sync_db_method - Endpoint async `register` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 228 -> async_endpoint_uses_sync_db_method - Endpoint async `reenviar_confirmacao` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 235 -> async_endpoint_uses_sync_db_method - Endpoint async `reenviar_confirmacao` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 237 -> async_endpoint_uses_sync_db_method - Endpoint async `reenviar_confirmacao` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 252 -> async_endpoint_uses_sync_db_method - Endpoint async `esqueci_senha` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 260 -> async_endpoint_uses_sync_db_method - Endpoint async `esqueci_senha` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 263 -> async_endpoint_uses_sync_db_method - Endpoint async `esqueci_senha` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 49 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_beta_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 61 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_beta_lead` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 75 -> async_endpoint_uses_sync_db_method - Endpoint async `listar_beta_leads` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits\checkout.py](C:\fralib\backend\endpoints\credits\checkout.py) -> linha 671 -> async_endpoint_uses_sync_db_method - Endpoint async `credits_balance` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits\checkout.py](C:\fralib\backend\endpoints\credits\checkout.py) -> linha 687 -> async_endpoint_uses_sync_db_method - Endpoint async `credits_check` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits\status.py](C:\fralib\backend\endpoints\credits\status.py) -> linha 25 -> async_endpoint_uses_sync_db_method - Endpoint async `get_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits\status.py](C:\fralib\backend\endpoints\credits\status.py) -> linha 42 -> async_endpoint_uses_sync_db_method - Endpoint async `credits_check` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 39 -> async_endpoint_uses_sync_db_method - Endpoint async `criar_portal_session` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 85 -> async_endpoint_uses_sync_db_method - Endpoint async `get_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 336 -> async_endpoint_uses_sync_db_method - Endpoint async `credits_balance` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 353 -> async_endpoint_uses_sync_db_method - Endpoint async `credits_check` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 22 -> async_endpoint_uses_sync_db_method - Endpoint async `get_incomplete` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 25 -> async_endpoint_uses_sync_db_method - Endpoint async `get_incomplete` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 40 -> async_endpoint_uses_sync_db_method - Endpoint async `get_crm` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 135 -> async_endpoint_uses_sync_db_method - Endpoint async `get_cost_per_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 181 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 188 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 201 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 224 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 240 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 38 -> async_endpoint_uses_sync_db_method - Endpoint async `listar_falhas` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 51 -> async_endpoint_uses_sync_db_method - Endpoint async `listar_falhas` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 85 -> async_endpoint_uses_sync_db_method - Endpoint async `contador_falhas` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 104 -> async_endpoint_uses_sync_db_method - Endpoint async `marcar_visto` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 112 -> async_endpoint_uses_sync_db_method - Endpoint async `marcar_visto` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 132 -> async_endpoint_uses_sync_db_method - Endpoint async `retry_falha` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 167 -> async_endpoint_uses_sync_db_method - Endpoint async `retry_falha` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 175 -> async_endpoint_uses_sync_db_method - Endpoint async `retry_falha` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 85 -> async_endpoint_uses_sync_db_method - Endpoint async `list_insights` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 100 -> async_endpoint_uses_sync_db_method - Endpoint async `get_insight` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 120 -> async_endpoint_uses_sync_db_method - Endpoint async `create_insight` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 132 -> async_endpoint_uses_sync_db_method - Endpoint async `create_insight` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 135 -> async_endpoint_uses_sync_db_method - Endpoint async `create_insight` usa chamada síncrona `db.rollback()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 151 -> async_endpoint_uses_sync_db_method - Endpoint async `promote_insight` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 159 -> async_endpoint_uses_sync_db_method - Endpoint async `promote_insight` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 166 -> async_endpoint_uses_sync_db_method - Endpoint async `promote_insight` usa chamada síncrona `db.rollback()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 180 -> async_endpoint_uses_sync_db_method - Endpoint async `discard_insight` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 187 -> async_endpoint_uses_sync_db_method - Endpoint async `discard_insight` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 194 -> async_endpoint_uses_sync_db_method - Endpoint async `discard_insight` usa chamada síncrona `db.rollback()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 233 -> async_endpoint_uses_sync_db_method - Endpoint async `upload_foto` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 802 -> async_endpoint_uses_sync_db_method - Endpoint async `enviar_mensagem_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 867 -> async_endpoint_uses_sync_db_method - Endpoint async `enviar_mensagem_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 870 -> async_endpoint_uses_sync_db_method - Endpoint async `enviar_mensagem_lead` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\llm_endpoints.py](C:\fralib\backend\endpoints\llm_endpoints.py) -> linha 21 -> async_endpoint_uses_sync_db_method - Endpoint async `llm_usage` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\llm_endpoints.py](C:\fralib\backend\endpoints\llm_endpoints.py) -> linha 33 -> async_endpoint_uses_sync_db_method - Endpoint async `llm_usage` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\llm_endpoints.py](C:\fralib\backend\endpoints\llm_endpoints.py) -> linha 45 -> async_endpoint_uses_sync_db_method - Endpoint async `llm_usage` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 24 -> async_endpoint_uses_sync_db_method - Endpoint async `get_ciclos` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 36 -> async_endpoint_uses_sync_db_method - Endpoint async `get_fila_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 81 -> async_endpoint_uses_sync_db_method - Endpoint async `reprocessar_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 88 -> async_endpoint_uses_sync_db_method - Endpoint async `reprocessar_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 91 -> async_endpoint_uses_sync_db_method - Endpoint async `reprocessar_lead` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 119 -> async_endpoint_uses_sync_db_method - Endpoint async `fila_reprocessamento` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_edit_endpoints.py](C:\fralib\backend\endpoints\pipeline_edit_endpoints.py) -> linha 31 -> async_endpoint_uses_sync_db_method - Endpoint async `editar_secao_endpoint` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\pipeline_edit_endpoints.py](C:\fralib\backend\endpoints\pipeline_edit_endpoints.py) -> linha 70 -> async_endpoint_uses_sync_db_method - Endpoint async `listar_secoes_endpoint` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 54 -> async_endpoint_uses_sync_db_method - Endpoint async `list_alerts` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 88 -> async_endpoint_uses_sync_db_method - Endpoint async `list_alerts` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 96 -> async_endpoint_uses_sync_db_method - Endpoint async `unread_count` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 104 -> async_endpoint_uses_sync_db_method - Endpoint async `mark_read` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 110 -> async_endpoint_uses_sync_db_method - Endpoint async `mark_read` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 112 -> async_endpoint_uses_sync_db_method - Endpoint async `mark_read` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 120 -> async_endpoint_uses_sync_db_method - Endpoint async `mark_all_read` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 124 -> async_endpoint_uses_sync_db_method - Endpoint async `mark_all_read` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 133 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_alert` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 137 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_alert` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 138 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_alert` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 148 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_all_read` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 149 -> async_endpoint_uses_sync_db_method - Endpoint async `delete_all_read` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 133 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_html` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 137 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_html` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 282 -> async_endpoint_uses_sync_db_method - Endpoint async `editar_com_ia` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 284 -> async_endpoint_uses_sync_db_method - Endpoint async `editar_com_ia` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 87 -> async_endpoint_uses_sync_db_method - Endpoint async `get_profile` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 112 -> async_endpoint_uses_sync_db_method - Endpoint async `update_profile` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 113 -> async_endpoint_uses_sync_db_method - Endpoint async `update_profile` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 122 -> async_endpoint_uses_sync_db_method - Endpoint async `onboarding_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 134 -> async_endpoint_uses_sync_db_method - Endpoint async `onboarding_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 139 -> async_endpoint_uses_sync_db_method - Endpoint async `onboarding_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 164 -> async_endpoint_uses_sync_db_method - Endpoint async `criar_lead_demo` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 172 -> async_endpoint_uses_sync_db_method - Endpoint async `criar_lead_demo` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 188 -> async_endpoint_uses_sync_db_method - Endpoint async `criar_lead_demo` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 201 -> async_endpoint_uses_sync_db_method - Endpoint async `status_anthropic_key` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 222 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_anthropic_key` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 231 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_anthropic_key` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 233 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_anthropic_key` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 244 -> async_endpoint_uses_sync_db_method - Endpoint async `remover_anthropic_key` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 246 -> async_endpoint_uses_sync_db_method - Endpoint async `remover_anthropic_key` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 266 -> async_endpoint_uses_sync_db_method - Endpoint async `get_sdr_horario` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 300 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_sdr_horario` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 303 -> async_endpoint_uses_sync_db_method - Endpoint async `salvar_sdr_horario` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 331 -> async_endpoint_uses_sync_db_method - Endpoint async `change_password` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 344 -> async_endpoint_uses_sync_db_method - Endpoint async `change_password` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 346 -> async_endpoint_uses_sync_db_method - Endpoint async `change_password` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 66 -> async_endpoint_uses_sync_db_method - Endpoint async `whatsapp_connect` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 152 -> async_endpoint_uses_sync_db_method - Endpoint async `get_bot_config` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 171 -> async_endpoint_uses_sync_db_method - Endpoint async `update_bot_config` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 180 -> async_endpoint_uses_sync_db_method - Endpoint async `update_bot_config` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\dashboard_analytics.py](C:\fralib\scripts\deploy\dashboard_analytics.py) -> linha 24 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\dashboard_analytics.py](C:\fralib\scripts\deploy\dashboard_analytics.py) -> linha 38 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\dashboard_analytics.py](C:\fralib\scripts\deploy\dashboard_analytics.py) -> linha 52 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 98 -> async_endpoint_uses_sync_db_method - Endpoint async `get_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 128 -> async_endpoint_uses_sync_db_method - Endpoint async `get_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 137 -> async_endpoint_uses_sync_db_method - Endpoint async `get_status` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 192 -> async_endpoint_uses_sync_db_method - Endpoint async `save_config` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 213 -> async_endpoint_uses_sync_db_method - Endpoint async `save_config` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 229 -> async_endpoint_uses_sync_db_method - Endpoint async `start_supply` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 233 -> async_endpoint_uses_sync_db_method - Endpoint async `start_supply` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 236 -> async_endpoint_uses_sync_db_method - Endpoint async `start_supply` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 269 -> async_endpoint_uses_sync_db_method - Endpoint async `pause_supply` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 274 -> async_endpoint_uses_sync_db_method - Endpoint async `pause_supply` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 346 -> async_endpoint_uses_sync_db_method - Endpoint async `retry_all` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 355 -> async_endpoint_uses_sync_db_method - Endpoint async `retry_all` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 365 -> async_endpoint_uses_sync_db_method - Endpoint async `retry_all` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 27 -> async_endpoint_uses_sync_db_method - Endpoint async `get_escalados` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 63 -> async_endpoint_uses_sync_db_method - Endpoint async `assumir_lead` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 73 -> async_endpoint_uses_sync_db_method - Endpoint async `assumir_lead` usa chamada síncrona `db.commit()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 91 -> async_endpoint_uses_sync_db_method - Endpoint async `get_conversas_ativas` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 133 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 148 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 163 -> async_endpoint_uses_sync_db_method - Endpoint async `get_pipeline_analytics` usa chamada síncrona `db.execute()` em parâmetro Depends(get_db)

## CRÍTICO — blind_json_truncation

- [C:\fralib\backend\dreaming_job.py](C:\fralib\backend\dreaming_job.py) -> linha 97 -> blind_json_truncation - Sites APROVADOS ({len(dados['sucesso'])}): {json.dumps(sucesso_resumo, ensure_ascii=False)[:1000]}
- [C:\fralib\backend\dreaming_job.py](C:\fralib\backend\dreaming_job.py) -> linha 98 -> blind_json_truncation - Sites REPROVADOS ({len(dados['falha'])}): {json.dumps(falha_resumo, ensure_ascii=False)[:1000]}
- [C:\fralib\backend\integration_healthcheck.py](C:\fralib\backend\integration_healthcheck.py) -> linha 187 -> blind_json_truncation - check("POST /api/auth/login", False, f"HTTP {code}: {json.dumps(data)[:150]}")

## CRÍTICO — router_function_without_decorator

- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 37 -> router_function_without_decorator - Função de topo `require_superadmin` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 14 -> router_function_without_decorator - Função de topo `criar_tabela_se_nao_existe` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 151 -> router_function_without_decorator - Função de topo `emitir_erro_pipeline` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 282 -> router_function_without_decorator - Função de topo `executar_pipeline_completo` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1728 -> router_function_without_decorator - Função de topo `executar_pipeline_multiplos` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2219 -> router_function_without_decorator - Função de topo `executar_pipeline_lead_existente` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 20 -> router_function_without_decorator - Função de topo `require_superadmin` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 37 -> router_function_without_decorator - Função de topo `require_superadmin` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\sse_endpoints.py](C:\fralib\backend\endpoints\sse_endpoints.py) -> linha 235 -> router_function_without_decorator - Função de topo `adicionar_log` em arquivo de router sem decorator
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 20 -> router_function_without_decorator - Função de topo `require_superadmin` em arquivo de router sem decorator
- [C:\fralib\backend\agent_router.py](C:\fralib\backend\agent_router.py) -> linha 26 -> router_function_without_decorator - Função de topo `calcular_complexidade_lead` em arquivo de router sem decorator
- [C:\fralib\backend\agent_router.py](C:\fralib\backend\agent_router.py) -> linha 110 -> router_function_without_decorator - Função de topo `set_router` em arquivo de router sem decorator
- [C:\fralib\backend\agent_router.py](C:\fralib\backend\agent_router.py) -> linha 114 -> router_function_without_decorator - Função de topo `get_router` em arquivo de router sem decorator
- [C:\fralib\backend\agents\llm_router.py](C:\fralib\backend\agents\llm_router.py) -> linha 134 -> router_function_without_decorator - Função de topo `get_circuit_breaker` em arquivo de router sem decorator
- [C:\fralib\backend\agents\llm_router.py](C:\fralib\backend\agents\llm_router.py) -> linha 156 -> router_function_without_decorator - Função de topo `get_model_map` em arquivo de router sem decorator
- [C:\fralib\backend\agents\llm_router.py](C:\fralib\backend\agents\llm_router.py) -> linha 161 -> router_function_without_decorator - Função de topo `resolve_model_id` em arquivo de router sem decorator
- [C:\fralib\backend\agents\llm_router.py](C:\fralib\backend\agents\llm_router.py) -> linha 419 -> router_function_without_decorator - Função de topo `get_router` em arquivo de router sem decorator
- [C:\fralib\backend\agents\llm_router.py](C:\fralib\backend\agents\llm_router.py) -> linha 427 -> router_function_without_decorator - Função de topo `call_llm` em arquivo de router sem decorator
- [C:\fralib\backend\agents\llm_router.py](C:\fralib\backend\agents\llm_router.py) -> linha 454 -> router_function_without_decorator - Função de topo `call_llm_direct` em arquivo de router sem decorator
- [C:\fralib\backend\core\design_system_router.py](C:\fralib\backend\core\design_system_router.py) -> linha 75 -> router_function_without_decorator - Função de topo `build_visual_seed` em arquivo de router sem decorator
- [C:\fralib\backend\core\design_system_router.py](C:\fralib\backend\core\design_system_router.py) -> linha 79 -> router_function_without_decorator - Função de topo `build_design_dna` em arquivo de router sem decorator
- [C:\fralib\backend\core\design_system_router.py](C:\fralib\backend\core\design_system_router.py) -> linha 179 -> router_function_without_decorator - Função de topo `choose_section_variant` em arquivo de router sem decorator
- [C:\fralib\backend\core\router_setup.py](C:\fralib\backend\core\router_setup.py) -> linha 29 -> router_function_without_decorator - Função de topo `register_routers` em arquivo de router sem decorator
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 395 -> router_function_without_decorator - Função de topo `get_openai_models` em arquivo de router sem decorator
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 405 -> router_function_without_decorator - Função de topo `get_ollama_models` em arquivo de router sem decorator
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 413 -> router_function_without_decorator - Função de topo `get_groq_models` em arquivo de router sem decorator
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 423 -> router_function_without_decorator - Função de topo `get_litellm_models` em arquivo de router sem decorator
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 588 -> router_function_without_decorator - Função de topo `check_wandb_auth` em arquivo de router sem decorator

## CRÍTICO — string_missing_f_prefix

- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 1 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """A/B Test Reporting endpoints (Fase 5).

Tabela franz_ab_events criada em database.py.
Endpoints:
  POST /api/abtest/r
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 48 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/convert/{lead_id}"
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 72 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{agent_name}'
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 1 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """agentes_endpoints.py — Treino do Franz por conversa (superadmin).

O dono (superadmin) conversa com o Franz no painel
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 193 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/training/{rule_id}"
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 1 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """
Endpoints da lista de falhas de pipeline.

GET  /api/falhas             - lista falhas do tenant (com paginacao simp
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 95 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{falha_id}/visto'
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 118 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{falha_id}/retry'
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 1 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """franz_insights_endpoints.py — CRUD de insights do Franz (SDR learning).

Endpoints:
  GET  /api/franz/insights       
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 92 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/insights/{insight_id}'
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 140 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/insights/{insight_id}/promote'
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 171 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/insights/{insight_id}'
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 228 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/leads/{inventory_id}/discard"
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 254 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/leads/{inventory_id}/retry"
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 48 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/conversa'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 63 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 89 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/reprocessar'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 110 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/editar-site'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 223 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/upload-foto'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 423 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/chat'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 548 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/aprovar-pipeline'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 569 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/descartar'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 601 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/campos'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 686 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 710 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/feedback'
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 795 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/enviar-mensagem'
- [C:\fralib\backend\endpoints\obs_endpoints.py](C:\fralib\backend\endpoints\obs_endpoints.py) -> linha 120 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/trace/{trace_id}"
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 66 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/reprocessar/{lead_id}"
- [C:\fralib\backend\endpoints\pipeline_edit_endpoints.py](C:\fralib\backend\endpoints\pipeline_edit_endpoints.py) -> linha 62 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/listar-secoes/{lead_id}"
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 649 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """
                            UPDATE leads SET dados_completos = jsonb_set(
                                COALESCE(C
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2558 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/reprocessar/{lead_id}'
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 100 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{alert_id}/read'
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 129 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{alert_id}'
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 102 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{key_id}'
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 158 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{key_id}'
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 169 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{key_id}/toggle'
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 180 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{key_id}/reset-cooldown'
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 207 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{key_id}/test'
- [C:\fralib\backend\endpoints\queue_endpoints.py](C:\fralib\backend\endpoints\queue_endpoints.py) -> linha 38 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/job/{job_id}"
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 83 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/html'
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 101 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/salvar-html'
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 155 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '/{lead_id}/editar-ia'
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 198 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/users/{user_id}/toggle"
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 224 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/users/{user_id}/set-plan"
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 246 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/users/{user_id}/set-creditos"
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 266 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/impersonate/{user_id}"
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 722 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/dashboard/jobs/{job_id}/replay"
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 16 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """Checa se o WhatsApp do user esta conectado no meowhats.

    Tem dois caminhos: rota direta /api/sessions/{tenant}/st
- [C:\fralib\backend\services\cakto_client.py](C:\fralib\backend\services\cakto_client.py) -> linha 151 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """Cria oferta (preco + trial + recorrencia) para um produto.

        Retorna dict com ``id`` da oferta — checkout URL 
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 30 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Oi {nome}, tudo certo?\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 31 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Passando pra avisar que preparei o exemplo do site pro {segmento}.\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 32 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Se quiser dar uma olhada: {link_site}\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 36 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Oi {nome}, lembra da gente?\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 37 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Um cliente do {segmento} na sua regiao triplicou os contatos em 60 dias.\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 38 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Posso te mandar o exemplo? {link_site}"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 41 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Oi {nome}, oferta especial essa semana pra voce:\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 42 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Site premium pro {segmento} com condicao especial.\n"
- [C:\fralib\backend\services\retargeting.py](C:\fralib\backend\services\retargeting.py) -> linha 43 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Quer ver? {link_site}"
- [C:\fralib\backend\services\vite_prompts.py](C:\fralib\backend\services\vite_prompts.py) -> linha 128 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """You are generating file batch "{batch_name}" for a Vite React landing page.

Return ONLY a JSON object with the reque
- [C:\fralib\backend\services\vite_templates.py](C:\fralib\backend\services\vite_templates.py) -> linha 494 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """import * as React from 'react';

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ classN
- [C:\fralib\backend\services\vite_templates.py](C:\fralib\backend\services\vite_templates.py) -> linha 533 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """import { useEffect, useState } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { motion } from 'm
- [C:\fralib\backend\agents\bloco_copy.py](C:\fralib\backend\agents\bloco_copy.py) -> linha 56 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """## depoimentos
omitir: {omitir_val}
h2: titulo
body: texto com reviews reais"""
- [C:\fralib\backend\agents\builder\quality_gate_v2\inject.py](C:\fralib\backend\agents\builder\quality_gate_v2\inject.py) -> linha 63 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """Replace {placeholder} tokens in partial HTML with PRD values.

    Falls back to sensible defaults when the PRD doesn
- [C:\fralib\backend\agents\cinematic_post_processor.py](C:\fralib\backend\agents\cinematic_post_processor.py) -> linha 209 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """
<script>
(function() {
  'use strict';
  document.documentElement.classList.remove('no-js');

  // ── Scroll Progres
- [C:\fralib\backend\agents\franz\franz_agent_loop.py](C:\fralib\backend\agents\franz\franz_agent_loop.py) -> linha 111 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "{nome}, vi que você tem um negócio de {segmento} em {cidade}! 🚀 Muitos empresários da área estão usando site profission
- [C:\fralib\backend\agents\franz\franz_agent_loop.py](C:\fralib\backend\agents\franz\franz_agent_loop.py) -> linha 112 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Oi {nome}! Tudo bem? Estou entrando em contato sobre {segmento} em {cidade} — preparei uma oferta especial pra você! 😊"
- [C:\fralib\backend\agents\franz\franz_agent_loop.py](C:\fralib\backend\agents\franz\franz_agent_loop.py) -> linha 113 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "E aí {nome}! Aqui é o Franz da FraLib. Vi que você trabalha com {segmento} aí em {cidade} e tenho uma ideia que pode mu
- [C:\fralib\backend\agents\franz\franz_agent_loop.py](C:\fralib\backend\agents\franz\franz_agent_loop.py) -> linha 121 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Te entendo, {nome}. O investimento é menor do que parece — muitos clientes recuperam o valor no primeiro mês. Quer que 
- [C:\fralib\backend\agents\franz\franz_agent_loop.py](C:\fralib\backend\agents\franz\franz_agent_loop.py) -> linha 129 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "Oi {nome}! Passando pra ver se conseguiu ver a proposta. Alguma dúvida? Estou aqui! 😊"
- [C:\fralib\backend\agents\franz\franz_agent_loop.py](C:\fralib\backend\agents\franz\franz_agent_loop.py) -> linha 130 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "E aí, {nome}! Lembrete: a oferta especial pra {cidade} ainda tá valendo essa semana. Quer avançar?"
- [C:\fralib\backend\agents\lgpd_personalized.py](C:\fralib\backend\agents\lgpd_personalized.py) -> linha 77 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '''";

  return (
    <motion.div
      data-lgpd-banner
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity:
- [C:\fralib\backend\agents\liz.py](C:\fralib\backend\agents\liz.py) -> linha 713 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: rf'<!--\s*SECTION:\s*{secao}\s*-->(.*?)<!--\s*/SECTION:\s*{secao}\s*-->'
- [C:\fralib\backend\agents\pipeline_checkpoint.py](C:\fralib\backend\agents\pipeline_checkpoint.py) -> linha 1 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """
Sistema de Checkpoint do Pipeline FraLib
Salva estado de cada agente para retomar de onde parou.

Multi-tenant: o pi
- [C:\fralib\backend\agents\sdr_langgraph\prompts.py](C:\fralib\backend\agents\sdr_langgraph\prompts.py) -> linha 244 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: 'Neighbor signal: "Boa tarde! Voces trabalham mais com {segmento} ou atendem outro foco tambem?"'
- [C:\fralib\backend\agents\sdr_langgraph\prompts.py](C:\fralib\backend\agents\sdr_langgraph\prompts.py) -> linha 245 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: 'Observation signal: "Vi voces no Google com {rating} estrelas, isso chama atencao."'
- [C:\fralib\backend\agents\sdr_langgraph\prompts.py](C:\fralib\backend\agents\sdr_langgraph\prompts.py) -> linha 246 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: 'Research signal: "Estou fazendo um levantamento rapido sobre {segmento} em {cidade}."'
- [C:\fralib\backend\agents\sdr_langgraph\tools.py](C:\fralib\backend\agents\sdr_langgraph\tools.py) -> linha 55 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """Classify the lead intent into exactly ONE category.

- opt_out: "não quero", "para", "me tira", "chega", "remover"
- 
- [C:\fralib\backend\agents\section_editor.py](C:\fralib\backend\agents\section_editor.py) -> linha 9 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: rf"<!--\s*SECTION:\s*{secao}\s*-->(.*?)<!--\s*/SECTION:\s*{secao}\s*-->"
- [C:\fralib\backend\agents\visual_fingerprint.py](C:\fralib\backend\agents\visual_fingerprint.py) -> linha 145 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: rf"{name}\s*=\s*['\"]([^'\"]+)['\"]"
- [C:\fralib\backend\core\observability_setup.py](C:\fralib\backend\core\observability_setup.py) -> linha 50 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "{time:ISO8601} | {level} | {name}:{function}:{line} | {message}"
- [C:\fralib\backend\core\observability_setup.py](C:\fralib\backend\core\observability_setup.py) -> linha 57 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</lev
- [C:\fralib\backend\utils\google_maps_gosom.py](C:\fralib\backend\utils\google_maps_gosom.py) -> linha 1 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """
Google Maps Scraper Client — gosom/google-maps-scraper
Alternativa open-source ao Playwright. Roda como daemon na VP
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 364 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """Retorna True se o tenant esta com WhatsApp pareado e pronto para envio.

    Usa o cache local (alimentado pelo WebSo
- [C:\fralib\backend\whatsapp_listener.py](C:\fralib\backend\whatsapp_listener.py) -> linha 448 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """Converte tenant_id 'fralib_user_{N}' em int N, ou None se inválido."""
- [C:\fralib\openui-service-wandb\backend\openui\config.py](C:\fralib\openui-service-wandb\backend\openui\config.py) -> linha 44 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "sk-{SESSION_KEY}"
- [C:\fralib\openui-service-wandb\backend\openui\eval\to_fine_tune.py](C:\fralib\openui-service-wandb\backend\openui\eval\to_fine_tune.py) -> linha 10 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_he
- [C:\fralib\openui-service-wandb\backend\openui\generate.py](C:\fralib\openui-service-wandb\backend\openui\generate.py) -> linha 570 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "PRD_OPENUI: prompt_inicio=[{preview}]"
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 520 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/openui/{name}.svg"
- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 544 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/openui/{name}.mp3"
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 54 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "/{lead_id}/assumir"
- [C:\fralib\scripts\deploy\patch_leads.py](C:\fralib\scripts\deploy\patch_leads.py) -> linha 9 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: '''

# ─── Adicionado por Hermes (2026-08-06) ─────────────────────────────────────

@router.get("/escalados")
async def
- [C:\fralib\scripts\deploy_openui_python.py](C:\fralib\scripts\deploy_openui_python.py) -> linha 46 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: """[Unit]
Description=FraLib OpenUI Python Service (wandb/openui + LiteLLM)
After=network.target

[Service]
Type=simple

- [C:\fralib\scripts\deploy_openui_python.py](C:\fralib\scripts\deploy_openui_python.py) -> linha 85 -> string_missing_f_prefix - String literal contém placeholder de interpolação sem prefixo f: "curl -s -o /dev/null -w '%{http_code}' http://localhost:7878/v1/models 2>/dev/null"

## MÉDIO — direct_db_execute_in_router

- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 34 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 57 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\abtest_endpoints.py](C:\fralib\backend\endpoints\abtest_endpoints.py) -> linha 80 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 70 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 97 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 102 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 111 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 122 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 132 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 141 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 157 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 179 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 207 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 220 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 304 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 313 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 346 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 358 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 458 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 464 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 595 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 609 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 634 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py](C:\fralib\backend\endpoints\admin_pipeline_control_endpoints.py) -> linha 676 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 50 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 85 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 92 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 97 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 162 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 191 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 264 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 276 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agent_config_endpoints.py](C:\fralib\backend\endpoints\agent_config_endpoints.py) -> linha 286 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 122 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 143 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 148 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 152 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 171 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 200 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 234 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 273 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 279 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\agentes_endpoints.py](C:\fralib\backend\endpoints\agentes_endpoints.py) -> linha 284 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 50 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 57 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 78 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 83 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 120 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 143 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 150 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 173 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 179 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 212 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 221 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 228 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 235 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 252 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 260 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 274 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 290 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 307 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 314 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\auth_endpoints.py](C:\fralib\backend\endpoints\auth_endpoints.py) -> linha 320 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 15 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 49 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\beta_endpoints.py](C:\fralib\backend\endpoints\beta_endpoints.py) -> linha 75 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits\checkout.py](C:\fralib\backend\endpoints\credits\checkout.py) -> linha 671 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits\checkout.py](C:\fralib\backend\endpoints\credits\checkout.py) -> linha 687 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits\status.py](C:\fralib\backend\endpoints\credits\status.py) -> linha 25 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits\status.py](C:\fralib\backend\endpoints\credits\status.py) -> linha 42 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 39 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 85 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 336 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\credits_endpoints.py](C:\fralib\backend\endpoints\credits_endpoints.py) -> linha 353 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 22 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 25 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 40 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 135 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 181 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 188 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 201 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 224 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\dashboard_endpoints.py](C:\fralib\backend\endpoints\dashboard_endpoints.py) -> linha 240 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 38 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 51 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 85 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 104 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 132 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\falhas_endpoints.py](C:\fralib\backend\endpoints\falhas_endpoints.py) -> linha 167 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 85 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 100 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 120 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 151 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\franz_insights_endpoints.py](C:\fralib\backend\endpoints\franz_insights_endpoints.py) -> linha 180 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 21 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 39 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 236 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 262 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\lead_supply_endpoints.py](C:\fralib\backend\endpoints\lead_supply_endpoints.py) -> linha 289 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 16 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 52 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 82 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 93 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 96 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 113 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 123 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 233 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 313 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 409 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 428 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 431 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 453 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 475 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 488 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 501 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 527 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 552 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 555 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 573 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 576 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 605 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 631 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 647 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 671 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 690 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 694 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 695 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 729 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 742 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 752 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 770 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 802 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 867 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 896 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 948 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 1004 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\leads_endpoints.py](C:\fralib\backend\endpoints\leads_endpoints.py) -> linha 1029 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\llm_endpoints.py](C:\fralib\backend\endpoints\llm_endpoints.py) -> linha 21 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\llm_endpoints.py](C:\fralib\backend\endpoints\llm_endpoints.py) -> linha 33 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\llm_endpoints.py](C:\fralib\backend\endpoints\llm_endpoints.py) -> linha 45 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 24 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 36 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 81 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 88 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_crud.py](C:\fralib\backend\endpoints\pipeline_crud.py) -> linha 119 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_edit_endpoints.py](C:\fralib\backend\endpoints\pipeline_edit_endpoints.py) -> linha 31 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_edit_endpoints.py](C:\fralib\backend\endpoints\pipeline_edit_endpoints.py) -> linha 70 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 100 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 106 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 111 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 131 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 214 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1692 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1787 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1849 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1871 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1899 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1916 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1989 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1990 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1991 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 1992 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2014 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2039 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2042 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2085 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2137 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2180 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2209 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2566 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2569 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2600 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2630 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2631 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2632 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2633 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2644 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2647 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2650 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2652 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2676 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2677 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2680 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2691 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2700 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\pipeline_endpoints.py](C:\fralib\backend\endpoints\pipeline_endpoints.py) -> linha 2701 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 28 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 54 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 88 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 96 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 104 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 110 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 120 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 133 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 137 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_alerts_endpoints.py](C:\fralib\backend\endpoints\provider_alerts_endpoints.py) -> linha 148 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 45 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 171 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 182 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\provider_keys_endpoints.py](C:\fralib\backend\endpoints\provider_keys_endpoints.py) -> linha 210 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 74 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 133 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\site_editor_endpoints.py](C:\fralib\backend\endpoints\site_editor_endpoints.py) -> linha 282 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 29 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 55 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 58 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 63 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 66 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 71 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 78 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 91 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 121 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 149 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 202 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 210 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 270 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 315 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 321 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 326 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 334 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 342 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 401 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 411 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 421 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 462 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 475 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 491 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 506 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 527 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 553 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 561 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 568 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 597 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 603 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 612 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 641 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 648 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 657 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 667 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 672 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 706 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 727 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 730 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 748 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\superadmin_endpoints.py](C:\fralib\backend\endpoints\superadmin_endpoints.py) -> linha 763 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\tracking_endpoints.py](C:\fralib\backend\endpoints\tracking_endpoints.py) -> linha 41 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\tracking_endpoints.py](C:\fralib\backend\endpoints\tracking_endpoints.py) -> linha 50 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\tracking_endpoints.py](C:\fralib\backend\endpoints\tracking_endpoints.py) -> linha 58 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 122 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 134 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 139 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 164 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 172 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 201 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 222 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 231 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 244 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 266 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 300 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 331 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\users_endpoints.py](C:\fralib\backend\endpoints\users_endpoints.py) -> linha 344 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 66 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 152 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\backend\endpoints\whatsapp_endpoints.py](C:\fralib\backend\endpoints\whatsapp_endpoints.py) -> linha 171 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\dashboard_analytics.py](C:\fralib\scripts\deploy\dashboard_analytics.py) -> linha 24 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\dashboard_analytics.py](C:\fralib\scripts\deploy\dashboard_analytics.py) -> linha 38 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\dashboard_analytics.py](C:\fralib\scripts\deploy\dashboard_analytics.py) -> linha 52 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 98 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 128 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 137 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 192 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 229 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 236 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 269 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 346 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\lead_supply_endpoints.py](C:\fralib\scripts\deploy\lead_supply_endpoints.py) -> linha 355 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 27 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 63 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 91 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 133 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 148 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router
- [C:\fralib\scripts\deploy\leads_missing_endpoints.py](C:\fralib\scripts\deploy\leads_missing_endpoints.py) -> linha 163 -> direct_db_execute_in_router - Uso direto de db.execute(text(...)) em arquivo de router

## MÉDIO — endpoint_uses_request_json_instead_of_pydantic

- [C:\fralib\openui-service-wandb\backend\openui\server.py](C:\fralib\openui-service-wandb\backend\openui\server.py) -> linha 113 -> endpoint_uses_request_json_instead_of_pydantic - Endpoint async `chat_completions` usa await request.json() sem modelo Pydantic explícito
