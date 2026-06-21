/**
 * FraLib Admin - Stations
 * Lista curada de estacoes + integracao com Radio-Browser API.
 *
 * Radio-Browser API: https://de1.api.radio-browser.info/
 * - Sem auth, sem API key, 30k+ radios
 * - Endpoint usado: /json/stations/search?name=<query>&limit=1
 *
 * Cada estacao tem: { id, nome, genero, query, fallbackUrl }
 * - id: slug usado no localStorage
 * - query: termo de busca no Radio-Browser (ex: "kboing")
 * - fallbackUrl: URL hardcoded caso a API esteja offline
 */
(function () {
  'use strict';

  // Hosts da API Radio-Browser (tenta varios para resiliência)
  var API_HOSTS = [
    'https://de1.api.radio-browser.info',
    'https://at1.api.radio-browser.info',
    'https://de2.api.radio-browser.info'
  ];

  // Cache de URL resolvida: { stationId: { url, name, expiresAt } }
  var cache = {};
  var CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 horas

  /**
   * Lista curada de estacoes.
   * Brasileiras primeiro (preferencia do admin), depois tematicas internacionais.
   */
  var STATIONS = [
    // === BRASILEIRAS (12) ===
    { id: 'kboing',     nome: 'Kboing FM',       genero: 'Sertanejo / Pop',     query: 'kboing' },
    { id: 'antena1',    nome: 'Antena 1',        genero: 'MPB / Jazz',          query: 'antena 1' },
    { id: 'kissfm',     nome: 'Kiss FM',         genero: 'Rock',                query: 'kiss fm' },
    { id: 'jovempan',   nome: 'Jovem Pan',       genero: 'Pop / Hits',          query: 'jovem pan' },
    { id: 'bandnews',   nome: 'BandNews FM',     genero: 'Notícias',            query: 'bandnews' },
    { id: 'culturafm',  nome: 'Cultura FM',      genero: 'Clássica / Cultural', query: 'cultura fm' },
    { id: 'gaucha',     nome: 'Rádio Gaúcha',    genero: 'Jornalismo / Esportes', query: 'radio gaucha' },
    { id: '89fm',       nome: '89 FM A Rádio Rock', genero: 'Rock',              query: '89 fm rock' },
    { id: 'alphafm',    nome: 'Alpha FM',        genero: 'Adulto Contemporâneo', query: 'alpha fm' },
    { id: 'cbn',        nome: 'CBN SP',          genero: 'Notícias',            query: 'cbn sao paulo' },
    { id: 'globoradio', nome: 'Rádio Globo',     genero: 'Pop / Hits',          query: 'radio globo' },
    { id: 'transamerica', nome: 'Transamérica',  genero: 'Pop / Hits',          query: 'transamerica' },

    // === TEMÁTICAS INTERNACIONAIS (4) ===
    { id: 'lofi',       nome: 'Lofi Radio',      genero: 'Lofi / Chill',        query: 'lofi radio' },
    { id: 'jazz',       nome: 'Jazz Radio',      genero: 'Jazz / Smooth',       query: 'jazz' },
    { id: 'classic',    nome: 'Classical Radio', genero: 'Clássica / Piano',    query: 'classical radio' },
    { id: 'synthwave',  nome: 'Synthwave Radio', genero: 'Synth / Eletrônica',  query: 'synthwave' }
  ];

  /** @returns {Array} copia imutavel da lista */
  function getAll() {
    return STATIONS.slice();
  }

  /**
   * Busca uma estacao por id.
   * @param {string} id
   * @returns {object|null}
   */
  function getById(id) {
    for (var i = 0; i < STATIONS.length; i++) {
      if (STATIONS[i].id === id) return STATIONS[i];
    }
    return null;
  }

  /**
   * Tenta um host da API ate um funcionar.
   * @param {string} path ex: '/json/stations/search?name=lofi&limit=1'
   * @returns {Promise<Array>} array de estacoes (ou [] se todos falharem)
   */
  function fetchFromAPI(path) {
    var attempt = 0;
    function tryNext() {
      if (attempt >= API_HOSTS.length) {
        return Promise.resolve([]);
      }
      var host = API_HOSTS[attempt++];
      return fetch(host + path, { headers: { 'User-Agent': 'FraLib-Audio/1.0' } })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .catch(function () { return tryNext(); });
    }
    return tryNext();
  }

  /**
   * Resolve a URL de stream de uma estacao via Radio-Browser.
   * Usa cache local de 24h.
   *
   * @param {string} stationId id da estacao (ex: 'kboing')
   * @returns {Promise<{url: string, name: string, stationId: string}|null>}
   */
  function resolveStreamUrl(stationId) {
    // 1. Tenta cache
    var cached = cache[stationId];
    if (cached && cached.expiresAt > Date.now()) {
      return Promise.resolve({ url: cached.url, name: cached.name, stationId: stationId });
    }
    // 2. Busca na API
    var station = getById(stationId);
    if (!station) return Promise.resolve(null);
    var path = '/json/stations/search?name=' + encodeURIComponent(station.query) +
               '&limit=5&hidebroken=true&order=clickcount&reverse=true';
    return fetchFromAPI(path).then(function (results) {
      if (!results || results.length === 0) return null;
      // Pega a primeira que tenha url_resolved
      var found = results.find(function (r) { return r.url_resolved; }) || results[0];
      if (!found.url_resolved) return null;
      // Cacheia
      cache[stationId] = {
        url: found.url_resolved,
        name: found.name || station.nome,
        expiresAt: Date.now() + CACHE_TTL_MS
      };
      return { url: found.url_resolved, name: found.name || station.nome, stationId: stationId };
    });
  }

  /**
   * Limpa o cache de URLs (util para debug).
   */
  function clearCache() { cache = {}; }

  // Expoe no namespace global
  window.fralibAudioStations = {
    getAll: getAll,
    getById: getById,
    resolveStreamUrl: resolveStreamUrl,
    clearCache: clearCache
  };
})();
