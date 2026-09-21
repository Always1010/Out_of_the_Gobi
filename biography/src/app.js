'use strict';
const story = JSON.parse(document.getElementById('story-data').textContent);
const land = JSON.parse(document.getElementById('land-data').textContent);
const guide = story.guide;
const indexById = items => Object.fromEntries(items.map(x=>[x.id,x]));
const stages=indexById(story.stages), events=indexById(story.events), people=indexById(story.people);
const places=indexById([...story.places,...guide.places]), threads=indexById(story.threads);
const sources=indexById(guide.sources), images=indexById(guide.images||[]);
const $=selector=>document.querySelector(selector);
const E=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reading=$('#reading');
const parts={orientation:'认识人物',book:'原书主线',extension:'书外续篇',reflection:'回看与继续探索'};
const bookmarkKey='gobi-guided-reading-v2';
let current=0,mapView='pacific',mapContext=null;
function narrativeHTML(step) {
  const names={'shibin':'石滨','liu-xiaotong':'刘小彤','li-rongtian':'李荣田','cui-xianchao':'崔贤超','doctor-yu':'于医生','yi-kong':'易空','yellen':'耶伦','teece':'提斯','casous':'卡苏夫妇','calhouns':'卡洪夫妇','ergou':'二狗'};
  const linked=new Set();
  return step.paragraphs.map(paragraph=>{
    let html=E(paragraph);
    for(const id of step.people){const name=names[id];if(name&&!linked.has(id)&&linked.size<2&&html.includes(name)){html=html.replace(name,`<button class="inline-person" data-person="${id}" aria-label="了解${name}在这段人生中的作用">${name}</button>`);linked.add(id);}}
    return `<p>${html}</p>`;
  }).join('');
}
function bookFeature(kind) {
  const games=kind==='games', image=images[games?'money-games-cover':'money-machine-cover'];
  if(!image)return '';
  const source=sources[games?'wiley-games':'wiley-machine'];
  return `<section class="book-feature"><img src="assets/${image.file}" alt="${E(image.alt)}" loading="lazy"><div><h2>${games?'Money Games':'Money Machine'}</h2><p>${games?'从谈判与重整的当事人视角，继续了解韩国第一银行。':'从当事人的回顾，继续了解深圳发展银行的交易与治理。'}</p><a href="${E(source.url)}" target="_blank" rel="noopener">出版社介绍 ↗</a><small>${games?'2020年首版；图为作者官网所示含追加内容封面。':'2023年出版。'} <a href="${E(image.source_url)}" target="_blank" rel="noopener">图片来源：作者官网</a></small></div></section>`;
}
function externalSources(step) {
  return `<ol class="evidence-list">${step.source_ids.map(id=>{const s=sources[id];return `<li><a href="${E(s.url)}" target="_blank" rel="noopener">${E(s.title)} ↗</a><p>${E(s.publisher)} · ${E(s.published_at||'未标发布日期')} · ${E(s.kind)}</p><p>依据：${E(s.supports)}</p></li>`;}).join('')}</ol>${step.source_note?`<p class="detail-note">${E(step.source_note)}</p>`:''}<p class="detail-note">资料核查：${E(guide.reviewed_at)}。正文的事实依据见上；理解问题与收束语为编辑整理。</p>`;
}
function supplementary(step) {
  return `<details class="further"><summary>${step.part==='extension'?'想继续发掘：资料来源与阅读线索':'想多了解一点：人物、原书照片与场景依据'}</summary><div class="supplement">${step.people.length?`<h3>这一段里的人</h3><div class="person-chips">${step.people.map(id=>`<button class="chip" data-person="${id}">${E(people[id].name)} ↗</button>`).join('')}</div>`:''}${step.events.length?`<h3>展开具体场景</h3>${relatedList(step.events)}<details class="source"><summary>查原书短引文与扫描页</summary>${step.events.map(id=>sourceLinks(events[id])).join('')}</details>`:''}${step.source_ids.length?externalSources(step):''}<div class="quiet-actions"><button data-map>在地图上看这一段</button>${step.photo?`<button data-photo="${step.photo}">查看原书整页照片</button>`:''}<button data-people>所有同行人物</button></div></div></details>`;
}
function renderReading() {
  const step=guide.steps[current];
  $('#part-label').textContent=parts[step.part];
  $('#position-label').textContent=`${current+1} / ${guide.steps.length}`;
  $('#progress').setAttribute('aria-valuemax',guide.steps.length);
  $('#progress').setAttribute('aria-valuenow',current+1);
  $('#progress').setAttribute('aria-valuetext',`${parts[step.part]}，第${current+1}步：${step.title}`);
  $('#progress-fill').style.width=`${(current+1)/guide.steps.length*100}%`;
  const portrait=images['shan-author-portrait'];
  const portraitHTML=step.id==='meet'&&portrait?`<figure class="portrait"><img src="assets/${portrait.file}" alt="单伟建肖像"><figcaption>单伟建<br><a href="${E(portrait.source_url)}" target="_blank" rel="noopener">图片来源：作者官网</a></figcaption></figure>`:'';
  let photoHTML='';
  if(['gobi','beijing','berkeley','return'].includes(step.id)){
    const stage=stages[step.photo];
    photoHTML=`<figure class="episode-photo"><button data-photo="${stage.id}" aria-label="放大这一段的原书照片"><img src="assets/page-${String(stage.photo).padStart(3,'0')}.jpg" alt="${E(stage.photo_caption)}" loading="lazy"></button><figcaption><strong>从原书照片看这段人生</strong>${E(stage.photo_caption)}<span class="image-hint">点击照片，放大看原页</span></figcaption></figure>`;
  }
  const boundary=step.id==='beyond-banker'?'<aside class="boundary">从这里进入书外续篇。时间回到1993年，后续内容依据机构公告、出版社资料与公开分享整理。</aside>':'';
  const bookHTML=step.id==='beyond-korea'?bookFeature('games'):step.id==='beyond-shenzhen'?bookFeature('machine'):step.id==='beyond-author'?`<div class="bookshelf">${bookFeature('games')}${bookFeature('machine')}</div>`:'';
  const finish=step.id==='reflect'?`<section class="further-reading"><h2>接下来，沿着感兴趣的一段继续读</h2><a href="../../book_reader/site/dist/index.html" target="_blank" rel="noopener">回到《走出戈壁》全书 ↗</a>${guide.reading_links.map(link=>`<a href="${E(link.url)}" target="_blank" rel="noopener">${E(link.label)} ↗</a>`).join('')}</section>`:'';
  reading.innerHTML=`<header class="step-heading"><span class="eyebrow">${E(step.label)}</span><h1 id="step-title" tabindex="-1">${E(step.title)}</h1><div class="where"><span>${E(step.date)}</span><span>${E(step.place)}</span><button data-map>看地图 ↗</button></div></header>${boundary}${step.id==='meet'?'<p class="path-note">先读书中的人生，再走进书外续篇。每一步只往前走一小段。</p>':''}<div class="narrative">${portraitHTML}${narrativeHTML(step)}</div>${photoHTML}${bookHTML}<aside class="takeaway"><h2>读到这里，可以这样理解</h2><p>${E(step.takeaway)}</p></aside><p class="bridge">${E(step.bridge)}</p>${finish}${supplementary(step)}`;
  $('#previous').disabled=current===0;
  const next=guide.steps[current+1];
  $('#next').innerHTML=next?`<span><small>${next.part!==step.part?'接下来 · '+parts[next.part]:'继续读'}</small><strong>${E(next.title)}</strong></span><span class="arrow" aria-hidden="true">→</span>`:'<span><small>沿着自己的兴趣继续</small><strong>回到阅读目录</strong></span><span class="arrow" aria-hidden="true">↗</span>';
}
function resolveStep(id) {
  const value=String(id||'').replace(/^read\//,'');
  let index=guide.steps.findIndex(s=>s.id===value);
  if(index<0&&stages[value])index=guide.steps.findIndex(s=>s.stage===value&&s.part==='book');
  return index;
}
function navigateStep(value,{focus=true,persist=true,updateURL=true}={}) {
  const index=typeof value==='number'?value:resolveStep(value);
  current=Math.max(0,Math.min(guide.steps.length-1,index<0?0:index));
  renderReading();
  if(updateURL)history.replaceState(null,'',`#read/${guide.steps[current].id}`);
  if(persist){try{localStorage.setItem(bookmarkKey,guide.steps[current].id);}catch{/* Reading still works when browser storage is unavailable. */}}
  if(focus){$('#step-title').focus({preventScroll:true});$('.layout').scrollIntoView({behavior:'instant',block:'start'});}
}
function selectStage(id) {navigateStep(id||'meet');}
function advance(direction) {
  if(direction>0&&current===guide.steps.length-1){launchDetail('menu');return;}
  navigateStep(current+direction);
}
function menuHTML() {
  return `<h2 id="detail-title">这一路，怎样往下读</h2><p class="detail-note">你现在在第${current+1}步。可以从这里选一段；关闭目录，就回到刚才的正文。</p>${Object.entries(parts).map(([key,label])=>`<section class="toc-group"><h3>${label}${key==='book'?' · 以《走出戈壁》为依据':key==='extension'?' · 公开资料补读':''}</h3>${guide.steps.map((s,i)=>s.part===key?`<button class="toc-row" data-step="${s.id}" ${i===current?'aria-current="step"':''}><span>${String(i+1).padStart(2,'0')}</span><span>${E(s.title)}<small>${E(s.date)}</small></span></button>`:'').join('')}</section>`).join('')}<details class="further"><summary>还想自由探索</summary><div class="quiet-actions"><button data-people>所有同行人物</button>${story.threads.map(t=>`<button data-thread="${t.id}">沿着「${E(t.name)}」重读</button>`).join('')}<button data-about>资料与图片出处</button></div></details>`;
}
function mapHTML() {
  mapContext=guide.steps[current];mapView=mapContext.map;
  return `<h2 id="detail-title">这一段，发生在哪里？</h2><p class="detail-note">${E(mapContext.place)}</p><div class="map-heading"><h3 id="map-title"></h3><div class="map-switch" aria-label="地图范围"><button data-view="pacific">全程</button><button data-view="china">东亚</button><button data-view="usa">美国</button></div></div><div class="map-canvas"><svg id="map" viewBox="0 0 960 590" role="img" aria-labelledby="map-a11y-title map-a11y-desc"></svg></div><div id="place-list" class="place-list"></div><p class="detail-note">${mapContext.part==='extension'?'书外地图标注相关机构所在城市；不代表作者在特定日期的行程。':'地点为城市或地域示意；连线表示叙事迁移，不是精确交通路线。'}</p>`;
}

function renderMap() {
  const stage = mapContext;
  const settings = {
    pacific:{extent:[75,305,5,76],title:'跨越太平洋的旅程'},
    china:{extent:[95,133,16,50],title:'东亚的相关地点'},
    usa:{extent:[225,298,23,51],title:'在美国，从求学到任教'}
  }[mapView];
  $('#map-title').textContent = settings.title;
  document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===mapView)));
  const [minX,maxX,minY,maxY] = settings.extent;
  const scale = Math.min(830/(maxX-minX),430/((maxY-minY)*1.28));
  const project = (lon,lat) => [480+(lon-(minX+maxX)/2)*scale,285-(lat-(minY+maxY)/2)*scale*1.28];
  const point = id => {const p=places[id];return project(p.lon<0?p.lon+360:p.lon,p.lat);};
  const fmt = n=>n.toFixed(2);
  let paths='';
  for (const feature of land.features) {
    const polygons = feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
    for (const shift of [0,360]) for (const polygon of polygons) {
      const path = polygon.map(ring=>ring.map((coord,i)=>{const [x,y]=project(coord[0]+shift,coord[1]);return `${i?'L':'M'}${fmt(x)},${fmt(y)}`;}).join('')+'Z').join('');
      paths+=`<path class="land" d="${path}"/>`;
    }
  }
  let grid='';
  for(let lon=0;lon<=360;lon+=20){const [x]=project(lon,0);grid+=`<path class="graticule" d="M${fmt(x)},0V590"/>`;}
  for(let lat=0;lat<90;lat+=15){const [,y]=project(0,lat);grid+=`<path class="graticule" d="M0,${fmt(y)}H960"/>`;}
  const route = stage?stage.route:['beijing','wulate','beijing','sanfrancisco','philadelphia','hongkong','wuliang'];
  let routePaths='';
  for(let i=1;i<route.length;i++){
    const [ax,ay]=point(route[i-1]),[bx,by]=point(route[i]);
    const bend=Math.min(100,Math.hypot(bx-ax,by-ay)*.22);
    routePaths+=`<path class="route" d="M${fmt(ax)},${fmt(ay)} Q${fmt((ax+bx)/2)},${fmt((ay+by)/2-bend)} ${fmt(bx)},${fmt(by)}" marker-end="url(#arrow)"/>`;
  }
  const stopIds=stage?stage.stops:story.overview.stops;
  const seen=new Set();
  const offsets={beijing:[13,30],shandong:[16,20],wulate:[-14,-22],wuliang:[-14,-22],sanfrancisco:[-15,33],berkeley:[-15,33],washington:[-12,40],philadelphia:[14,-18],hongkong:[14,30],baotou:[-13,35]};
  let labels='';
  for(const id of stopIds){
    const key=['wulate','wuliang','baotou'].includes(id)?'gobi':['sanfrancisco','berkeley'].includes(id)?'bay':id;
    if(seen.has(key))continue;
    seen.add(key);
    const [x,y]=point(id);
    if(x<20||x>940||y<20||y>565)continue;
    let [dx,dy]=offsets[id]||[14,-16];
    if(key==='gobi' && mapView==='pacific'){dx=14;dy=-25;}
    if(key==='bay' && mapView==='usa'){dx=14;dy=33;}
    const name=key==='gobi'?'戈壁 · 乌梁素海':key==='bay'?'旧金山湾区':places[id].name;
    labels+=`<a href="#place-${id}" data-map-place="${id}" aria-label="探索${E(name)}"><circle class="map-dot" cx="${fmt(x)}" cy="${fmt(y)}" r="6"/><text class="map-label" x="${fmt(x+dx)}" y="${fmt(y+dy)}" text-anchor="${dx<0?'end':'start'}">${E(name)}</text></a>`;
  }
  const ocean=mapView==='pacific'?'<text class="map-region" x="480" y="460" text-anchor="middle">PACIFIC OCEAN</text>':'';
  $('#map').innerHTML=`<title id="map-a11y-title">${E(settings.title)}</title><desc id="map-a11y-desc">${E(stopIds.map(id=>places[id].name).join('、'))}。地点入口在地图下方；连线仅表示迁移联系。</desc><defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#a36119"/></marker></defs>${grid}${paths}${ocean}${routePaths}${labels}`;
  $('#place-list').innerHTML=stopIds.map(id=>`<button data-place="${id}">${E(places[id].name)} ↗</button>`).join('');
}

const dialog = $('#detail'), detailBody = $('#detail-body');
let dialogHistory=[];
function sourceLinks(event) {
  const chapter=story.chapters.find(c=>c.id===event.chapter_id);
  const supporting=story.chapters.filter((c,i)=>event.pdf_pages.some(p=>p>=c.start && p<(story.chapters[i+1]?.start??421)));
  return `<details class="source"><summary>查看原书依据 · ${E(chapter?.title||'原书')} · PDF ${event.pdf_pages.join('、')} 页</summary><blockquote>「${E(event.quote.text)}」</blockquote><p>原书短引文 · PDF物理第${event.quote.pdf_page}页。以上叙事为编辑整理，以下可回查文字及扫描原页。</p><div class="source-links">${supporting.map(c=>`<a href="../../book_reader/site/dist/index.html#${c.section}" target="_blank" rel="noopener">${E(c.title)} ↗</a>`).join('')}${event.pdf_pages.map(p=>`<a href="../../走出戈壁-单伟健.pdf#page=${p}" target="_blank" rel="noopener">扫描第${p}页 ↗</a>`).join('')}</div>${event.notes.length?`<ul class="source-notes">${event.notes.map(n=>`<li>${E(n)}</li>`).join('')}</ul>`:''}</details>`;
}
function relatedList(ids) {
  return `<div class="related-list">${ids.map(id=>{const event=events[id];return `<button class="related-link" data-event="${id}"><span>第${stages[event.stage].number}幕 · ${E(event.date_label)}</span>${E(event.title)} ↗</button>`;}).join('')}</div>`;
}
function openDetail(kind,id,{back=false}={}) {
  if(!back)dialogHistory.push({kind,id});
  const backButton=dialogHistory.length>1?'<button class="inline-back" data-detail-back>← 返回刚才的阅读</button>':'';
  let html='';
  if(kind==='menu'){html=menuHTML();}
  else if(kind==='map'){html=mapHTML();}
  else if(kind==='event'){
    const event=events[id],stage=stages[event.stage];

    html=`<div class="stage-kicker">第${stage.number}幕 · ${E(event.date_label)}</div><h2 id="detail-title">${E(event.title)}</h2><p class="eyebrow">${E(event.place)}</p><p class="narrative">${E(event.summary)}</p><section class="detail-section"><h3>当时的处境</h3><p>${E(event.stakes)}</p></section><section class="detail-section"><h3>他怎样回应</h3><p>${E(event.action)}</p></section><section class="detail-section"><h3>这一刻之后</h3><p>${E(event.change)}</p></section>${event.people.length?`<section class="detail-section"><h3>在这件事里，人们做了什么</h3>${event.people.map(p=>`<p><strong>${E(p.name)}</strong> · ${E(p.role)}</p>`).join('')}${event.person_ids.length?`<div class="person-chips">${event.person_ids.map(pid=>`<button class="chip" data-person="${pid}">${E(people[pid].name)} ↗</button>`).join('')}</div>`:''}</section>`:''}${sourceLinks(event)}<section class="detail-section"><h3>带着这个场景继续读</h3><div class="person-chips">${event.tags.map(t=>`<button class="chip" data-thread="${t}">沿着「${E(threads[t].name)}」↗</button>`).join('')}<button class="chip" data-go-stage="${event.stage}">在主线读这一段 →</button></div></section>`;
  } else if(kind==='person'){
    const person=people[id];
    html=`<div class="stage-kicker">同行的人 / ${E(person.role)}</div><h2 id="detail-title">${E(person.name)}</h2><p class="narrative">${E(person.bio)}</p><section class="detail-section"><h3>从具体的相遇理解这段关系</h3>${relatedList(person.events)}</section>`;
  } else if(kind==='thread'){
    const thread=threads[id];
    const ids=story.stages.flatMap(s=>s.scenes).filter(eid=>events[eid].tags.includes(id));
    html=`<div class="stage-kicker">一条贯穿人生的线索</div><h2 id="detail-title">${E(thread.name)}：${E(thread.subtitle)}</h2><p class="narrative">${E(thread.intro)}</p><p class="detail-note">以下场景按七幕顺序排列，表现主题的呼应；不把时间先后直接视为因果。</p>${relatedList(ids)}`;
  } else if(kind==='place'){
    const place=places[id];
    let ids=[id],title=place.name;
    if(['wuliang','wulate','baotou'].includes(id)){ids=['wuliang','wulate','baotou'];title='戈壁 · 乌拉特前旗与乌梁素海';}
    if(['sanfrancisco','berkeley'].includes(id)){ids=['sanfrancisco','berkeley'];title='旧金山湾区 · 两次求学';}
    const related=story.stages.flatMap(s=>s.scenes).filter(eid=>ids.includes(events[eid].map_place));
    const passing=story.stages.filter(s=>s.stops.some(pid=>ids.includes(pid)));
    html=`<div class="stage-kicker">地点 / ${E(place.precision)}</div><h2 id="detail-title">${E(title)}</h2><p class="narrative">${E(place.note)}</p><p class="detail-note">地点按城市或地域组织。每个场景正文保留更具体的地点说明；地图点位不代表旧址的精确位置。</p><div class="person-chips">${passing.map(s=>`<button class="chip" data-go-stage="${s.id}">第${s.number}幕 · ${E(s.title)}</button>`).join('')}</div>${guide.steps.filter(s=>s.part==='extension'&&s.stops.some(p=>ids.includes(p))).map(s=>`<button class="related-link" data-step="${s.id}"><span>书外续篇 · ${E(s.date)}</span>${E(s.title)} ↗</button>`).join('')}${related.length?relatedList(related):''}`;
  } else if(kind==='people'){
    html=`<div class="stage-kicker">同行的人</div><h2 id="detail-title">改变人生的，<br>也有一次具体的相助</h2><p class="narrative">从家人、戈壁的同伴，到大学里的师友。选择一个人，回到他们相遇、相助或共同选择的场景。</p><div class="person-directory">${story.people.map(p=>`<button class="related-link" data-person="${p.id}"><span>${E(p.role)}</span><strong>${E(p.name)} ↗</strong></button>`).join('')}</div>`;
  } else if(kind==='photo'){
    const stage=stages[id];
    html=`<h2 id="detail-title">原书照片 · PDF第${stage.photo}页</h2><img class="photo-large" src="assets/page-${String(stage.photo).padStart(3,'0')}.jpg" alt="${E(stage.photo_caption)}"><p class="detail-note">${E(stage.photo_caption)}</p><a href="assets/page-${String(stage.photo).padStart(3,'0')}.jpg" target="_blank" rel="noopener">打开原图继续放大 ↗</a>`;
  } else {
    html=`<div class="stage-kicker">资料与编排</div><h2 id="detail-title">从人生轨迹，回到原书</h2><p class="narrative">这张地图以《走出戈壁》的全书文字稿为主要依据，保留34个有原书依据的场景，并编排为一条逐步带读的主线。书外续篇另以公开来源补充投资与写作经历。</p><p class="detail-note">主线先读原书，再读书外续篇。原书结束于2005年重访，续篇明确回到1993年的职业转向。人物、地图和主题是按需展开的补充阅读，关闭后仍回到当前步骤。阅读位置只保存在本机浏览器中。</p><ul class="about-list">${story.notes.map(n=>`<li>${E(n)}</li>`).join('')}</ul><section class="detail-section"><h3>资料、地图与影像</h3><p>书外续篇的每一步都有公开资料链接。事实叙述与“读到这里，可以这样理解”的编辑归纳分开呈现。</p><p>海陆轮廓采用 <a href="${story.map_source.url}" target="_blank" rel="noopener">Natural Earth 1:110m Land</a> 公共领域数据。地图不表达行政边界。</p><p>历史照片为原书扫描页，保留原图注；肖像与两本著作封面来自作者官网，各图附来源。书封所示版本与正文首版出版年分别说明。</p><p>页面和照片可以离线阅读。全书与扫描页链接需要保留当前项目的目录结构。</p></section><div class="source-links"><a href="../../book_reader/site/dist/index.html" target="_blank" rel="noopener">进入全书阅读器 ↗</a><a href="../../走出戈壁-单伟健.pdf" target="_blank" rel="noopener">打开原书PDF ↗</a></div>`;
  }
  detailBody.innerHTML=backButton+html;
  if(kind==='map')renderMap();
  if(!dialog.open)dialog.showModal();
  dialog.scrollTop=0;
  $('#detail-title').setAttribute('tabindex','-1');
  $('#detail-title').focus({preventScroll:true});
}

let opener=null;
function launchDetail(kind,id){if(!dialog.open){dialogHistory=[];opener=document.activeElement;}openDetail(kind,id);}
function closeDetail(){dialog.close();dialogHistory=[];}
$('#close-detail').addEventListener('click',closeDetail);
dialog.addEventListener('close',()=>{dialogHistory=[];if(opener?.isConnected)opener.focus({preventScroll:true});});
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeDetail();}});
$('#previous').addEventListener('click',()=>advance(-1));
$('#next').addEventListener('click',()=>advance(1));
document.addEventListener('click',e=>{
  const link=e.target.closest('[data-map-place]');
  if(link){e.preventDefault();launchDetail('place',link.dataset.mapPlace);return;}
  const b=e.target.closest('button');if(!b)return;
  if(b.hasAttribute('data-home'))navigateStep('meet');
  else if(b.hasAttribute('data-menu'))launchDetail('menu');
  else if(b.hasAttribute('data-map'))launchDetail('map');
  else if(b.dataset.step){closeDetail();navigateStep(b.dataset.step);}
  else if(b.dataset.view){mapView=b.dataset.view;renderMap();}
  else if(b.dataset.event)launchDetail('event',b.dataset.event);
  else if(b.dataset.person)launchDetail('person',b.dataset.person);
  else if(b.dataset.thread)launchDetail('thread',b.dataset.thread);
  else if(b.dataset.place)launchDetail('place',b.dataset.place);
  else if(b.dataset.photo)launchDetail('photo',b.dataset.photo);
  else if(b.hasAttribute('data-people'))launchDetail('people');
  else if(b.hasAttribute('data-about'))launchDetail('about');
  else if(b.dataset.goStage){closeDetail();selectStage(b.dataset.goStage);}
  else if(b.hasAttribute('data-detail-back')){dialogHistory.pop();const previous=dialogHistory[dialogHistory.length-1];if(previous)openDetail(previous.kind,previous.id,{back:true});}
});
function restoreReading() {
  let index=resolveStep(location.hash.slice(1));
  if(index<0&&!location.hash){try{index=resolveStep(localStorage.getItem(bookmarkKey));}catch{/* First-time/offline reading remains available. */}}
  navigateStep(index<0?0:index,{focus:false,persist:false});
}
window.addEventListener('hashchange',()=>{if(dialog.open)closeDetail();navigateStep(location.hash.slice(1),{focus:true,updateURL:false});});
restoreReading();
