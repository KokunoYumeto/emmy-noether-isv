'use strict';
window.MathJax={tex:{inlineMath:[['$','$'],['\\(','\\)']],processEscapes:true},svg:{fontCache:'local'},options:{enableMenu:false},startup:{typeset:true}};
let records=[],filtered=[],page=0,english=false;
const size=30, $=id=>document.getElementById(id);
const clean=s=>String(s??'').normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase();
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
function table(rows){
  if(!rows.length)return null;
  const wrap=node('div',undefined,'table-wrap'),t=node('table'),head=node('tr');
  (english?['Compared form','Selected form or function','Line / uses']:['Sravniteljnaja forma','Izbrana forma ili funkcija','Red / pojav.']).forEach(s=>head.append(node('th',s)));
  t.append(head);
  for(const row of rows){const tr=node('tr');row.forEach(s=>tr.append(node('td',s)));t.append(tr)}
  wrap.append(t);return wrap;
}
function comparisonRows(r){
  const e=r.evidence??{},rows=[];
  for(const x of e.exact_phrases??[])rows.push([x.before,x.after,x.occurrences]);
  for(const x of e.exact_changes??[])if((x.before??x.before_prefix)!==undefined&&!String(x.before??x.before_prefix).startsWith('% Identity:'))rows.push([x.before??x.before_prefix,x.after??x.after_prefix,x.line??x.assembled_line??x.unit??'']);
  if(Array.isArray(e.exact_sites))for(const x of e.exact_sites){
    if(x.old!==undefined||x.before!==undefined)rows.push([x.old??x.before,x.new??x.after,x.line??'']);
    else if(x.surface??x.payload??x.text)rows.push([x.surface??x.payload??x.text,english?'Retained citation':'Zachovany citat',x.line??'']);
  }
  if(!rows.length&&e.mapping)for(const [a,b]of Object.entries(e.mapping))if(typeof b==='string')rows.push([a,b,'']);
  for(const x of e.name_families??[])rows.push([x.old_stem+' → '+x.new_stem+'; '+x.occurrences+'; '+(english?'estimate ':'ocěna ')+x.confidence,english?x.explanation_en:x.explanation_isv,'']);
  for(const x of r.mappings??[])rows.push([x.before,x.after,x.occurrences]);
  return rows;
}
function render(){
  if(window.MathJax?.typesetClear)window.MathJax.typesetClear();
  const begin=page*size,end=Math.min(begin+size,filtered.length);
  $('entries').replaceChildren();
  $('count').textContent=(english?'Entries':'Zapisy')+': '+filtered.length+' / '+records.length;
  for(const r of filtered.slice(begin,end)){
    const a=node('article',undefined,'entry');a.id=r.id;
    const link=node('a',r.id);link.href='#'+r.id;
    const meta=node('div',undefined,'entry-meta');meta.append(link);
    a.append(meta,node('h2',english?(r.title_en??r.title):r.title));
    if(r.source && r.kind!=='convention'){
      const c=node('div',undefined,'comparanda');
      c.append(node('div',(english?'Source: ':'Iztočnik: ')+r.source));
      if(r.russian?.length)c.append(node('div',(english?'Russian: ':'Rusky: ')+r.russian.join('; ')));
      if(r.ukrainian?.length)c.append(node('div',(english?'Ukrainian: ':'Ukrajinsky: ')+r.ukrainian.join('; ')));
      a.append(c);
    }
    a.append(node('p',english?r.en:r.isv,'reason'));
    if(r.sources_isv||r.sources_en)a.append(node('p',english?r.sources_en:r.sources_isv,'citations'));
    for(const c of r.comparisons??[]){
      const box=node('div',undefined,'comparison');
      box.append(node('p',english?c.english:c.text));
      const citations=node('p',undefined,'citations');
      for(const ref of c.references??[])if(ref.url?.startsWith('https://')){
        const l=node('a',ref.title+': '+ref.locator);l.href=ref.url;
        citations.append(l,node('br'));
      }
      box.append(citations);a.append(box);
    }
    const rows=comparisonRows(r);
    if(rows.length){
      const det=node('details');
      det.append(node('summary',(english?'Comparisons of forms':'Sravnjenja formov')+' ('+rows.length+')'),table(rows));
      a.append(det);
    }
    $('entries').append(a);
  }
  $('page').textContent=filtered.length?(begin+1)+'–'+end:'0';
  $('previous').disabled=page===0;$('next').disabled=end>=filtered.length;
  if(window.MathJax?.startup?.promise)window.MathJax.startup.promise.then(()=>window.MathJax.typesetPromise([$('entries')])).catch(()=>{});
}
function filter(){
  const q=clean($('search').value.trim()),kind=$('kind').value;
  filtered=records.filter(r=>(kind==='all'||r.kind===kind)&&(!q||r.search.includes(q)));
  if(q){
    const rank=r=>{
      const titles=[r.title,r.title_en].filter(Boolean).map(clean);
      if(titles.some(t=>t===q))return 0;
      if(titles.some(t=>t.startsWith(q)))return 1;
      if(titles.some(t=>t.includes(q)))return 2;
      if(clean(r.source).includes(q))return 3;
      return 4;
    };
    filtered.sort((a,b)=>rank(a)-rank(b));
  }
  page=0;render();
}
$('search').addEventListener('input',filter);$('kind').addEventListener('change',filter);
$('previous').onclick=()=>{if(page){page--;render();$('count').scrollIntoView()}};
$('next').onclick=()=>{if((page+1)*size<filtered.length){page++;render();$('count').scrollIntoView()}};
$('language').onclick=()=>{
  english=!english;document.documentElement.lang=english?'en':'isv';
  $('language').textContent=english?'Medžuslovjansky':'English';render();
};
fetch('entries.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(data=>{
  records=data.map(r=>({...r,search:clean(JSON.stringify(r))}));
  if(location.hash)$('search').value=decodeURIComponent(location.hash.slice(1));filter();
}).catch(()=>{$('count').textContent='Slovnik ne mogl byti zagruženy. Upotrěbite PDF. / Dictionary could not be loaded. Please use the PDF.'});
