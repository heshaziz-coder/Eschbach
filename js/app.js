(() => {
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const root = document.documentElement;

/* ---------------- Data ---------------- */
const COLL = [
  {id:'loft', name:'Loft', finish:'concrete', url:'https://eschbach-design.com/collections/pflanzkuebel-kollektion-loft',
   text:'Urbaner Charakter in ruhigen Grau- und Erdtönen. Für Architektur mit klaren Linien.',
   colors:[['Off White','#E4DFD4'],['Light Grey','#B8B5AE'],['Concrete Grey','#8D8A84'],['Rust Brown','#7B4B31'],['Lead Grey','#5A5C5D'],['Espresso Black','#2C2825']]},
  {id:'terra', name:'Terra', finish:'sand', url:'https://eschbach-design.com/collections/pflanzkuebel-kollektion-terra',
   text:'Warme, mineralische Töne von Champagne White bis Siena Red. Für Gärten mit südlichem Licht.',
   colors:[['Champagne White','#E2D8C4'],['Desert Beige','#C2AC89'],['Macchiato Grey','#9B8F82'],['Lead Grey','#5E5F5E'],['Black Sand','#35322E'],['Siena Red','#8F402C']]},
  {id:'antique', name:'Antique', finish:'patina', url:'https://eschbach-design.com/collections/antique-collection',
   text:'Oberflächen mit Patina, gealtert wie Metall. In Antique Brown, Copper Green und Bronze.',
   colors:[['Antique Brown','#5E4532','#2C2018'],['Copper Green','#587C6E','#6A4D31'],['Bronze','#7D5D38','#382817']]},
  {id:'lava', name:'Lava', finish:'lava', url:'https://eschbach-design.com/collections/pflanzkuebel-kollektion-lava',
   text:'Eine lebendige, poröse Struktur. In Volcanic Black und Antique White.',
   colors:[['Volcanic Black','#2B2927'],['Antique White','#DBD4C5']]},
  {id:'pure', name:'Pure', finish:'smooth', url:'https://eschbach-design.com/collections/pflanzkuebel-kollektion-pure',
   text:'Reduziert und glatt.', colors:[['Santorin White','#EFEEEA'],['Onyx Black','#1A1A1A']]},
  {id:'granite', name:'Granite', finish:'granite', url:'https://eschbach-design.com/collections/granite',
   text:'Gesprenkelt wie Naturstein.', colors:[['Granite Grey','#6E6E6B']]},
  {id:'vertical', name:'Vertical Lines', finish:'ribs', url:'https://eschbach-design.com/collections/kollektion-vertical-stripes',
   text:'Feine vertikale Rillen.', colors:[['Vertical White','#EBE9E3']]},
  {id:'empire', name:'Empire', finish:'concrete', url:'https://eschbach-design.com/collections/pflanzkuebel-kollektion-heritage',
   text:'Klassische Formensprache.', colors:[['Lead Grey','#585A5A']]},
];
const FORMS = [
  {id:'balloon', name:'Balloon', price:'ab €70', aspect:.86, pts:[[0,.7],[.1,.85],[.32,.98],[.52,1],[.75,.9],[.92,.72],[1,.6]]},
  {id:'highballoon', name:'High Balloon', price:'ab €80', aspect:1.18, pts:[[0,.72],[.12,.87],[.38,1],[.62,.97],[.84,.8],[1,.6]]},
  {id:'egg', name:'New Egg Pot', price:'ab €90', aspect:1.0, pts:[[0,.74],[.12,.9],[.35,1],[.6,.96],[.82,.78],[1,.5]]},
  {id:'talleg', name:'Tall Egg Pot', price:'ab €190', aspect:1.62, pts:[[0,.8],[.18,.96],[.4,1],[.66,.88],[.88,.64],[1,.48]]},
  {id:'bowl', name:'Grand Bowl', price:'ab €500', aspect:.46, pts:[[0,1],[.18,.99],[.45,.92],[.75,.74],[1,.52]]},
  {id:'box', name:'Box', price:'ab €220', box:true},
];
const findForm = id => FORMS.find(f => f.id === id);
const hex = h => [parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];

/* ---------------- Procedural textures ---------------- */
const TEX = 512, MASK = TEX - 1, TN = TEX*TEX;
const rng = seed => { let s = seed >>> 0; return () => (s = (s*1664525 + 1013904223) >>> 0) / 4294967296; };
function vnoise(period, seed){
  const r = rng(seed), lat = new Float32Array(period*period);
  for (let i=0;i<lat.length;i++) lat[i] = r();
  const out = new Float32Array(TN), sc = period/TEX;
  for (let y=0;y<TEX;y++){
    const fy=y*sc, iy=fy|0, ty=fy-iy, sy=ty*ty*(3-2*ty), y0=(iy%period)*period, y1=((iy+1)%period)*period;
    for (let x=0;x<TEX;x++){
      const fx=x*sc, ix=fx|0, tx=fx-ix, sx=tx*tx*(3-2*tx), x0=ix%period, x1=(ix+1)%period;
      const a=lat[y0+x0], b=lat[y0+x1], c=lat[y1+x0], d=lat[y1+x1];
      const top=a+(b-a)*sx, bot=c+(d-c)*sx;
      out[y*TEX+x] = top + (bot-top)*sy;
    }
  }
  return out;
}
function fbm(base, oct, seed, gain=.5){
  const out = new Float32Array(TN); let amp=1, tot=0;
  for (let o=0;o<oct;o++){
    const n = vnoise(Math.min(TEX, base<<o), seed + o*131);
    for (let i=0;i<TN;i++) out[i] += (n[i]-.5)*2*amp;
    tot += amp; amp *= gain;
  }
  for (let i=0;i<TN;i++) out[i] /= tot;
  return out;
}
function white(seed){ const r=rng(seed), o=new Float32Array(TN); for (let i=0;i<TN;i++) o[i]=r()*2-1; return o; }
function stamp(arr, count, rmin, rmax, val, seed){
  const r = rng(seed);
  for (let n=0;n<count;n++){
    const cx=r()*TEX, cy=r()*TEX, rad=rmin + r()*(rmax-rmin), R=Math.ceil(rad);
    for (let dy=-R;dy<=R;dy++) for (let dx=-R;dx<=R;dx++){
      const d=Math.sqrt(dx*dx+dy*dy); if (d>=rad) continue;
      const x=((cx+dx)|0)&MASK, y=((cy+dy)|0)&MASK;
      arr[y*TEX+x] += val*(1-d/rad);
    }
  }
}
const FIN = {
  concrete:{label:'Loft', amp:.15, gloss:.05, shin:8, gen(){ const a=fbm(8,5,11), g=white(7), t=new Float32Array(TN); for (let i=0;i<TN;i++) t[i]=a[i]*.6+g[i]*.22; stamp(t,1100,.6,2.2,-1.5,3); return {t}; }},
  sand:{label:'Terra', amp:.13, gloss:.04, shin:8, gen(){ const a=fbm(16,4,21), g=white(9), t=new Float32Array(TN); for (let i=0;i<TN;i++) t[i]=a[i]*.35+g[i]*.45; stamp(t,1800,.5,1.2,.9,5); stamp(t,1400,.5,1.2,-.9,6); return {t}; }},
  patina:{label:'Antique', amp:.12, gloss:.3, shin:20, gen(){ const a=fbm(32,4,31), g=white(4), mm=fbm(3,6,77), t=new Float32Array(TN), m=new Float32Array(TN); for (let i=0;i<TN;i++){ t[i]=a[i]*.5+g[i]*.15; const v=Math.min(1,Math.max(0,(mm[i]+.05)/.4)); m[i]=v*v*(3-2*v); } return {t,m}; }},
  smooth:{label:'Pure', amp:.025, gloss:.55, shin:46, gen(){ const a=fbm(8,3,41), g=white(2), t=new Float32Array(TN); for (let i=0;i<TN;i++) t[i]=a[i]*.4+g[i]*.08; return {t}; }},
  lava:{label:'Lava', amp:.2, gloss:.06, shin:10, gen(){ const a=fbm(16,4,51), g=white(8), t=new Float32Array(TN); for (let i=0;i<TN;i++) t[i]=a[i]*.4+g[i]*.2; stamp(t,3200,.7,3.4,-1.7,12); return {t}; }},
  granite:{label:'Granite', amp:.3, gloss:.18, shin:28, gen(){ const a=fbm(16,3,61), g=white(13), t=new Float32Array(TN); for (let i=0;i<TN;i++){ const w=g[i]; t[i]=a[i]*.25+(w>.84?1.3:w<-.8?-1.5:w*.08); } stamp(t,900,.6,1.6,-1.2,14); return {t}; }},
  ribs:{label:'Vertical Lines', amp:.06, gloss:.12, shin:16, ribs:true, gen(){ const a=fbm(16,4,71), g=white(15), t=new Float32Array(TN); for (let i=0;i<TN;i++) t[i]=a[i]*.3+g[i]*.2; return {t}; }},
};
const texCache = {};
const tex = id => texCache[id] || (texCache[id] = FIN[id].gen());

/* ---------------- Profile sampling ---------------- */
const N = 72;
function sampleProfile(pts){
  const out = new Float32Array(N);
  for (let i=0;i<N;i++){
    const v = i/(N-1); let s = 0;
    while (s < pts.length-2 && v > pts[s+1][0]) s++;
    const p0=pts[Math.max(0,s-1)], p1=pts[s], p2=pts[s+1], p3=pts[Math.min(pts.length-1,s+2)];
    const t=(v-p1[0])/((p2[0]-p1[0])||1), t2=t*t, t3=t2*t;
    out[i] = .5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3);
  }
  return out;
}
FORMS.forEach(f => { if (!f.box) f.prof = sampleProfile(f.pts); });

/* ---------------- Theme values for canvas ---------------- */
let SH = .6, RIM = .3, DARKUI = true;
function readTheme(){
  const cs = getComputedStyle(root);
  SH = parseFloat(cs.getPropertyValue('--shadow-a')) || .5;
  RIM = parseFloat(cs.getPropertyValue('--rim-a')) || .2;
  DARKUI = SH > .45;
  root.classList.toggle('is-dark-ui', DARKUI);
}

/* ---------------- Vessel renderer ---------------- */
const pots = [];
class Pot {
  constructor(canvas, o){
    this.c = canvas; this.ctx = canvas.getContext('2d');
    this.off = document.createElement('canvas'); this.octx = this.off.getContext('2d');
    this.form = findForm(o.form); this.prof = new Float32Array(this.form.prof || FORMS[0].prof);
    this.aspect = this.form.aspect || 1; this.isBoxNow = !!this.form.box;
    this.setColor(o.coll, o.ci, true);
    this.rot = o.rot || 0; this.extraRot = 0; this.auto = !!o.auto && !RM;
    this.light = [-.55,-.5,.75]; this.tLight = this.light.slice();
    this.visible = true; this.dirty = true; this.static = !!o.static;
    this.res = o.res || 1;
    this.fit(); pots.push(this);
    if ('IntersectionObserver' in window){
      new IntersectionObserver(es => es.forEach(e => { this.visible = e.isIntersecting; if (e.isIntersecting) this.dirty = true; }), {rootMargin:'200px'}).observe(canvas);
    }
  }
  fit(){
    const w = this.c.clientWidth || this.c.width, h = this.c.clientHeight || this.c.height;
    const dpr = Math.min(1.6, window.devicePixelRatio || 1) * this.res;
    const W = Math.max(120, Math.round(w*dpr)), H = Math.max(120, Math.round(h*dpr));
    if (this.c.width !== W || this.c.height !== H){ this.c.width = W; this.c.height = H; this.off.width = W; this.off.height = H; this.img = null; }
    this.dirty = true;
  }
  setColor(collId, ci, instant){
    const coll = COLL.find(c => c.id === collId); const col = coll.colors[ci];
    this.coll = coll; this.ci = ci; this.cname = col[0];
    this.finish = coll.finish; this.tCol = hex(col[1]); this.alt = col[2] ? hex(col[2]) : null;
    if (instant || !this.col) this.col = this.tCol.slice();
    this.dirty = true;
  }
  setForm(id){
    const f = findForm(id); if (!f || f === this.form) return;
    const swap = !!f.box !== !!this.form.box;
    this.form = f;
    if (swap){
      this.c.classList.add('swap');
      setTimeout(() => { if (!f.box){ this.prof.set(f.prof); this.aspect = f.aspect; } this.isBoxNow = !!f.box; this.dirty = true; this.c.classList.remove('swap'); }, 240);
    }
    this.dirty = true;
  }
  step(){
    let moving = false;
    const f = this.form;
    if (!f.box && !this.isBoxNow){
      for (let i=0;i<N;i++){ const d=f.prof[i]-this.prof[i]; if (Math.abs(d)>.0008){ this.prof[i]+=d*.14; moving=true; } else this.prof[i]=f.prof[i]; }
      const da = f.aspect - this.aspect; if (Math.abs(da)>.001){ this.aspect += da*.14; moving = true; } else this.aspect = f.aspect;
    }
    for (let k=0;k<3;k++){ const d=this.tCol[k]-this.col[k]; if (Math.abs(d)>.5){ this.col[k]+=d*.12; moving=true; } else this.col[k]=this.tCol[k]; }
    for (let k=0;k<3;k++){ const d=this.tLight[k]-this.light[k]; if (Math.abs(d)>.002){ this.light[k]+=d*.08; moving=true; } }
    if (this.auto && !this.drag){ this.rot += .0028; moving = true; }
    return moving;
  }
  getImg(W,H){ if (!this.img || this.img.width!==W || this.img.height!==H) this.img = this.octx.createImageData(W,H); return this.img; }
  lightVec(){
    let [lx,ly,lz] = this.light; const l = Math.hypot(lx,ly,lz); lx/=l; ly/=l; lz/=l;
    let hx=lx, hy=ly, hz=lz+1; const hl=Math.hypot(hx,hy,hz); return [lx,ly,lz,hx/hl,hy/hl,hz/hl];
  }
  drawShadow(cx, ys, R){
    const ctx = this.ctx; ctx.save(); ctx.translate(cx, ys); ctx.scale(1, .24);
    const g = ctx.createRadialGradient(0,0,0,0,0,R);
    g.addColorStop(0, `rgba(0,0,0,${SH})`); g.addColorStop(.55, `rgba(0,0,0,${SH*.35})`); g.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0,0,R,0,Math.PI*2); ctx.fill(); ctx.restore();
  }
  render(){
    const ctx = this.ctx, W = this.c.width, H = this.c.height;
    ctx.clearRect(0,0,W,H);
    if (this.isBoxNow) return this.renderBox();
    const prof = this.prof, aspect = this.aspect, k = .22;
    const maxR = Math.min(W*.4, H*.8/(2*aspect + .62));
    const PH = 2*maxR*aspect, cx = W/2;
    const yTop = (H - PH)/2 - maxR*.06, yBot = yTop + PH;
    const r0 = maxR*prof[0], rB = maxR*prof[N-1];
    this.drawShadow(cx, yBot + k*rB*.55, rB*1.75);
    const img = this.getImg(W,H), d = img.data; d.fill(0);
    const T = tex(this.finish), t = T.t, m = T.m, F = FIN[this.finish];
    const [lx,ly,lz,hx,hy,hz] = this.lightVec();
    const br=this.col[0], bg=this.col[1], bb=this.col[2];
    const ar=this.alt?this.alt[0]:0, ag=this.alt?this.alt[1]:0, ab=this.alt?this.alt[2]:0;
    const amp=F.amp, gloss=F.gloss*255, shin=F.shin, ribs=!!F.ribs;
    const rimR = DARKUI ? 210 : 255, rimG = DARKUI ? 180 : 255, rimB = DARKUI ? 130 : 255, rimA = RIM;
    const rot = this.rot + this.extraRot;
    const texPerPx = TEX*2/(2*Math.PI*maxR), uScale = TEX*2/(2*Math.PI);
    const y0 = Math.max(0, Math.floor(yTop)), y1 = Math.min(H-1, Math.ceil(yBot + k*rB));
    for (let y=y0; y<=y1; y++){
      const v = (y - yTop)/PH, vc = v<0?0:v>1?1:v;
      const fi = vc*(N-1), i0 = Math.min(N-2, fi|0), fr = fi - i0;
      const r = (prof[i0] + (prof[i0+1]-prof[i0])*fr)*maxR;
      const ia = Math.max(0,i0-1), ib = Math.min(N-1,i0+2);
      const rp = (prof[ib]-prof[ia])/((ib-ia)/(N-1))*maxR/PH;
      let ao = 1; if (v > .84) ao = 1 - (Math.min(v,1.05)-.84)*1.5; if (v < .07) ao *= .8 + v*2.8;
      const ty = (((Math.floor((y-yTop)*texPerPx)) % TEX) + TEX) % TEX;
      const rowOff = ty*TEX, xr = Math.ceil(r), below = y > yBot;
      for (let x=-xr; x<=xr; x++){
        const ax = x<0?-x:x; if (ax >= r) continue;
        if (ax < r0){ if (y < yTop + k*r0*Math.sqrt(1 - (ax/r0)*(ax/r0))) continue; }
        else if (y < yTop) continue;
        if (below){ if (ax >= rB) continue; if (y > yBot + k*rB*Math.sqrt(1 - (ax/rB)*(ax/rB))) continue; }
        const sx = x/r, cz = Math.sqrt(1 - sx*sx), th = Math.asin(sx);
        let nx = sx, nz = cz; const ny = -rp;
        if (ribs){ const rb = Math.sin((th + rot)*44); nx += rb*.2*cz; nz -= rb*.05*sx; }
        const len = Math.sqrt(nx*nx + ny*ny + nz*nz);
        const dif = (nx*lx + ny*ly + nz*lz)/len;
        const lum = (.16 + .84*Math.max(0,(dif+.3)/1.3))*ao;
        let s = (nx*hx + ny*hy + nz*hz)/len; s = s>0 ? Math.pow(s, shin)*gloss : 0;
        let e = 1 - cz; e = e*e*e*rimA;
        const tu = ((Math.floor((th + rot)*uScale) % TEX) + TEX) % TEX;
        const idx = rowOff + tu, f = 1 + t[idx]*amp;
        let cr=br, cg=bg, cb=bb;
        if (m){ const w = m[idx]; cr = br + (ar-br)*w*.75; cg = bg + (ag-bg)*w*.75; cb = bb + (ab-bb)*w*.75; }
        const p = (y*W + (cx + x | 0))*4;
        d[p]   = cr*lum*f + s + rimR*e;
        d[p+1] = cg*lum*f + s + rimG*e;
        d[p+2] = cb*lum*f + s + rimB*e;
        const edge = r - ax; d[p+3] = edge < 1 ? edge*255 : 255;
      }
    }
    this.octx.putImageData(img,0,0); ctx.drawImage(this.off,0,0);
    // opening
    const ry = k*r0;
    ctx.save(); ctx.beginPath(); ctx.ellipse(cx, yTop, r0, ry, 0, 0, Math.PI*2);
    const g = ctx.createLinearGradient(0, yTop-ry, 0, yTop+ry);
    const c = (f) => `rgb(${br*f|0},${bg*f|0},${bb*f|0})`;
    g.addColorStop(0, c(.5)); g.addColorStop(.5, c(.16)); g.addColorStop(1, c(.06));
    ctx.fillStyle = g; ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx, yTop + ry*.35, r0*.84, ry*.62, 0, 0, Math.PI*2);
    ctx.fillStyle = 'rgba(28,22,17,.92)'; ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx, yTop, r0, ry, 0, 0, Math.PI*2);
    ctx.lineWidth = Math.max(1.5, r0*.045); ctx.strokeStyle = c(.92); ctx.stroke();
    ctx.lineWidth = Math.max(1, r0*.012); ctx.strokeStyle = `rgba(255,255,255,${DARKUI?.18:.32})`;
    ctx.beginPath(); ctx.ellipse(cx, yTop - ctx.lineWidth, r0, ry, 0, Math.PI*1.05, Math.PI*1.95); ctx.stroke();
    ctx.restore();
  }
  renderBox(){
    const ctx = this.ctx, W = this.c.width, H = this.c.height;
    const s = Math.min(W*.46, H*.5), w = s, dw = s*.42, dy = dw*.48, h = s*.98;
    const xL = Math.round(W/2 - (w+dw)/2), xR = xL + w, yT = Math.round((H - h + dy)/2);
    this.drawShadow(xL + (w+dw)/2, yT + h - dy*.2, (w+dw)*.78);
    const img = this.getImg(W,H), d = img.data; d.fill(0);
    const T = tex(this.finish), t = T.t, m = T.m, F = FIN[this.finish];
    const [lx,ly,lz,hx,hy,hz] = this.lightVec();
    const col = this.col, alt = this.alt, gloss = F.gloss*255;
    const faces = [ {n:[0,0,1]}, {n:[.92,0,.39]} ];
    faces.forEach(fc => { const [nx,ny,nz]=fc.n; const dif=nx*lx+ny*ly+nz*lz; fc.l=.16+.84*Math.max(0,(dif+.3)/1.3); let sp=nx*hx+ny*hy+nz*hz; fc.s=sp>0?Math.pow(sp,F.shin)*gloss:0; });
    const put = (x, y, fc, u, vv, edgeA) => {
      const tu = ((u|0)%TEX+TEX)%TEX, tv=((vv|0)%TEX+TEX)%TEX, idx = tv*TEX+tu, f = 1 + t[idx]*F.amp;
      let ribL = 1; if (F.ribs) ribL = .86 + .14*Math.sin(u*.55);
      let cr=col[0], cg=col[1], cb=col[2]; if (m && alt){ const q=m[idx]*.75; cr+= (alt[0]-cr)*q; cg+=(alt[1]-cg)*q; cb+=(alt[2]-cb)*q; }
      const ao = 1 - Math.max(0,(y - (yT + h*.82))/(h*.18))*.3;
      const L = fc.l*f*ribL*ao, p = (y*W + x)*4;
      d[p]=cr*L+fc.s; d[p+1]=cg*L+fc.s; d[p+2]=cb*L+fc.s; d[p+3]=edgeA;
    };
    const sc = TEX*1.2/w;
    for (let y=Math.max(0,yT); y<Math.min(H,yT+h); y++) for (let x=xL; x<xR; x++) put(x, y, faces[0], (x-xL)*sc, (y-yT)*sc, 255);
    for (let x=xR; x<xR+dw; x++){
      const top = yT - (x-xR)*dy/dw;
      for (let y=Math.max(0,Math.ceil(top)); y<Math.min(H,top+h); y++) put(x, y, faces[1], (w + (x-xR)*1.6)*sc, (y-top)*sc, 255);
    }
    this.octx.putImageData(img,0,0); ctx.drawImage(this.off,0,0);
    // top face with opening
    const topL = Math.max(0,-ly)*.84 + .16;
    const c = (f) => `rgb(${col[0]*f|0},${col[1]*f|0},${col[2]*f|0})`;
    ctx.beginPath(); ctx.moveTo(xL,yT); ctx.lineTo(xR,yT); ctx.lineTo(xR+dw,yT-dy); ctx.lineTo(xL+dw,yT-dy); ctx.closePath();
    ctx.fillStyle = c(Math.min(1.12, topL*1.05)); ctx.fill();
    const ins = .1, ix = w*ins, idx2 = dw*ins, idy = dy*ins;
    ctx.beginPath(); ctx.moveTo(xL+ix+idx2, yT-idy); ctx.lineTo(xR-ix+idx2, yT-idy); ctx.lineTo(xR-ix+dw-idx2, yT-dy+idy); ctx.lineTo(xL+ix+dw-idx2, yT-dy+idy); ctx.closePath();
    const g = ctx.createLinearGradient(0, yT-dy, 0, yT); g.addColorStop(0, c(.42)); g.addColorStop(1, c(.08));
    ctx.fillStyle = g; ctx.fill();
    ctx.strokeStyle = `rgba(255,255,255,${DARKUI?.14:.3})`; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(xL,yT); ctx.lineTo(xR,yT); ctx.lineTo(xR+dw,yT-dy); ctx.stroke();
  }
}

let loopOn = false;
function loop(){
  for (const p of pots){
    if (!p.visible) continue;
    const moving = p.static ? false : p.step();
    if (moving || p.dirty){ p.render(); p.dirty = false; }
  }
  requestAnimationFrame(loop);
}

/* Hero: the still photo is the base (and the poster). After the page has loaded, the looping video
   (assets/hero.mp4 desktop, hero_m.mp4 = portrait crop of the same video for phones; tools/hero_video.py) is laid over it
   and faded in once it can play. No video for reduced motion / data saver, or if the file is missing -> the photo stays. */
(() => {
  const media = document.getElementById('heroMedia'); if (!media) return;
  const conn = navigator.connection || {};
  if (RM || conn.saveData || /(^|-)2g$/.test(conn.effectiveType || '')) return;
  const start = () => {
    const src = matchMedia('(max-width: 700px)').matches ? media.dataset.videoM : media.dataset.video; if (!src) return;
    const v = document.createElement('video');
    v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true; v.preload = 'auto';
    v.setAttribute('muted', ''); v.setAttribute('playsinline', ''); v.setAttribute('aria-hidden', 'true'); v.tabIndex = -1;
    v.addEventListener('playing', () => v.classList.add('on'), {once:true});
    v.addEventListener('error', () => v.remove());
    v.src = src; media.appendChild(v);
    const p = v.play(); if (p && p.catch) p.catch(() => {});
    let userPaused = false;
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'hp-pause';
    const ICON = {pause:'<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9M11 3.5v9" stroke="currentColor" stroke-width="1.6" fill="none"/></svg>',
                  play:'<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5.5 3.5l7 4.5-7 4.5z" fill="currentColor"/></svg>'};
    const sync = () => { btn.innerHTML = userPaused ? ICON.play : ICON.pause; btn.setAttribute('aria-label', userPaused ? 'Video abspielen' : 'Video pausieren'); };
    btn.addEventListener('click', () => { userPaused = !userPaused; if (userPaused) v.pause(); else { const q = v.play(); if (q && q.catch) q.catch(() => {}); } sync(); });
    media.parentElement.appendChild(btn);
    // sit on the same line as the "Kollektionen" button (layout positions, transforms ignored)
    const cta = document.querySelector('.hp-copy .btn'), hero = media.parentElement;
    const align = () => { if (!cta) return; const y = cta.offsetTop + cta.offsetHeight / 2;
      let el = cta.offsetParent, top = 0; while (el && el !== hero) { top += el.offsetTop; el = el.offsetParent; }
      btn.style.bottom = Math.round(hero.offsetHeight - (top + y) - 20) + 'px'; };
    align(); addEventListener('resize', align);
    sync(); v.addEventListener('playing', () => { align(); btn.classList.add('on'); }, {once:true});
    // pause while the hero is out of view (but never restart a video the visitor paused)
    new IntersectionObserver(es => { if (es[0].isIntersecting && !userPaused) { const q = v.play(); if (q && q.catch) q.catch(() => {}); } else v.pause(); }, {threshold:.05}).observe(media);
  };
  if (document.readyState === 'complete') start(); else addEventListener('load', start);
})();

function bindDrag(p){
  let lastX = 0;
  p.c.addEventListener('pointerdown', e => { p.drag = true; lastX = e.clientX; p.c.setPointerCapture(e.pointerId); });
  p.c.addEventListener('pointermove', e => { if (!p.drag) return; p.rot -= (e.clientX - lastX)*.012; lastX = e.clientX; p.dirty = true; });
  const end = () => { p.drag = false; };
  p.c.addEventListener('pointerup', end); p.c.addEventListener('pointercancel', end);
}

/* ---------------- Atelier ---------------- */
const atCanvas = document.getElementById('atPot');
const at = new Pot(atCanvas, {form:'egg', coll:'loft', ci:3, auto:true, res:.9});
bindDrag(at);
const atSec = document.getElementById('atelier');
atSec.addEventListener('pointermove', e => {
  const r = atCanvas.getBoundingClientRect(), mx = (e.clientX - r.left)/r.width, my = (e.clientY - r.top)/r.height;
  at.tLight = [Math.max(-1.4,Math.min(1.4,(mx-.5)*2)), -.4 + Math.max(-.5,Math.min(.5,(my-.5)*.8)), .8];
});
const formsEl = document.getElementById('forms');
function silhouette(f){
  if (f.box) return '<svg viewBox="0 0 40 40"><path d="M8 14h18v20H8zM26 14l7-4v20l-7 4M8 14l7-4h18"/></svg>';
  const H = 34*Math.min(1, f.aspect/1.62) , W = 30, top = 38 - H; let l = '', rr = '';
  for (let i=0;i<N;i+=4){ const v=i/(N-1), r=f.prof[i]*W/2*(f.aspect<.6?1.2:1); l += `${(20-r).toFixed(1)},${(top+v*H).toFixed(1)} `; rr = `${(20+r).toFixed(1)},${(top+v*H).toFixed(1)} ` + rr; }
  return `<svg viewBox="0 0 40 40"><polygon points="${l}${rr}"/></svg>`;
}
FORMS.forEach(f => {
  const b = document.createElement('button'); b.type='button'; b.className='form-btn'; b.dataset.id = f.id;
  b.setAttribute('aria-pressed', f.id==='egg'); b.innerHTML = silhouette(f) + `<span>${f.name}</span>`;
  b.addEventListener('click', () => { at.setForm(f.id); formsEl.querySelectorAll('.form-btn').forEach(x => x.setAttribute('aria-pressed', x===b)); updateDetail(); });
  formsEl.appendChild(b);
});
const groupsEl = document.getElementById('groups');
COLL.forEach(coll => {
  const g = document.createElement('div'); g.className = 'group';
  g.innerHTML = `<span class="group-name">${coll.name}</span><div class="swatches" role="group" aria-label="${coll.name}"></div>`;
  const sw = g.querySelector('.swatches');
  coll.colors.forEach((col, ci) => {
    const b = document.createElement('button'); b.type='button'; b.className='sw'; b.style.setProperty('--c', col[1]);
    b.title = col[0]; b.setAttribute('aria-label', `${col[0]}, ${coll.name}`); b.setAttribute('aria-pressed', coll.id==='loft' && ci===3);
    b.addEventListener('click', () => {
      at.setColor(coll.id, ci); atSec.style.setProperty('--tint', col[1]);
      groupsEl.querySelectorAll('.sw').forEach(x => x.setAttribute('aria-pressed', x===b)); updateDetail();
    });
    sw.appendChild(b);
  });
  groupsEl.appendChild(g);
});
const dName = document.getElementById('dName'), dColl = document.getElementById('dColl'), dForm = document.getElementById('dForm'), dPrice = document.getElementById('dPrice'), dLink = document.getElementById('dLink');
/* ---- Scenery mode: kie.ai scene photo + Blender layers (env = shadow/soil/grass, body = vessel) ----
   assets/atelier/manifest.json -> {scenes:[{id,name,image,thumb}], forms:[...], tint:[finish...]}
   Missing manifest => Studio mode only (procedural canvas), nothing breaks. */
const SCENE = (() => {
  const stage = document.getElementById('sceneStage'), A = document.getElementById('sceneA'), B = document.getElementById('sceneB');
  const tag = document.getElementById('sceneTag'), ctl = document.getElementById('scenesCtl'), list = document.getElementById('scenes');
  const hint = document.getElementById('atHint'), grid = document.querySelector('.at-grid');
  const cache = new Map();
  let man = null, scene = null, front = A, back = B, token = 0;
  const loadImg = url => cache.get(url) || (cache.set(url, new Promise((res, rej) => {
    const i = new Image(); i.decoding = 'async'; i.onload = () => res(i); i.onerror = () => { cache.delete(url); rej(url); }; i.src = url;
  })), cache.get(url));
  const slug = s => s.toLowerCase().replace(/\s+/g, '-');
  function variant(){
    const coll = at.coll, col = coll.colors[at.ci];
    if (man.tint.includes(coll.finish)) return {key: coll.finish, tint: col[1]};
    return {key: `${coll.id}-${slug(col[0])}`, tint: null};
  }
  async function draw(){
    if (!scene || !man) return;
    const my = ++token, v = variant(), f = at.form.id, base = `assets/atelier/${scene.id}/${f}/`;
    stage.classList.add('loading');
    try {
      const [bg, env, body] = await Promise.all([loadImg(scene.image), loadImg(base + 'env.webp'), loadImg(base + `body_${v.key}.webp`)]);
      if (my !== token) return;
      const W = bg.naturalWidth, H = bg.naturalHeight; back.width = W; back.height = H;
      const c = back.getContext('2d'); c.globalCompositeOperation = 'source-over';
      c.drawImage(bg, 0, 0, W, H); c.drawImage(env, 0, 0, W, H);
      const off = document.createElement('canvas'); off.width = W; off.height = H; const o = off.getContext('2d');
      o.drawImage(body, 0, 0, W, H);
      if (v.tint){
        o.globalCompositeOperation = 'multiply'; o.fillStyle = v.tint; o.fillRect(0, 0, W, H);
        o.globalCompositeOperation = 'destination-in'; o.drawImage(body, 0, 0, W, H);
      }
      c.drawImage(off, 0, 0);
      back.style.opacity = 1; front.style.opacity = 0; [front, back] = [back, front];
      front.setAttribute('aria-label', `${at.form.name} in ${at.cname}, Szenerie ${scene.name}`); back.removeAttribute('aria-label');
      tag.textContent = `${scene.name} · ${at.form.name} · ${at.cname}`;
    } catch(e){ console.warn('Atelier-Asset fehlt:', e); }
    finally { if (my === token) stage.classList.remove('loading'); }
  }
  function select(s){
    scene = s;
    list.querySelectorAll('.scene-btn').forEach(b => b.setAttribute('aria-pressed', b.dataset.id === (s ? s.id : 'studio')));
    stage.hidden = !s; atCanvas.hidden = !!s; grid.classList.toggle('has-scenes', !!s);
    hint.hidden = !!s;
    if (s) draw(); else { at.fit(); at.dirty = true; }
  }
  const init = () => fetch('assets/atelier/manifest.json').then(r => r.ok ? r.json() : null).then(m => {
    if (!m || !m.scenes || !m.scenes.length) return;
    man = m; ctl.hidden = false;
    const mk = (id, name, thumb) => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'scene-btn' + (thumb ? '' : ' studio'); b.dataset.id = id;
      if (thumb) b.style.backgroundImage = `url("${thumb}")`;
      b.innerHTML = `<span>${name}</span>`; list.appendChild(b); return b;
    };
    mk('studio', 'Studio', null).addEventListener('click', () => select(null));
    m.scenes.forEach(s => mk(s.id, s.name, s.thumb).addEventListener('click', () => select(s)));
    select(m.scenes[0]);
  }).catch(() => {});
  return {draw, init, active: () => !!scene};
})();

/* ---- Atelier 2: real ESCHBACH shop photos in kie.ai sceneries, light matched live in canvas ----
   assets/atelier2/catalog.json (tools/atelier2_publish.py): {scenes:[{id,name,image,thumb,light}], collections:[{id,name,url,forms:[{id,name,colours:[{name,hex,img,url}]}]}]}
   The pot is always centred horizontally with its foot on light.contact_y, so switching scenes swaps only the
   background; tint / side light / rim / cast shadow / contact shadow / floor reflection follow light.*.
   Missing catalog => old scene mode (SCENE.init) / Studio canvas. */
const ATELIER = (() => {
  const stage = document.getElementById('sceneStage'), A = document.getElementById('sceneA'), B = document.getElementById('sceneB');
  const tag = document.getElementById('sceneTag'), ctl = document.getElementById('scenesCtl'), list = document.getElementById('scenes');
  const hint = document.getElementById('atHint'), grid = document.querySelector('.at-grid');
  const formsEl = document.getElementById('forms');
  const cache = new Map(), meanCache = new Map();
  let cat = null, scene = null, coll = null, form = null, colour = null, front = A, back = B, token = 0;
  const loadImg = url => cache.get(url) || (cache.set(url, new Promise((res, rej) => {
    const i = new Image(); i.decoding = 'async'; i.onload = () => res(i); i.onerror = () => { cache.delete(url); rej(url); }; i.src = url;
  })), cache.get(url));
  const mk = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
  const rgb = (a, al = 1) => `rgba(${a[0]|0},${a[1]|0},${a[2]|0},${al})`;
  // cross-browser blur (Safari has no ctx.filter): render small, scale back up with smoothing
  function soften(src, r){
    if (r < 1.5) return src;
    const d = Math.min(24, r / 1.6), sm = mk(src.width / d, src.height / d), out = mk(src.width, src.height);
    const a = sm.getContext('2d'); a.imageSmoothingQuality = 'high'; a.drawImage(src, 0, 0, sm.width, sm.height);
    const b = out.getContext('2d'); b.imageSmoothingQuality = 'high'; b.drawImage(sm, 0, 0, out.width, out.height);
    return out;
  }
  function sceneMean(bg, key, box){
    if (meanCache.has(key)) return meanCache.get(key);
    const c = mk(32, 32), x = c.getContext('2d', {willReadFrequently:true});
    x.drawImage(bg, box[0], box[1], box[2], box[3], 0, 0, 32, 32);
    const d = x.getImageData(0, 0, 32, 32).data, m = [0, 0, 0];
    for (let i = 0; i < d.length; i += 4){ m[0] += d[i]; m[1] += d[i+1]; m[2] += d[i+2]; }
    const r = m.map(v => v / (d.length / 4)); meanCache.set(key, r); return r;
  }
  function studioBg(W, H){
    const c = mk(W, H), x = c.getContext('2d');
    const g = x.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#d9d4cc'); g.addColorStop(.62, '#cfc9bf'); g.addColorStop(.63, '#c6bfb4'); g.addColorStop(1, '#b9b2a6');
    x.fillStyle = g; x.fillRect(0, 0, W, H);
    const v = x.createRadialGradient(W/2, H*.55, H*.1, W/2, H*.55, W*.7); v.addColorStop(0, 'rgba(255,255,255,.18)'); v.addColorStop(1, 'rgba(40,30,20,.28)');
    x.fillStyle = v; x.fillRect(0, 0, W, H); return c;
  }
  function footWidth(sil){   // width of the opaque base (bottom 6 %) of the silhouette
    const w = 64, h = Math.max(8, Math.round(64 * sil.height / sil.width)), c = mk(w, h), x = c.getContext('2d', {willReadFrequently:true});
    x.drawImage(sil, 0, 0, w, h); const rows = Math.max(1, Math.round(h * .06)), d = x.getImageData(0, h - rows - 1, w, rows).data;
    let l = w, r = 0; for (let i = 0; i < d.length; i += 4) if (d[i+3] > 128){ const px = (i / 4) % w; l = Math.min(l, px); r = Math.max(r, px); }
    return r > l ? (r - l + 1) / w : .6;
  }
  function footDepth(sil){   // how far the visible foot curve rises above the lowest pixel (0..1 of height)
    const w = 64, h = Math.max(16, Math.round(64 * sil.height / sil.width)), c = mk(w, h), x = c.getContext('2d', {willReadFrequently:true});
    x.drawImage(sil, 0, 0, w, h); const d = x.getImageData(0, 0, w, h).data, width = y => { let n = 0; for (let i = 0; i < w; i++) if (d[(y * w + i) * 4 + 3] > 128) n++; return n; };
    let ref = 0; for (let y = Math.floor(h * .6); y < h; y++) ref = Math.max(ref, width(y));
    for (let y = h - 1; y > h * .6; y--) if (width(y) >= ref * .92) return (h - 1 - y) / h;
    return .05;
  }
  async function draw(){
    if (!cat || !scene || !colour) return;
    const my = ++token; stage.classList.add('loading');
    try {
      const [bgImg, pot] = await Promise.all([scene.image ? loadImg(scene.image) : Promise.resolve(null), loadImg(colour.img)]);
      if (my !== token) return;
      const L = scene.light, W = scene.w, H = scene.h, bg = bgImg || studioBg(W, H);
      const base = H * L.contact_y, s = Math.min(H * L.pot_h / pot.naturalHeight, W * .24 / pot.naturalWidth);
      const pw = pot.naturalWidth * s, ph = pot.naturalHeight * s, x0 = (W - pw) / 2, y0 = base - ph;
      back.width = W; back.height = H; const c = back.getContext('2d');
      c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1; c.drawImage(bg, 0, 0, W, H);
      // 1) grade the pot with the scene light
      const P = mk(pw, ph), p = P.getContext('2d'); p.imageSmoothingQuality = 'high'; p.drawImage(pot, 0, 0, P.width, P.height);
      const box = [Math.max(0, W/2 - pw), Math.max(0, y0), Math.min(W, pw * 2), Math.min(H - y0, ph * 1.3)];
      const mean = sceneMean(bg, scene.id, box), mx = Math.max(...mean), t = L.tint ?? .5, ex = Math.min(1, L.exposure ?? 1);
      p.globalCompositeOperation = 'multiply'; p.fillStyle = rgb(mean.map(v => 255 * ex * ((1 - t) + t * v / mx))); p.fillRect(0, 0, P.width, P.height);
      if (L.side){
        const k = Math.abs(L.side), g = p.createLinearGradient(0, 0, P.width, 0), dark = `rgba(0,0,0,${k})`, light = `rgba(255,255,255,${k * .8})`;
        g.addColorStop(0, L.side > 0 ? dark : light); g.addColorStop(.5, 'rgba(128,128,128,0)'); g.addColorStop(1, L.side > 0 ? light : dark);
        p.globalCompositeOperation = 'soft-light'; p.fillStyle = g; p.fillRect(0, 0, P.width, P.height);
      }
      if (L.rim){
        const R = mk(P.width, P.height), r = R.getContext('2d');
        r.drawImage(pot, 0, 0, R.width, R.height); r.globalCompositeOperation = 'source-in'; r.fillStyle = rgb(L.rim_color || [255, 220, 180]); r.fillRect(0, 0, R.width, R.height);
        r.globalCompositeOperation = 'destination-out'; r.drawImage(pot, R.width * .012, R.height * .02, R.width * .976, R.height * .98);
        p.globalCompositeOperation = 'screen'; p.globalAlpha = Math.min(1, L.rim); p.drawImage(soften(R, pw * .02), 0, 0); p.globalAlpha = 1;
      }
      p.globalCompositeOperation = 'destination-in'; p.drawImage(pot, 0, 0, P.width, P.height);
      // 2) shadow layer: projected silhouette (near sharp -> far soft, fading) + contact occlusion, multiplied in the shadow colour
      const sh = L.shadow, sc = W / 2752;
      const Sil = mk(pw, ph), si = Sil.getContext('2d'); si.drawImage(pot, 0, 0, Sil.width, Sil.height);
      si.globalCompositeOperation = 'source-in'; si.fillStyle = '#000'; si.fillRect(0, 0, Sil.width, Sil.height);
      // project around the middle of the footprint (photos look down a little), not the lowest pixel
      const pb = base - footDepth(Sil) * ph * .55;
      const proj = () => { const T = mk(W, H), x = T.getContext('2d'); x.setTransform(1, 0, -sh.sx, -sh.sy, sh.sx * pb, pb * (1 + sh.sy));
        x.drawImage(Sil, 0, 0, Sil.width, Sil.height * (pb - y0) / ph, x0, y0, pw, pb - y0); return T; };
      const raw = proj(), span = Math.max(20, Math.abs(sh.sy) * H * .4), dir = sh.sy >= 0 ? 1 : -1;
      const ramp = (cv, stops) => { const x = cv.getContext('2d'), g = x.createLinearGradient(0, base, 0, base + dir * span);
        stops.forEach(([o, a]) => g.addColorStop(o, `rgba(0,0,0,${a})`)); x.globalCompositeOperation = 'destination-in'; x.fillStyle = g; x.fillRect(0, 0, W, H); return cv; };
      const near = ramp(soften(raw, (sh.blur_near ?? 4) * sc), [[0, 1], [.5, .45], [1, 0]]);
      const far = ramp(soften(raw, (sh.blur_far ?? 30) * sc), [[0, 0], [.5, .38], [1, .45]]);
      const S = mk(W, H), sx = S.getContext('2d');
      sx.globalAlpha = sh.opacity ?? .6; sx.globalCompositeOperation = 'lighter'; sx.drawImage(near, 0, 0); sx.drawImage(far, 0, 0); sx.globalAlpha = 1;
      if (L.contact){
        // The shop photos look slightly down onto the pot, so the foot is a curve (egg) or a V (cube), not a line.
        // Contact shadow = lower part of the silhouette, nudged down + softened -> hugs every foot shape.
        const Cs = mk(pw, ph * 1.08), cs = Cs.getContext('2d');
        cs.drawImage(Sil, 0, ph * .018, pw, ph);
        const g = cs.createLinearGradient(0, 0, 0, Cs.height); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(.6, 'rgba(0,0,0,0)'); g.addColorStop(.9, 'rgba(0,0,0,1)');
        cs.globalCompositeOperation = 'destination-in'; cs.fillStyle = g; cs.fillRect(0, 0, Cs.width, Cs.height);
        sx.globalAlpha = L.contact; sx.drawImage(soften(Cs, ph * .025), x0, y0); sx.globalAlpha = 1;
        // wide, faint ambient occlusion
        const bw = footWidth(Sil) * pw, rx = Math.max(bw, pw * .55) * .62;
        sx.save(); sx.translate(W / 2, base); sx.scale(1, .12);
        const r = sx.createRadialGradient(0, 0, 0, 0, 0, rx); r.addColorStop(0, `rgba(0,0,0,${L.contact * .45})`); r.addColorStop(1, 'rgba(0,0,0,0)');
        sx.fillStyle = r; sx.beginPath(); sx.arc(0, 0, rx, 0, Math.PI * 2); sx.fill(); sx.restore();
      }
      sx.globalCompositeOperation = 'source-in'; sx.fillStyle = rgb(sh.color || [40, 34, 30]); sx.fillRect(0, 0, W, H);
      // multiply: bg * (1 - a*(1-col))
      const M = mk(W, H), mm = M.getContext('2d'); mm.fillStyle = '#fff'; mm.fillRect(0, 0, W, H); mm.drawImage(S, 0, 0);
      c.globalCompositeOperation = 'multiply'; c.drawImage(M, 0, 0); c.globalCompositeOperation = 'source-over';
      // 3) floor reflection (glossy floors)
      if (L.reflection){
        const Rf = mk(pw, ph), rf = Rf.getContext('2d'); rf.translate(0, Rf.height); rf.scale(1, -1); rf.drawImage(P, 0, 0); rf.setTransform(1, 0, 0, 1, 0, 0);
        const g = rf.createLinearGradient(0, 0, 0, Rf.height); g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(.45, 'rgba(0,0,0,0)');
        rf.globalCompositeOperation = 'destination-in'; rf.fillStyle = g; rf.fillRect(0, 0, Rf.width, Rf.height);
        c.globalAlpha = L.reflection; c.drawImage(soften(Rf, (L.reflection_blur ?? 6) * sc), x0, base - 2); c.globalAlpha = 1;
      }
      // 4) the pot
      c.drawImage(P, x0, y0, pw, ph);
      back.style.opacity = 1; front.style.opacity = 0; [front, back] = [back, front];
      front.setAttribute('aria-label', `${form.name} ${coll.name} in ${colour.name}, Szenerie ${scene.name}`); back.removeAttribute('aria-label');
      tag.textContent = `${scene.name} · ${form.name} · ${colour.name}`;
    } catch(e){ console.warn('Atelier-Asset fehlt:', e); }
    finally { if (my === token) stage.classList.remove('loading'); }
  }
  function detail(){
    dName.textContent = colour.name; dColl.textContent = coll.name; dForm.textContent = form.name;
    dPrice.previousElementSibling.textContent = 'Farben'; dPrice.textContent = `${form.colours.length} ${form.colours.length === 1 ? 'Farbe' : 'Farben'}`;
    dLink.href = colour.url; dLink.firstChild.textContent = 'Im Shop ansehen ';
    atSec.style.setProperty('--tint', colour.hex);
    if (window.gsap && !RM) gsap.fromTo(dName, {y:14, opacity:.4}, {y:0, opacity:1, duration:.6, ease:'power3.out'});
  }
  const press = (root, sel, el) => root.querySelectorAll(sel).forEach(x => x.setAttribute('aria-pressed', x === el));
  function pickColour(c, btn){ colour = c; if (btn) press(groupsEl, '.sw', btn); detail(); draw(); }
  function pickForm(f, btn){
    form = f; if (btn) press(formsEl, '.form-btn', btn);
    groupsEl.innerHTML = '<div class="swatches" role="group" aria-label="Farben"></div>';
    const sw = groupsEl.firstChild;
    const keep = colour && f.colours.find(c => c.name === colour.name);
    f.colours.forEach(c => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'sw'; b.style.setProperty('--c', c.hex);
      b.title = c.name; b.setAttribute('aria-label', c.name); b.addEventListener('click', () => pickColour(c, b)); sw.appendChild(b);
      if (c === (keep || f.colours[0])) b.setAttribute('aria-pressed', 'true'); else b.setAttribute('aria-pressed', 'false');
    });
    pickColour(keep || f.colours[0]);
  }
  function pickColl(cl, btn, formId){
    coll = cl; if (btn) press(collsEl, '.coll-chip', btn);
    formsEl.innerHTML = '';
    let first = null;
    cl.forms.forEach(f => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'form-btn photo';
      b.innerHTML = `<img src="${f.colours[0].img}" alt="" loading="lazy" decoding="async"><span>${f.name}</span>`;
      b.addEventListener('click', () => pickForm(f, b)); formsEl.appendChild(b);
      if (!first || f.id === formId) first = [f, b];
    });
    pickForm(...first);
  }
  function pickScene(s){
    scene = s; press(list, '.scene-btn', list.querySelector(`[data-id="${s.id}"]`)); draw();
  }
  let collsEl;
  const start = () => fetch('assets/atelier2/catalog.json', {cache:'no-store'}).then(r => r.ok ? r.json() : null).then(m => {
    if (!m || !m.scenes || !m.scenes.length || !m.collections.length) { SCENE.init(); return; }
    cat = m; window.__atelier2 = true;
    stage.hidden = false; atCanvas.hidden = true; hint.hidden = true; grid.classList.add('has-scenes'); ctl.hidden = false;
    // scenes (+ neutral studio)
    const studio = {id:'studio', name:'Studio', image:null, w:m.scenes[0].w, h:m.scenes[0].h,
      light:{contact_y:.76, pot_h:.34, tint:0, exposure:1, side:0, rim:0, shadow:{sx:.35, sy:.22, opacity:.35, blur_near:6, blur_far:40, color:[60,50,40]}, contact:.6, reflection:0}};
    list.innerHTML = '';
    [...m.scenes, studio].forEach(s => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'scene-btn' + (s.thumb ? '' : ' studio'); b.dataset.id = s.id;
      if (s.thumb) b.style.backgroundImage = `url("${s.thumb}")`;
      b.innerHTML = `<span>${s.name}</span>`; b.addEventListener('click', () => pickScene(s)); list.appendChild(b);
    });
    // collection chips above the forms
    const formsWrap = formsEl.parentElement, cw = document.createElement('div');
    cw.innerHTML = '<span class="ctl-label" id="collsLabel">Kollektion</span><div class="coll-chips" id="collChips" role="group" aria-labelledby="collsLabel"></div>';
    formsWrap.parentElement.insertBefore(cw, formsWrap); collsEl = cw.querySelector('#collChips');
    groupsEl.previousElementSibling.textContent = 'Farbe';
    const total = m.collections.reduce((n, c) => n + c.forms.reduce((k, f) => k + f.colours.length, 0), 0);
    const lead = document.querySelector('.at-head .lead'); if (lead) lead.textContent = `${total} Gefäße in ${m.collections.length} Kollektionen. Wählen Sie Szenerie, Kollektion, Form und Farbe und sehen Sie das Original dort, wo es stehen wird.`;
    m.collections.forEach(cl => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'coll-chip'; b.textContent = cl.name; b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', () => pickColl(cl, b)); collsEl.appendChild(b);
    });
    scene = m.scenes[0]; press(list, '.scene-btn', list.querySelector(`[data-id="${scene.id}"]`));
    const loft = m.collections.find(c => c.id === 'loft') || m.collections[0];
    const f0 = loft.forms.find(f => f.id === 'new-egg-pot') || loft.forms[0];
    colour = f0.colours.find(c => /rust/i.test(c.name)) || null;
    pickColl(loft, collsEl.children[m.collections.indexOf(loft)], f0.id);
    // warm the cache for the other scenes so switching is instant
    m.scenes.slice(1).forEach(s => loadImg(s.image).catch(() => {}));
  }).catch(e => { console.warn(e); SCENE.init(); });
  return {draw, start};
})();

/* ---- Lava test: fully AI-rendered scene photos (kie.ai, product photo as reference), one image per scene x form x colour ----
   assets/lava/catalog.json (tools/lava_publish.py). Every image of a scene shares one crop, and the crops are chosen so the
   reference pot (U Pot) has the same size + position in every scene -> switching scenes keeps the pot in place.
   Missing catalog => ATELIER.start() (photo compositing mode). */
const LAVA = (() => {
  const stage = document.getElementById('sceneStage'), A = document.getElementById('sceneA'), B = document.getElementById('sceneB');
  const tag = document.getElementById('sceneTag'), ctl = document.getElementById('scenesCtl'), list = document.getElementById('scenes');
  const hint = document.getElementById('atHint'), grid = document.querySelector('.at-grid'), formsEl = document.getElementById('forms');
  const cache = new Map();
  const loadImg = url => cache.get(url) || (cache.set(url, new Promise((res, rej) => {
    const i = new Image(); i.decoding = 'async'; i.onload = () => res(i); i.onerror = () => { cache.delete(url); rej(url); }; i.src = url;
  })), cache.get(url));
  let m, scene, form, colour, front = A, back = B, token = 0;
  const press = (root, sel, el) => root.querySelectorAll(sel).forEach(x => x.setAttribute('aria-pressed', x === el));
  const url = () => `assets/lava/${scene.id}/${form.id}__${colour.id}.webp`;
  async function draw(){
    const my = ++token; stage.classList.add('loading');
    try {
      const img = await loadImg(url()); if (my !== token) return;
      back.width = img.naturalWidth; back.height = img.naturalHeight; back.getContext('2d').drawImage(img, 0, 0);
      back.style.opacity = 1; front.style.opacity = 0; [front, back] = [back, front];
      front.setAttribute('aria-label', `Lava ${form.name} in ${colour.name}, ${scene.name}`); back.removeAttribute('aria-label');
      tag.textContent = `${scene.name} · ${form.name} · ${colour.name}`;
      // preload the neighbours so the next click is instant
      m.scenes.forEach(s => loadImg(`assets/lava/${s.id}/${form.id}__${colour.id}.webp`).catch(() => {}));
    } catch(e){ console.warn('Lava-Bild fehlt:', e); }
    finally { if (my === token) stage.classList.remove('loading'); }
  }
  function detail(){
    const v = form.variants[colour.id] || {};
    dName.textContent = colour.name; dColl.textContent = 'Lava'; dForm.textContent = form.name; const dSize = document.getElementById('dSize'); if (dSize) dSize.textContent = form.size;
    dPrice.previousElementSibling.textContent = 'Preis'; dPrice.textContent = form.price;
    dLink.href = v.url || m.url; dLink.firstChild.textContent = 'Im Shop ansehen ';
    // scene + form previews show the currently selected form / colour
    list.querySelectorAll('.scene-btn').forEach(b => { b.style.backgroundImage = `url("assets/lava/${b.dataset.id}/thumb__${form.id}__${colour.id}.webp?v=3")`; });
    formsEl.querySelectorAll('.form-btn img').forEach((img, i) => { const t = (m.forms[i].variants[colour.id] || {}).thumb; if (t && !img.src.endsWith(t)) img.src = t; });
    if (window.gsap && !RM) gsap.fromTo(dName, {y:14, opacity:.4}, {y:0, opacity:1, duration:.6, ease:'power3.out'});
  }
  const start = () => fetch('assets/lava/catalog.json', {cache:'no-store'}).then(r => r.ok ? r.json() : null).then(c => {
    if (!c || !c.scenes || !c.scenes.length) return ATELIER.start();
    m = c; window.__atelier2 = true;
    stage.hidden = false; stage.classList.add('portrait'); atCanvas.hidden = true; hint.hidden = true; grid.classList.add('has-scenes', 'lava'); ctl.hidden = false;
    list.innerHTML = '';
    m.scenes.forEach(s => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'scene-btn'; b.dataset.id = s.id;
      b.style.backgroundImage = `url("${s.thumb}?v=3")`; b.innerHTML = `<span>${s.name}</span>`;
      b.addEventListener('click', () => { scene = s; press(list, '.scene-btn', b); draw(); }); list.appendChild(b);
    });
    formsEl.innerHTML = '';
    m.forms.forEach(f => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'form-btn photo';
      b.innerHTML = `<img src="${f.thumb}" alt="" decoding="async"><span>${f.name}</span>`; b.setAttribute('aria-label', `${f.name}, ${f.size}`);
      b.addEventListener('click', () => { form = f; press(formsEl, '.form-btn', b); detail(); draw(); }); formsEl.appendChild(b);
    });
    groupsEl.previousElementSibling.textContent = 'Farbe';
    groupsEl.innerHTML = '<div class="swatches" role="group" aria-label="Farben"></div>';
    m.colours.forEach(col => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'sw'; b.style.setProperty('--c', col.hex);
      b.title = col.name; b.setAttribute('aria-label', col.name);
      b.addEventListener('click', () => { colour = col; press(groupsEl, '.sw', b); detail(); draw(); }); groupsEl.firstChild.appendChild(b);
    });
    const lead = document.querySelector('.at-head .lead');
    scene = m.scenes[0]; form = m.forms[0]; colour = m.colours[0];
    press(list, '.scene-btn', list.firstChild); press(formsEl, '.form-btn', formsEl.firstChild); press(groupsEl, '.sw', groupsEl.querySelector('.sw'));
    detail(); draw();
  }).catch(e => { console.warn(e); ATELIER.start(); });
  start();
  return {draw};
})();

function updateDetail(){
  if (window.__atelier2) return;
  dName.textContent = at.cname; dColl.textContent = at.coll.name; dForm.textContent = at.form.name; dPrice.textContent = at.form.price;
  dLink.href = at.coll.url;
  if (SCENE.active()) SCENE.draw();
  if (window.gsap && !RM) gsap.fromTo(dName, {y:14, opacity:.4}, {y:0, opacity:1, duration:.6, ease:'power3.out'});
}

/* ---------------- Collections ---------------- */
// Blender product shots (assets/products/<id>.webp) replace the code-drawn vessel; canvas Pot stays as fallback.
function useRender(canvas, url, fallback){
  const img = new Image(); img.decoding = 'async';  // no loading=lazy: a detached image would never load
  img.alt = canvas.getAttribute('aria-label') || ''; img.className = 'render';
  img.onload = () => canvas.replaceWith(img);
  img.onerror = fallback;
  img.src = url;
}
// Real shop photos (cut out, tools/cutout.py + atelier2_publish.py); Blender render, then canvas Pot as fallbacks.
const PHOTO = {loft:'loft/new-egg-pot/rust-brown', terra:'terra/tall-egg-pot/champagne-white', antique:'antique-stone/new-egg-pot/copper-green',
  lava:'lava/u-pot/volcanic-black', pure:'pure/high-balloon/santorin-white', granite:'granite/new-egg-pot/granite-grey',
  vertical:'vertical-lines/classic-egg-pot/vertical-white', empire:'heritage/hampshire/classic-lead'};
const usePhoto = (cv, cid, fallback) => useRender(cv, `assets/pots/${PHOTO[cid]}.webp`, () => useRender(cv, `assets/products/${cid}.webp`, fallback));
/* Collections: the shop's own collection photos (eschbach-design.com/collections, 1100x1400) in two columns.
   Pairs sit side by side; the right column starts lower and scrolls a little faster (parallax), every image
   reveals bottom-up while it enters -> the pictures come up slightly offset. Order = shop order. */
const CGRID = [['loft','Loft'],['terra','Terra'],['pure','Pure'],['empire','Empire'],['lava','Lava'],['vertical','Vertical Lines'],['antique','Antique'],['granite','Granite']];
const cgrid = document.getElementById('cgrid'), cstage = document.getElementById('cstage');
if (cstage){
  // one image after the other, alternating left / right; each comes up from the bottom into the centre
  CGRID.forEach(([cid, name], i) => {
    const coll = COLL.find(c => c.id === cid);
    const slot = document.createElement('div'); slot.className = 'cslot ' + (i % 2 ? 'r' : 'l'); slot.style.zIndex = i + 1;
    const a = document.createElement('a'); a.className = 'ctile';
    a.href = coll ? coll.url : 'https://eschbach-design.com/collections'; a.target = '_blank'; a.rel = 'noopener';
    const src = `${i < 2 ? '' : 'data-'}src="assets/collections/${cid}-760.webp?v=2" ${i < 2 ? '' : 'data-'}srcset="assets/collections/${cid}-760.webp?v=2 760w, assets/collections/${cid}.webp?v=2 1100w"`;
    a.innerHTML = `<div class="cimg"><img ${src} sizes="(max-width: 600px) 100vw, 40vw" alt="${name} Collection" width="1100" height="1400"><i class="shade"></i></div>
      <div class="cap"><b>${name}</b><span>Ansehen</span></div>`;
    slot.appendChild(a); cstage.appendChild(slot);
  });
  // the remaining six must be fully loaded before they travel up, but must not compete with the hero
  let rest = false;
  const loadRest = () => { if (rest) return; rest = true;
    cstage.querySelectorAll('img[data-src]').forEach(im => { im.srcset = im.dataset.srcset; im.src = im.dataset.src; im.removeAttribute('data-src'); im.removeAttribute('data-srcset'); }); };
  if (document.readyState === 'complete') setTimeout(loadRest, 200); else addEventListener('load', () => setTimeout(loadRest, 200));
  addEventListener('scroll', loadRest, {once:true, passive:true});
}

/* ---------------- Material loupe ---------------- */
const tabsEl = document.getElementById('tabs'), flat = document.getElementById('flat'), fctx = flat.getContext('2d');
const lensC = document.getElementById('lensC'), lctx = lensC.getContext('2d'), lens = document.getElementById('lens'), surf = document.getElementById('surface');
const matChoices = [['loft',2],['terra',1],['antique',1],['lava',0],['granite',0],['vertical',0]];
let lensPos = {x:.62, y:.48};
// Blender surface macros (assets/textures/<id>.webp); procedural texture stays as fallback.
const texImgs = {}; let flatSel = '';
function renderFlat(cid, ci){
  const coll0 = COLL.find(c=>c.id===cid);
  const done = img => { flat.width = img.naturalWidth; flat.height = img.naturalHeight; fctx.drawImage(img, 0, 0);
    drawLens(); };
  const cached = texImgs[cid];
  if (cached === false) { flatSel = cid; return renderFlatProcedural(cid, ci); }
  if (cached) { flatSel = cid; return done(cached); }
  const img = new Image(), full = `assets/textures/${cid}.webp`, sel = flatSel = cid;
  const big = surf.offsetWidth * 3 * Math.min(2, window.devicePixelRatio || 1) > 2600;
  const prev = new Image();                                       // ~20 KB preview (tools/optimize_images.py -480) -> no empty box
  prev.onload = () => { if (flatSel === sel && !texImgs[cid]) done(prev); };
  prev.src = `assets/textures/${cid}-480.webp`;
  img.onload = () => { texImgs[cid] = img; if (flatSel === sel) done(img); };
  img.onerror = () => { if (!img.src.endsWith(full)) { img.src = full; return; } texImgs[cid] = false; renderFlatProcedural(cid, ci); };
  img.src = big ? full : `assets/textures/${cid}-2400.webp`;
}
function renderFlatProcedural(cid, ci){
  flat.width = 960; flat.height = 540;
  const coll = COLL.find(c=>c.id===cid), col = hex(coll.colors[ci][1]), alt = coll.colors[ci][2] ? hex(coll.colors[ci][2]) : null;
  const F = FIN[coll.finish], T = tex(coll.finish), t = T.t, m = T.m;
  const W = flat.width, H = flat.height, img = fctx.createImageData(W,H), d = img.data, sc = .9;
  for (let y=0;y<H;y++){
    const vy = Math.floor(y*sc) & MASK;
    const shade = 1 - Math.abs(y/H - .4)*.35;
    for (let x=0;x<W;x++){
      const ux = Math.floor(x*sc) & MASK, i = vy*TEX + ux;
      const gx = t[vy*TEX + ((ux+1)&MASK)] - t[vy*TEX + ((ux-1)&MASK)];
      const gy = t[(((vy+1)&MASK)*TEX) + ux] - t[(((vy-1)&MASK)*TEX) + ux];
      let emb = 1 + (-gx*.9 - gy*.6)*F.amp*3.2;
      if (F.ribs) emb *= .84 + .16*Math.sin(x*.16);
      let f = (1 + t[i]*F.amp)*emb*shade;
      let r=col[0], g=col[1], b=col[2]; if (m && alt){ const q = m[i]*.75; r+=(alt[0]-r)*q; g+=(alt[1]-g)*q; b+=(alt[2]-b)*q; }
      const p = (y*W+x)*4; d[p]=r*f; d[p+1]=g*f; d[p+2]=b*f; d[p+3]=255;
    }
  }
  fctx.putImageData(img,0,0); drawLens();
}
function drawLens(){
  const W = flat.width, H = flat.height, zoom = 3;
  const want = Math.round(lens.offsetWidth * Math.min(3, window.devicePixelRatio || 1));   // crisp on HiDPI
  if (want && lensC.width !== want){ lensC.width = lensC.height = want; }
  const lw = lensC.width, src = (lens.offsetWidth / surf.offsetWidth) * W / zoom;
  const sx = lensPos.x*W - src/2, sy = lensPos.y*H - src/2;
  lctx.imageSmoothingEnabled = true; lctx.imageSmoothingQuality = 'high'; lctx.clearRect(0,0,lw,lw);
  lctx.drawImage(flat, sx, sy, src, src, 0, 0, lw, lw);
  lens.style.left = (lensPos.x*100)+'%'; lens.style.top = (lensPos.y*100)+'%';
}
matChoices.forEach(([cid,ci], i) => {
  const coll = COLL.find(c=>c.id===cid);
  const b = document.createElement('button'); b.type='button'; b.className='tab'; b.setAttribute('role','tab'); b.setAttribute('aria-selected', i===0);
  b.textContent = coll.name;
  b.addEventListener('click', () => { tabsEl.querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected', x===b)); renderFlat(cid, ci); });
  tabsEl.appendChild(b);
});
surf.addEventListener('pointermove', e => {
  const r = surf.getBoundingClientRect();
  lensPos.x = Math.min(.96, Math.max(.04, (e.clientX - r.left)/r.width));
  lensPos.y = Math.min(.94, Math.max(.06, (e.clientY - r.top)/r.height));
  drawLens();
});
let flatDone = false;
const flatIO = new IntersectionObserver(es => { if (es[0].isIntersecting && !flatDone){ flatDone = true; renderFlat('loft',2); } }, {rootMargin:'900px'});
flatIO.observe(surf);

/* ---------------- Theme toggle ---------------- */
const themeBtn = document.getElementById('themeBtn');
function effTheme(){ const a = root.getAttribute('data-theme'); if (a === 'dark' || a === 'light') return a; return matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'; }
// fixed light brand look (no toggle any more): drop a value saved by the old theme switch
try { localStorage.removeItem('eschbach-theme'); } catch(e){}
root.setAttribute('data-theme', 'light');
function refreshTheme(){ readTheme(); pots.forEach(p => p.dirty = true); }
if (themeBtn) themeBtn.addEventListener('click', () => {
  const next = effTheme() === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  try { localStorage.setItem('eschbach-theme', next); } catch(e){}
  requestAnimationFrame(refreshTheme); setTimeout(refreshTheme, 650);
});
matchMedia('(prefers-color-scheme: light)').addEventListener?.('change', refreshTheme);
new MutationObserver(refreshTheme).observe(root, {attributes:true, attributeFilter:['data-theme']});
readTheme();

/* ---------------- Nav ---------------- */
const nav = document.getElementById('nav');
// light nav while it sits on the hero picture (plain scroll check: also right at the very top and after jumps)
const heroEl = document.getElementById('hero');
const darkEls = [...document.querySelectorAll('.manifest, .band, footer')];   // dark sections: nav becomes a dark bar over them
const navState = () => {
  const onHero = !!heroEl && scrollY < heroEl.offsetHeight - 72, mid = nav.offsetHeight / 2;
  nav.classList.toggle('scrolled', scrollY > 20); nav.classList.toggle('on-hero', onHero);
  nav.classList.toggle('on-dark', !onHero && darkEls.some(el => { const r = el.getBoundingClientRect(); return r.top <= mid && r.bottom >= mid; }));
};
addEventListener('scroll', navState, {passive:true}); addEventListener('resize', navState); navState();
// newsletter: sign-up happens in the shop (footer link), no form on this page

/* ---------------- Resize ---------------- */
let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { pots.forEach(p => p.fit()); if (flatDone) drawLens(); }, 150); });

/* ---------------- Phone / tablet menu ---------------- */
const menuBtn = document.getElementById('menuBtn'), menu = document.getElementById('menu');
function setMenu(open){
  if (!menu || menu.hidden === !open) return;
  root.classList.toggle('menu-open', open);
  menuBtn.setAttribute('aria-expanded', open); menuBtn.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
  menu.hidden = !open;
  if (lenis) open ? lenis.stop() : lenis.start();
  if (open && window.gsap && !RM) gsap.fromTo(menu.querySelectorAll('a'), {y:18, opacity:0}, {y:0, opacity:1, duration:.5, ease:'power3.out', stagger:.05});
}
if (menuBtn && menu){
  menuBtn.addEventListener('click', () => setMenu(menu.hidden));
  menu.addEventListener('click', e => { if (e.target.closest('a')) setMenu(false); }, true);   // capture: close (and restart Lenis) before the anchor scrolls
  addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });
  matchMedia('(min-width: 961px)').addEventListener('change', e => { if (e.matches) setMenu(false); });
}

/* ---------------- Manifest words ---------------- */
const man = document.getElementById('manifest');
man.innerHTML = man.textContent.split(' ').map(w => `<span class="w">${w}</span>`).join(' ');

/* ---------------- Motion (GSAP + Lenis) ---------------- */
let lenis = null;
if (!(window.gsap && window.ScrollTrigger)) root.classList.add('no-motion');
if (RM) root.classList.add('reduce-motion');
if (window.gsap && window.ScrollTrigger){
  gsap.registerPlugin(ScrollTrigger);
  if (!RM && window.Lenis){
    lenis = new Lenis({lerp:.1, smoothWheel:true});
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add(t => lenis.raf(t*1000)); gsap.ticker.lagSmoothing(0);
  }
  // Hero: full-bleed photo/video at every width, the nav sits on it (light); gentle zoom-out on load, slow drift on scroll
  const heroSec = document.getElementById('hero'), heroImg = heroSec && heroSec.querySelector('.hp-media');   // figure: photo + video move together
  const phone = () => matchMedia('(max-width: 700px)').matches;
  if (heroSec){
    if (!RM && heroImg){
      gsap.fromTo(heroImg, {scale:1.12}, {scale:1, duration:2, ease:'power3.out'});
      gsap.from('.hp-copy > *', {y:28, opacity:0, duration:1.1, ease:'power3.out', stagger:.12, delay:.25});
      gsap.to(heroImg, {yPercent:7, ease:'none', scrollTrigger:{trigger:heroSec, start:'top top', end:'bottom top', scrub:true}});
    }
  }
  const words = man.querySelectorAll('.w');
  ScrollTrigger.create({trigger:man, start:'top 78%', end:'bottom 45%', onUpdate:s => { const n = Math.round(s.progress*words.length); words.forEach((w,i) => w.classList.toggle('on', i < n)); }});
  if (!RM){
    gsap.utils.toArray('.at-head, .colls-head, .mat-copy, .loupe-wrap, .xxl-copy, .scale, .since-copy, .markets, .f-top').forEach(el => {
      gsap.from(el, {y:40, opacity:.35, duration:1.1, ease:'power3.out', scrollTrigger:{trigger:el, start:'top 88%'}});
    });
    // relay: only ever one image sprints. Image i waits (lagging just below the screen) until image i-1 has
    // locked in near the top; then it rises fast from the bottom edge, visibly catching up with the now slower
    // (normally scrolling) image i-1, and locks in near the top itself -> then image i+1 starts, and so on.
    if (cstage && matchMedia('(max-width: 600px)').matches){
      // phone: one full-width column; each image comes up fast, overlaps the one above and locks in near the top
      gsap.utils.toArray('#cstage .cslot').forEach((slot, i) => {
        if (!i) return;
        // rises faster than the page, slides over the image above and locks in only near the top (15 %)
        gsap.fromTo(slot.firstElementChild, {y:() => window.innerHeight * .4}, {y:0, ease:'power1.out',
          scrollTrigger:{trigger:slot, start:'top bottom', end:'top 15%', scrub:.8, invalidateOnRefresh:true}});
      });
    } else if (cstage){
      const slots = gsap.utils.toArray('#cstage .cslot'), LOCK = .3;   // .12 -> .3: next image starts and locks in earlier, less empty space
      slots.forEach((slot, i) => {
        if (!i) return;
        const prev = slots[i - 1];
        // start offset: put the image right at the bottom edge when its sprint begins
        const lag = () => Math.max(window.innerHeight * (1 - LOCK) - (slot.offsetTop - prev.offsetTop), window.innerHeight * .25);
        gsap.fromTo(slot.firstElementChild, {y:lag}, {y:0, ease:'none',
          scrollTrigger:{trigger:prev, start:`top ${LOCK * 100}%`, endTrigger:slot, end:`top ${LOCK * 100}%`, scrub:1, invalidateOnRefresh:true}});
      });
    }
    const xp = document.querySelector('.xxl-photo img');
    if (xp) gsap.fromTo(xp, {scale:1.14, yPercent:-4}, {scale:1, yPercent:4, ease:'none', scrollTrigger:{trigger:'.xxl-photo', start:'top bottom', end:'bottom top', scrub:true}});
    document.querySelectorAll('[data-count]').forEach(el => {
      const to = +el.dataset.count, from = el.hasAttribute('data-plain') ? 1900 : 0, o = {v:from};
      ScrollTrigger.create({trigger:el, start:'top 90%', once:true, onEnter:() => gsap.fromTo(o, {v:from}, {v:to, duration:1.8, ease:'power2.out', onUpdate:() => el.textContent = Math.round(o.v)})});
    });
  }
  const yearEl = document.getElementById('year');
  ScrollTrigger.create({trigger:'#manufaktur', start:'top 70%', end:'bottom 70%', scrub:true, onUpdate:s => {
    const y = Math.round(1976 + 50*s.progress); yearEl.innerHTML = y === 2026 ? '20<em>26</em>' : String(y);
  }});
}
document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', e => {
  const id = a.getAttribute('href'); const el = id.length > 1 ? document.querySelector(id) : document.body; if (!el) return;
  e.preventDefault();
  if (lenis) lenis.scrollTo(el, {offset: id === '#top' ? 0 : -72, duration:1.4});
  else el.scrollIntoView({behavior: RM ? 'auto' : 'smooth'});
}));

requestAnimationFrame(() => { pots.forEach(p => p.fit()); loop(); updateDetail(); });
})();
