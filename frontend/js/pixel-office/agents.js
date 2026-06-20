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
    Dev:['Gerando HTML...','Otimizando CSS','Injetando SEO','Renderizando site','Open Design processando...'],
    Designer:['Extraindo cores...','Analisando estilo','Paleta definida!','Tipografia OK','Design aplicado'],
    QA:['Validando site...','Score calculado','Checando mobile','Aprovado! Score 95','Rejeitado, refazendo'],
    Marketing:['Enviando WhatsApp...','Lead contatado!','Mensagem entregue','Franz em acao','Copy personalizada'],
    Hunter:['Buscando leads...','Google Maps aberto','Capturando dados','Lead encontrado!','Scraping em curso'],
    Analista:['Qualificando lead...','Score calculado','Tier A detectado!','Analisando perfil','Caio avaliando'],
    Fotos:['Buscando fotos...','Imagens capturadas','Logo encontrado!','Curadoria processando','Galeria montada'],
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
