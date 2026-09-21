'use strict';
const story = JSON.parse(document.getElementById('story-data').textContent);
const land = JSON.parse(document.getElementById('land-data').textContent);
const byId = kind => Object.fromEntries(story[kind].map(x => [x.id, x]));
const stages = byId('stages'), events = byId('events'), people = byId('people'), places = byId('places'), threads = byId('threads');
const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const E = escapeHTML;
let activeStage = null, mapView = 'pacific';
const reading = $('#reading');
function actButton(stage) {
  return `<button class="act-summary" data-act="${stage.id}"><span>第${stage.number}幕 · ${E(stage.date)} · ${E(stage.place)}</span><strong>${E(stage.title)} ↗</strong><p>${E(stage.deck)}</p></button>`;
}
function sceneButton(event) {
  return `<button class="scene" data-event="${event.id}"><div><span class="meta">${E(event.date_label)}</span><strong>${E(event.title)}</strong><p>${E(event.stakes)}</p></div><span class="arrow" aria-hidden="true">↗</span></button>`;
}
function renderStory() {
  $('#act-nav').innerHTML = story.stages.map(s => `<button class="act-link" data-act="${s.id}" ${activeStage===s.id?'aria-current="step"':''}><span class="nav-meta">${s.number} / ${E(s.date)}</span>${E(s.title)}</button>`).join('');
  const stage = stages[activeStage];
  if (!stage) {
    reading.innerHTML = `<div class="overview-intro"><span class="eyebrow">一部回忆录 · 七幕人生</span><h1>${E(story.overview.title)}</h1><p class="lead">${E(story.overview.intro)}</p><button class="primary" data-act="childhood">从童年开始 <span aria-hidden="true">→</span></button><p class="scope">${E(story.scope)}<br>可以顺着七幕阅读，也可以从地图、人物或线索进入。</p></div><section class="act-index"><h2>沿着人生的转弯处往下读</h2>${story.stages.map(actButton).join('')}</section>`;
    $('#map-context').innerHTML = `<span class="eyebrow">先看整段旅程</span><p>北京 → 戈壁 → 北京 → 美国 → 香港<br>多年以后，旅程又回到戈壁。</p>`;
  } else {
    const index = story.stages.indexOf(stage);
    reading.innerHTML = `<button class="back-overview" data-home>← 回到全程</button><div class="stage-kicker">第${stage.number}幕 / ${E(stage.date)} / ${E(stage.place)}</div><h1>${E(stage.title)}</h1><p class="stage-deck">${E(stage.deck)}</p><p class="lead">${E(stage.intro)}</p><figure><button data-photo="${stage.id}" aria-label="放大查看原书照片"><img src="assets/page-${String(stage.photo).padStart(3,'0')}.jpg" alt="${E(stage.photo_caption)}" loading="lazy"></button><figcaption>${E(stage.photo_caption)} 点击可放大。</figcaption></figure><h2 class="scene-heading">走进这一幕</h2>${stage.scenes.map(id=>sceneButton(events[id])).join('')}<aside class="reflection"><h2>这一幕留下的问题</h2><p>${E(stage.reflection)}</p></aside><div class="chapter-turn">${index?`<button data-act="${story.stages[index-1].id}">← 上一幕<br>${E(story.stages[index-1].title)}</button>`:'<button data-home>← 全程</button>'}${index<6?`<button data-act="${story.stages[index+1].id}">下一幕 →<br>${E(story.stages[index+1].title)}</button>`:'<button data-home>回看整段人生 →</button>'}</div>`;
    $('#map-context').innerHTML = `<span class="eyebrow">带着一个问题进入</span><p>${E(stage.question)}</p>`;
  }
  $('#thread-links').innerHTML = story.threads.map(t=>`<button data-thread="${t.id}">${E(t.name)}<span aria-hidden="true">↗</span></button>`).join('');
  renderMap();
}
function renderMap() {
  const stage = stages[activeStage];
  const settings = {
    pacific:{extent:[75,305,5,76],title:'跨越太平洋的旅程'},
    china:{extent:[95,133,16,50],title:'从北京到戈壁，再回到北京'},
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
function selectStage(id, moveFocus=true) {
  activeStage=stages[id]?id:null;
  mapView=activeStage?stages[activeStage].map:'pacific';
  renderStory();
  history.replaceState(null,'',activeStage?`#${activeStage}`:location.pathname+location.search);
  if(moveFocus){reading.focus({preventScroll:true});$('.layout').scrollIntoView({behavior:'instant',block:'start'});}
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
  if(kind==='event'){
    const event=events[id],stage=stages[event.stage];
    if(activeStage!==event.stage)selectStage(event.stage,false);
    html=`<div class="stage-kicker">第${stage.number}幕 · ${E(event.date_label)}</div><h2 id="detail-title">${E(event.title)}</h2><p class="eyebrow">${E(event.place)}</p><p class="narrative">${E(event.summary)}</p><section class="detail-section"><h3>当时的处境</h3><p>${E(event.stakes)}</p></section><section class="detail-section"><h3>他怎样回应</h3><p>${E(event.action)}</p></section><section class="detail-section"><h3>这一刻之后</h3><p>${E(event.change)}</p></section>${event.people.length?`<section class="detail-section"><h3>在这件事里，人们做了什么</h3>${event.people.map(p=>`<p><strong>${E(p.name)}</strong> · ${E(p.role)}</p>`).join('')}${event.person_ids.length?`<div class="person-chips">${event.person_ids.map(pid=>`<button class="chip" data-person="${pid}">${E(people[pid].name)} ↗</button>`).join('')}</div>`:''}</section>`:''}${sourceLinks(event)}<section class="detail-section"><h3>带着这个场景继续读</h3><div class="person-chips">${event.tags.map(t=>`<button class="chip" data-thread="${t}">沿着「${E(threads[t].name)}」↗</button>`).join('')}<button class="chip" data-go-stage="${event.stage}">回到第${stage.number}幕 →</button></div></section>`;
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
    html=`<div class="stage-kicker">地点 / ${E(place.precision)}</div><h2 id="detail-title">${E(title)}</h2><p class="narrative">${E(place.note)}</p><p class="detail-note">地点按城市或地域组织。每个场景正文保留更具体的地点说明；地图点位不代表旧址的精确位置。</p><div class="person-chips">${passing.map(s=>`<button class="chip" data-go-stage="${s.id}">第${s.number}幕 · ${E(s.title)}</button>`).join('')}</div>${related.length?relatedList(related):'<p class="detail-note">这里是旅途中的地点。进入相关一幕，阅读它前后的变化。</p>'}`;
  } else if(kind==='people'){
    html=`<div class="stage-kicker">同行的人</div><h2 id="detail-title">改变人生的，<br>也有一次具体的相助</h2><p class="narrative">从家人、戈壁的同伴，到大学里的师友。选择一个人，回到他们相遇、相助或共同选择的场景。</p><div class="person-directory">${story.people.map(p=>`<button class="related-link" data-person="${p.id}"><span>${E(p.role)}</span><strong>${E(p.name)} ↗</strong></button>`).join('')}</div>`;
  } else if(kind==='photo'){
    const stage=stages[id];
    html=`<h2 id="detail-title">原书照片 · PDF第${stage.photo}页</h2><img class="photo-large" src="assets/page-${String(stage.photo).padStart(3,'0')}.jpg" alt="${E(stage.photo_caption)}"><p class="detail-note">${E(stage.photo_caption)}</p><a href="assets/page-${String(stage.photo).padStart(3,'0')}.jpg" target="_blank" rel="noopener">打开原图继续放大 ↗</a>`;
  } else {
    html=`<div class="stage-kicker">资料与编排</div><h2 id="detail-title">从人生轨迹，回到原书</h2><p class="narrative">这张地图以《走出戈壁》的全书文字稿为主要依据，选择七幕、34个场景，讲述单伟建在不同处境中的行动，以及他与他人的联系。</p><p class="detail-note">七幕按人生阶段和主题组织，部分时间互有重叠。可以依次阅读，也可以通过人物、地点和「求知／相助／选择」重新进入故事。</p><ul class="about-list">${story.notes.map(n=>`<li>${E(n)}</li>`).join('')}</ul><section class="detail-section"><h3>地图与影像</h3><p>海陆轮廓采用 <a href="${story.map_source.url}" target="_blank" rel="noopener">Natural Earth 1:110m Land</a> 公共领域数据。地图不表达行政边界。</p><p>照片为本地原书扫描页，保留原图注。它们呈现人物与时代环境，不等于每个事件的现场照片。</p><p>页面和照片可以离线阅读。全书与扫描页链接需要保留当前项目的目录结构。</p></section><div class="source-links"><a href="../../book_reader/site/dist/index.html" target="_blank" rel="noopener">进入全书阅读器 ↗</a><a href="../../走出戈壁-单伟健.pdf" target="_blank" rel="noopener">打开原书PDF ↗</a></div>`;
  }
  detailBody.innerHTML=backButton+html;
  if(!dialog.open)dialog.showModal();
  dialog.scrollTop=0;
  $('#detail-title').setAttribute('tabindex','-1');
  $('#detail-title').focus({preventScroll:true});
}
function launchDetail(kind,id){if(!dialog.open)dialogHistory=[];openDetail(kind,id);}
function closeDetail(){dialog.close();dialogHistory=[];}
$('#close-detail').addEventListener('click',closeDetail);
dialog.addEventListener('close',()=>{dialogHistory=[];});
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeDetail();}});
document.addEventListener('click',e=>{
  const mapLink=e.target.closest('[data-map-place]');
  if(mapLink){e.preventDefault();launchDetail('place',mapLink.dataset.mapPlace);return;}
  const button=e.target.closest('button');if(!button)return;
  if(button.hasAttribute('data-home'))selectStage(null);
  else if(button.dataset.act)selectStage(button.dataset.act);
  else if(button.dataset.view){mapView=button.dataset.view;renderMap();}
  else if(button.dataset.event)launchDetail('event',button.dataset.event);
  else if(button.dataset.person)launchDetail('person',button.dataset.person);
  else if(button.dataset.thread)launchDetail('thread',button.dataset.thread);
  else if(button.dataset.place)launchDetail('place',button.dataset.place);
  else if(button.dataset.photo)launchDetail('photo',button.dataset.photo);
  else if(button.hasAttribute('data-people'))launchDetail('people');
  else if(button.hasAttribute('data-about'))launchDetail('about');
  else if(button.dataset.goStage){closeDetail();selectStage(button.dataset.goStage);}
  else if(button.hasAttribute('data-detail-back')){dialogHistory.pop();const previous=dialogHistory[dialogHistory.length-1];openDetail(previous.kind,previous.id,{back:true});}
});
window.addEventListener('hashchange',()=>selectStage(location.hash.slice(1),false));
selectStage(location.hash.slice(1),false);
