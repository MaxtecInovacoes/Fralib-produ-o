// ============================================================
// BLOCK 1 — SETUP + PALETA
// ============================================================
// cv e cx declarados globalmente, atribuidos em initPixelOffice
let cv, cx, W=800, H=400;

const P={
    floorA:'#f0ece0', floorB:'#e8e4d8', floorGrid:'#d8d4c8',
    glassWall:'#5b8fa8', glassWallLight:'#7ab0c8', glassWallDark:'#3d6e88',
    glassFrame:'#8ab8cc', glassFill:'rgba(100,170,200,0.18)',
    divWall:'#6a9ab0', divFrame:'#4a7a90',
    deskTop:'#d4a843', deskFront:'#b8882a', deskShadow:'#8a6010',
    bigTop:'#c8922a', bigFront:'#a07018',
    meetTop:'#4a9fd4', meetFront:'#2a7ab0', meetEdge:'#6ab8e8',
    chairSeat:'#e07060', chairBack:'#c05040', chairLeg:'#1a1a2a',
    bossBack:'#0d0820', bossSeat:'#1a1040', bossAccent:'#7f5af0',
    cabinetTop:'#d4a843', cabinetFront:'#b8882a',
    leafDark:'#1b5e20', leafMid:'#2e7d32', leafLight:'#43a047',
    skinA:'#fdbcb4', skinB:'#f0c27f',
    shadow:'rgba(0,0,0,0.18)',
    cafeWall:'#8b6f47', cafeWallLight:'#a08060',
};
function mc(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return[c,c.getContext('2d')];}

// ── DECORAÇÕES EXTRAS ─────────────────────────────────────
function drawFlowerPot(x,y,color='#e91e63'){
    // vaso
    cx.fillStyle='#bf360c';
    cx.beginPath(); cx.moveTo(x+5,y+14); cx.lineTo(x+3,y+22); cx.lineTo(x+17,y+22); cx.lineTo(x+15,y+14); cx.closePath(); cx.fill();
    cx.fillStyle='#d84315'; cx.fillRect(x+4,y+13,12,3);
    cx.fillStyle='#3e2010'; cx.fillRect(x+4,y+13,12,3);
    // flor
    cx.fillStyle=color;
    [[x+10,y+6],[x+6,y+9],[x+14,y+9],[x+8,y+3],[x+12,y+3]].forEach(([fx,fy])=>{
        cx.beginPath(); cx.arc(fx,fy,3,0,Math.PI*2); cx.fill();
    });
    // centro amarelo
    cx.fillStyle='#fdd835'; cx.beginPath(); cx.arc(x+10,y+6,2.5,0,Math.PI*2); cx.fill();
    // caule
    cx.strokeStyle='#2e7d32'; cx.lineWidth=1.5;
    cx.beginPath(); cx.moveTo(x+10,y+14); cx.lineTo(x+10,y+9); cx.stroke();
    // folhinhas
    cx.fillStyle='#388e3c';
    cx.beginPath(); cx.ellipse(x+7,y+12,3,2,-0.5,0,Math.PI*2); cx.fill();
    cx.beginPath(); cx.ellipse(x+13,y+12,3,2,0.5,0,Math.PI*2); cx.fill();
}

function drawTrashBin(x,y){
    cx.fillStyle='#546e7a'; cx.fillRect(x+3,y+8,14,14);
    cx.fillStyle='#455a64'; cx.fillRect(x+3,y+8,14,3);
    cx.fillStyle='#37474f'; cx.fillRect(x+2,y+6,16,4);
    cx.fillStyle='#607d8b'; cx.fillRect(x+9,y+4,2,4);
    cx.strokeStyle='#37474f'; cx.lineWidth=1;
    cx.beginPath(); cx.moveTo(x+7,y+11); cx.lineTo(x+7,y+20); cx.stroke();
    cx.beginPath(); cx.moveTo(x+10,y+11); cx.lineTo(x+10,y+20); cx.stroke();
    cx.beginPath(); cx.moveTo(x+13,y+11); cx.lineTo(x+13,y+20); cx.stroke();
}

function drawClock(x,y){
    cx.fillStyle='#eceff1'; cx.beginPath(); cx.arc(x+10,y+10,9,0,Math.PI*2); cx.fill();
    cx.strokeStyle='#546e7a'; cx.lineWidth=1.5; cx.beginPath(); cx.arc(x+10,y+10,9,0,Math.PI*2); cx.stroke();
    cx.fillStyle='#546e7a'; cx.beginPath(); cx.arc(x+10,y+10,1.5,0,Math.PI*2); cx.fill();
    // ponteiros
    cx.strokeStyle='#263238'; cx.lineWidth=1.5;
    cx.beginPath(); cx.moveTo(x+10,y+10); cx.lineTo(x+10,y+4); cx.stroke();
    cx.lineWidth=2;
    cx.beginPath(); cx.moveTo(x+10,y+10); cx.lineTo(x+15,y+12); cx.stroke();
    // marcações
    cx.fillStyle='#546e7a';
    [[x+10,y+2],[x+10,y+18],[x+2,y+10],[x+18,y+10]].forEach(([mx,my])=>{
        cx.beginPath(); cx.arc(mx,my,1,0,Math.PI*2); cx.fill();
    });
}

function drawRug2(x,y,w,h,c1,c2){
    cx.fillStyle=c1; cx.fillRect(x,y,w,h);
    cx.strokeStyle=c2; cx.lineWidth=2; cx.strokeRect(x+4,y+4,w-8,h-8);
    cx.strokeRect(x+8,y+8,w-16,h-16);
    cx.fillStyle=c2;
    cx.beginPath(); cx.arc(x+w/2,y+h/2,6,0,Math.PI*2); cx.fill();
    cx.fillStyle=c1;
    cx.beginPath(); cx.arc(x+w/2,y+h/2,3,0,Math.PI*2); cx.fill();
    // franjas
    for(let i=8;i<w-4;i+=8){ cx.fillStyle=c2; cx.fillRect(x+i,y,4,3); cx.fillRect(x+i,y+h-3,4,3); }
}

function drawNoticeboard(x,y){
    // moldura
    cx.fillStyle='#5d4037'; cx.fillRect(x,y,60,40);
    cx.fillStyle='#8d6e63'; cx.fillRect(x+2,y+2,56,36);
    // post-its
    cx.fillStyle='#fff176'; cx.fillRect(x+4,y+4,16,14); cx.strokeStyle='#f9a825'; cx.lineWidth=1; cx.strokeRect(x+4,y+4,16,14);
    cx.fillStyle='#80cbc4'; cx.fillRect(x+22,y+4,16,14); cx.strokeStyle='#00897b'; cx.strokeRect(x+22,y+4,16,14);
    cx.fillStyle='#ef9a9a'; cx.fillRect(x+40,y+4,16,14); cx.strokeStyle='#e53935'; cx.strokeRect(x+40,y+4,16,14);
    cx.fillStyle='#a5d6a7'; cx.fillRect(x+4,y+22,16,12); cx.strokeStyle='#388e3c'; cx.strokeRect(x+4,y+22,16,12);
    cx.fillStyle='#ce93d8'; cx.fillRect(x+22,y+22,34,12); cx.strokeStyle='#8e24aa'; cx.strokeRect(x+22,y+22,34,12);
    // texto nos post-its
    cx.fillStyle='#333'; cx.font='4px Arial';
    cx.fillText('TODO',x+5,y+12); cx.fillText('BUG',x+24,y+12); cx.fillText('DONE',x+41,y+12);
    cx.fillText('REVIEW',x+5,y+30); cx.fillText('DEPLOY HOJE!',x+23,y+30);
    // tachinhas
    cx.fillStyle='#e53935';
    [[x+12,y+4],[x+30,y+4],[x+48,y+4],[x+12,y+22],[x+39,y+22]].forEach(([px,py])=>{
        cx.beginPath(); cx.arc(px,py,2,0,Math.PI*2); cx.fill();
    });
}

// ============================================================
// SISTEMA DE COLISÃO — retângulos bloqueados
// ============================================================
// Cada rect: {x,y,w,h} — área que agentes NÃO podem entrar
// Definidos depois que as constantes de layout existirem
let OBSTACLES=[];
let ROOM_BOUNDS={}; // limites de cada sala para restringir agentes

// Waypoints de navegação — pontos seguros para contornar obstáculos
// Definidos depois do layout
let NAV_WAYPOINTS=[];

function rectOverlap(ax,ay,aw,ah,bx,by,bw,bh){
    return ax<bx+bw && ax+aw>bx && ay<by+bh && ay+ah>by;
}

function agentCollides(x,y,obstacles){
    const aw=14, ah=16; // hitbox do agente (menor que o sprite)
    for(const o of obstacles){
        if(rectOverlap(x-aw/2,y-ah/2,aw,ah,o.x,o.y,o.w,o.h)) return true;
    }
    return false;
}

// Encontra caminho simples: tenta ir direto, se colidir usa waypoint intermediário
function findPath(fromX,fromY,toX,toY,agentRole){
    // Waypoints disponíveis para navegação
    const wps = NAV_WAYPOINTS.filter(wp=>{
        if(wp.onlyRole && wp.onlyRole!==agentRole) return false;
        if(wp.excludeRole && wp.excludeRole===agentRole) return false;
        return true;
    });

    // Tenta caminho direto
    const steps=10;
    let blocked=false;
    for(let i=1;i<=steps;i++){
        const ix=fromX+(toX-fromX)*(i/steps);
        const iy=fromY+(toY-fromY)*(i/steps);
        if(agentCollides(ix,iy,OBSTACLES)){blocked=true;break;}
    }
    if(!blocked) return [toX,toY];

    // Encontra waypoint mais próximo do destino que não colide
    let best=null, bestDist=Infinity;
    for(const wp of wps){
        if(agentCollides(wp.x,wp.y,OBSTACLES)) continue;
        const d=Math.hypot(wp.x-toX,wp.y-toY);
        if(d<bestDist){bestDist=d;best=wp;}
    }
    if(best) return [best.x,best.y];
    return [toX,toY];
}
// ============================================================
// BLOCK 2 — SPRITES
// ============================================================
const Sprites={
floor(){
    const[c,x]=mc(32,32);
    x.fillStyle=P.floorA; x.fillRect(0,0,32,32);
    x.fillStyle=P.floorB; x.fillRect(0,0,16,16); x.fillRect(16,16,16,16);
    x.strokeStyle=P.floorGrid; x.lineWidth=0.5; x.strokeRect(0,0,32,32);
    return c;
},
desk(){
    const[c,x]=mc(54,36);
    x.fillStyle=P.shadow; x.fillRect(5,32,50,4);
    x.fillStyle=P.deskFront; x.fillRect(2,26,50,8);
    x.fillStyle='rgba(0,0,0,0.2)'; x.fillRect(2,32,50,2);
    x.fillStyle=P.deskTop; x.fillRect(2,6,50,22);
    x.fillStyle='rgba(255,255,255,0.22)'; x.fillRect(3,7,46,5);
    x.strokeStyle=P.deskShadow; x.lineWidth=1.5; x.strokeRect(2,6,50,22);
    x.fillStyle=P.deskShadow; x.fillRect(4,28,6,8); x.fillRect(44,28,6,8);
    return c;
},
bigDesk(){
    const[c,x]=mc(76,44);
    x.fillStyle=P.shadow; x.fillRect(5,40,72,4);
    x.fillStyle=P.bigFront; x.fillRect(2,34,72,8);
    x.fillStyle='rgba(0,0,0,0.2)'; x.fillRect(2,40,72,2);
    x.fillStyle=P.bigTop; x.fillRect(2,8,72,28);
    x.fillStyle='rgba(255,255,255,0.18)'; x.fillRect(3,9,68,6);
    x.strokeStyle=P.bigFront; x.lineWidth=2; x.strokeRect(2,8,72,28);
    x.fillStyle='rgba(0,0,0,0.08)';
    for(let i=0;i<4;i++) x.fillRect(4+i*18,10,12,24);
    x.fillStyle=P.bigFront; x.fillRect(4,36,10,8); x.fillRect(62,36,10,8);
    return c;
},
cabinet(){
    const[c,x]=mc(40,52);
    x.fillStyle=P.shadow; x.fillRect(4,48,38,4);
    x.fillStyle=P.cabinetFront; x.fillRect(2,38,38,12);
    x.fillStyle='rgba(0,0,0,0.2)'; x.fillRect(2,48,38,2);
    x.fillStyle=P.cabinetTop; x.fillRect(2,4,38,36);
    x.fillStyle='rgba(255,255,255,0.18)'; x.fillRect(3,5,36,6);
    x.strokeStyle=P.cabinetFront; x.lineWidth=2; x.strokeRect(2,4,38,36);
    x.fillStyle=P.cabinetFront; x.fillRect(2,22,38,3);
    x.fillStyle='#888'; x.fillRect(17,14,6,3); x.fillRect(17,28,6,3);
    return c;
},
computer(){
    const[c,x]=mc(26,20);
    x.fillStyle='#2a2a3e'; x.fillRect(10,16,6,3); x.fillRect(7,18,12,2);
    x.fillStyle='#1a1a2e'; x.fillRect(2,2,22,14);
    const g=x.createLinearGradient(3,3,3,15);
    g.addColorStop(0,'#0a1628'); g.addColorStop(1,'#0d2040');
    x.fillStyle=g; x.fillRect(3,3,20,12);
    x.fillStyle='#0183ff'; x.fillRect(4,4,18,2);
    x.fillStyle='rgba(1,131,255,0.5)'; x.fillRect(4,7,12,1); x.fillRect(4,9,16,1); x.fillRect(4,11,10,1);
    x.fillStyle='#16c784'; x.fillRect(16,9,5,1);
    x.fillStyle='rgba(255,255,255,0.07)'; x.fillRect(3,3,8,5);
    x.fillStyle='#2a2a3e'; x.fillRect(4,17,18,2);
    return c;
},
chair(){
    const[c,x]=mc(28,30);
    x.fillStyle=P.shadow; x.fillRect(4,26,22,4);
    x.fillStyle=P.chairLeg;
    x.beginPath(); x.moveTo(14,22); x.lineTo(4,27); x.lineTo(6,27); x.lineTo(14,23); x.lineTo(22,27); x.lineTo(24,27); x.closePath(); x.fill();
    [[4,27],[24,27],[14,28]].forEach(([rx,ry])=>{x.fillStyle='#111';x.beginPath();x.arc(rx,ry,2,0,Math.PI*2);x.fill();});
    x.fillStyle=P.chairSeat; x.beginPath(); x.roundRect(3,14,22,10,3); x.fill();
    x.fillStyle='rgba(255,255,255,0.2)'; x.fillRect(4,15,20,3);
    x.fillStyle=P.chairBack; x.beginPath(); x.roundRect(4,3,20,13,3); x.fill();
    x.fillStyle='rgba(255,255,255,0.15)'; x.fillRect(5,4,18,5);
    return c;
},
bossChair(){
    const[c,x]=mc(32,34);
    x.fillStyle=P.shadow; x.fillRect(4,30,26,4);
    x.fillStyle='#111';
    x.beginPath(); x.moveTo(16,24); x.lineTo(5,30); x.lineTo(7,30); x.lineTo(16,25); x.lineTo(25,30); x.lineTo(27,30); x.closePath(); x.fill();
    [[5,30],[27,30],[16,31]].forEach(([rx,ry])=>{x.fillStyle='#0a0a0a';x.beginPath();x.arc(rx,ry,2,0,Math.PI*2);x.fill();});
    x.fillStyle=P.bossSeat; x.beginPath(); x.roundRect(3,18,26,9,3); x.fill();
    x.fillStyle=P.bossAccent; x.fillRect(4,19,24,3);
    x.fillStyle=P.bossBack; x.beginPath(); x.roundRect(4,2,24,18,3); x.fill();
    x.fillStyle=P.bossAccent; x.fillRect(5,3,22,4);
    x.fillStyle='rgba(127,90,240,0.2)'; x.fillRect(5,8,22,10);
    x.fillStyle='#1a1040'; x.fillRect(1,16,5,8); x.fillRect(26,16,5,8);
    return c;
},
// Mesa reunião — sem cadeiras embutidas
meetTable(){
    const[c,x]=mc(140,60);
    x.fillStyle=P.shadow; x.fillRect(8,56,130,4);
    x.fillStyle=P.meetFront; x.fillRect(4,46,132,12);
    x.fillStyle='rgba(0,0,0,0.25)'; x.fillRect(4,56,132,2);
    x.fillStyle=P.meetTop; x.fillRect(4,8,132,40);
    const g=x.createLinearGradient(4,8,4,48);
    g.addColorStop(0,'rgba(255,255,255,0.2)'); g.addColorStop(1,'rgba(0,0,0,0.1)');
    x.fillStyle=g; x.fillRect(4,8,132,40);
    x.strokeStyle=P.meetEdge; x.lineWidth=2; x.strokeRect(4,8,132,40);
    x.fillStyle=P.meetFront; x.fillRect(6,48,14,12); x.fillRect(120,48,14,12);
    return c;
},
meetChairTop(){
    // cadeira virada para baixo (sentada do lado de cima da mesa)
    const[c,x]=mc(24,20);
    x.fillStyle=P.chairBack; x.fillRect(1,0,22,8);
    x.fillStyle='rgba(255,255,255,0.12)'; x.fillRect(2,1,20,3);
    x.fillStyle=P.chairSeat; x.fillRect(1,8,22,12);
    x.fillStyle='rgba(255,255,255,0.15)'; x.fillRect(2,9,20,4);
    return c;
},
meetChairBottom(){
    // cadeira virada para cima (sentada do lado de baixo da mesa)
    const[c,x]=mc(24,20);
    x.fillStyle=P.chairSeat; x.fillRect(1,0,22,12);
    x.fillStyle='rgba(255,255,255,0.15)'; x.fillRect(2,1,20,4);
    x.fillStyle=P.chairBack; x.fillRect(1,12,22,8);
    x.fillStyle='rgba(255,255,255,0.12)'; x.fillRect(2,13,20,3);
    return c;
},
plant(){
    const[c,x]=mc(28,34);
    x.fillStyle=P.shadow; x.beginPath(); x.ellipse(14,33,10,3,0,0,Math.PI*2); x.fill();
    x.fillStyle='#8d3a1a';
    x.beginPath(); x.moveTo(9,22); x.lineTo(6,32); x.lineTo(22,32); x.lineTo(19,22); x.closePath(); x.fill();
    x.fillStyle='#a04020'; x.fillRect(7,21,14,3);
    x.fillStyle='#3e2010'; x.fillRect(7,21,14,4);
    x.fillStyle=P.leafDark;
    x.beginPath(); x.ellipse(10,14,5,8,-0.3,0,Math.PI*2); x.fill();
    x.beginPath(); x.ellipse(18,14,5,8,0.3,0,Math.PI*2); x.fill();
    x.fillStyle=P.leafMid;
    x.beginPath(); x.ellipse(14,12,6,9,0,0,Math.PI*2); x.fill();
    x.beginPath(); x.ellipse(9,16,4,6,-0.5,0,Math.PI*2); x.fill();
    x.beginPath(); x.ellipse(19,16,4,6,0.5,0,Math.PI*2); x.fill();
    x.fillStyle=P.leafLight;
    x.beginPath(); x.ellipse(14,10,4,6,0,0,Math.PI*2); x.fill();
    x.strokeStyle='rgba(0,80,0,0.3)'; x.lineWidth=1;
    x.beginPath(); x.moveTo(14,20); x.lineTo(14,10); x.stroke();
    return c;
},
smallPlant(){
    const[c,x]=mc(20,24);
    x.fillStyle=P.shadow; x.beginPath(); x.ellipse(10,23,7,2,0,0,Math.PI*2); x.fill();
    x.fillStyle='#bf360c';
    x.beginPath(); x.moveTo(7,16); x.lineTo(5,22); x.lineTo(15,22); x.lineTo(13,16); x.closePath(); x.fill();
    x.fillStyle='#3e2010'; x.fillRect(6,15,8,3);
    x.fillStyle=P.leafMid;
    x.beginPath(); x.ellipse(10,10,5,7,0,0,Math.PI*2); x.fill();
    x.fillStyle=P.leafLight;
    x.beginPath(); x.ellipse(10,8,3,5,0,0,Math.PI*2); x.fill();
    return c;
},
whiteboard(){
    const[c,x]=mc(72,48);
    x.fillStyle='#455a64'; x.fillRect(0,4,72,40);
    x.fillStyle='#37474f'; x.fillRect(0,4,72,5); x.fillRect(0,40,72,4);
    x.fillStyle='#fafafa'; x.fillRect(3,9,66,31);
    x.strokeStyle='#1565c0'; x.lineWidth=1.5;
    x.beginPath(); x.moveTo(8,16); x.lineTo(26,16); x.lineTo(26,28); x.lineTo(44,28); x.stroke();
    x.strokeStyle='#c62828'; x.beginPath(); x.arc(22,34,5,0,Math.PI*2); x.stroke();
    x.strokeStyle='#2e7d32'; x.beginPath(); x.arc(48,20,4,0,Math.PI*2); x.stroke();
    x.fillStyle='#1565c0'; x.font='bold 6px Arial'; x.fillText('SPRINT',50,32);
    x.fillStyle='rgba(255,255,255,0.15)'; x.fillRect(3,9,22,12);
    x.fillStyle='#546e7a'; x.fillRect(3,42,66,4);
    return c;
},
sofa(){
    const[c,x]=mc(88,42);
    x.fillStyle=P.shadow; x.fillRect(4,39,82,3);
    x.fillStyle='#1a237e'; x.fillRect(6,16,76,22);
    x.fillStyle='#283593'; x.fillRect(6,4,76,16);
    x.fillStyle='rgba(255,255,255,0.07)'; x.fillRect(6,4,76,5);
    x.fillStyle='#1a237e'; x.fillRect(2,6,6,30); x.fillRect(80,6,6,30);
    x.fillStyle='#3949ab'; x.beginPath(); x.roundRect(10,6,28,14,3); x.fill();
    x.beginPath(); x.roundRect(50,6,28,14,3); x.fill();
    x.fillStyle='rgba(255,255,255,0.12)'; x.fillRect(11,7,26,5); x.fillRect(51,7,26,5);
    x.fillStyle='#283593'; x.fillRect(8,20,72,16);
    x.fillStyle='#111'; x.fillRect(8,36,10,5); x.fillRect(70,36,10,5);
    return c;
},
coffeeTable(){
    const[c,x]=mc(56,30);
    x.fillStyle=P.shadow; x.fillRect(4,27,52,3);
    x.fillStyle='#5d4037'; x.fillRect(2,18,52,10);
    x.fillStyle='#795548'; x.fillRect(2,8,52,12);
    x.fillStyle='rgba(255,255,255,0.1)'; x.fillRect(3,9,50,4);
    x.strokeStyle='#4e342e'; x.lineWidth=1.5; x.strokeRect(2,8,52,12);
    x.fillStyle='#4e342e'; x.fillRect(4,20,8,8); x.fillRect(44,20,8,8);
    x.fillStyle='#e3f2fd'; x.fillRect(8,9,16,10);
    x.fillStyle='#1565c0'; x.fillRect(8,9,16,3);
    x.fillStyle='#fff'; x.fillRect(34,10,10,7);
    x.fillStyle='#6d4c41'; x.fillRect(35,11,8,5);
    return c;
},
coffee(){
    const[c,x]=mc(32,42);
    x.fillStyle='#1e2d3d'; x.fillRect(4,6,24,30);
    x.beginPath(); x.arc(16,6,12,Math.PI,0); x.fill();
    x.fillStyle='#0d1f2d'; x.fillRect(6,12,20,10);
    x.fillStyle='#1b5e20'; x.fillRect(7,13,18,4);
    x.fillStyle='#a5d6a7'; x.font='5px monospace'; x.fillText('READY',9,17);
    x.fillStyle='#e53935'; x.beginPath(); x.arc(10,26,3,0,Math.PI*2); x.fill();
    x.fillStyle='#1e88e5'; x.beginPath(); x.arc(22,26,3,0,Math.PI*2); x.fill();
    x.fillStyle='#90a4ae'; x.fillRect(12,36,8,4);
    x.fillStyle='#eceff1'; x.fillRect(10,38,12,4);
    x.strokeStyle='rgba(200,220,255,0.4)'; x.lineWidth=1.5;
    x.beginPath(); x.moveTo(14,37); x.quadraticCurveTo(12,33,14,30); x.stroke();
    x.beginPath(); x.moveTo(18,37); x.quadraticCurveTo(20,33,18,30); x.stroke();
    return c;
},
fridge(){
    const[c,x]=mc(28,40);
    x.fillStyle=P.shadow; x.fillRect(2,37,24,3);
    x.fillStyle='#cfd8dc'; x.fillRect(3,2,22,36);
    x.fillStyle='#b0bec5'; x.fillRect(3,2,22,4);
    x.strokeStyle='#90a4ae'; x.lineWidth=1.5;
    x.strokeRect(4,5,20,14); x.strokeRect(4,21,20,15);
    x.fillStyle='#78909c'; x.fillRect(22,10,2,6); x.fillRect(22,26,2,8);
    x.fillStyle='#ef5350'; x.fillRect(7,24,5,4);
    x.fillStyle='#42a5f5'; x.fillRect(15,26,5,4);
    x.fillStyle='rgba(255,255,255,0.3)'; x.fillRect(4,5,7,7);
    return c;
},
painting(type=0){
    const[c,x]=mc(38,30);
    x.fillStyle='#4e342e'; x.fillRect(0,0,38,30);
    x.fillStyle='#6d4c41'; x.fillRect(1,1,36,28);
    x.fillStyle='#3e2723'; x.fillRect(0,0,38,3); x.fillRect(0,27,38,3); x.fillRect(0,0,3,30); x.fillRect(35,0,3,30);
    if(type===0){
        x.fillStyle='#1a237e'; x.fillRect(3,3,32,24);
        x.fillStyle='#42a5f5'; x.fillRect(6,18,5,9); x.fillRect(13,13,5,14); x.fillRect(20,9,5,18); x.fillRect(27,5,5,22);
        x.fillStyle='rgba(255,255,255,0.15)'; x.fillRect(3,3,32,5);
        x.fillStyle='#fff'; x.font='bold 5px Arial'; x.fillText('GROWTH',5,11);
    } else if(type===1){
        x.fillStyle='#f3e5f5'; x.fillRect(3,3,32,24);
        x.fillStyle='#7b1fa2'; x.beginPath(); x.arc(19,15,9,0,Math.PI*2); x.fill();
        x.fillStyle='#fff'; x.font='bold 9px Arial'; x.fillText('F',16,19);
        x.fillStyle='#7b1fa2'; x.font='bold 5px Arial'; x.fillText('FRALIB',7,25);
    } else {
        x.fillStyle='#e8f5e9'; x.fillRect(3,3,32,24);
        x.fillStyle='#2e7d32'; x.fillRect(3,18,32,9);
        [[9,14],[16,13],[23,15],[30,13]].forEach(([px,py])=>{
            x.fillStyle='#fdbcb4'; x.beginPath(); x.arc(px,py,3,0,Math.PI*2); x.fill();
            x.fillStyle='#555'; x.fillRect(px-3,py+3,6,5);
        });
    }
    return c;
},
};
// ============================================================
// BLOCK 3 — PERSONAGENS 32x40
// ============================================================
function makeChar(bodyColor,role,female){
    const hairMap={CEO_F:'#6d1b7b',CEO:'#1a1a1a',Dev:'#1a237e',Designer:'#9c27b0',QA:'#1b5e20',Auditora:'#b71c1c',Marketing:'#e65100',Hunter:'#064e3b',Analista:'#4c1d95',Fotos:'#78350f',SEO:'#064e3b'};
    const hairKey=(female&&role==='CEO')?'CEO_F':role;
    const hair=hairMap[hairKey]||'#2c3e50';
    const skin=female?P.skinA:P.skinB;
    const frames=[];
    for(let f=0;f<4;f++){
        const[c,x]=mc(32,40);
        const leg=f===0?-2:f===2?2:0;
        const arm=f===0?2:f===2?-2:0;
        const bob=f===1?-1:0;
        x.fillStyle='rgba(0,0,0,0.2)'; x.beginPath(); x.ellipse(16,39,10,3,0,0,Math.PI*2); x.fill();
        if(female){
            x.fillStyle='#e91e63';
            x.beginPath(); x.moveTo(8,25); x.lineTo(5,33); x.lineTo(27,33); x.lineTo(24,25); x.closePath(); x.fill();
            x.fillStyle='rgba(255,255,255,0.15)'; x.fillRect(9,25,7,6);
            x.fillStyle=skin; x.fillRect(9,32,5,6+leg); x.fillRect(18,32,5,6-leg);
            x.fillStyle='#880e4f'; x.fillRect(8,37+leg,7,3); x.fillRect(17,37-leg,7,3);
        } else {
            x.fillStyle='#263238'; x.fillRect(9,25,5,13+leg); x.fillRect(18,25,5,13-leg);
            x.fillStyle='#111'; x.fillRect(8,37+leg,7,3); x.fillRect(17,37-leg,7,3);
        }
        x.fillStyle=bodyColor; x.beginPath(); x.roundRect(6,14,20,13,3); x.fill();
        x.fillStyle='rgba(255,255,255,0.18)'; x.fillRect(7,15,18,4);
        x.fillStyle='rgba(0,0,0,0.15)'; x.fillRect(7,25,18,2);
        x.fillStyle='rgba(255,255,255,0.3)';
        x.beginPath(); x.arc(16,18,1,0,Math.PI*2); x.fill();
        x.beginPath(); x.arc(16,21,1,0,Math.PI*2); x.fill();
        x.fillStyle=bodyColor;
        x.beginPath(); x.roundRect(2,15+arm,5,10,2); x.fill();
        x.beginPath(); x.roundRect(25,15-arm,5,10,2); x.fill();
        x.fillStyle=skin;
        x.beginPath(); x.arc(4,25+arm,3,0,Math.PI*2); x.fill();
        x.beginPath(); x.arc(28,25-arm,3,0,Math.PI*2); x.fill();
        x.fillStyle=skin; x.fillRect(13,10+bob,6,5);
        x.fillStyle=skin; x.beginPath(); x.arc(16,8+bob,7,0,Math.PI*2); x.fill();
        x.fillStyle='rgba(255,150,150,0.25)';
        x.beginPath(); x.arc(11,10+bob,3,0,Math.PI*2); x.fill();
        x.beginPath(); x.arc(21,10+bob,3,0,Math.PI*2); x.fill();
        x.fillStyle=hair;
        if(female){
            x.beginPath(); x.arc(16,6+bob,7,Math.PI,Math.PI*2); x.fill();
            x.fillRect(9,5+bob,4,12); x.fillRect(19,5+bob,4,12);
            x.fillRect(10,2+bob,12,4);
        } else {
            x.beginPath(); x.arc(16,5+bob,7,Math.PI,Math.PI*2); x.fill();
        }
        x.fillStyle=hair; x.fillRect(10,4+bob,5,1.5); x.fillRect(17,4+bob,5,1.5);
        x.fillStyle='#fff';
        x.beginPath(); x.ellipse(12,7+bob,3,2.5,0,0,Math.PI*2); x.fill();
        x.beginPath(); x.ellipse(20,7+bob,3,2.5,0,0,Math.PI*2); x.fill();
        x.fillStyle=female?'#5c35a0':'#1a5276';
        x.beginPath(); x.arc(12,7+bob,2,0,Math.PI*2); x.fill();
        x.beginPath(); x.arc(20,7+bob,2,0,Math.PI*2); x.fill();
        x.fillStyle='#111';
        x.beginPath(); x.arc(12,7+bob,1,0,Math.PI*2); x.fill();
        x.beginPath(); x.arc(20,7+bob,1,0,Math.PI*2); x.fill();
        x.fillStyle='rgba(255,255,255,0.9)'; x.fillRect(13,6+bob,1,1); x.fillRect(21,6+bob,1,1);
        x.fillStyle='rgba(0,0,0,0.12)'; x.beginPath(); x.arc(16,10+bob,1,0,Math.PI*2); x.fill();
        if(female){ x.fillStyle='#e91e63'; x.beginPath(); x.arc(16,12+bob,2.5,0.1,Math.PI-0.1); x.fill(); }
        else { x.strokeStyle='#c0392b'; x.lineWidth=1.2; x.beginPath(); x.arc(16,12+bob,2.5,0.1,Math.PI-0.1); x.stroke(); }
        if(role==='CEO'&&!female){ x.fillStyle='#c0392b'; x.fillRect(15,15,3,10); x.fillRect(13,15,6,3); x.fillStyle='#922b21'; x.fillRect(15,23,3,2); x.fillStyle='#fff'; x.fillRect(12,14,4,3); x.fillRect(16,14,4,3); }
        if(role==='CEO'&&female){ x.fillStyle='#e91e63'; x.fillRect(15,15,3,8); x.fillRect(13,15,6,3); x.fillStyle='#fff'; x.fillRect(12,14,4,3); x.fillRect(16,14,4,3); }
        if(role==='Dev'){ x.strokeStyle='#263238'; x.lineWidth=3; x.beginPath(); x.arc(16,7+bob,9,Math.PI*0.7,Math.PI*0.3); x.stroke(); x.fillStyle='#37474f'; x.fillRect(7,7+bob,5,6); x.fillRect(20,7+bob,5,6); x.fillStyle='#0183ff'; x.fillRect(8,8+bob,3,4); x.fillRect(21,8+bob,3,4); }
        if(role==='Designer'){ x.fillStyle='#ecf0f1'; x.fillRect(0,22,7,10); x.fillStyle='#0183ff'; x.fillRect(1,23,5,8); x.strokeStyle='#bbb'; x.lineWidth=1; x.strokeRect(0,22,7,10); }
        if(role==='QA'||role==='Auditora'){ x.strokeStyle='#333'; x.lineWidth=1.5; x.strokeRect(9,5+bob,6,5); x.strokeRect(17,5+bob,6,5); x.beginPath(); x.moveTo(15,7+bob); x.lineTo(17,7+bob); x.stroke(); x.fillStyle='rgba(100,180,255,0.15)'; x.fillRect(9,5+bob,6,5); x.fillRect(17,5+bob,6,5); }
        if(role==='Marketing'){ x.fillStyle='#ff6f00'; x.fillRect(9,0+bob,14,6); x.fillStyle='#e65100'; x.fillRect(9,0+bob,14,2); x.fillStyle='#ff6f00'; x.fillRect(6,5+bob,6,3); x.fillStyle='#fff'; x.font='bold 4px Arial'; x.fillText('MKT',11,5+bob); }
        frames.push(c);
    }
    return frames;
}
// ============================================================
// BLOCK 4 — BUBBLE + AGENT COM COLISÃO E WAYPOINTS
// ============================================================
class Bubble{
    constructor(text,x,y){this.text=text;this.x=x;this.y=y;this.life=5;this.t=0;this.alpha=0;}
    update(dt){
        this.t+=dt;
        if(this.t<0.25) this.alpha=this.t/0.25;
        else if(this.t>this.life-0.5) this.alpha=Math.max(0,(this.life-this.t)/0.5);
        else this.alpha=1;
        return this.t>=this.life;
    }
    draw(ctx){
        ctx.save(); ctx.globalAlpha=this.alpha;
        ctx.font='bold 11px Arial,sans-serif';
        const pad=8,maxW=160,lh=15;
        const words=this.text.split(' '); const lines=[]; let cur='';
        for(const w of words){const t=cur?cur+' '+w:w;if(ctx.measureText(t).width>maxW-pad*2){if(cur)lines.push(cur);cur=w;}else cur=t;}
        if(cur) lines.push(cur);
        const bw=Math.max(...lines.map(l=>ctx.measureText(l).width))+pad*2;
        const bh=lines.length*lh+pad*2;
        let bx=this.x-bw/2,by=this.y-bh-62;
        bx=Math.max(4,Math.min(bx,W-bw-4)); by=Math.max(4,by);
        // sombra
        ctx.fillStyle='rgba(0,0,0,0.18)'; ctx.beginPath(); ctx.roundRect(bx+2,by+2,bw,bh,10); ctx.fill();
        // fundo branco
        ctx.fillStyle='#ffffff'; ctx.strokeStyle='rgba(100,100,120,0.35)'; ctx.lineWidth=1.5;
        ctx.beginPath(); ctx.roundRect(bx,by,bw,bh,10); ctx.fill(); ctx.stroke();
        // rabinho
        ctx.fillStyle='#ffffff';
        ctx.beginPath(); ctx.moveTo(this.x-5,by+bh); ctx.lineTo(this.x,by+bh+9); ctx.lineTo(this.x+5,by+bh); ctx.closePath(); ctx.fill();
        ctx.strokeStyle='rgba(100,100,120,0.35)'; ctx.lineWidth=1.5;
        ctx.beginPath(); ctx.moveTo(this.x-5,by+bh); ctx.lineTo(this.x,by+bh+9); ctx.lineTo(this.x+5,by+bh); ctx.stroke();
        // texto escuro
        ctx.fillStyle='#1a1a2e'; ctx.textAlign='left';
        lines.forEach((l,i)=>ctx.fillText(l,bx+pad,by+pad+lh*(i+1)+2));
        ctx.restore();
    }
}

const WORK_DLG={
    Dev:['Gerando HTML...','Otimizando CSS','Injetando SEO','Renderizando site','Liam processando...'],
    Designer:['Extraindo cores...','Analisando estilo','Paleta definida!','Tipografia OK','Design aplicado'],
    QA:['Validando site...','Score calculado','Checando mobile','Aprovado! Score 95','Rejeitado, refazendo'],
    Marketing:['Enviando WhatsApp...','Lead contatado!','Mensagem entregue','Bryan em acao','Copy personalizado'],
    Hunter:['Buscando leads...','Google Maps aberto','Capturando dados','Lead encontrado!','Scraping em curso'],
    Analista:['Qualificando lead...','Score calculado','Tier A detectado!','Analisando perfil','Caio avaliando'],
    Fotos:['Buscando fotos...','Imagens capturadas','Logo encontrado!','Alex processando','Galeria montada'],
    SEO:['Otimizando SEO...','Meta tags OK','Keywords inseridas','Franz analisando','Ranking melhorou'],
    CEO:['Analisando KPIs','Revisando roadmap','Preparando pitch','Checando metricas','Estrategia Q2'],
};

class Agent{
    constructor(def){
        this.name=def.name; this.role=def.role; this.female=def.female;
        this.homeX=def.homeX; this.homeY=def.homeY;
        this.x=def.homeX; this.y=def.homeY;
        this.path=[]; // fila de waypoints
        this.spd=50+Math.random()*20;
        this.frames=makeChar(def.color,def.role,def.female);
        this.fr=0; this.ft=0; this.fd=0.13;
        this.state='working'; this.st=0; this.sd=6+Math.random()*10;
        this.bubble=null; this.ge=null; this.gt=0; this.gd=0; this.gdlg=[]; this.dlt=Math.random()*3;
        this.moving=false;
        // salas permitidas
        this.allowedRooms=def.allowedRooms||['main'];
    }

    // Navega para destino usando waypoints para contornar obstáculos
    navigateTo(tx,ty){
        // Verifica se destino está em sala permitida
        const inCEO = tx>=ROOM_X && ty<200;
        const inAudit = tx>=ROOM_X && ty>=200;
        if(inCEO && !this.allowedRooms.includes('ceo')) {
            // Redireciona para perto da porta CEO
            tx=ROOM_X-20; ty=95;
        }
        if(inAudit && !this.allowedRooms.includes('audit')) {
            tx=ROOM_X-20; ty=295;
        }

        // Tenta caminho direto
        const steps=12;
        let blocked=false;
        for(let i=1;i<=steps;i++){
            const ix=this.x+(tx-this.x)*(i/steps);
            const iy=this.y+(ty-this.y)*(i/steps);
            if(agentCollides(ix,iy,OBSTACLES)){blocked=true;break;}
        }

        if(!blocked){
            this.path=[{x:tx,y:ty}];
            return;
        }

        // Encontra waypoints intermediários
        const wp=NAV_WAYPOINTS
            .filter(w=>!agentCollides(w.x,w.y,OBSTACLES))
            .sort((a,b)=>Math.hypot(a.x-tx,a.y-ty)-Math.hypot(b.x-tx,b.y-ty));

        if(wp.length>0){
            this.path=[{x:wp[0].x,y:wp[0].y},{x:tx,y:ty}];
        } else {
            this.path=[{x:tx,y:ty}];
        }
    }

    go(tx,ty){ this.navigateTo(tx,ty); }
    say(t){ this.bubble=new Bubble(t,this.x,this.y); }

    startEv(ev,pos){
        this.ge=ev.id; this.gd=ev.duration(); this.gt=0;
        this.gdlg=ev.dialogues; this.dlt=Math.random()*2; this.state=ev.id;
        const tx=pos.x+(Math.random()-.5)*ev.spread;
        const ty=pos.y+(Math.random()-.5)*ev.spread*.5;
        this.navigateTo(tx,ty);
    }
    endEv(){ this.ge=null; this.state='working'; this.navigateTo(this.homeX,this.homeY); }

    update(dt){
        if(this.ge){
            this.gt+=dt; this.dlt-=dt;
            if(this.dlt<=0){this.dlt=2.5+Math.random()*3.5;if(Math.random()<.55)this.say(this.gdlg[Math.floor(Math.random()*this.gdlg.length)]);}
            if(this.gt>=this.gd) this.endEv();
        } else {
            this.st+=dt;
            if(this.st>=this.sd){
                this.st=0; this.sd=5+Math.random()*12;
                if(Math.random()<.15){
                    this.state='walking';
                    // Caminhada aleatória dentro da área principal
                    const tx=30+Math.random()*520;
                    const ty=30+Math.random()*340;
                    this.navigateTo(tx,ty);
                } else {
                    this.state='working';
                    this.navigateTo(this.homeX+(Math.random()-.5)*8,this.homeY+(Math.random()-.5)*8);
                    if(Math.random()<.3){const d=WORK_DLG[this.role]||['...'];this.say(d[Math.floor(Math.random()*d.length)]);}
                }
            }
        }

        // Seguir path
        if(this.path.length>0){
            const target=this.path[0];
            const dx=target.x-this.x, dy=target.y-this.y;
            const dist=Math.sqrt(dx*dx+dy*dy);
            this.moving=dist>3;
            if(dist<4){
                this.path.shift(); // chegou neste waypoint, vai pro próximo
            } else {
                const mv=this.spd*dt;
                const nx=this.x+dx/dist*Math.min(mv,dist);
                const ny=this.y+dy/dist*Math.min(mv,dist);
                // Só move se não colidir
                if(!agentCollides(nx,ny,OBSTACLES)){
                    this.x=nx; this.y=ny;
                } else {
                    // Tenta desviar lateralmente
                    const side=Math.random()<0.5?1:-1;
                    const sx=this.x+(-dy/dist)*side*this.spd*dt*0.8;
                    const sy=this.y+(dx/dist)*side*this.spd*dt*0.8;
                    if(!agentCollides(sx,sy,OBSTACLES)){this.x=sx;this.y=sy;}
                    else this.path.shift(); // desiste deste waypoint
                }
            }
        } else {
            this.moving=false;
        }

        // Animação
        if(this.moving){this.ft+=dt;if(this.ft>=this.fd){this.ft=0;this.fr=(this.fr+1)%4;}}else this.fr=1;
        if(this.bubble){this.bubble.x=this.x;this.bubble.y=this.y;if(this.bubble.update(dt))this.bubble=null;}
    }

    draw(ctx){
        ctx.drawImage(this.frames[this.fr],this.x-16,this.y-32);
        ctx.font='bold 9px Arial,sans-serif'; ctx.textAlign='center';
        const tw=ctx.measureText(this.name).width;
        ctx.fillStyle='rgba(0,0,20,0.85)'; ctx.fillRect(this.x-tw/2-5,this.y-46,tw+10,14);
        ctx.strokeStyle='#0183ff'; ctx.lineWidth=1; ctx.strokeRect(this.x-tw/2-5,this.y-46,tw+10,14);
        ctx.fillStyle='#7dd3fc'; ctx.fillText(this.name,this.x,this.y-35);
        ctx.textAlign='left';
        if(this.bubble) this.bubble.draw(ctx);
    }
}
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
    {x:70, y:50,  owner:'Liam'},
    {x:190,y:50,  owner:'Theo'},
    {x:70, y:180, owner:'Liz'},
    {x:190,y:180, owner:'Bryan'},
    {x:430,y:50,  owner:'Alex'},
    {x:430,y:180, owner:'Hunter'},
    {x:500,y:50,  owner:'Caio'},
];

const AGENT_DEFS=[
    {name:'Liam',   role:'Dev',       color:'#3730a3',female:false,homeX:97, homeY:83, allowedRooms:['main']},
    {name:'Theo',   role:'Designer',  color:'#7e22ce',female:false,homeX:217,homeY:83, allowedRooms:['main']},
    {name:'Liz',    role:'QA',        color:'#92400e',female:true, homeX:97, homeY:213,allowedRooms:['main']},
    {name:'Bryan',  role:'Marketing', color:'#7c2d12',female:false,homeX:217,homeY:213,allowedRooms:['main']},
    {name:'Alex',   role:'Fotos',     color:'#b45309',female:false,homeX:457,homeY:83, allowedRooms:['main']},
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
    'pipeline':'Liam',
    'PIPELINE_STATUS':'Liam',
    'SUCCESS': 'Liz',
    'ERROR':   'Liz',
    'WARNING': 'Bryan',
    'INFO':    'Theo',
};

function mostrarBolhaAgente(nomeAgente, mensagem) {
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

