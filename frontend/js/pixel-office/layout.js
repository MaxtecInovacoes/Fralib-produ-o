// ============================================================
// BLOCK 5 — LAYOUT, OBSTÁCULOS, WAYPOINTS, LOOP
// ============================================================
const WALL_W=20;
const ROOM_X=590;
const CEO_ROOM  ={x:ROOM_X,y:0,  w:210,h:200};
const AUDIT_ROOM={x:ROOM_X,y:200,w:210,h:200};

// ZONAS
const MEET_POS ={x:300,y:160};  // mesa reunião
const LOUNGE_X =280, LOUNGE_Y=320; // lounge — canto inferior centro
// SALA DO CAFÉ — canto inferior ESQUERDO
const CAFE_X=30,  CAFE_Y=290;   // sala café começa aqui
const CAFE_W=130, CAFE_H=100;   // dimensões da sala café

// MESAS DE TRABALHO — 2 fileiras de 2, bem espaçadas
const WORK_DESKS=[
    {x:70, y:50,  owner:'Open Design'},
    {x:190,y:50,  owner:'Agente Nicho'},
    {x:70, y:180, owner:'Validador'},
    {x:190,y:180, owner:'Franz'},
    {x:430,y:50,  owner:'Curadoria'},
    {x:430,y:180, owner:'Hunter'},
    {x:500,y:50,  owner:'Caio'},
];

const AGENT_DEFS=[
    {name:'Open Design',   role:'Dev',       color:'#3730a3',female:false,homeX:97, homeY:83, allowedRooms:['main']},
    {name:'Agente Nicho',   role:'Designer',  color:'#7e22ce',female:false,homeX:217,homeY:83, allowedRooms:['main']},
    {name:'Validador',    role:'QA',        color:'#92400e',female:true, homeX:97, homeY:213,allowedRooms:['main']},
    {name:'Franz',  role:'Marketing', color:'#7c2d12',female:false,homeX:217,homeY:213,allowedRooms:['main']},
    {name:'Curadoria',   role:'Fotos',     color:'#b45309',female:false,homeX:457,homeY:83, allowedRooms:['main']},
    {name:'Hunter', role:'Hunter',    color:'#065f46',female:false,homeX:457,homeY:213,allowedRooms:['main']},
    {name:'Caio',   role:'Analista',  color:'#7c3aed',female:false,homeX:527,homeY:83, allowedRooms:['main']},
    {name:'Renata', role:'CEO',       color:'#4a044e',female:true, homeX:ROOM_X+90,homeY:110,allowedRooms:['main','ceo']},
    {name:'Franz',  role:'SEO',       color:'#064e3b',female:false,homeX:ROOM_X+90,homeY:310,allowedRooms:['main','audit']},
];

const GROUP_EVENTS=[
    {id:'coffee',label:'☕ Pausa no café',
     getPos:()=>({x:CAFE_X+60,y:CAFE_Y+65}),
     spread:30,min:2,max:4,interval:()=>28+Math.random()*22,duration:()=>12+Math.random()*10,
     dialogues:['Esse café tá bom!','Alguém viu o deploy?','Precisamos de mais café','Que semana pesada...','Finalmente uma pausa!']},
    {id:'ceo_visit',label:'🔍 Briefing com Hunter',
     getPos:()=>({x:ROOM_X+90,y:110}),
     spread:22,min:1,max:2,interval:()=>50+Math.random()*40,duration:()=>10+Math.random()*10,
     dialogues:['Hunter, quantos leads hoje?','Novos leads chegando!','Segmento capturado!','Score acima de 70!']},
    {id:'meeting',label:'🗣️ Reunião em grupo',
     getPos:()=>({x:MEET_POS.x+70,y:MEET_POS.y+35}),
     spread:55,min:3,max:5,interval:()=>60+Math.random()*40,duration:()=>16+Math.random()*14,
     dialogues:['Vamos alinhar as prioridades','Quais são os blockers?','Sprint review agora','Precisamos acelerar','Alguém fez o daily?']},
    {id:'celebration',label:'🎉 Venda fechada!',
     getPos:()=>({x:240+Math.random()*80,y:150+Math.random()*60}),
     spread:70,min:4,max:6,interval:()=>95+Math.random()*75,duration:()=>14+Math.random()*10,
     dialogues:['FECHAMOS! Novo cliente!','Isso merece comemorar!','Time incrível, parabéns!','Mais uma venda no board!','Resultado: INCRÍVEL!']},
    {id:'chat',label:'💬 Papo aleatório',
     getPos:()=>({x:150+Math.random()*200,y:120+Math.random()*130}),
     spread:26,min:2,max:3,interval:()=>16+Math.random()*20,duration:()=>6+Math.random()*8,
     dialogues:['Viu aquele meme?','Que bug bizarro...','Almoço junto hoje?','Tô precisando de férias','Pair programming depois?']},
];

// PRE-RENDER
const S={
    floor:Sprites.floor(),
    desk:Sprites.desk(), bigDesk:Sprites.bigDesk(), comp:Sprites.computer(),
    chair:Sprites.chair(), bossChair:Sprites.bossChair(), cabinet:Sprites.cabinet(),
    meetTable:Sprites.meetTable(),
    mChairTop:Sprites.meetChairTop(), mChairBot:Sprites.meetChairBottom(),
    coffee:Sprites.coffee(), plant:Sprites.plant(), smallPlant:Sprites.smallPlant(),
    wb:Sprites.whiteboard(), sofa:Sprites.sofa(), coffeeTable:Sprites.coffeeTable(),
    fridge:Sprites.fridge(),
    p0:Sprites.painting(0), p1:Sprites.painting(1), p2:Sprites.painting(2),
};

// ── OBSTÁCULOS (hitboxes) ──────────────────────────────────
function initObstacles(){
    OBSTACLES=[
        // parede esquerda (vidro)
        {x:0,y:0,w:WALL_W+5,h:H},
        // parede norte
        {x:0,y:0,w:ROOM_X,h:18},
        // parede sul
        {x:0,y:H-18,w:ROOM_X,h:18},
        // divisória salas — passagens largas (50px) para entrar/sair
        {x:ROOM_X,y:0,w:WALL_W+5,h:60},          // acima passagem CEO
        {x:ROOM_X,y:110,w:WALL_W+5,h:150},        // entre passagens
        {x:ROOM_X,y:310,w:WALL_W+5,h:H-310},      // abaixo passagem Auditora
        // divisória horizontal CEO/Auditora
        {x:ROOM_X,y:194,w:CEO_ROOM.w,h:12},
        // mesas de trabalho
        ...WORK_DESKS.map(d=>({x:d.x,y:d.y,w:54,h:36})),
        // mesas extras
        {x:430,y:50,w:54,h:36},
        {x:430,y:180,w:54,h:36},
        {x:500,y:50,w:54,h:36},
        // mesa reunião
        {x:MEET_POS.x,y:MEET_POS.y,w:140,h:60},
        // armários
        {x:290,y:18,w:40,h:52},{x:336,y:18,w:40,h:52},
        // sala café — canto inferior esquerdo, abertura no lado direito
        {x:CAFE_X,y:CAFE_Y,w:CAFE_W,h:10},                    // parede norte
        {x:CAFE_X,y:CAFE_Y,w:10,h:CAFE_H},                    // parede oeste (parede esquerda total)
        {x:CAFE_X,y:CAFE_Y+CAFE_H-10,w:CAFE_W,h:10},          // parede sul
        {x:CAFE_X+CAFE_W-10,y:CAFE_Y,w:10,h:40},              // parede leste acima abertura
        {x:CAFE_X+CAFE_W-10,y:CAFE_Y+80,w:10,h:CAFE_H-80},   // parede leste abaixo abertura
        // sofá lounge
        {x:LOUNGE_X+8,y:LOUNGE_Y,w:88,h:42},
    ];
}

// ── WAYPOINTS DE NAVEGAÇÃO ────────────────────────────────
function initWaypoints(){
    NAV_WAYPOINTS=[
        // corredor principal horizontal
        {x:50, y:130},{x:150,y:130},{x:260,y:130},{x:370,y:130},{x:450,y:130},
        // corredor vertical esquerdo
        {x:50, y:50},{x:50, y:250},{x:50, y:350},
        // corredor vertical centro
        {x:260,y:50},{x:260,y:250},{x:260,y:350},
        // corredor vertical direito (antes das salas)
        {x:450,y:50},{x:450,y:250},{x:450,y:350},
        // perto das passagens das salas
        {x:ROOM_X-25,y:85},   // passagem CEO
        {x:ROOM_X+30,y:85},   // dentro CEO
        {x:ROOM_X-25,y:285},  // passagem Auditora
        {x:ROOM_X+30,y:285},  // dentro Auditora
        // dentro das salas (só para Renata e Franz)
        {x:ROOM_X+50,y:100,onlyRole:'CEO'},
        {x:ROOM_X+50,y:300,onlyRole:'Auditora'},
        // entrada sala café (abertura no lado direito)
        {x:CAFE_X+CAFE_W+20,y:CAFE_Y+55},
        {x:CAFE_X+CAFE_W-20,y:CAFE_Y+55},
        // lounge
        {x:LOUNGE_X+50,y:LOUNGE_Y+60},
        // zona reunião
        {x:MEET_POS.x-30,y:MEET_POS.y+30},
        {x:MEET_POS.x+170,y:MEET_POS.y+30},
    ];
}

// ── DESENHO PAREDE VIDRO ESQUERDA ─────────────────────────
function drawGlassWall(){
    cx.fillStyle=P.glassWall; cx.fillRect(0,0,WALL_W,H);
    cx.fillStyle=P.glassWallLight; cx.fillRect(0,0,WALL_W,4);
    cx.fillStyle=P.glassWallDark; cx.fillRect(WALL_W-3,0,3,H);
    // janelas
    [20,100,180,260,340].forEach(wy=>{
        cx.fillStyle='#b3e5fc';
        const g=cx.createLinearGradient(2,wy,2,wy+60);
        g.addColorStop(0,'#81d4fa'); g.addColorStop(1,'#e1f5fe');
        cx.fillStyle=g; cx.fillRect(2,wy,WALL_W-4,60);
        cx.fillStyle='rgba(255,255,255,0.3)'; cx.fillRect(2,wy,6,60);
        cx.strokeStyle=P.glassFrame; cx.lineWidth=1; cx.strokeRect(2,wy,WALL_W-4,60);
        cx.fillStyle=P.glassFrame; cx.fillRect(2,wy+28,WALL_W-4,2);
    });
}

// ── DESENHO DIVISÓRIA SALAS ───────────────────────────────
function drawRoomDivider(){
    // parede divisória vertical — com passagens abertas (50px cada)
    // CEO: passagem y=60 a y=110
    // Auditora: passagem y=260 a y=310
    cx.fillStyle=P.glassWall;
    cx.fillRect(ROOM_X,0,WALL_W,60);           // acima passagem CEO
    cx.fillRect(ROOM_X,110,WALL_W,150);        // entre passagens
    cx.fillRect(ROOM_X,310,WALL_W,H-310);      // abaixo passagem Auditora
    cx.fillStyle=P.glassWallLight;
    cx.fillRect(ROOM_X,0,4,60);
    cx.fillRect(ROOM_X,110,4,150);
    cx.fillRect(ROOM_X,310,4,H-310);
    cx.fillStyle=P.glassWallDark;
    cx.fillRect(ROOM_X+WALL_W-3,0,3,60);
    cx.fillRect(ROOM_X+WALL_W-3,110,3,150);
    cx.fillRect(ROOM_X+WALL_W-3,310,3,H-310);
    // divisória horizontal CEO/Auditora
    cx.fillStyle=P.glassWall; cx.fillRect(ROOM_X,194,CEO_ROOM.w,12);
    cx.fillStyle=P.glassWallLight; cx.fillRect(ROOM_X,194,CEO_ROOM.w,3);
    // labels
    cx.font='bold 8px Arial,sans-serif'; cx.textAlign='center';
    cx.fillStyle='#a78bfa'; cx.fillText('RENATA — CEO',ROOM_X+CEO_ROOM.w/2,12);
    cx.fillStyle='#6ee7b7'; cx.fillText('FRANZ — AUDITORA',ROOM_X+CEO_ROOM.w/2,212);
    cx.textAlign='left';
}

// ── SALA DO CAFÉ ──────────────────────────────────────────
function drawCafeRoom(){
    // piso diferente
    cx.fillStyle='rgba(180,140,100,0.14)';
    cx.fillRect(CAFE_X+10,CAFE_Y+10,CAFE_W-20,CAFE_H-20);
    // paredes — abertura no lado direito (leste)
    cx.fillStyle=P.cafeWall;
    cx.fillRect(CAFE_X,CAFE_Y,CAFE_W,10);                   // norte
    cx.fillRect(CAFE_X,CAFE_Y,10,CAFE_H);                   // oeste (total, encostado na parede esquerda)
    cx.fillRect(CAFE_X,CAFE_Y+CAFE_H-10,CAFE_W,10);         // sul
    cx.fillRect(CAFE_X+CAFE_W-10,CAFE_Y,10,40);             // leste acima abertura
    cx.fillRect(CAFE_X+CAFE_W-10,CAFE_Y+80,10,CAFE_H-80);  // leste abaixo abertura
    // label
    cx.font='bold 7px Arial'; cx.textAlign='center';
    cx.fillStyle='rgba(100,60,20,0.6)';
    cx.fillText('CAFÉ',CAFE_X+CAFE_W/2,CAFE_Y+22);
    cx.textAlign='left';
}

function drawBG(){
    for(let x=0;x<W;x+=32) for(let y=0;y<H;y+=32) cx.drawImage(S.floor,x,y);
    drawGlassWall();
    drawCafeRoom();
    drawRoomDivider();
    cx.strokeStyle='rgba(100,170,200,0.4)'; cx.lineWidth=1.5; cx.strokeRect(1,1,W-2,H-2);
    cx.font='7px Arial'; cx.fillStyle='rgba(0,0,0,0.15)';
    cx.fillText('ÁREA DE TRABALHO',30,46);
    cx.fillText('REUNIÃO',MEET_POS.x+30,MEET_POS.y-8);
    cx.fillText('LOUNGE',LOUNGE_X+4,LOUNGE_Y-6);
}

function drawFurniture(){
    // ZONA TRABALHO
    cx.drawImage(S.wb,28,20);
    cx.drawImage(S.p0,116,20); cx.drawImage(S.p1,160,20); cx.drawImage(S.p2,204,20);
    cx.drawImage(S.cabinet,290,20); cx.drawImage(S.cabinet,336,20);
    WORK_DESKS.forEach(d=>{
        cx.drawImage(S.desk,d.x,d.y);
        cx.drawImage(S.comp,d.x+14,d.y-14);
        cx.drawImage(S.chair,d.x+13,d.y+26);
        cx.drawImage(S.smallPlant,d.x+40,d.y-6);
    });
    cx.drawImage(S.plant,290,110); cx.drawImage(S.plant,390,110);

    // ZONA REUNIÃO
    cx.drawImage(S.meetTable,MEET_POS.x,MEET_POS.y);
    [0,36,72,108].forEach(ox=>{
        cx.drawImage(S.mChairTop,MEET_POS.x+8+ox,MEET_POS.y-22);
        cx.drawImage(S.mChairBot,MEET_POS.x+8+ox,MEET_POS.y+62);
    });

    // ZONA LOUNGE
    cx.drawImage(S.sofa,LOUNGE_X+8,LOUNGE_Y);
    cx.drawImage(S.coffeeTable,LOUNGE_X+16,LOUNGE_Y+44);

    // SALA CAFÉ
    cx.drawImage(S.coffee,CAFE_X+16,CAFE_Y+20);
    cx.drawImage(S.fridge,CAFE_X+60,CAFE_Y+20);
    cx.fillStyle='#8b6f47'; cx.fillRect(CAFE_X+12,CAFE_Y+54,100,8);
    cx.fillStyle='#6b5235'; cx.fillRect(CAFE_X+12,CAFE_Y+58,100,4);
    cx.drawImage(S.p1,CAFE_X+16,CAFE_Y+68);

    // SALAS PRIVADAS
    cx.drawImage(S.p0,ROOM_X+24,20); cx.drawImage(S.p1,ROOM_X+68,20);
    cx.drawImage(S.p2,ROOM_X+24,220); cx.drawImage(S.p0,ROOM_X+68,220);
    cx.drawImage(S.bigDesk,ROOM_X+28,75);
    cx.drawImage(S.comp,ROOM_X+46,61);
    cx.drawImage(S.bossChair,ROOM_X+42,111);
    cx.drawImage(S.bigDesk,ROOM_X+28,275);
    cx.drawImage(S.comp,ROOM_X+46,261);
    cx.drawImage(S.bossChair,ROOM_X+42,311);

    // DECORAÇÕES — cantos e bordas apenas
    drawClock(500,8);
    drawNoticeboard(420,8);
    // plantas grandes nos 3 cantos livres
    cx.drawImage(S.plant,558,10);
    cx.drawImage(S.plant,558,358);
    cx.drawImage(S.plant,22,358);
    // plantas nas salas privadas
    cx.drawImage(S.plant,ROOM_X+158,65);
    cx.drawImage(S.smallPlant,ROOM_X+158,265);
    // vasos pequenos nos cantos das paredes
    cx.drawImage(S.smallPlant,22,10);
    cx.drawImage(S.smallPlant,460,372);
    cx.drawImage(S.smallPlant,160,372);
}

// SIMULATOR
let agents=[], evTimers={}, lastT=performance.now(), fc=0, ft=0;

function triggerEv(ev){
    const avail=agents.filter(a=>!a.ge);
    if(avail.length<ev.min) return;
    const n=Math.min(ev.max,ev.min+Math.floor(Math.random()*(ev.max-ev.min+1)));
    const picked=avail.sort(()=>Math.random()-.5).slice(0,n);
    const pos=ev.getPos();
    picked.forEach(a=>a.startEv(ev,pos));
    if(picked.length) picked[0].say(ev.dialogues[Math.floor(Math.random()*ev.dialogues.length)]);
    document.getElementById('po-ev').textContent=ev.label;
}

function updateEvTimers(dt){
    GROUP_EVENTS.forEach(ev=>{
        if(evTimers[ev.id]===undefined) evTimers[ev.id]=ev.interval();
        evTimers[ev.id]-=dt;
        if(evTimers[ev.id]<=0){evTimers[ev.id]=ev.interval();triggerEv(ev);}
    });
}

function loop(){
    const now=performance.now();
    const dt=Math.min((now-lastT)/1000,0.1);
    lastT=now;
    fc++; ft+=dt;
    if(ft>=1){document.getElementById('po-sf').textContent=fc;fc=0;ft=0;}
    cx.clearRect(0,0,W,H);
    drawBG();
    drawFurniture();
    updateEvTimers(dt);
    agents.forEach(a=>a.update(dt));
    agents.sort((a,b)=>a.y-b.y);
    agents.forEach(a=>a.draw(cx));
    const working=agents.filter(a=>a.state==='working').length;
    document.getElementById('po-sc').textContent=agents.length;
    document.getElementById('po-sp').textContent=Math.round(working/agents.length*100)+'%';
    window._pixelOfficeRAF = requestAnimationFrame(loop);
}


// ── SSE -> BOLHAS DOS AGENTES ─────────────────────────────
const AGENT_SSE_MAP = {
    'leads':   'Hunter',
    'LEADS':   'Hunter',
    'caio':    'Caio',
    'CAIO':    'Caio',
    'pipeline':'Open Design',
    'PIPELINE_STATUS':'Open Design',
    'SUCCESS': 'Validador',
    'ERROR':   'Validador',
    'WARNING': 'Franz',
    'INFO':    'Agente Nicho',
};

window.mostrarBolhaAgente = function mostrarBolhaAgente(nomeAgente, mensagem) {
    if(!agents || !agents.length) return;
    const agente = agents.find(a => a.name === nomeAgente);
    if(!agente) return;
    // Truncar mensagem
    const txt = mensagem.length > 40 ? mensagem.substring(0,37)+'...' : mensagem;
    agente.bubble = new Bubble(txt, agente.x, agente.y);
}

// Interceptar SSE existente
const _origSSEOnMessage = window._pixelOfficeSSEHook;
window._pixelOfficeSSEHook = function(data) {
    const nomeAgente = AGENT_SSE_MAP[data.evento] || AGENT_SSE_MAP[data.tipo];
    if(nomeAgente && data.mensagem) {
        mostrarBolhaAgente(nomeAgente, data.mensagem);
    }
};

window.initPixelOffice = function(){
    cv=document.getElementById('pixelOfficeCanvas');
    if(!cv){ console.warn('[PixelOffice] canvas nao encontrado'); return; }
    if(window._pixelOfficeRAF){ cancelAnimationFrame(window._pixelOfficeRAF); }
    window._pixelOfficeStarted = true;
    cx=cv.getContext('2d');
    console.log('[PixelOffice] iniciando animacao');
    cv.width=W; cv.height=H;
    function resize(){
        const container = document.getElementById('pixelOfficeWrap');
        if(!container) return;
        const maxW = container.clientWidth || 800;
        const s = Math.min(maxW/W, 1);
        cv.style.width=W*s+'px'; cv.style.height=H*s+'px';
    }
    resize();
    window._pixelOfficeResizeHandler = resize;
    window.addEventListener('resize', window._pixelOfficeResizeHandler);
    initObstacles();
    initWaypoints();
    agents=AGENT_DEFS.map((d,i)=>{const a=new Agent(d);a.st=i*1.8;return a;});
    loop();
};
