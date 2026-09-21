// Data/state smoke tests in Node; browser layout is tested separately only when authorized.
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const base=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(base,'dist/index.html'),'utf8');
const scripts=[...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const dom=new Map();
let focused=null,clock=0,timerID=0;
const timers=new Map();
class Element{
  constructor(){this.html='';this.textContent='';this.hidden=false;this.inert=false;this.style={};this.dataset={};this.attrs={};this.listeners={};this.clientWidth=1350;this.clientHeight=827;this.isConnected=true;const set=new Set();this.classList={add:(...k)=>k.forEach(v=>set.add(v)),remove:(...k)=>k.forEach(v=>set.delete(v)),contains:k=>set.has(k),toggle:(k,b)=>{if(b===undefined)b=!set.has(k);b?set.add(k):set.delete(k);}};}
  set innerHTML(v){this.html=v;}
  get innerHTML(){return this.html;}
  setAttribute(k,v){this.attrs[k]=v;}
  getAttribute(k){return this.attrs[k];}
  addEventListener(k,fn){this.listeners[k]=fn;}
  querySelector(){return new Element();}
  querySelectorAll(){return [];}
  focus(){focused=this;}
  scrollIntoView(){}
  getBoundingClientRect(){return {width:this.clientWidth,height:this.clientHeight,left:0,top:0};}
}
for(const m of html.matchAll(/\bid="([^"]+)"/g))dom.set(m[1],new Element());
for(const s of scripts){const m=s[1].match(/id="([^"]+)"/);if(m)dom.get(m[1]).textContent=s[2];}
const body=new Element(),masthead=new Element();
const document={body,hidden:false,get activeElement(){return focused;},getElementById:id=>dom.get(id),querySelector:s=>s==='.masthead'?masthead:null,querySelectorAll:()=>[],listeners:{},addEventListener(k,fn){this.listeners[k]=fn;}};
const location={hash:'',pathname:'/biography/dist/index.html',search:''};
const context=vm.createContext({document,window:{innerWidth:1440,addEventListener(){}},location,history:{replaceState(a,b,c){location.hash=c.startsWith('#')?c:'';}},performance:{now:()=>clock},setInterval:fn=>{timers.set(++timerID,fn);return timerID;},clearInterval:id=>timers.delete(id),console,assert,timerCount:()=>timers.size,advanceClock:n=>{clock+=n;}});
vm.runInContext(scripts.find(s=>!s[1].includes('application/json'))[2],context);
vm.runInContext(`
  assert.equal(state.selected,null);
  assert.equal(($('mapClusters').innerHTML.match(/data-open=/g)||[]).length,32);
  assert.equal(($('extensionMap').innerHTML.match(/data-open=/g)||[]).length,9);
  assert.equal(($('chapterNav').innerHTML.match(/data-open=/g)||[]).length,13);
  const reachable=new Set();
  for(const n of A.nodes){for(const id of [...(n.events||[]),...(n.related||[])])reachable.add(id);}
  for(const event of D.events)assert.ok(reachable.has(event.id),'Missing scene link '+event.id);
  for(const n of A.nodes){
    openNode(n.id,{focus:false});
    assert.ok($('panelBody').innerHTML.includes(esc(n.title)),n.id);
    assert.ok(!/undefined|NaN/.test($('panelBody').innerHTML),n.id);
    assert.equal(state.selected,n.id);
    assert.ok(!$('detailPanel').hidden);
    if(n.quote){assert.ok($('panelBody').innerHTML.includes(esc(n.quote.text)));assert.ok($('panelBody').innerHTML.includes('#page='+n.quote.pdf_page));}
    assert.ok(refsFor(n).length||(n.source_ids||[]).length,n.id+' evidence');
  }
  openNode('h4',{focus:false});assert.ok($('panelBody').innerHTML.includes('离开的五道关口'));
  closePanel({focus:false});assert.ok($('detailPanel').hidden);assert.equal(state.selected,null);
  const before={scale:state.scale,x:state.x,y:state.y};
  openNode('h4',{focus:false});closePanel({focus:false});assert.deepEqual({scale:state.scale,x:state.x,y:state.y},before,'Return to same map view');
  for(const r of A.relations){selectRelation(r.id);assert.ok(!$('relationDetail').hidden);for(const id of r.nodes)assert.ok($('relationDetail').innerHTML.includes(id));selectRelation(r.id);assert.ok($('relationDetail').hidden);}
  showSources();assert.ok($('panelBody').innerHTML.includes('非现场史料照片'));closePanel({focus:false});
  openFilm(0);assert.ok(state.filmOpen);assert.ok($('workspace').inert);assert.equal(state.playing,false);
  for(let i=0;i<film.scenes.length;i++){
    showFilmScene(i);const s=film.scenes[i];assert.ok($('cinemaContent').innerHTML.includes(esc(s.title)));assert.ok($('cinemaScene').innerHTML.includes(s.image.file));
    assert.equal($('filmPrevious').disabled,i===0);assert.equal($('filmNext').disabled,i===film.scenes.length-1);
    assert.ok($('cinemaContent').innerHTML.includes(esc(s.image.caption)));
  }
  showFilmScene(-1);assert.equal(state.filmIndex,0);
  playFilm();assert.equal(timerCount(),1);advanceClock(40000);filmTick();assert.equal(state.filmIndex,1);
  advanceClock(5000);filmTick();const elapsed=state.elapsed;pauseFilm();assert.equal(timerCount(),0);assert.equal(state.elapsed,elapsed);
  playFilm();assert.equal(timerCount(),1);playFilm();assert.equal(timerCount(),0,'No duplicated interval');
  showFilmScene(16);playFilm();advanceClock(40000);filmTick();assert.equal(state.playing,false);assert.equal(state.filmIndex,16);assert.equal(timerCount(),0);
  playFilm();assert.equal(state.filmIndex,0,'End can restart');pauseFilm();
  showFilmScene(4);closeFilm({expand:true});assert.equal(state.selected,'h4');assert.equal(state.filmOpen,false);assert.equal($('workspace').inert,false);
  openFilm(3);playFilm();document.hidden=true;document.listeners.visibilitychange();assert.equal(state.playing,false);document.hidden=false;
  closeFilm();assert.equal(state.selected,'h4','Returning retains previously open node');
  for(const id of ['h1','history-admission','beyond-korea']){location.hash='#node='+id;navigateHash();assert.equal(state.selected,id);}
  location.hash='#film=cinema-h6-family';navigateHash();assert.equal(film.scenes[state.filmIndex].node,'h6');closeFilm();closePanel({focus:false});
`,context);
const data=JSON.parse(dom.get('story-data').textContent);
for(const stage of data.stages)assert.ok(fs.existsSync(path.join(base,'dist/assets',`page-${String(stage.photo).padStart(3,'0')}.jpg`)));
for(const s of data.cinema.scenes)assert.ok(fs.existsSync(path.join(base,'dist/assets',s.image.file)),s.image.file);
for(const file of ['book_reader/site/dist/index.html','走出戈壁-单伟健.pdf'])assert.ok(fs.existsSync(path.join(base,'..',file)),file);
const reader=fs.readFileSync(path.join(base,'../book_reader/site/dist/data.js'),'utf8');
for(const c of data.chapters)assert.ok(reader.includes(c.section),c.section);
assert.ok(!/<(?:script|link)[^>]+(?:src|href)="https?:/.test(html),'Remote runtime dependency');
assert.ok(!html.includes('/* LAND */'));
console.log('Passed: 41 visible nodes, 65 panels, all 34 book scenes reachable, citations and assets, 17 film scenes, playback/pause/resume/end/restart, background pause, film↔map context, deep links.');
console.log('Scope: Node data/state tests; no browser rendering or click simulation.');
