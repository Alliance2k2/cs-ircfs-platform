'use strict';
const menuBtn=document.getElementById('menuBtn');
const nav=document.getElementById('nav');
menuBtn.addEventListener('click',()=>{const open=nav.classList.toggle('open');menuBtn.setAttribute('aria-expanded',String(open));menuBtn.setAttribute('aria-label',open?'Close navigation':'Open navigation')});
nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');menuBtn.setAttribute('aria-expanded','false')}));
document.getElementById('year').textContent=new Date().getFullYear();
const revealItems=document.querySelectorAll('.reveal');
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{for(const e of entries){if(e.isIntersecting){e.target.classList.add('visible');observer.unobserve(e.target)}}},{threshold:.12});revealItems.forEach(el=>observer.observe(el))}else revealItems.forEach(el=>el.classList.add('visible'));
// Only verified project constants appear in the counters (not live metrics).
const counters=document.querySelectorAll('[data-count]');
function animateCount(el){const end=Number(el.dataset.count),suffix=el.dataset.suffix||'';if(matchMedia('(prefers-reduced-motion: reduce)').matches){el.textContent=end+suffix;return}let start=0;const duration=1200,begin=performance.now();function frame(now){const t=Math.min((now-begin)/duration,1),ease=1-Math.pow(1-t,3);el.textContent=(Number.isInteger(end)?Math.round(end*ease):(end*ease).toFixed(1))+suffix;if(t<1)requestAnimationFrame(frame)}requestAnimationFrame(frame)}
if('IntersectionObserver' in window){const co=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){animateCount(e.target);co.unobserve(e.target)}})},{threshold:.7});counters.forEach(x=>co.observe(x))}
const translations={en:{nav:['Our mission','Solutions','Our approach','Pilot projects','FAQs'],label:'EN'},rw:{nav:['Intego yacu','Ibisubizo','Uko dukora','Imishinga y’igerageza','Ibibazo'],label:'RW'}};
// Navigation language preview, rather than an inaccurate claim of full translation.
let lang='en';document.getElementById('langBtn').addEventListener('click',()=>{lang=lang==='en'?'rw':'en';document.getElementById('langLabel').textContent=translations[lang].label;nav.querySelectorAll('a').forEach((a,i)=>a.textContent=translations[lang].nav[i]);document.getElementById('langBtn').title=lang==='rw'?'Navigation translated; full page is English':'English navigation'});
// Keep one FAQ expanded for a tidy reading experience.
document.querySelectorAll('.faq-list details').forEach(d=>d.addEventListener('toggle',()=>{if(d.open)document.querySelectorAll('.faq-list details').forEach(other=>{if(other!==d)other.open=false})}));
