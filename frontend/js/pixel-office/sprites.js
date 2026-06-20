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
