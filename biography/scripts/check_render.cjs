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
  constructor() { this.html = ''; this.textContent = ''; this.open = false; this.attrs = {}; }
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
const context = vm.createContext({
  document:{getElementById:id=>nodes.get('#'+id),querySelector:s=>nodes.get(s),querySelectorAll:()=>views,addEventListener(){}},
  window:{addEventListener(){}},history:{replaceState(){}},location:{hash:'',pathname:'/biography/dist/index.html',search:''},
  assert,console,
});
vm.runInContext(scripts.find(s=>!s[1].includes('application/json'))[2], context);
vm.runInContext(`
  for (const stage of story.stages) {
    selectStage(stage.id, false);
    assert.ok(reading.innerHTML.includes(E(stage.title)), stage.id);
    for (const view of ['pacific','china','usa']) {
      mapView=view;renderMap();
      assert.ok(!/NaN|Infinity|undefined/.test($('#map').innerHTML), stage.id+'/'+view);
    }
  }
  for (const event of story.events) {
    launchDetail('event',event.id);
    assert.equal(activeStage,event.stage);
    assert.ok(detailBody.innerHTML.includes(E(event.quote.text)), event.id);
    assert.ok(detailBody.innerHTML.includes('#page='+event.quote.pdf_page), event.id);
    closeDetail();
  }
  for (const [kind,items] of [['person',story.people],['thread',story.threads],['place',story.places],['photo',story.stages]]) {
    for (const item of items) {launchDetail(kind,item.id);assert.ok(!detailBody.innerHTML.includes('undefined'),kind+'/'+item.id);closeDetail();}
  }
  for (const kind of ['people','about']) {launchDetail(kind);closeDetail();}
  selectStage(null,false);
  assert.ok(reading.innerHTML.includes(E(story.overview.title)));
`, context);
const data = JSON.parse(nodes.get('#story-data').textContent);
for (const stage of data.stages) assert.ok(fs.existsSync(path.join(base, 'dist/assets', `page-${String(stage.photo).padStart(3,'0')}.jpg`)));
for (const file of ['book_reader/site/dist/index.html','走出戈壁-单伟健.pdf']) assert.ok(fs.existsSync(path.join(base,'..',file)), file);
const reader = fs.readFileSync(path.join(base,'../book_reader/site/dist/data.js'),'utf8');
for (const chapter of data.chapters) assert.ok(reader.includes(chapter.section), chapter.section);
assert.ok(!/<(?:script|link)[^>]+(?:src|href)="https?:/.test(html), 'Unexpected remote runtime dependency');
console.log('Passed: 7 stages × 3 map views, 34 scene renderings, all person/thread/place/photo panels, source links and offline assets.');
console.log('Scope: JavaScript/data smoke checks only; no browser rendering or interaction testing.');
