/* frontend/js/admin/_shared.js — Utilitários compartilhados pelos módulos de admin.
 *
 * Canônico para M6 do plano DRY (codex/dry-refactor).
 * Substitui 2 cópias inline do filtro de período (hoje/semana/mes) em crm-uti.js.
 *
 * STATUS: helper criado mas NÃO migrado (M12 re-audit).
 * O módulo crm-uti.js é INLINE em frontend/partials/admin/_scripts.html
 * (5726 linhas), e nenhum HTML admin inclui <script src="_shared.js">.
 * Adicionar a tag exigiria validar ordem de carregamento do bundle admin
 * em produção — risco > ganho. Migrar apenas quando o build admin for
 * refatorado para módulos separados.
 */
(function(global){
  'use strict';

  /**
   * Filtra uma lista de itens por período (hoje/semana/mes).
   * @param {Array} items - Lista de objetos com campo `criado_em` ou `created_at`.
   * @param {string|null} period - 'hoje' | 'semana' | 'mes' | null/outros = sem filtro.
   * @param {string[]} [searchFields=['nome']] - Campos onde buscar o query.
   * @param {string} [query=''] - String de busca (case-insensitive substring).
   * @returns {Array} Items filtrados.
   */
  function filterByPeriod(items, period, query, searchFields) {
    searchFields = searchFields || ['nome'];
    query = (query || '').toLowerCase();
    var now = new Date();
    return (items || []).filter(function(item) {
      if (query) {
        var hit = searchFields.some(function(f) {
          return ((item[f] || '') + '').toLowerCase().indexOf(query) >= 0;
        });
        if (!hit) return false;
      }
      if (!period) return true;
      var d = new Date(item.criado_em || item.created_at || now);
      if (period === 'hoje') {
        return d.toDateString() === now.toDateString();
      }
      if (period === 'semana') {
        var weekAgo = new Date(now.getTime() - 7 * 86400000);
        return d >= weekAgo;
      }
      if (period === 'mes') {
        return d >= new Date(now.getFullYear(), now.getMonth(), 1);
      }
      return true;
    });
  }

  global.filterByPeriod = filterByPeriod;
})(typeof window !== 'undefined' ? window : this);
