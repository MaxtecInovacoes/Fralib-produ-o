export const meta = {
  name: 'split-arquitecto-builder',
  description: 'Split Arquiteto and Builder LLM calls into partial chunks (parallel implementation)',
  phases: [{ title: 'Implement' }, { title: 'Review' }, { title: 'Test' }],
}

phase('Implement')

log('Phase 1: Parallel implementation of Builder split + Arquiteto split')

const builderAgent = await agent(
  'You are implementing the Builder HTML split in C:\\fralib\\backend\\agents\\builder\\agent.py.\n' +
  'Follow these exact steps:\n' +
  '1. Read the file C:\\fralib\\backend\\agents\\builder\\agent.py using the Read tool.\n' +
  '2. After the _archetype_briefing function (line 191), add these new functions:\n' +
  '   a. _BLOCOS_HTML constant (list of 4 groups: [["hero","sobre"], ["servicos","depoimentos"], ["faq","localizacao"], ["contato"]])\n' +
  '   b. _split_spec_blocks(spec) - splits spec dict into blocks for each group\n' +
  '   c. _concat_html(partials) - concatenates partial HTMLs, keeping <head> from first only\n' +
  '   d. _render_block(block_spec) - renders one block via OpenUI with 6 retries\n' +
  '3. Replace the render_site function (lines 193-273) with a new version that:\n' +
  '   - Calls _prd_to_spec(prd) once\n' +
  '   - Calls _split_spec_blocks(spec) to get 4 blocks\n' +
  '   - Calls _render_block() for each block sequentially\n' +
  '   - Calls _concat_html(partials) to merge all partials\n' +
  '   - Validates final HTML length >= 1000 chars\n' +
  '   - Returns BuildResult(html=full_html, model="openui-chunked", success=True)\n' +
  '   - Fail-fast: if ANY block fails, return BuildResult with error (no fallback)\n' +
  '4. Keep _prd_to_spec, _archetype_briefing, _wait_for_openui, BuildResult unchanged.\n' +
  '5. After editing, verify syntax with: python -c "import ast; ast.parse(open(r\'C:\\fralib\\backend\\agents\\builder\\agent.py\').read()); print(\'Syntax OK\')\"\n' +
  'The _concat_html function must:\n' +
  '  - Keep <head>...</head> from first partial only\n' +
  '  - Strip <head>...</head> from all subsequent partials\n' +
  '  - Strip <!DOCTYPE>, opening <html>, closing </html> from subsequent partials\n' +
  '  - Insert body content before </body> if it exists in the full HTML, else append\n' +
  'The _render_block function must:\n' +
  '  - Add _bloco_labels and _render_hint="body_only" to the block spec\n' +
  '  - Use same retry logic as current render_site: 6 retries, delays [60, 120, 180, 300, 300, 600]\n' +
  '  - On success (status 200 + html > 200 chars), print "[builder] Bloco [{labels}] OK ({chars} chars)" and return html\n' +
  '  - On failure after all retries, print error and return empty string\n' +
  'IMPORTANT: Do NOT add any imports that do not already exist (os, json, time, requests are already imported).',
  {label: 'builder-split', phase: 'Implement'}
)

const arquitetoAgent = await agent(
  'You are implementing the Arquiteto LLM split in C:\\fralib\\backend\\agents\\arquiteto_agent_loop.py.\n' +
  'Follow these exact steps:\n' +
  '1. Read the file C:\\fralib\\backend\\agents\\arquiteto_agent_loop.py using the Read tool.\n' +
  '2. Also read C:\\fralib\\backend\\agents\\bloco_copy.py to understand the exact pattern being replicated.\n' +
  '3. Replace the tool-use loop (lines 239-295) with 4 direct LLM calls using call_claude().\n' +
  '   The key change: instead of letting Claude decide which tools to call iteratively,\n' +
  '   YOU call the tools in Python FIRST (via execute_tool()), collect all results,\n' +
  '   build a shared context string, then make 4 direct LLM calls for the PRD generation.\n' +
  '\n' +
  '### New function: _build_shared_context\n' +
  'This builds the shared context once (same for all 4 calls):\n' +
  '  - Receives: nome, cidade, segmento, telefone, endereco, rating, total_av, caio_tier, dark_mode,\n' +
  '    jina_insights, instrucao_criativa, reviews_fmt, reviews_intel_ctx, seo_ctx, faq_seo_fmt,\n' +
  '    keyword_research, reviews_has, craft_ctx, autocritica_ctx, tool_results_fmt\n' +
  '  - Returns a single string with ALL context formatted for the LLM\n' +
  '  - Include the tool results (from execute_tool calls) in a TOOL RESULTS section\n' +
  '\n' +
  '### New function: _callar_bloco_arquiteto\n' +
  'Makes a single LLM call for a subset of PRD fields:\n' +
  '  - Receives: shared_context, section_labels (list of field groups), system_prompt\n' +
  '  - Calls call_claude(system=system_prompt, user=prompt, model="sonnet", max_tokens=4096, temperature=0.3, agent_name="arquiteto_mestre")\n' +
  '  - Parses JSON from response\n' +
  '  - Returns dict or None\n' +
  '\n' +
  '### New function: _GRUPOS_CAMPOS_PRD\n' +
  'Groups the PRD JSON fields into 4 call groups:\n' +
  '  [\n' +
  '    ["business_name", "segmento", "cidade", "color_palette", "typography", "dark_mode", "layout_type"],  # core identity\n' +
  '    ["sections", "animations", "instrucao_criativa_para_dev", "anti_patterns", "schema_org_types"],  # structure\n' +
  '    ["seo_keywords", "faq_questions", "value_props", "competitor_analysis"],  # SEO/content\n' +
  '    ["photos", "reviews_list", "reviews_rating", "reviews_count", "phone", "address", "hours", "google_maps_embed", "components_21dev", "geo"],  # data\n' +
  '  ]\n' +
  '\n' +
  '### Modified arquiteto_agent_loop function:\n' +
  'Replace lines 239-295 (the tool-use loop) with:\n' +
  '  a. Call ALL 8 tools via execute_tool() BEFORE any LLM call:\n' +
  '     tool_results = {}\n' +
  '     for tool_name in ["get_keyword_research", "get_design_system", "get_animation_profile",\n' +
  '                        "get_seo_context", "get_open_design_reference", "get_craft_rules",\n' +
  '                        "get_jina_insights", "verify_prd"]:\n' +
  '         try:\n' +
  '             result = execute_tool(tool_name, {}, context)\n' +
  '             tool_results[tool_name] = result\n' +
  '         except Exception as e:\n' +
  '             tool_results[tool_name] = f"ERROR: {e}"\n' +
  '  b. Build shared_context using _build_shared_context()\n' +
  '  c. Make 4 sequential direct LLM calls via _callar_bloco_arquiteto()\n' +
  '  d. Merge all partial PRD dicts into one final prd_data dict\n' +
  '  e. Fail-fast: if ANY partial call returns None, raise RuntimeError\n' +
  '  f. Call _enrich_prd() on the merged result (same as before)\n' +
  '  g. Return ArquitetoAgentOutput with prd_data, tools_used, iterations, verified=True\n' +
  '\n' +
  '### System prompt for partial calls\n' +
  'Use a SHORTENED version of ARQUITETO_AGENT_SYSTEM for each partial call:\n' +
  '  - Include only the rules relevant to the fields in that group\n' +
  '  - Keep the Output Final JSON format showing ONLY the fields for that group\n' +
  '  - Keep the RESTRIÇÃO line\n' +
  '\n' +
  '### Keep unchanged:\n' +
  '  - _resolve_anthropic()\n' +
  '  - _parse_prd_response() — REPLACE with a simpler _merge_prd_partials()\n' +
  '  - _extract_largest_json()\n' +
  '  - _enrich_prd()\n' +
  '  - gerar_arquiteto_mestre_prd_agent() (wrapper, only change the call to arquiteto_agent_loop)\n' +
  '  - ARQUITETO_AGENT_SYSTEM (keep as the master system prompt, reference it in partial prompts)\n' +
  '  - All imports\n' +
  '\n' +
  '### After editing, verify syntax:\n' +
  'python -c "import ast; ast.parse(open(r\'C:\\fralib\\backend\\agents\\arquiteto_agent_loop.py\').read()); print(\'Syntax OK\')\"\n' +
  '\n' +
  'IMPORTANT: The _build_shared_context function must include the full ARQUITETO_AGENT_SYSTEM prompt\n' +
  'as context so each partial LLM call has the full design rules available.\n' +
  'The 4 partial calls replace the iterative tool-use loop — this is the core trade-off.',
  {label: 'arquiteto-split', phase: 'Implement'}
)

const builderResult = await builderAgent
const arquitetoResult = await arquitetoAgent

log(`Builder split done: ${builderResult ? 'OK' : 'check output'}`)
log(`Arquiteto split done: ${arquitetoResult ? 'OK' : 'check output'}`)

phase('Review')

log('Phase 2: Python review of both files')

const builderReview = await agent(
  'Review C:\\fralib\\backend\\agents\\builder\\agent.py for:\n' +
  '1. Correctness of _split_spec_blocks: does it handle missing sections gracefully?\n' +
  '2. Correctness of _concat_html: does it handle edge cases (no </body>, empty partials, malformed HTML)?\n' +
  '3. Does render_site fail-fast on block failure (no fallback/silent swallow)?\n' +
  '4. Is the retry logic identical to the original (6 retries, same delays)?\n' +
  '5. Are there any import issues?\n' +
  '6. Is the tracking code still present?\n' +
  'Report findings as CRITICAL/HIGH/MEDIUM/LOW with specific line numbers.',
  {label: 'builder-review', phase: 'Review'}
)

const arquitetoReview = await agent(
  'Review C:\\fralib\\backend\\agents\\arquiteto_agent_loop.py for:\n' +
  '1. Are ALL 8 tools called via execute_tool() before LLM calls (no tool-use loop remains)?\n' +
  '2. Does _build_shared_context include all necessary context from the original tool-use loop?\n' +
  '3. Does _callar_bloco_arquiteto properly parse JSON from the LLM response?\n' +
  '4. Does the merge logic combine all 4 partial dicts correctly?\n' +
  '5. Is there fail-fast on any partial call failure?\n' +
  '6. Are the imports correct (call_claude from llm_direct, execute_tool from arquiteto_tools)?\n' +
  '7. Does _enrich_prd still get called on the merged result?\n' +
  '8. Is the fallback in gerar_arquiteto_mestre_prd_agent still functional?\n' +
  'Report findings as CRITICAL/HIGH/MEDIUM/LOW with specific line numbers.',
  {label: 'arquiteto-review', phase: 'Review'}
)

log(`Builder review: ${builderReview ? 'done' : 'check output'}`)
log(`Arquiteto review: ${arquitetoReview ? 'done' : 'check output'}`)

phase('Test')

log('Phase 3: Running test suite')

const testResult = await agent(
  'Run the test suite for the fralib project:\n' +
  '1. First check if there are existing tests: glob for tests/agents/test_builder* and tests/agents/test_arquiteto*\n' +
  '2. Run pytest tests/agents/ -v --tb=short (max 120s timeout)\n' +
  '3. Report: how many tests pass, how many fail, and the specific errors for any failures.\n' +
  '4. Also run: python -c "import ast; ast.parse(open(r\'C:\\fralib\\backend\\agents\\builder\\agent.py\').read()); ast.parse(open(r\'C:\\fralib\\backend\\agents\\arquiteto_agent_loop.py\').read()); print(\'Both files syntax OK\')"\n' +
  '5. Report overall status: GREEN (all pass) or RED (any failures).',
  {label: 'test-run', phase: 'Test'}
)

log(`Tests done. Status: see test-run output`)

return {
  builder: builderResult,
  arquiteto: arquitetoResult,
  builder_review: builderReview,
  arquiteto_review: arquitetoReview,
  tests: testResult,
}
