'use strict';
const D = JSON.parse(document.getElementById('story-data').textContent);
const A = D.atlas;
const nodes = new Map(A.nodes.map(n => [n.id,n]));
const people = new Map(D.people.map(p => [p.id,p]));
const sources = new Map(A.sources.map(s => [s.id,s]));
const chapters = new Map(D.chapters.map(c => [c.id,c]));
const hubs = [...A.clusters.map(c=>nodes.get(c.hub)),...A.extension_map.map(c=>nodes.get(c.hub))];
const film = D.cinema;
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (n,min,max) => Math.min(max,Math.max(min,n));
const external = (url,title) => `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title)} ↗</a>`;
const pdfLink = page => `../../走出戈壁-单伟健.pdf#page=${page}`;
const nodeButton = (id,label,cls='') => `<button class="${cls}" data-open="${esc(id)}">${esc(label || nodes.get(id).label)}</button>`;
const sceneType = {chapter:'人生主线',history:'时代与机制',scene:'原书场景',story:'人物与经历',extension:'书外续篇','extension-story':'书外故事'};
const state = {selected:null,lastFocus:null,relation:null,scale:1,x:0,y:0,fit:1,savedMap:null,filmIndex:0,filmOpen:false,playing:false,elapsed:0,tickAt:0,timer:null,filmFocus:null};

function renderMap(){
  $('mapClusters').innerHTML=A.clusters.map(c=>{
    const n=nodes.get(c.hub);
    return `<article class="cluster" data-hub="${n.id}" style="--x:${c.x};--y:${c.y}" aria-label="${n.number} ${esc(n.label)}">
      <button class="history-node" data-open="${c.history.id}"><span class="node-kind">时代背景</span><strong>${esc(c.history.label)}</strong></button>
      <span class="history-relation">${esc(c.history.relation)}</span>
      <button class="main-node" data-open="${n.id}"><span class="medallion">${n.number}</span><span class="node-date">${esc(n.date)} · ${esc(n.chapter)}</span><h3>${esc(n.label)}</h3><p>${esc(n.short)}</p></button>
      <div class="branch-pair">${c.branches.map(b=>`<button class="branch-node" data-open="${b.id}"><small>${esc(b.relation)}</small><strong>${esc(b.label)}</strong></button>`).join('')}</div></article>`;
  }).join('');
  const main='M 170 165 H 1235 C 1360 165 1395 190 1395 282 V 475 C 1395 561 1350 590 1235 590 H 170';
  let svg=`<defs><marker id="direction" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M1 1 L7 4 L1 7" fill="none" stroke="#cfb07b"/></marker></defs><path class="main-track-glow" d="${main}"/><path class="main-track" d="${main}"/>`;
  const labels=['愿望落空','被送下乡','争取出路','重返课堂','继续求学','走向实践','回望故人'];
  for(let i=0;i<7;i++){
    const a=A.clusters[i],b=A.clusters[i+1];
    if(i===3){svg+=`<text class="route-label" x="1371" y="383" text-anchor="middle" writing-mode="vertical-rl">${labels[i]}</text><path class="main-track" d="M1395 356 V383" marker-end="url(#direction)"/>`;continue;}
    const mid=(a.x+b.x)/2,dir=b.x>a.x?1:-1;
    svg+=`<text class="route-label" x="${mid}" y="${a.y-17}" text-anchor="middle">${labels[i]}</text><path class="main-track" d="M${mid-16*dir} ${a.y} h${32*dir}" marker-end="url(#direction)"/>`;
  }
  for(const c of A.clusters){
    svg+=`<path class="history-track" d="M${c.x} ${c.y-76} V${c.y-44}"/><path class="branch-track" d="M${c.x} ${c.y+168} V${c.y+173} M${c.x-76} ${c.y+179} V${c.y+173} H${c.x+76} V${c.y+179}"/>`;
  }
  $('mapPaths').innerHTML=svg;
  $('extensionMap').innerHTML=A.extension_map.map(c=>{
    const n=nodes.get(c.hub);
    return `<article class="extension-cluster" data-extension="${n.id}"><span class="extension-context">${esc(c.context)}</span><button class="extension-node" data-open="${n.id}"><span class="medallion">${n.number}</span><h3>${esc(n.label)}</h3><p>${esc(n.short)}</p></button>${c.branches.map(b=>`<button class="extension-branch" data-open="${b.id}"><small>${esc(b.relation)}</small><strong>${esc(b.label)}</strong></button>`).join('')}</article>`;
  }).join('');
  $('chapterNav').innerHTML=hubs.map(n=>`<button data-open="${n.id}" title="${esc(n.label)}" aria-label="${n.number} ${esc(n.label)}">${n.number}</button>`).join('');
  $('relationList').innerHTML=A.relations.map((r,i)=>`<button class="relation-tab" data-relation="${r.id}" aria-pressed="false"><small>0${i+1} / 贯穿线索</small><strong>${esc(r.label)}</strong><span>${esc(r.description)}</span></button>`).join('');
}

function refsFor(n){
  const grouped=new Map();
  for(const ref of [...(n.source_refs||[]),...(n.events||[]).flatMap(id=>nodes.get(id).source_refs)]){
    if(!grouped.has(ref.chapter_id))grouped.set(ref.chapter_id,new Set());
    for(const p of ref.pdf_pages)grouped.get(ref.chapter_id).add(p);
  }
  return [...grouped].map(([id,pages])=>({id,pages:[...pages].sort((a,b)=>a-b)}));
}
function renderSource(id){
  const s=sources.get(id);
  if(!s)return '';
  const who=s.publisher||s.organization||s.kind||s.type||'';
  const when=s.published_at||s.published||'';
  const supported=Array.isArray(s.supports)?s.supports.join('；'):s.supports||'';
  return `<div class="source-entry">${external(s.url,s.title)}<small>${esc(who)}${when?' · '+esc(when):''}</small>${supported?`<p>${esc(supported)}</p>`:''}</div>`;
}
function renderEvidence(n){
  const refs=refsFor(n),src=n.source_ids||[];
  return `<details class="evidence-block"><summary>依据与原文 · ${refs.length?`${refs.length} 组原书页码`:''}${refs.length&&src.length?' / ':''}${src.length?`${src.length} 项书外资料`:''}</summary>${refs.map(ref=>{
    const c=chapters.get(ref.id);
    return `<div class="source-entry">${external('../../book_reader/site/dist/index.html#'+c.section,c.title)}<div class="page-links">${ref.pages.map(p=>`<a href="${esc(pdfLink(p))}" target="_blank" rel="noopener" aria-label="原书 PDF 第 ${p} 页">${p}</a>`).join('')}</div><small>上方数字为 PDF 页码，点击可打开扫描原页。</small></div>`;
  }).join('')}${src.map(renderSource).join('')}${n.evidence_boundary?`<p class="boundary">材料说明：${esc(n.evidence_boundary)}</p>`:''}</details>`;
}
function renderPhoto(photo){
  if(!photo)return '';
  if(typeof photo==='number'){
    const stage=D.stages.find(s=>s.photo===photo);
    const caption=stage?.photo_caption||`原书 PDF 第 ${photo} 页照片，保留原页图注。`;
    return `<figure class="panel-figure"><a href="${esc(pdfLink(photo))}" target="_blank" rel="noopener"><img src="assets/page-${String(photo).padStart(3,'0')}.jpg" alt="${esc(caption)}" loading="lazy"></a><figcaption>${esc(caption)} ${external(pdfLink(photo),'原书 PDF '+photo)}</figcaption></figure>`;
  }
  const asset=A.images.find(i=>i.file===photo);
  return `<figure class="panel-figure cover"><img src="assets/${esc(photo)}" alt="${esc(asset?.title||(photo==='money-games.jpg'?'Money Games 书封':'Money Machine 书封'))}" loading="lazy"><figcaption>作者官网所示书封 · ${external('https://weijian-shan.com/books/','影像来源')}</figcaption></figure>`;
}
function admissionMechanism(){
  const gates=[['群众推荐','1974、1975年两次得票第二。投票不直接等于录取。','群众支持'],['候补与体检','战友争取候补；于医生改表；陈德才因肺部阴影落选。','援手、裁量与他人的受限'],['学校考查','李国忠考查朗读与作文。学校需要的能力，与多年准备在此相接。','准备开始被评价'],['师部批准','考试通过后仍需最终审批；直到1975年9月14日获批。','最后决定权'],['当晚离开','通知传来，当晚就走。火车开动后才真正放心。','机会终于变成现实']];
  return `<h3 class="panel-section-title">1975 年 · 离开的五道关口</h3><ol class="mechanism">${gates.map(g=>`<li><strong>${g[0]}</strong><p>${g[1]}</p><small>${g[2]}</small></li>`).join('')}</ol>`;
}
function renderPanel(n){
  const home=findHub(n.id),filmIndex=film.scenes.findIndex(s=>s.node===home?.id);
  const quote=n.quote||((n.kind==='chapter'&&n.events?.length)?nodes.get(n.events[0]).quote:null);
  const related=[...new Set(n.related||[])].filter(id=>id!==n.id);
  const scenes=(n.events||[]).filter(id=>!related.includes(id));
  const intro=n.kind==='scene'?'':`<p class="panel-intro">${esc(n.short)}</p>`;
  return `<p class="panel-kicker">${esc(sceneType[n.kind])}${n.number?' / '+n.number:''}</p><h2 class="panel-title" tabindex="-1">${esc(n.title)}</h2><p class="panel-place">${esc([n.date,n.place].filter(Boolean).join(' · '))}</p>${intro}${filmIndex>=0?`<button class="node-film-button" data-film="${filmIndex}">▷ 放映这一段人生</button>`:''}<div class="panel-prose">${n.paragraphs.map(p=>`<p>${esc(p)}</p>`).join('')}</div>${n.id==='h4'||n.id==='history-admission'?admissionMechanism():''}${n.insight?`<div class="panel-insight"><span>从这里理解 · 阅读分析</span><p>${esc(n.insight)}</p></div>`:''}${quote?`<blockquote class="quote"><p>“${esc(quote.text)}”</p><cite>原书记述 · ${external(pdfLink(quote.pdf_page),'PDF 第 '+quote.pdf_page+' 页')}</cite></blockquote>`:''}${renderPhoto(n.photo)}${related.length?`<h3 class="panel-section-title">这件事与什么相连</h3><div class="linked-nodes">${related.map(id=>nodeButton(id,nodes.get(id).label)).join('')}</div>`:''}${n.people?.length?`<h3 class="panel-section-title">共同经历的人</h3>${n.people.map(id=>{const p=people.get(id);return `<div class="person-entry"><strong>${esc(p.name)}</strong><p>${esc(p.bio)}</p></div>`;}).join('')}`:''}${scenes.length?`<h3 class="panel-section-title">回到具体场景</h3><div class="linked-nodes">${scenes.map(id=>nodeButton(id,nodes.get(id).title)).join('')}</div>`:''}${renderEvidence(n)}`;
}
function findHub(id){
  const n=nodes.get(id);if(!n)return null;
  if(hubs.some(h=>h.id===id))return n;
  if(n.parent)return findHub(n.parent);
  return hubs.find(h=>h.events?.includes(id))||null;
}
function setHash(hash){try{history.replaceState(null,'',hash||location.pathname+location.search);}catch{}}
function focusMapNode(id){
  if(window.innerWidth<=1200)return;
  const hub=findHub(id),c=A.clusters.find(c=>c.hub===hub?.id);
  if(!c)return;
  const rect=$('mapViewport').getBoundingClientRect();
  state.scale=Math.max(state.fit,.9);state.x=rect.width/2-c.x*state.scale;state.y=rect.height/2-(c.y+50)*state.scale;applyMapTransform();
}
function openNode(id,{focus=true,hash=true}={}){
  const n=nodes.get(id);if(!n)return;
  if(!state.selected){state.savedMap={scale:state.scale,x:state.x,y:state.y};state.lastFocus=document.activeElement;}
  state.selected=id;$('detailPanel').hidden=false;document.body.classList.add('detail-open');
  const home=findHub(id);$('panelBack').textContent=n.parent?`← ${nodes.get(n.parent).number||''} ${nodes.get(n.parent).label}`:(home&&home.id!==id?`← ${home.label}`:'← 回到全景');
  $('panelBody').innerHTML=renderPanel(n);$('panelBody').scrollTop=0;
  document.querySelectorAll('[data-open]').forEach(el=>{el.classList.toggle('is-selected',el.dataset.open===id);if(el.closest('.chapter-nav')){el.classList.toggle('active',el.dataset.open===home?.id);el.setAttribute('aria-current',el.dataset.open===home?.id?'step':'false');}});
  if(hash)setHash('#node='+encodeURIComponent(id));
  if(focus)$('panelBody').querySelector('.panel-title')?.focus({preventScroll:true});
  resizeMap(false);focusMapNode(id);$('announcement').textContent=n.title;
}
function closePanel({focus=true}={}){
  if(!state.selected&&$('detailPanel').hidden)return;
  state.selected=null;$('detailPanel').hidden=true;document.body.classList.remove('detail-open');
  document.querySelectorAll('.is-selected,.chapter-nav .active').forEach(el=>el.classList.remove('is-selected','active'));
  resizeMap(true);if(state.savedMap){Object.assign(state,state.savedMap);applyMapTransform();}state.savedMap=null;
  setHash('');if(focus&&state.lastFocus?.isConnected)state.lastFocus.focus({preventScroll:true});
}
function showSources(){
  if(!state.selected){state.lastFocus=document.activeElement;state.savedMap={scale:state.scale,x:state.x,y:state.y};}
  state.selected='sources';$('detailPanel').hidden=false;document.body.classList.add('detail-open');$('panelBack').textContent='← 回到全景';
  $('panelBody').innerHTML=`<p class="panel-kicker">资料档案 / 2026.09</p><h2 class="panel-title" tabindex="-1">每一段解释，都能回到材料</h2><p class="sources-intro">原书是主要依据，场景中的引文已逐条对照页码文字。书外事实采用机构记录、正式交易文件与当事人采访；人物回忆与阅读分析分别标明。</p><h3 class="panel-section-title">原书与照片</h3><div class="source-entry">${external('../../book_reader/site/dist/index.html','完整原书文字阅读器')}<p>扫描文本经过 OCR，仍可能保留识别错误；涉及原文含义时可打开 PDF 页核对。照片使用原书整页，保留原图注。</p></div><h3 class="panel-section-title">网络资料</h3>${A.sources.map(s=>renderSource(s.id)).join('')}<h3 class="panel-section-title">影像</h3><div class="source-entry">${external('https://weijian-shan.com/biographyofweijianshan/','单伟建肖像 · 作者官网')}${external('https://weijian-shan.com/books/','两本交易著作封面 · 作者官网')}<p>肖像拍摄时间未注明。原书照片与官网图片用于本地阅读。</p></div><div class="source-entry"><p>节点地图背景与北京课堂、乌梁素海劳动、加州求学三张插画由 ImageGen 生成。它们是历史氛围的艺术表达，非现场史料照片，也不是作者实际教室、营房或书桌的复原。</p></div>`;
  $('panelBody').scrollTop=0;$('panelBody').querySelector('.panel-title')?.focus({preventScroll:true});setHash('#sources');resizeMap(false);
}
function selectRelation(id){
  const r=A.relations.find(r=>r.id===id);if(!r)return;
  state.relation=state.relation===id?null:id;
  document.querySelectorAll('[data-relation]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.relation===state.relation)));
  document.querySelectorAll('[data-open]').forEach(el=>el.classList.toggle('relation-highlight',Boolean(state.relation&&r.nodes.includes(el.dataset.open))));
  $('relationDetail').hidden=!state.relation;
  $('relationDetail').innerHTML=state.relation?`<p>${esc(r.text)}</p><div class="relation-links">${r.nodes.map(id=>nodeButton(id)).join('')}</div>`:'';
}
function applyMapTransform(){
  const v=$('mapViewport');
  const w=v.clientWidth,h=v.clientHeight;
  state.x=1420*state.scale<=w?(w-1420*state.scale)/2:clamp(state.x,w-1420*state.scale,0);
  state.y=870*state.scale<=h?(h-870*state.scale)/2:clamp(state.y,h-870*state.scale,0);
  $('mapWorld').style.transform=`translate(${state.x}px,${state.y}px) scale(${state.scale})`;
  $('zoomValue').textContent=Math.round(state.scale*100)+'%';
}
function resizeMap(reset=true){
  if(window.innerWidth<=1200)return;
  const width=$('mapViewport').clientWidth;
  state.fit=clamp(width/1420,.82,1.15);
  $('mapViewport').style.height=`${870*state.fit}px`;
  if(reset){state.scale=state.fit;state.x=0;state.y=0;}
  applyMapTransform();
}
function zoomMap(factor){
  const v=$('mapViewport'),before=state.scale,next=clamp(before*factor,.82,1.7);
  state.x=v.clientWidth/2-(v.clientWidth/2-state.x)*next/before;
  state.y=v.clientHeight/2-(v.clientHeight/2-state.y)*next/before;state.scale=next;applyMapTransform();
}
let drag=null;
$('mapViewport').addEventListener('pointerdown',e=>{
  if(window.innerWidth<=1200||e.target.closest('button,a')||e.button!==0)return;
  drag={x:e.clientX,y:e.clientY,oldX:state.x,oldY:state.y,id:e.pointerId};e.currentTarget.setPointerCapture(e.pointerId);e.currentTarget.classList.add('is-dragging');
});
$('mapViewport').addEventListener('pointermove',e=>{if(!drag)return;state.x=drag.oldX+e.clientX-drag.x;state.y=drag.oldY+e.clientY-drag.y;applyMapTransform();});
function stopDrag(){drag=null;$('mapViewport').classList.remove('is-dragging');}
$('mapViewport').addEventListener('pointerup',stopDrag);$('mapViewport').addEventListener('pointercancel',stopDrag);

function filmTick(){
  if(!state.playing)return;
  const now=performance.now();state.elapsed+=now-state.tickAt;state.tickAt=now;
  const length=film.scenes[state.filmIndex].duration_seconds*1000;
  $('filmProgress').style.width=Math.min(100,state.elapsed/length*100)+'%';
  if(state.elapsed>=length){if(state.filmIndex===film.scenes.length-1){pauseFilm();$('filmPlay').textContent='↺ 重新放映';}else showFilmScene(state.filmIndex+1);}
}
function pauseFilm(){state.playing=false;clearInterval(state.timer);state.timer=null;$('filmPlay').textContent='▷ 自动放映';$('filmPlay').setAttribute('aria-pressed','false');}
function playFilm(){
  if(state.playing){pauseFilm();return;}
  if(state.filmIndex===film.scenes.length-1&&state.elapsed>=film.scenes[state.filmIndex].duration_seconds*1000)showFilmScene(0);
  state.playing=true;state.tickAt=performance.now();state.timer=setInterval(filmTick,150);$('filmPlay').textContent='Ⅱ 暂停放映';$('filmPlay').setAttribute('aria-pressed','true');
}
function showFilmScene(index){
  state.filmIndex=clamp(index,0,film.scenes.length-1);state.elapsed=0;state.tickAt=performance.now();
  if(!state.playing)$('filmPlay').textContent='▷ 自动放映';
  const s=film.scenes[state.filmIndex],n=nodes.get(s.node);
  $('cinemaScene').className='cinema-scene'+(s.image.kind==='original'?' book-plate':'');
  $('cinemaScene').innerHTML=`<img src="assets/${esc(s.image.file)}" alt="${esc(s.image.alt)}">`;
  $('cinemaContent').innerHTML=`<p class="film-era">${n.number} / ${esc(n.label)}<br>${esc(n.date)}${n.place?' · '+esc(n.place):''}</p><h2 class="film-title">${esc(s.title)}</h2><div class="film-text-block"><span>时代与处境</span><p>${esc(s.era)}</p></div><div class="film-text-block"><span>他的经历</span><p>${esc(s.life)}</p></div>${s.sequence?`<div class="film-sequence" aria-label="离开的五道关口">${s.sequence.map(t=>`<span>${esc(t)}</span>`).join('')}</div>`:''}<p class="film-meaning">${esc(s.meaning)}</p><p class="film-caption">${esc(s.image.caption)}</p>`;
  $('filmPosition').textContent=`${state.filmIndex+1} / ${film.scenes.length} 幕 · ${state.filmIndex<12?'原书':'书外续篇'}`;
  $('filmChapters').innerHTML=hubs.map(h=>{const i=film.scenes.findIndex(s=>s.node===h.id);return `<button data-film-jump="${i}" class="${h.id===s.node?'current':i<state.filmIndex?'past':''}" aria-label="${h.number} ${esc(h.label)}" aria-current="${h.id===s.node?'step':'false'}"><span>${h.number}</span>${esc(h.label)}</button>`;}).join('');
  $('filmPrevious').disabled=state.filmIndex===0;$('filmNext').disabled=state.filmIndex===film.scenes.length-1;
  $('filmProgress').style.width='0%';$('cinema').scrollTop=0;$('announcement').textContent=`第 ${state.filmIndex+1} 幕，${s.title}`;
  if(state.filmOpen)setHash('#film='+encodeURIComponent(s.id));
}
function openFilm(index=0){
  state.filmFocus=document.activeElement;pauseFilm();state.filmOpen=true;$('cinema').hidden=false;document.body.classList.add('film-open');
  $('workspace').inert=true;document.querySelector('.masthead').inert=true;showFilmScene(index);$('closeFilm').focus();
}
function closeFilm({expand=false}={}){
  pauseFilm();state.filmOpen=false;$('cinema').hidden=true;document.body.classList.remove('film-open');$('workspace').inert=false;document.querySelector('.masthead').inert=false;
  if(expand){const id=film.scenes[state.filmIndex].node;openNode(id);const hubEl=document.querySelector(`[data-hub="${id}"]`)||document.querySelector(`[data-extension="${id}"]`);hubEl?.scrollIntoView({block:'center',behavior:'smooth'});}
  else{setHash(state.selected?(state.selected==='sources'?'#sources':'#node='+state.selected):'');state.filmFocus?.focus({preventScroll:true});}
}
function navigateHash(){
  const hash=decodeURIComponent(location.hash.slice(1));
  if(hash.startsWith('node=')){if(state.filmOpen)closeFilm();openNode(hash.slice(5),{hash:false});}
  else if(hash.startsWith('film=')){const index=film.scenes.findIndex(s=>s.id===hash.slice(5));if(index>=0)openFilm(index);}
  else if(hash==='sources')showSources();
}

document.addEventListener('click',e=>{
  const open=e.target.closest('[data-open]');if(open){openNode(open.dataset.open);return;}
  const rel=e.target.closest('[data-relation]');if(rel){selectRelation(rel.dataset.relation);return;}
  const start=e.target.closest('[data-film]');if(start){openFilm(Number(start.dataset.film));return;}
  const jump=e.target.closest('[data-film-jump]');if(jump){showFilmScene(Number(jump.dataset.filmJump));return;}
});
$('closePanel').addEventListener('click',()=>closePanel());
$('panelBack').addEventListener('click',()=>{const n=nodes.get(state.selected),home=n&&findHub(n.id);if(n?.parent)openNode(n.parent);else if(home&&home.id!==n.id)openNode(home.id);else closePanel();});
$('showSources').addEventListener('click',showSources);$('fitMap').addEventListener('click',()=>resizeMap(true));$('zoomIn').addEventListener('click',()=>zoomMap(1.17));$('zoomOut').addEventListener('click',()=>zoomMap(1/1.17));
$('filmLaunch').addEventListener('click',()=>openFilm(0));$('closeFilm').addEventListener('click',()=>closeFilm());$('filmPlay').addEventListener('click',playFilm);$('filmNext').addEventListener('click',()=>showFilmScene(state.filmIndex+1));$('filmPrevious').addEventListener('click',()=>showFilmScene(state.filmIndex-1));$('filmNode').addEventListener('click',()=>closeFilm({expand:true}));
document.addEventListener('keydown',e=>{
  if(state.filmOpen){
    if(e.key==='Escape'){e.preventDefault();closeFilm();}
    else if(e.key==='ArrowRight'){e.preventDefault();showFilmScene(state.filmIndex+1);}
    else if(e.key==='ArrowLeft'){e.preventDefault();showFilmScene(state.filmIndex-1);}
    else if(e.code==='Space'&&!e.repeat){e.preventDefault();playFilm();}
    else if(e.key==='Tab'){
      const items=[...$('cinema').querySelectorAll('button:not(:disabled),a[href]')];const first=items[0],last=items.at(-1);
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  }else if(e.key==='Escape')closePanel();
});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&state.playing)pauseFilm();});
window.addEventListener('resize',()=>{resizeMap(!state.selected);if(state.selected)focusMapNode(state.selected);});
window.addEventListener('hashchange',navigateHash);
renderMap();resizeMap(true);navigateHash();
