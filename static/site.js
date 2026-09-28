/* The page-wide parts of main.js, for pages without the two demos (ADR 0007).
   main.js stops at the first demo element it cannot find, so these pages load this
   file instead. Each block below is copied from main.js unchanged. */

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
