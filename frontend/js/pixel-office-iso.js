/**
 * pixel-office-iso.js
 * ===================
 * Escritorio isometrico 3D do FraLib — versao NOVA, ocupa toda a area.
 *
 * Visao isometrica (tiles 2:1) com 4 zonas representando as 4 macroetapas
 * do pipeline:
 *   1. BUSCAR   (roxo)  - sala de caca com mapa + luneta
 *   2. ANALISAR (ciano) - laboratorio com microscopio + graficos
 *   3. PRODUZIR (rosa)  - estudio com tela + pinceis
 *   4. PUBLICAR (verde) - torre de broadcast com antena + microfone
 *
 * Dutos visuais conectam as zonas mostrando o fluxo.
 * Bonecos pixel andam com sombra isometrica.
 * Background parallax (3 camadas: ceu / silhueta de predios / chao).
 * Animacoes idle: digitando, telefonando, desenhando, transmitindo.
 *
 * Conecta-se ao PipelineWaveform.ativar(faseKey) para destacar a zona
 * correspondente (a zona ativa brilha e os dutos pulsam na direcao dela).
 *
 * Auto-inicia quando encontra <canvas id="pixelOfficeIsoCanvas"> ou
 * chama window.initPixelOfficeIso().
 */
(function () {
  'use strict';

  // ── Setup basico ─────────────────────────────────────────────────
  var cv, cx, W = 1200, H = 675; // 16:9
  var lastT = performance.now();
  var raf = null;

  // ── Paleta ───────────────────────────────────────────────────────
  var P = {
    sky: '#0b0a1a',
    skyMid: '#1a1530',
    skyHorizon: '#3a1a4a',
    ground: '#2a1a3a',
    groundTile: '#3a254a',
    groundGrid: '#1f0f2f',
    building: '#0d0a1f',
    buildingLight: '#2a1a4a',
    window: '#ffd166',
    windowOff: '#3a254a',
    pipe: '#4a3a6a',
    pipeGlow: '#7dd3fc',
    zoneBuscar: '#a855f7',
    zoneAnalisar: '#06b6d4',
    zoneProduzir: '#ec4899',
    zonePublicar: '#10b981',
    shadow: 'rgba(0,0,0,0.35)',
    textBright: '#fef3c7',
    textDim: '#94a3b8'
  };

  // ── Zonas (coordenadas isometricas em tile-space) ────────────────
  // Cada zona tem: x,y em tile (16x16 tiles de 40px = 640x360 area util)
  // Visual sera desenhado em screen-space com offset isometrico
  var ZONES = [
    {
      key: 'buscar',
      label: 'BUSCAR',
      sub: 'Caça Leads',
      color: P.zoneBuscar,
      colorDark: '#5b21b6',
      // posicao isometrica (tile space) — centro da sala
      tx: 2, ty: 5,
      // largura/altura da sala em tiles
      w: 4, h: 4
    },
    {
      key: 'analisar',
      label: 'ANALISAR',
      sub: 'Qualifica',
      color: P.zoneAnalisar,
      colorDark: '#0e7490',
      tx: 7, ty: 5, w: 4, h: 4
    },
    {
      key: 'produzir',
      label: 'PRODUZIR',
      sub: 'Cria Site',
      color: P.zoneProduzir,
      colorDark: '#9d174d',
      tx: 2, ty: 10, w: 4, h: 4
    },
    {
      key: 'publicar',
      label: 'PUBLICAR',
      sub: 'Envia SDR',
      color: P.zonePublicar,
      colorDark: '#047857',
      tx: 7, ty: 10, w: 4, h: 4
    }
  ];

  // Conexoes entre zonas (dutos)
  var PIPES = [
    { from: 'buscar',   to: 'analisar', label: 'leads' },
    { from: 'analisar', to: 'produzir', label: 'aprovados' },
    { from: 'produzir', to: 'publicar', label: 'sites' }
  ];

  var activeZone = null; // destacada quando PipelineWaveform.ativar(key)

  // ── Helpers isometricos ──────────────────────────────────────────
  // tile (tx, ty) → screen (sx, sy)
  // padrao: x cresce para direita-baixo, y cresce para esquerda-baixo
  var TILE_W = 40;  // largura de um tile (no eixo horizontal)
  var TILE_H = 20;  // altura (metade, para perspectiva 2:1)
  var ORIGIN_X = W * 0.5;  // centro horizontal
  var ORIGIN_Y = 200;     // topo do chao

  function iso(tx, ty) {
    return {
      sx: ORIGIN_X + (tx - ty) * TILE_W,
      sy: ORIGIN_Y + (tx + ty) * TILE_H
    };
  }

  // Desenha um tile (losango 2:1)
  function drawTile(tx, ty, color, stroke) {
    var p = iso(tx, ty);
    cx.fillStyle = color;
    cx.beginPath();
    cx.moveTo(p.sx, p.sy);
    cx.lineTo(p.sx + TILE_W, p.sy + TILE_H);
    cx.lineTo(p.sx, p.sy + TILE_H * 2);
    cx.lineTo(p.sx - TILE_W, p.sy + TILE_H);
    cx.closePath();
    cx.fill();
    if (stroke) {
      cx.strokeStyle = stroke;
      cx.lineWidth = 1;
      cx.stroke();
    }
  }

  // Desenha parede isometrica (caixa) — front + side + top
  function drawIsoBox(tx, ty, tw, th, height, colorTop, colorFront, colorSide) {
    // 4 cantos do top
    var t1 = iso(tx, ty);
    var t2 = iso(tx + tw, ty);
    var t3 = iso(tx + tw, ty + th);
    var t4 = iso(tx, ty + th);
    // projecao vertical
    var h = height;
    // top
    cx.fillStyle = colorTop;
    cx.beginPath();
    cx.moveTo(t1.sx, t1.sy);
    cx.lineTo(t2.sx, t2.sy);
    cx.lineTo(t3.sx, t3.sy);
    cx.lineTo(t4.sx, t4.sy);
    cx.closePath();
    cx.fill();
    // front (sul) — entre t4 e t3, indo para baixo
    cx.fillStyle = colorFront;
    cx.beginPath();
    cx.moveTo(t4.sx, t4.sy);
    cx.lineTo(t3.sx, t3.sy);
    cx.lineTo(t3.sx, t3.sy + h);
    cx.lineTo(t4.sx, t4.sy + h);
    cx.closePath();
    cx.fill();
    // side (oeste) — entre t1 e t4
    cx.fillStyle = colorSide;
    cx.beginPath();
    cx.moveTo(t1.sx, t1.sy);
    cx.lineTo(t4.sx, t4.sy);
    cx.lineTo(t4.sx, t4.sy + h);
    cx.lineTo(t1.sx, t1.sy + h);
    cx.closePath();
    cx.fill();
    // outlines
    cx.strokeStyle = 'rgba(0,0,0,0.4)';
    cx.lineWidth = 1;
    cx.beginPath();
    cx.moveTo(t1.sx, t1.sy); cx.lineTo(t2.sx, t2.sy);
    cx.lineTo(t3.sx, t3.sy); cx.lineTo(t4.sx, t4.sy);
    cx.closePath();
    cx.stroke();
    cx.beginPath();
    cx.moveTo(t4.sx, t4.sy); cx.lineTo(t4.sx, t4.sy + h);
    cx.lineTo(t3.sx, t3.sy + h); cx.stroke();
    cx.beginPath();
    cx.moveTo(t1.sx, t1.sy); cx.lineTo(t1.sx, t1.sy + h);
    cx.lineTo(t4.sx, t4.sy + h); cx.stroke();
  }

  // ── Background parallax ──────────────────────────────────────────
  var parallax = { t: 0 };
  function drawSky() {
    // gradiente vertical
    var g = cx.createLinearGradient(0, 0, 0, H * 0.6);
    g.addColorStop(0, P.sky);
    g.addColorStop(0.7, P.skyMid);
    g.addColorStop(1, P.skyHorizon);
    cx.fillStyle = g;
    cx.fillRect(0, 0, W, H * 0.6);
    // estrelas
    for (var i = 0; i < 60; i++) {
      var sx = (i * 137.5 + parallax.t * 2) % W;
      var sy = (i * 79.3) % (H * 0.5);
      var a = 0.3 + 0.7 * Math.abs(Math.sin(i + parallax.t * 0.02));
      cx.fillStyle = 'rgba(255,255,255,' + a.toFixed(2) + ')';
      cx.fillRect(sx, sy, 1.5, 1.5);
    }
    // lua
    cx.fillStyle = '#fef3c7';
    cx.beginPath();
    cx.arc(950, 80, 28, 0, Math.PI * 2);
    cx.fill();
    cx.fillStyle = P.sky;
    cx.beginPath();
    cx.arc(940, 74, 24, 0, Math.PI * 2);
    cx.fill();
  }

  function drawSkyline() {
    // silhueta de predios ao fundo (parallax 1)
    var offset = (parallax.t * 4) % 200;
    cx.fillStyle = P.building;
    for (var x = -200; x < W + 200; x += 80) {
      var real = (x + offset) % (W + 400);
      var h = 40 + ((real * 13) % 80);
      cx.fillRect(real - 100, H * 0.6 - h, 60, h);
    }
    // janelas acesas
    cx.fillStyle = P.window;
    for (var x2 = -200; x2 < W + 200; x2 += 80) {
      var real2 = (x2 + offset) % (W + 400);
      var h2 = 40 + ((real2 * 13) % 80);
      for (var wy = 0; wy < h2 - 10; wy += 12) {
        for (var wx = 0; wx < 50; wx += 15) {
          if ((wx + wy + real2) % 30 < 12) {
            cx.fillRect(real2 - 95 + wx, H * 0.6 - h2 + 6 + wy, 4, 6);
          }
        }
      }
    }
    // silhueta mais proxima (parallax 2)
    cx.fillStyle = P.buildingLight;
    for (var xx = -200; xx < W + 200; xx += 100) {
      var real3 = (xx + parallax.t * 8) % (W + 400);
      var h3 = 30 + ((real3 * 7) % 50);
      cx.fillRect(real3 - 100, H * 0.6 - h3 + 10, 80, h3);
    }
  }

  // ── Chao (grid isometrico) ───────────────────────────────────────
  function drawGround() {
    // fundo base
    cx.fillStyle = P.ground;
    cx.fillRect(0, H * 0.55, W, H * 0.45);

    // grid isometrico de tiles
    var range = 16; // 16x16 tiles visiveis
    for (var tx = -range / 2; tx < range; tx++) {
      for (var ty = -range / 2; ty < range; ty++) {
        var p = iso(tx, ty);
        // tile base
        cx.fillStyle = ((tx + ty) % 2 === 0) ? P.ground : P.groundTile;
        cx.beginPath();
        cx.moveTo(p.sx, p.sy);
        cx.lineTo(p.sx + TILE_W, p.sy + TILE_H);
        cx.lineTo(p.sx, p.sy + TILE_H * 2);
        cx.lineTo(p.sx - TILE_W, p.sy + TILE_H);
        cx.closePath();
        cx.fill();
        // grid lines
        cx.strokeStyle = P.groundGrid;
        cx.lineWidth = 0.5;
        cx.stroke();
      }
    }
  }

  // ── Salas (zonas) ────────────────────────────────────────────────
  function drawZone(z) {
    var isActive = (z.key === activeZone);
    var pulse = isActive ? (Math.sin(performance.now() * 0.005) + 1) / 2 : 0;

    // chao da sala (tile destacado)
    for (var dx = 0; dx < z.w; dx++) {
      for (var dy = 0; dy < z.h; dy++) {
        drawTile(z.tx + dx, z.ty + dy, isActive ? z.color : z.colorDark, 'rgba(0,0,0,0.3)');
      }
    }

    // glow sob a zona (se ativa)
    if (isActive) {
      var center = iso(z.tx + z.w / 2, z.ty + z.h / 2);
      var g = cx.createRadialGradient(center.sx, center.sy, 10, center.sx, center.sy, 120);
      g.addColorStop(0, hexToRgba(z.color, 0.45 * pulse + 0.15));
      g.addColorStop(1, hexToRgba(z.color, 0));
      cx.fillStyle = g;
      cx.fillRect(center.sx - 130, center.sy - 130, 260, 260);
    }

    // itens decorativos da sala
    drawZoneDecor(z, isActive, pulse);
  }

  function drawZoneDecor(z, active, pulse) {
    var cxTile = z.tx + z.w / 2;
    var cyTile = z.ty + z.h / 2;
    if (z.key === 'buscar') {
      // luneta + mapa
      drawTelescope(z.tx + 1, z.ty + 1);
      drawMap(z.tx + 1, z.ty + 2);
    } else if (z.key === 'analisar') {
      // microscopio + grafico
      drawMicroscope(z.tx + 1, z.ty + 1);
      drawChart(z.tx + 1, z.ty + 2);
    } else if (z.key === 'produzir') {
      // monitor + pincel
      drawMonitor(z.tx + 1, z.ty + 1);
      drawPaint(z.tx + 1, z.ty + 2);
    } else if (z.key === 'publicar') {
      // antena + microfone
      drawAntenna(z.tx + 1, z.ty + 1);
      drawMic(z.tx + 1, z.ty + 2);
    }

    // label flutuante da sala
    var c = iso(cxTile, z.ty);
    cx.save();
    cx.font = 'bold 11px "Courier New", monospace';
    cx.textAlign = 'center';
    var tw = cx.measureText(z.label).width;
    var labelY = c.sy - 25 - (active ? 4 * pulse : 0);
    cx.fillStyle = active ? z.color : 'rgba(20,15,40,0.9)';
    cx.fillRect(c.sx - tw / 2 - 8, labelY - 12, tw + 16, 18);
    cx.strokeStyle = active ? '#fff' : z.color;
    cx.lineWidth = 1;
    cx.strokeRect(c.sx - tw / 2 - 8, labelY - 12, tw + 16, 18);
    cx.fillStyle = active ? '#fff' : P.textBright;
    cx.fillText(z.label, c.sx, labelY + 2);
    cx.restore();
  }

  // ── Decoracao especifica por zona ────────────────────────────────
  function drawTelescope(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    // tripé
    cx.strokeStyle = '#6b7280'; cx.lineWidth = 2;
    cx.beginPath();
    cx.moveTo(p.sx - 10, p.sy + 8);
    cx.lineTo(p.sx, p.sy - 5);
    cx.lineTo(p.sx + 10, p.sy + 8);
    cx.stroke();
    // tubo
    cx.save();
    cx.translate(p.sx, p.sy - 5);
    cx.rotate(-Math.PI / 6);
    cx.fillStyle = '#9ca3af';
    cx.fillRect(-2, -18, 4, 24);
    cx.fillStyle = '#fcd34d';
    cx.beginPath(); cx.arc(0, -18, 4, 0, Math.PI * 2); cx.fill();
    cx.restore();
  }
  function drawMap(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    cx.fillStyle = '#d4a373';
    cx.fillRect(p.sx - 12, p.sy - 2, 24, 16);
    cx.strokeStyle = '#7a5230'; cx.lineWidth = 1;
    cx.strokeRect(p.sx - 12, p.sy - 2, 24, 16);
    // "mapa" com paths
    cx.strokeStyle = '#7a3030'; cx.lineWidth = 1.2;
    cx.beginPath();
    cx.moveTo(p.sx - 8, p.sy + 4); cx.lineTo(p.sx - 4, p.sy);
    cx.lineTo(p.sx + 2, p.sy + 6); cx.lineTo(p.sx + 8, p.sy + 2);
    cx.stroke();
    // pin
    cx.fillStyle = '#ef4444';
    cx.beginPath(); cx.arc(p.sx + 4, p.sy - 1, 2.5, 0, Math.PI * 2); cx.fill();
  }
  function drawMicroscope(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    cx.fillStyle = '#374151';
    cx.fillRect(p.sx - 4, p.sy + 2, 8, 10);
    cx.fillStyle = '#9ca3af';
    cx.fillRect(p.sx - 1, p.sy - 8, 2, 12);
    cx.beginPath(); cx.arc(p.sx, p.sy - 10, 4, 0, Math.PI * 2); cx.fill();
    cx.fillStyle = '#fef3c7';
    cx.fillRect(p.sx - 3, p.sy - 12, 6, 3);
  }
  function drawChart(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    cx.fillStyle = '#1f2937';
    cx.fillRect(p.sx - 12, p.sy - 8, 24, 14);
    // barras
    var bars = [4, 7, 5, 9, 6, 8];
    for (var i = 0; i < bars.length; i++) {
      cx.fillStyle = '#10b981';
      cx.fillRect(p.sx - 10 + i * 4, p.sy - 1 - bars[i], 3, bars[i]);
    }
  }
  function drawMonitor(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    // base
    cx.fillStyle = '#4b5563';
    cx.fillRect(p.sx - 6, p.sy + 6, 12, 3);
    // tela
    cx.fillStyle = '#1e293b';
    cx.fillRect(p.sx - 10, p.sy - 10, 20, 14);
    cx.fillStyle = '#7dd3fc';
    cx.fillRect(p.sx - 8, p.sy - 8, 16, 10);
    // código fake
    var t = performance.now() * 0.002;
    for (var i = 0; i < 4; i++) {
      var w = 3 + (Math.sin(t + i) + 1) * 4;
      cx.fillStyle = ['#a78bfa', '#ec4899', '#10b981'][i % 3];
      cx.fillRect(p.sx - 7, p.sy - 6 + i * 2, w, 1.5);
    }
  }
  function drawPaint(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    // paleta
    cx.fillStyle = '#d4a373';
    cx.beginPath();
    cx.ellipse(p.sx - 6, p.sy + 4, 7, 4, 0, 0, Math.PI * 2);
    cx.fill();
    // cores
    var colors = ['#ef4444', '#fbbf24', '#10b981', '#3b82f6', '#a855f7'];
    for (var i = 0; i < colors.length; i++) {
      cx.fillStyle = colors[i];
      cx.beginPath(); cx.arc(p.sx - 11 + i * 3, p.sy + 4, 1.5, 0, Math.PI * 2); cx.fill();
    }
    // pincel
    cx.strokeStyle = '#92400e'; cx.lineWidth = 1.5;
    cx.beginPath();
    cx.moveTo(p.sx + 4, p.sy + 8); cx.lineTo(p.sx + 10, p.sy - 2);
    cx.stroke();
    cx.fillStyle = '#7c2d12';
    cx.beginPath(); cx.arc(p.sx + 10, p.sy - 2, 2, 0, Math.PI * 2); cx.fill();
  }
  function drawAntenna(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    // torre
    cx.fillStyle = '#6b7280';
    cx.beginPath();
    cx.moveTo(p.sx - 2, p.sy + 10);
    cx.lineTo(p.sx + 2, p.sy + 10);
    cx.lineTo(p.sx + 1, p.sy - 12);
    cx.lineTo(p.sx - 1, p.sy - 12);
    cx.closePath();
    cx.fill();
    // esfera no topo
    cx.fillStyle = '#7dd3fc';
    cx.beginPath(); cx.arc(p.sx, p.sy - 14, 3, 0, Math.PI * 2); cx.fill();
    // ondas
    var t = performance.now() * 0.005;
    cx.strokeStyle = hexToRgba('#7dd3fc', 0.5);
    cx.lineWidth = 1.5;
    for (var r = 5; r < 12; r += 3) {
      var alpha = 0.5 * (1 - ((r + t * 3) % 9) / 9);
      cx.strokeStyle = hexToRgba('#7dd3fc', alpha);
      cx.beginPath();
      cx.arc(p.sx, p.sy - 14, r + (t * 3) % 9, -Math.PI * 0.6, -Math.PI * 0.4);
      cx.stroke();
    }
  }
  function drawMic(tx, ty) {
    var p = iso(tx + 0.5, ty + 0.5);
    cx.fillStyle = '#1f2937';
    cx.fillRect(p.sx - 3, p.sy + 2, 6, 8);
    // cabeça
    cx.fillStyle = '#374151';
    cx.beginPath(); cx.arc(p.sx, p.sy - 2, 5, 0, Math.PI * 2); cx.fill();
    cx.fillStyle = '#9ca3af';
    for (var i = 0; i < 4; i++) {
      cx.fillRect(p.sx - 4 + i * 2.5, p.sy - 4, 0.6, 3);
    }
    // ondas de som
    cx.strokeStyle = '#7dd3fc';
    cx.lineWidth = 1.5;
    for (var s = 0; s < 3; s++) {
      var a = 0.5 * Math.abs(Math.sin(performance.now() * 0.008 + s));
      cx.strokeStyle = hexToRgba('#7dd3fc', a);
      cx.beginPath();
      cx.arc(p.sx, p.sy - 2, 8 + s * 4, -Math.PI * 0.4, -Math.PI * 0.2);
      cx.stroke();
    }
  }

  // ── Dutos (conexoes) ─────────────────────────────────────────────
  function drawPipe(pipe) {
    var fromZ = ZONES.find(function (z) { return z.key === pipe.from; });
    var toZ = ZONES.find(function (z) { return z.key === pipe.to; });
    if (!fromZ || !toZ) return;
    var a = iso(fromZ.tx + fromZ.w / 2, fromZ.ty + fromZ.h / 2);
    var b = iso(toZ.tx + toZ.w / 2, toZ.ty + toZ.h / 2);

    // se a zona "to" eh a ativa, o duto brilha na direcao dela
    var isForward = (activeZone && toZ.key === activeZone);
    var pulse = isForward ? (Math.sin(performance.now() * 0.005) + 1) / 2 : 0;

    // tubo base
    cx.strokeStyle = isForward ? P.pipeGlow : P.pipe;
    cx.lineWidth = isForward ? 5 + pulse * 2 : 4;
    cx.lineCap = 'round';
    cx.beginPath();
    cx.moveTo(a.sx, a.sy);
    // leve curva
    var midX = (a.sx + b.sx) / 2;
    var midY = (a.sy + b.sy) / 2 - 15;
    cx.quadraticCurveTo(midX, midY, b.sx, b.sy);
    cx.stroke();

    // particula fluindo no duto
    var t = (performance.now() * 0.001) % 1;
    var px = a.sx + (b.sx - a.sx) * t + (a.sy < b.sy ? -0 : 0);
    var py = a.sy + (b.sy - a.sy) * t;
    // bezier
    var q = 1 - t;
    var bx = q * q * a.sx + 2 * q * t * midX + t * t * b.sx;
    var by = q * q * a.sy + 2 * q * t * midY + t * t * b.sy;
    cx.fillStyle = isForward ? '#fef3c7' : '#7dd3fc';
    cx.beginPath();
    cx.arc(bx, by, 3, 0, Math.PI * 2);
    cx.fill();
    // halo
    cx.fillStyle = hexToRgba(isForward ? '#fef3c7' : '#7dd3fc', 0.4);
    cx.beginPath();
    cx.arc(bx, by, 6, 0, Math.PI * 2);
    cx.fill();

    // label do duto
    cx.font = 'bold 8px "Courier New", monospace';
    cx.textAlign = 'center';
    cx.fillStyle = 'rgba(0,0,0,0.7)';
    var lw = cx.measureText(pipe.label).width;
    cx.fillRect(midX - lw / 2 - 3, midY - 5, lw + 6, 10);
    cx.fillStyle = P.textBright;
    cx.fillText(pipe.label, midX, midY + 2);
  }

  // ── Personagens isométricos ──────────────────────────────────────
  // Cada personagem tem: cor do corpo, papel, idleAnim, pos atual, alvo
  var CHARACTERS = [
    { name: 'CEO',    role: 'ceo',    bodyColor: '#1a5276',   tx: 4, ty: 4, idle: 'phone' },
    { name: 'Dev',    role: 'dev',    bodyColor: '#9b59b6',   tx: 4, ty: 4, idle: 'type' },
    { name: 'Design', role: 'design', bodyColor: '#e91e63',   tx: 4, ty: 4, idle: 'draw' },
    { name: 'Hunter', role: 'hunter', bodyColor: '#16a085',   tx: 4, ty: 4, idle: 'search' },
    { name: 'QA',     role: 'qa',     bodyColor: '#27ae60',   tx: 4, ty: 4, idle: 'check' },
    { name: 'Mkt',    role: 'mkt',    bodyColor: '#ff6f00',   tx: 4, ty: 4, idle: 'send' },
    { name: 'Foto',   role: 'foto',   bodyColor: '#a0522d',   tx: 4, ty: 4, idle: 'snap' },
    { name: 'SEO',    role: 'seo',    bodyColor: '#0e7490',   tx: 4, ty: 4, idle: 'analyze' },
    { name: 'Caio',   role: 'caio',   bodyColor: '#dc2626',   tx: 4, ty: 4, idle: 'review' }
  ];

  var characters = []; // instancias com posicao atual interpolada

  function initCharacters() {
    characters = CHARACTERS.map(function (c, i) {
      return {
        def: c,
        // distribui pelos 4 zonas
        tx: ZONES[i % 4].tx + 1 + (i % 2) * 1.5,
        ty: ZONES[i % 4].ty + 1 + Math.floor(i / 4) * 1.5,
        targetTx: ZONES[i % 4].tx + 1 + (i % 2) * 1.5,
        targetTy: ZONES[i % 4].ty + 1 + Math.floor(i / 4) * 1.5,
        t: 0, // progresso 0..1 entre origem e destino
        speed: 0.4 + Math.random() * 0.3,
        animT: Math.random() * 10,
        bobOffset: Math.random() * Math.PI * 2
      };
    });
  }

  // reatribui um personagem para uma zona especifica
  function reassignCharacter(ch, zoneIdx) {
    var z = ZONES[zoneIdx];
    if (!z) return;
    var offsetX = (Math.random() - 0.5) * (z.w - 1.5);
    var offsetY = (Math.random() - 0.5) * (z.h - 1.5);
    ch.tx = ch.targetTx;
    ch.ty = ch.targetTy;
    ch.targetTx = z.tx + z.w / 2 + offsetX;
    ch.targetTy = z.ty + z.h / 2 + offsetY;
    ch.t = 0;
  }

  // Personagem isométrico (32x40 sprite com sombra)
  function drawCharacter(ch) {
    // sombra isometrica (losango embaixo)
    var p = iso(ch.tx, ch.ty);
    var bob = Math.sin(performance.now() * 0.004 + ch.bobOffset) * 1.5;
    cx.save();
    cx.fillStyle = 'rgba(0,0,0,0.35)';
    cx.beginPath();
    cx.ellipse(p.sx, p.sy + 16, 11, 5, 0, 0, Math.PI * 2);
    cx.fill();
    cx.restore();

    // corpo (forma simplificada em isometrico: cilindro com cabeca)
    var sx = p.sx;
    var sy = p.sy - 8 + bob;
    // pernas
    cx.fillStyle = '#1f2937';
    cx.fillRect(sx - 3, sy + 8, 2.5, 8);
    cx.fillRect(sx + 0.5, sy + 8, 2.5, 8);
    // corpo
    cx.fillStyle = ch.def.bodyColor;
    cx.beginPath();
    cx.moveTo(sx - 5, sy - 2);
    cx.lineTo(sx + 5, sy - 2);
    cx.lineTo(sx + 6, sy + 10);
    cx.lineTo(sx - 6, sy + 10);
    cx.closePath();
    cx.fill();
    // detalhe do corpo (claro)
    cx.fillStyle = hexToRgba('#ffffff', 0.18);
    cx.fillRect(sx - 4, sy - 1, 8, 3);
    // cabeca
    cx.fillStyle = '#fdbcb4';
    cx.beginPath();
    cx.arc(sx, sy - 6, 4.5, 0, Math.PI * 2);
    cx.fill();
    // cabelo
    cx.fillStyle = ch.def.bodyColor;
    cx.beginPath();
    cx.arc(sx, sy - 8, 4.5, Math.PI, Math.PI * 2);
    cx.fill();
    // olhos
    cx.fillStyle = '#fff';
    cx.beginPath(); cx.arc(sx - 1.5, sy - 6, 1, 0, Math.PI * 2); cx.fill();
    cx.beginPath(); cx.arc(sx + 1.5, sy - 6, 1, 0, Math.PI * 2); cx.fill();
    cx.fillStyle = '#1a1a2e';
    cx.beginPath(); cx.arc(sx - 1.5, sy - 6, 0.5, 0, Math.PI * 2); cx.fill();
    cx.beginPath(); cx.arc(sx + 1.5, sy - 6, 0.5, 0, Math.PI * 2); cx.fill();

    // animacao idle especifica
    drawIdleAnimation(ch, sx, sy);
  }

  function drawIdleAnimation(ch, sx, sy) {
    var t = performance.now() * 0.005;
    switch (ch.def.idle) {
      case 'type':
        // dedos mexendo
        cx.fillStyle = '#fdbcb4';
        var dy = Math.sin(t * 2 + ch.bobOffset) * 0.8;
        cx.beginPath(); cx.arc(sx - 5, sy + 2 + dy, 1, 0, Math.PI * 2); cx.fill();
        cx.beginPath(); cx.arc(sx - 5, sy + 5 - dy, 1, 0, Math.PI * 2); cx.fill();
        break;
      case 'phone':
        // brasao de telefone na mao
        cx.fillStyle = '#1a1a2e';
        cx.fillRect(sx - 7, sy + 1, 2.5, 4);
        cx.fillStyle = '#10b981';
        if (Math.sin(t * 2) > 0) cx.fillRect(sx - 7, sy + 2, 2, 1);
        break;
      case 'draw':
        // brasao de pincel
        cx.strokeStyle = '#92400e'; cx.lineWidth = 1;
        cx.beginPath();
        cx.moveTo(sx + 5, sy + 4);
        cx.lineTo(sx + 8 + Math.sin(t) * 0.5, sy);
        cx.stroke();
        break;
      case 'search':
        // lupa
        cx.strokeStyle = '#fcd34d'; cx.lineWidth = 1.2;
        cx.beginPath();
        cx.arc(sx + 6, sy + 2, 3, 0, Math.PI * 2);
        cx.stroke();
        cx.beginPath();
        cx.moveTo(sx + 8, sy + 4);
        cx.lineTo(sx + 10, sy + 6);
        cx.stroke();
        break;
      case 'check':
        // check mark
        cx.strokeStyle = '#10b981'; cx.lineWidth = 1.5;
        cx.beginPath();
        cx.moveTo(sx - 5, sy + 3);
        cx.lineTo(sx - 3, sy + 5);
        cx.lineTo(sx - 1, sy + 1);
        cx.stroke();
        break;
      case 'send':
        // envelope
        cx.fillStyle = '#7dd3fc';
        cx.fillRect(sx - 5, sy + 1, 6, 4);
        cx.strokeStyle = '#1a1a2e'; cx.lineWidth = 0.5;
        cx.beginPath();
        cx.moveTo(sx - 5, sy + 1); cx.lineTo(sx - 2, sy + 3); cx.lineTo(sx + 1, sy + 1);
        cx.stroke();
        break;
      case 'snap':
        // camera
        cx.fillStyle = '#1a1a2e';
        cx.fillRect(sx - 5, sy + 1, 7, 4);
        cx.fillStyle = '#7dd3fc';
        cx.fillRect(sx - 4, sy + 2, 5, 2);
        break;
      case 'analyze':
        // grafico subindo
        cx.fillStyle = '#7dd3fc';
        for (var i = 0; i < 3; i++) {
          var h = 2 + Math.abs(Math.sin(t + i)) * 3;
          cx.fillRect(sx - 5 + i * 2, sy + 5 - h, 1.5, h);
        }
        break;
      case 'review':
        // papel
        cx.fillStyle = '#fef3c7';
        cx.fillRect(sx - 4, sy + 0, 5, 6);
        cx.fillStyle = '#1a1a2e';
        cx.fillRect(sx - 3, sy + 1, 3, 0.5);
        cx.fillRect(sx - 3, sy + 2.5, 3, 0.5);
        cx.fillRect(sx - 3, sy + 4, 2, 0.5);
        break;
    }
  }

  // ── Particulas ambiente ──────────────────────────────────────────
  var particles = [];
  for (var i = 0; i < 50; i++) {
    particles.push({
      x: Math.random() * W,
      y: Math.random() * H * 0.6,
      vx: (Math.random() - 0.5) * 15,
      vy: Math.random() * 8 + 2,
      r: 0.5 + Math.random() * 1.5,
      a: 0.15 + Math.random() * 0.35,
      c: ['#7dd3fc', '#a78bfa', '#fbbf24', '#34d399', '#f472b6', '#fef3c7'][i % 6]
    });
  }
  function drawParticles(dt) {
    particles.forEach(function (p) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (p.x < -10) p.x = W + 10;
      if (p.x > W + 10) p.x = -10;
      if (p.y > H * 0.6) {
        p.y = -10;
        p.x = Math.random() * W;
      }
      cx.save();
      cx.globalAlpha = p.a;
      cx.fillStyle = p.c;
      cx.beginPath();
      cx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      cx.fill();
      // glow
      cx.globalAlpha = p.a * 0.3;
      cx.beginPath();
      cx.arc(p.x, p.y, p.r * 2.5, 0, Math.PI * 2);
      cx.fill();
      cx.restore();
    });
  }

  // ── Atualizacao ──────────────────────────────────────────────────
  function update(dt) {
    parallax.t += dt;
    // move personagens em direcao ao alvo
    characters.forEach(function (ch) {
      var dx = ch.targetTx - ch.tx;
      var dy = ch.targetTy - ch.ty;
      var dist = Math.hypot(dx, dy);
      if (dist < 0.1) {
        // chegou — fica idle
        ch.animT += dt;
        // 30% chance de pegar nova zona a cada ~3s
        if (ch.animT > 3 && Math.random() < 0.02) {
          ch.animT = 0;
          // se alguma zona esta ativa, vai pra la
          if (activeZone) {
            var zIdx = ZONES.findIndex(function (z) { return z.key === activeZone; });
            if (zIdx >= 0) {
              reassignCharacter(ch, zIdx);
              return;
            }
          }
          // senao, vai pra zona aleatoria
          var rand = Math.floor(Math.random() * 4);
          reassignCharacter(ch, rand);
        }
        return;
      }
      // move
      var mv = ch.speed * dt;
      ch.tx += (dx / dist) * Math.min(mv, dist);
      ch.ty += (dy / dist) * Math.min(mv, dist);
    });
  }

  // ── Render principal ─────────────────────────────────────────────
  function render() {
    // camadas back-to-front:
    drawSky();
    drawSkyline();
    drawGround();
    // dutos primeiro (atras das salas)
    PIPES.forEach(drawPipe);
    // salas
    ZONES.forEach(drawZone);
    // personagens (ordenados por ty para parecer profundidade)
    characters.sort(function (a, b) { return a.ty - b.ty; });
    characters.forEach(drawCharacter);
    // camada de particulas na frente
    drawParticles(0.016);
  }

  // ── Loop ─────────────────────────────────────────────────────────
  function loop(now) {
    var dt = Math.min((now - lastT) / 1000, 0.1);
    lastT = now;
    cx.clearRect(0, 0, W, H);
    update(dt);
    render();
    raf = requestAnimationFrame(loop);
  }

  // ── Init ─────────────────────────────────────────────────────────
  function init() {
    cv = document.getElementById('pixelOfficeIsoCanvas');
    if (!cv) {
      // tenta achar o canvas antigo e trocar pelo iso
      var old = document.getElementById('pixelOfficeCanvas');
      if (old) {
        old.id = 'pixelOfficeIsoCanvas';
        old.style.aspectRatio = '16/9';
        cv = old;
      } else {
        console.warn('[PixelOfficeIso] canvas nao encontrado');
        return;
      }
    }
    cx = cv.getContext('2d');
    cv.width = W;
    cv.height = H;

    // responsivo
    function resize() {
      var wrap = document.getElementById('pixelOfficeWrap') || cv.parentElement;
      if (!wrap) return;
      var maxW = wrap.clientWidth || 1200;
      var s = Math.min(maxW / W, 1);
      cv.style.width = (W * s) + 'px';
      cv.style.height = (H * s) + 'px';
    }
    resize();
    window.addEventListener('resize', resize);

    initCharacters();
    if (raf) cancelAnimationFrame(raf);
    lastT = performance.now();
    raf = requestAnimationFrame(loop);
  }

  // ── API publica ──────────────────────────────────────────────────
  window.initPixelOfficeIso = init;
  window.PixelOfficeIso = {
    setActiveZone: function (key) { activeZone = key; },
    init: init,
    ZONES: ZONES
  };

  // hook com waveform (quando ela ativa uma fase, destacamos a zona)
  function hookWaveform() {
    var checkInterval = setInterval(function () {
      var pw = window.PipelineWaveform;
      if (pw && pw.ETAPAS) {
        clearInterval(checkInterval);
        // wrap em _syncFromStatus nao funciona (privado), entao
        // sobrescrevemos ativar para detectar mudanca
        var orig = pw.ativar;
        if (orig && !orig.__poi_wrapped) {
          pw.ativar = function (faseKey, label) {
            orig.call(this, faseKey, label);
            window.PixelOfficeIso.setActiveZone(pw.macroFromKey(faseKey));
          };
          pw.ativar.__poi_wrapped = true;
        }
      }
    }, 200);
  }

  // auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      init();
      hookWaveform();
    });
  } else {
    init();
    hookWaveform();
  }

  // ── Util ─────────────────────────────────────────────────────────
  function hexToRgba(hex, a) {
    var h = hex.replace('#', '');
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    var r = parseInt(h.substring(0, 2), 16);
    var g = parseInt(h.substring(2, 4), 16);
    var b = parseInt(h.substring(4, 6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }
})();
