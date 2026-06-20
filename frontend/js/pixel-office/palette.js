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
