// Headless JavaScript smoke checks. This does not test browser layout or clicks.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const base = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(base, 'dist/index.html'), 'utf8');
const scripts = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const nodes = new Map();
class Element {
  constructor() { this.html = ''; this.textContent = ''; this.open = false; this.attrs = {}; this.style = {}; }
  set innerHTML(value) {
    this.html = value;
    for (const match of value.matchAll(/\bid="([^"]+)"/g)) nodes.set('#' + match[1], new Element());
  }
  get innerHTML() { return this.html; }
  setAttribute(name, value) { this.attrs[name] = value; }
  addEventListener() {}
  focus() {}
  scrollIntoView() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
}
for (const id of html.matchAll(/\bid="([^"]+)"/g)) nodes.set('#' + id[1], new Element());
nodes.set('.layout', new Element());
for (const script of scripts) {
  const id = script[1].match(/id="([^"]+)"/);
  if (id) nodes.get('#' + id[1]).textContent = script[2];
}
const views = ['pacific','china','usa'].map(view => Object.assign(new Element(), {dataset:{view}}));
const storage = new Map();
const localStorage = {getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)};
const context = vm.createContext({
  document:{getElementById:id=>nodes.get('#'+id),querySelector:s=>nodes.get(s),querySelectorAll:()=>views,addEventListener(){}},
  window:{addEventListener(){}},history:{replaceState(){}},location:{hash:'',pathname:'/biography/dist/index.html',search:''},
  assert,console,localStorage,
});
vm.runInContext(scripts.find(s=>!s[1].includes('application/json'))[2], context);
vm.runInContext(`
  assert.equal(current,0,'New readers must start with orientation');
  for (let i=0;i<guide.steps.length;i++) {
    const step=guide.steps[i];
    navigateStep(i,{focus:false});
    assert.ok(reading.innerHTML.includes(E(step.title)), step.id);
    assert.ok(reading.innerHTML.includes(E(step.takeaway)), step.id);
    assert.equal($('#previous').disabled,i===0);
    assert.equal(localStorage.getItem(bookmarkKey),step.id);
    if(i<guide.steps.length-1)assert.ok($('#next').innerHTML.includes(E(guide.steps[i+1].title)),step.id);
    else assert.ok($('#next').innerHTML.includes('阅读目录'));
    launchDetail('map');
    for (const view of ['pacific','china','usa']) {
      mapView=view;renderMap();
      assert.ok(!/NaN|Infinity|undefined/.test($('#map').innerHTML), step.id+'/'+view);
    }
    closeDetail();assert.equal(current,i,'Map must not change the reading position');
  }
  navigateStep('family',{focus:false});
  const savedPosition=current;
  for (const event of story.events) {
    launchDetail('event',event.id);
    assert.equal(current,savedPosition,'An optional scene must not jump the main reading');
    assert.ok(detailBody.innerHTML.includes(E(event.quote.text)), event.id);
    assert.ok(detailBody.innerHTML.includes('#page='+event.quote.pdf_page), event.id);
    closeDetail();
  }
  for (const [kind,items] of [['person',story.people],['thread',story.threads],['place',[...story.places,...guide.places]],['photo',story.stages]]) {
    for (const item of items) {launchDetail(kind,item.id);assert.ok(!detailBody.innerHTML.includes('undefined'),kind+'/'+item.id);closeDetail();}
  }
  for (const kind of ['people','about','menu']) {launchDetail(kind);closeDetail();}
  assert.equal(current,savedPosition,'Supplementary exploration must retain reading position');
  navigateStep(0,{focus:false});advance(-1);assert.equal(current,0);
  for(let i=1;i<guide.steps.length;i++){advance(1);assert.equal(current,i);}
  advance(1);assert.equal(current,guide.steps.length-1);assert.ok(dialog.open);closeDetail();
  navigateStep('family',{focus:false});
  navigateStep('meet',{focus:false,persist:false});
  restoreReading();assert.equal(guide.steps[current].id,'family','Restore local bookmark');
  localStorage.setItem(bookmarkKey,'stale-id');restoreReading();assert.equal(current,0);
  assert.equal(resolveStep('childhood'),1,'Previous edition links remain usable');
  assert.equal(resolveStep('read/beyond-korea'),12);
`, context);
const data = JSON.parse(nodes.get('#story-data').textContent);
for (const stage of data.stages) assert.ok(fs.existsSync(path.join(base, 'dist/assets', `page-${String(stage.photo).padStart(3,'0')}.jpg`)));
for (const asset of data.guide.images) assert.ok(fs.existsSync(path.join(base,'dist/assets',asset.file)));
for (const file of ['book_reader/site/dist/index.html','走出戈壁-单伟健.pdf']) assert.ok(fs.existsSync(path.join(base,'..',file)), file);
const reader = fs.readFileSync(path.join(base,'../book_reader/site/dist/data.js'),'utf8');
for (const chapter of data.chapters) assert.ok(reader.includes(chapter.section), chapter.section);
assert.ok(!/<(?:script|link)[^>]+(?:src|href)="https?:/.test(html), 'Unexpected remote runtime dependency');
console.log('Passed: 17 guided steps, previous/next navigation, main-route isolation, bookmark restore, all maps and supplementary panels, source links and 10 local images.');
console.log('Scope: JavaScript/data smoke checks only; no browser rendering or interaction testing.');
