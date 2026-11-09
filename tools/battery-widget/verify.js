// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
ObjC.import('Foundation');
function run(argv) {
 var doc=JSON.parse($.NSString.stringWithContentsOfFileEncodingError(argv[0],$.NSUTF8StringEncoding,null).js);
 var w=doc.widgets.batterie_ladestaende_cell,defs=w.slots.background[0].config.functions;
 var states={},items=new Proxy({}, {get:function(_,name){return {state:states[name] || '-'};}}),f={},count=0;
 function check(v,msg){count++;if(!v)throw Error(msg);}
 Object.keys(defs).forEach(function(k){f[k]=Function('items','parseFloat','return ('+defs[k].slice(1)+')')(items,undefined);});
 [['0 %',0],['100 %',100],['2.5 %',2.5],['3,2 %',3.2],['NULL',null],['UNDEF',null],['-',null],['',null],['101 %',null],['-1 %',null],['42 V',null]].forEach(function(t){check(f.value(t[0])===t[1],'Value '+t[0]);});
 var list=[{name:'high',type:'Number:Dimensionless',label:'High Batterie'},{name:'low',type:'Number',label:'Low Batterieladung'},{name:'zero',type:'Number:Dimensionless',label:'Zero'},{name:'unknown',type:'Number:Dimensionless',label:'Unknown'},{name:'pending',type:'Number:Dimensionless',label:'Pending'},{name:'switch',type:'Switch'}];
 states={high:'100 %',low:'2.5 %',zero:'0 %',unknown:'UNDEF'};
 function view(){return f.summary(f.rows(list,f.read,f.value),f.sorted);}
 var v=view();check(v.rows.length===5,'Only percent-compatible numeric Items');
 check(v.lowest.map(function(r){return r.name;}).join(',')==='zero,low,high','Numeric sort and three lowest');
 check(v.rows.slice(3).every(function(r){return r.value===null;}),'Unknowns at end');
 check(v.pending===1 && v.unknown===1,'Pending and undefined distinct');
 check(!v.full,'Incomplete data cannot be full');
 check(f.format(0)==='0 %' && f.format(null)==='— %','Zero distinct from unknown');
 states.low='0.5 %';v=view();check(v.lowest[1].value===0.5,'Live update');
 states={high:'100 %',low:'100 %',zero:'100 %',unknown:'100 %',pending:'100 %'};
 v=view();check(v.full,'All 100 shows full message');
 check(!f.summary([],f.sorted).full,'Empty group cannot claim full');
 states.low='99.99 %';check(!view().full,'Rounded 100 does not claim all full');
 check(f.color(null).indexOf('gray')>=0 && f.color(0).indexOf('red')>=0,'Gauge colors');
 // Evaluate actual nested expressions for compact and detail views.
 function evaluate(x,loop){return typeof x==='string' && x.charAt(0)==='=' ? Function('fn','loop','props','return ('+x.slice(1)+')')(f,loop,{}) : x;}
 var widths=[],texts=[],editmode=false;
 function fields(x,loop,key) {
  if(typeof x==='string'){var value=evaluate(x,loop);if(key==='width' && x.charAt(0)==='='){widths.push(value);check(/^\d+(\.\d+)?%$/.test(value),'Gauge width '+value);}if(key==='text')texts.push(value);}
  else if(x && typeof x==='object')Object.keys(x).forEach(function(k){fields(x[k],loop,k);});
 }
 function render(n,loop){
  var cfg=n.config || {}; if(!editmode && cfg.visible!==undefined && !evaluate(cfg.visible,loop))return;
  if(n.component==='oh-repeater') {
   var arr=cfg.sourceType==='itemsInGroup'?list:evaluate(cfg.in,loop);
   arr.forEach(function(row,i){var next=Object.assign({},loop);next[cfg.for]=row;next[cfg.for+'_idx']=i;next[cfg.for+'_source']=arr;((n.slots || {}).default || []).forEach(function(ch){render(ch,next);});});return;
  }
  fields(cfg,loop);Object.keys(n.slots || {}).forEach(function(k){n.slots[k].forEach(function(ch){render(ch,loop);});});
 }
 states={high:'100 %',low:'100 %',zero:'100 %',unknown:'100 %',pending:'100 %'};
 render(w.slots.background[0],{});check(texts.indexOf('Alle Batterien voll geladen')>=0,'Full state actual text');check(widths.length===1,'Full state hides individual compact rows');
 widths=[];texts=[];states.low='0 %';render(w.slots.background[0],{});check(widths.indexOf('0%')>=0,'Empty gauge actually 0%');check(texts.indexOf('Alle Batterien voll geladen')<0,'No false full message');
 editmode=true;widths=[];texts=[];render(w.slots.background[0],{});
 check(texts.indexOf('Keine gültigen Prozentwerte')<0,'Editor does not force unknown message over valid rows');
 check(widths.length===4,'Editor renders header and three actual rows');
 states={high:'100 %',low:'100 %',zero:'100 %',unknown:'100 %',pending:'100 %'};
 widths=[];texts=[];render(w.slots.background[0],{});
 check(texts.indexOf('Alle Batterien voll geladen')>=0 && widths.length===1,'Editor full state');
 states={high:'UNDEF',low:'UNDEF',zero:'UNDEF',unknown:'UNDEF',pending:'UNDEF'};
 widths=[];texts=[];render(w.slots.background[0],{});
 check(texts.indexOf('Keine gültigen Prozentwerte')>=0 && widths.length===1,'Editor missing state');
 editmode=false;render(w.slots.default[0],{});
 check(JSON.stringify(defs)===JSON.stringify(w.slots.default[0].config.functions),'Identical functions in both views');
 if(argv[1]) {
  var actual=JSON.parse($.NSString.stringWithContentsOfFileEncodingError(argv[1],$.NSUTF8StringEncoding,null).js);
  var batteries=actual.filter(function(s){return (s.groupNames || []).indexOf('Battery_ALL')>=0;});
  var rows=f.rows(batteries,function(n){return batteries.find(function(s){return s.name===n;}).state;},f.value);
  var sorted=f.summary(rows,f.sorted);
  check(rows.length===57,'57 archived batteries');
  check(sorted.lowest.length===3,'Three lowest archived values');
  check(sorted.rows.every(function(r,i,a){return i===0 || r.value===null || a[i-1].value!==null && a[i-1].value<=r.value;}),'Archived ascending order');
 }
 return count+' Prüfungen für Sortierung, Prozentwerte, Füllstand und Vollzustand bestanden.';
}
