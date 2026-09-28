/* cursor */
(function(){
  if(matchMedia('(hover:none)').matches)return;
  const d=document.getElementById('cdot'),r=document.getElementById('cring');
  let mx=0,my=0,rx=0,ry=0;
  addEventListener('mousemove',e=>{mx=e.clientX;my=e.clientY;d.style.transform=`translate(${mx}px,${my}px)`;});
  (function t(){rx+=(mx-rx)*.17;ry+=(my-ry)*.17;r.style.transform=`translate(${rx}px,${ry}px)`;requestAnimationFrame(t);})();
  document.querySelectorAll('a,button,input[type=range],#plot').forEach(el=>{
    el.addEventListener('mouseenter',()=>r.classList.add('big'));
    el.addEventListener('mouseleave',()=>r.classList.remove('big'));});
})();

/* pointer parallax on background only, magnetic buttons */
(function(){
  if(matchMedia('(hover:none)').matches)return;
  const ps=[...document.querySelectorAll('[data-par]')];
  addEventListener('mousemove',e=>{
    const cx=e.clientX/innerWidth-.5, cy=e.clientY/innerHeight-.5;
    ps.forEach(el=>{const k=+el.dataset.par;el.style.transform=`translate(${cx*k*26}px,${cy*k*26}px)`;});
  });
  document.querySelectorAll('.mag').forEach(b=>{
    b.addEventListener('mousemove',e=>{const r=b.getBoundingClientRect();
      b.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.22}px,${(e.clientY-r.top-r.height/2)*.3}px)`;});
    b.addEventListener('mouseleave',()=>b.style.transform='translate(0,0)');});
})();

/* scroll parallax on project rows */
(function(){
  const rows=[...document.querySelectorAll('[data-scroll]')];
  if(!rows.length)return;
  let ticking=false;
  function upd(){
    const vh=innerHeight;
    rows.forEach(el=>{const r=el.getBoundingClientRect();
      const p=(r.top+r.height/2-vh/2)/vh;
      el.style.transform=`translateY(${p*+el.dataset.scroll*-16}px)`;});
    ticking=false;
  }
  addEventListener('scroll',()=>{if(!ticking){requestAnimationFrame(upd);ticking=true;}},{passive:true});
  upd();
})();

/* ticker */
(function(){
  const items=['Python','SQL','R','Java','pandas','NumPy','scikit-learn','Machine learning',
               'Data engineering','Credit risk','NLP','Model evaluation','Git'];
  const h=items.map(t=>`<span>${t} <i>/</i></span>`).join('');
  document.getElementById('mq').innerHTML=h+h;
})();

/* sparklines */
(function(){
  document.querySelectorAll('.spk').forEach(cv=>{
    const dpr=devicePixelRatio||1,w=150,h=52;
    cv.width=w*dpr;cv.height=h*dpr;const c=cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);
    let s=+cv.dataset.seed;const rnd=()=>(s=(s*9301+49297)%233280)/233280;
    const n=26,v=[];let y=h*.6;
    for(let i=0;i<n;i++){y+=(rnd()-.48)*11;y=Math.max(8,Math.min(h-8,y));v.push(y);}
    c.strokeStyle='#9A7A24';c.lineWidth=1.4;c.beginPath();
    v.forEach((p,i)=>{const x=i/(n-1)*w;i?c.lineTo(x,p):c.moveTo(x,p);});c.stroke();
    c.lineTo(w,h);c.lineTo(0,h);c.closePath();
    const g=c.createLinearGradient(0,0,0,h);
    g.addColorStop(0,'rgba(154,122,36,.16)');g.addColorStop(1,'rgba(154,122,36,0)');
    c.fillStyle=g;c.fill();
  });
})();

/* credit model */
(function(){
  const F=[
    {id:'inc', n:'Income',        w:-1.85, mn:20000, mx:200000, f:v=>'$'+(+v).toLocaleString()},
    {id:'dti', n:'Debt to income',w: 2.55, mn:0, mx:60,  f:v=>v+'%'},
    {id:'util',n:'Utilization',   w: 2.05, mn:0, mx:100, f:v=>v+'%'},
    {id:'hist',n:'History length',w:-1.45, mn:0, mx:240, f:v=>v+' months'},
    {id:'late',n:'Late payments', w: 2.25, mn:0, mx:10,  f:v=>v}
  ];
  const B0=-2.0,$=i=>document.getElementById(i);
  $('bars').innerHTML=F.map(f=>`<div class="bar"><div class="barh"><span>${f.n}</span>
    <b id="c_${f.id}">0.00</b></div><div class="trk"><div class="mid"></div>
    <div class="fill" id="b_${f.id}"></div></div></div>`).join('');
  function run(){
    let z=B0,parts=[];
    F.forEach(f=>{const raw=+$('s_'+f.id).value,nm=(raw-f.mn)/(f.mx-f.mn),c=f.w*nm;
      z+=c;parts.push({f,c});$('v_'+f.id).textContent=f.f(raw);});
    const pd=1/(1+Math.exp(-z));
    $('pd').textContent=(pd*100).toFixed(1)+'%';
    $('arc').style.strokeDashoffset=(257.6*(1-pd)).toFixed(1);
    let band,col;
    if(pd<.05){band='Very low risk';col='#2F7D4F';}
    else if(pd<.15){band='Low risk';col='#5A8F38';}
    else if(pd<.30){band='Moderate risk';col='#9A7A24';}
    else if(pd<.50){band='Elevated risk';col='#B4691C';}
    else{band='High risk';col='#A93526';}
    const b=$('band');b.textContent=band;b.style.color=col;
    $('arc').style.stroke=col;$('pd').style.color=col;
    const mxv=Math.max(...parts.map(p=>Math.abs(p.c)),.01);
    parts.forEach(p=>{const el=$('b_'+p.f.id),pct=Math.abs(p.c)/mxv*50;
      if(p.c>=0){el.style.left='50%';el.style.right='auto';el.style.background=col;}
      else{el.style.right='50%';el.style.left='auto';el.style.background='#5A8F38';}
      el.style.width=pct+'%';
      $('c_'+p.f.id).textContent=(p.c>=0?'+':'')+p.c.toFixed(2);});
  }
  F.forEach(f=>$('s_'+f.id).addEventListener('input',run));run();
})();

/* least squares */
(function(){
  const cv=document.getElementById('plot'),cx=cv.getContext('2d');
  let pts=[],W,H,dpr=devicePixelRatio||1;
  function size(){W=cv.offsetWidth;H=cv.offsetHeight;cv.width=W*dpr;cv.height=H*dpr;
    cx.setTransform(dpr,0,0,dpr,0,0);draw();}
  function fit(){
    const n=pts.length;if(n<2)return null;
    const mx=pts.reduce((s,p)=>s+p.x,0)/n,my=pts.reduce((s,p)=>s+p.y,0)/n;
    let sxy=0,sxx=0;pts.forEach(p=>{sxy+=(p.x-mx)*(p.y-my);sxx+=(p.x-mx)**2;});
    if(sxx===0)return null;
    const m=sxy/sxx,b=my-m*mx;let ssr=0,sst=0;
    pts.forEach(p=>{ssr+=(p.y-(m*p.x+b))**2;sst+=(p.y-my)**2;});
    return{m,b,r2:sst?1-ssr/sst:1};
  }
  function draw(){
    cx.clearRect(0,0,W,H);
    cx.strokeStyle='#E5E1D8';cx.lineWidth=1;
    for(let i=1;i<6;i++){const y=H/6*i;cx.beginPath();cx.moveTo(0,y);cx.lineTo(W,y);cx.stroke();}
    for(let i=1;i<8;i++){const x=W/8*i;cx.beginPath();cx.moveTo(x,0);cx.lineTo(x,H);cx.stroke();}
    const r=fit();
    if(r){
      cx.strokeStyle='rgba(154,122,36,.3)';cx.lineWidth=1;cx.setLineDash([3,4]);
      pts.forEach(p=>{cx.beginPath();cx.moveTo(p.x,H-p.y);cx.lineTo(p.x,H-(r.m*p.x+r.b));cx.stroke();});
      cx.setLineDash([]);
      cx.strokeStyle='#9A7A24';cx.lineWidth=2.2;cx.beginPath();
      cx.moveTo(0,H-r.b);cx.lineTo(W,H-(r.m*W+r.b));cx.stroke();
      document.getElementById('m_slope').textContent=r.m.toFixed(3);
      document.getElementById('m_int').textContent=r.b.toFixed(1);
      document.getElementById('m_r2').textContent=r.r2.toFixed(3);
    }else{['m_slope','m_int','m_r2'].forEach(i=>document.getElementById(i).textContent='—');}
    pts.forEach(p=>{cx.fillStyle='#15171C';cx.beginPath();cx.arc(p.x,H-p.y,4.5,0,7);cx.fill();
      cx.strokeStyle='#FCFBF8';cx.lineWidth=1.5;cx.stroke();});
  }
  cv.addEventListener('click',e=>{const r=cv.getBoundingClientRect();
    pts.push({x:e.clientX-r.left,y:H-(e.clientY-r.top)});draw();});
  document.getElementById('b_seed').onclick=()=>{
    for(let i=0;i<14;i++){const x=W*(.07+.86*Math.random());
      pts.push({x,y:H*.18+x*.4+(Math.random()-.5)*H*.22});}draw();};
  document.getElementById('b_out').onclick=()=>{pts.push({x:W*.85,y:H*.05});draw();};
  document.getElementById('b_clear').onclick=()=>{pts=[];draw();};
  addEventListener('resize',size);size();
  setTimeout(()=>document.getElementById('b_seed').click(),650);
})();

/* email chooser */
(function(){
  const b=document.getElementById('mailbtn'),m=document.getElementById('mailmenu'),
        c=document.getElementById('mailcopy'),addr='iliyavalizadeh60@gmail.com';
  if(!b)return;
  b.addEventListener('click',e=>{e.stopPropagation();
    const o=m.classList.toggle('open');b.setAttribute('aria-expanded',o);});
  document.addEventListener('click',e=>{if(!m.contains(e.target)){m.classList.remove('open');
    b.setAttribute('aria-expanded','false');}});
  addEventListener('keydown',e=>{if(e.key==='Escape'){m.classList.remove('open');
    b.setAttribute('aria-expanded','false');}});
  c.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(addr);}catch(_){
      const t=document.createElement('textarea');t.value=addr;document.body.appendChild(t);
      t.select();document.execCommand('copy');t.remove();}
    const old=c.textContent;c.textContent='Copied';
    setTimeout(()=>{c.textContent=old;},1600);
  });
})();

/* reveal + nav */
(function(){
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){
    e.target.classList.add('in');io.unobserve(e.target);}}),{threshold:.1,rootMargin:'0px 0px -50px'});
  document.querySelectorAll('.rv').forEach(el=>io.observe(el));
  addEventListener('scroll',()=>document.getElementById('nav').classList.toggle('solid',scrollY>60));
})();
