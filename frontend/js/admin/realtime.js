/**
 * FraLib Admin - Realtime Module
 * Socket.io and SSE handlers for live updates
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ MAGIC LOGS ══════════════════════════════════════════════════════ */
var mensagensMisticas = [
  '🔮 Lendo as estrelas...',
  '✨ Pulando arco-íris de dados...',
  '🌙 Sondando o cosmos digital...',
  '🎭 Interpretando os códigos sagrados...',
  '⚡ Carregando partículas mágicas...',
  '🌌 Navegando por nebulosas de leads...',
  '💫 Invocando a sabedoria ancestral...',
  '🎨 Fazendo a arte do site...',
  '⚡ Oportunidade encontrada!',
  '🌟 Invocando leads qualificados...',
  '🪄 Tecendo a teia de prospecção...',
  '💎 Garimpando ouro digital...',
  '🎯 Mirando no alvo perfeito...',
  '🚀 Lançando foguetes de vendas...',
  '🔥 Acendendo a fogueira do sucesso...',
  '💰 Contando moedas de ouro...',
  '📞 Preparando o telefone mágico...',
  '🎪 Montando o circo das vendas...',
  '🏆 Conquistando territórios...',
  '🌈 Seguindo o arco-íris do lucro...'
];

function adicionarLogMagico(mensagem) {
  var container = document.getElementById('magic-logs-container');
  var content = document.getElementById('magic-logs-content');

  if (!container || !content) return;

  container.style.display = 'block';

  if (!mensagem) {
    mensagem = mensagensMisticas[Math.floor(Math.random() * mensagensMisticas.length)];
  }

  var logLine = document.createElement('div');
  logLine.style.cssText = 'color:var(--fl-text-muted);padding:4px 8px;background:rgba(147,51,234,0.05);border-radius:4px;border-left:3px solid var(--fl-purple)';

  var timestamp = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  logLine.innerHTML = '<span style="color:var(--fl-text-dim)">[' + timestamp + ']</span> ' + escapeHtml(mensagem);

  content.insertBefore(logLine, content.firstChild);

  while (content.children.length > 20) {
    content.removeChild(content.lastChild);
  }
}

function limparTerminal() {
  var content = document.getElementById('magic-logs-content');
  if (content) content.innerHTML = '';
}

/* ══ SOCKET.IO HANDLERS ═════════════════════════════════════════════ */
if (typeof socket !== 'undefined') {
  socket.on('pipeline:start', function() {
    adicionarLogMagico('🔮 Pipeline iniciado! Preparando a magia...');
    iniciarCronometroPipelineAdmin();
  });

  socket.on('pipeline:lead', function(data) {
    adicionarLogMagico();
  });

  socket.on('pipeline:site', function(data) {
    adicionarLogMagico();
  });

  socket.on('pipeline:complete', function() {
    adicionarLogMagico('✅ Ciclo completo! A magia aconteceu!');
    pararCronometroPipelineAdmin();
  });

  socket.on('pipeline:error', function(data) {
    adicionarLogMagico('⚠️ Ops! O feitiço falhou...');
    var msg = (data && (data.erro || data.message)) || 'Pipeline falhou';
    if (typeof Toast !== 'undefined') Toast.error(msg);
    pararCronometroPipelineAdmin();
    mostrarErrosPipelineAdmin('Pipeline interrompido', msg, 'Revise os logs, busque novos leads ou atualize o status antes de iniciar novamente.');
    var overlay = document.getElementById('pipeline-overlay') || document.querySelector('.pipeline-overlay');
    if (overlay) overlay.style.display = 'none';
  });
}
</script>
