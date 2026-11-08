// Evaluate actual widget functions/bindings against an isolated MainUI-style
// Item proxy. No contact, alarm, or backend configuration is changed.
function verifyWindowWidget(vm, widget, oldWidget, items, metadataPlan) {
  const assert=(v,m)=>{if(!v)throw Error(m);};
  const original=new Map(items.map(i=>[i.name,i]));
  const contacts=items.filter(i=>i.type==='Contact'&&(i.groupNames||[]).includes('Fenster_ALL'))
    .map(i=>Object.assign({},i,{metadata:Object.assign({},i.metadata,{contactOverview:metadataPlan.find(p=>p.name===i.name).after})}));
  const equipment=items.filter(i=>(i.groupNames||[]).includes('Fenster_Uebersicht_Equipment'));
  let states=new Map(),reads=0;const tracked=new Set();
  const proxy=new Proxy({}, {get(_,key){reads++;tracked.add(key);return {state:states.has(key)?states.get(key):'-'};}});
  const props={contactGroup:'Fenster_ALL',alarmGroupItem:'Fenster_Alarm_ALL',closeAlarmItem:'Fenster_Schliessen_Alarm',testMode:'live'};
  function context(definition){
    const ctx=vm.createContext({items:proxy,props,loop:{},fn:{}});
    for(const [name,source] of Object.entries(definition))ctx.fn[name]=vm.runInContext('('+source.slice(1)+')',ctx);
    return ctx;
  }
  const ctx=context(widget.slots.background[0].config.functions),f=ctx.fn;
  function closed(){
    states=new Map();
    for(const c of contacts){states.set(c.name,'CLOSED');const a=c.metadata.contactOverview.value;if(a)states.set(a,'OFF');}
    states.set(props.alarmGroupItem,'OFF');states.set(props.closeAlarmItem,'OFF');
  }
  function model(rows=f.rows(contacts,f.read,f.meta),test=false){return f.summary(rows,f.rank,f.read,test);}
  const results=[];
  let m=model();assert(!m.ready&&!m.unknown&&!m.attention.length,'Cold placeholders must not become unknown window rows');
  assert(f.tone(m).includes('gray'),'Cold view must not be green');
  results.push('Cold start with MainUI placeholder -: neutral loading, zero false window rows');
  for(const c of contacts)states.set(c.name,'CLOSED');
  m=model();assert(!m.ready&&!m.unknown&&!m.attention.length,'Pending Alarm Items must not create phantom rows');
  results.push('Contacts loaded, alarms pending: keep loading without fabricated warnings');
  closed();m=model();assert(m.ready&&m.rows.length===16&&!m.opened&&!m.alarms&&!m.unknown&&!m.attention.length,'All closed');
  assert(f.tone(m).includes('green'),'Known closed state should be green');
  assert(m.rows.filter(r=>r.kind==='door').length===2&&m.rows.filter(r=>r.kind==='window').length===14,'Semantic symbol types');
  results.push('16 known closed contacts: green summary and correct 14 window / 2 door symbols');
  states.set(contacts[0].name,'UNDEF');m=model();assert(m.ready&&m.unknown===1&&m.attention.length===1,'Real UNDEF must stay visible');
  results.push('Real UNDEF remains a visible unknown; distinct from transport loading');
  closed();const alarm=contacts[0].metadata.contactOverview.value;states.set(alarm,'ON');m=model();
  assert(m.ready&&m.alarms===1&&m.attention[0].alarm===alarm&&f.tone(m).includes('red'),'Closed contact with active alarm must remain visible');
  results.push('Active alarm on closed contact is retained and prioritized');
  closed();states.set(contacts[1].name,'OPEN');states.set(contacts[2].name,'OPEN');m=model();
  assert(m.opened===2&&m.attention.length===2&&f.tone(m).includes('orange'),'Two open contacts');
  results.push('Real OPEN changes update the view model immediately');
  closed();states.set(contacts[0].metadata.contactOverview.value,'NULL');m=model();
  assert(m.ready&&m.unknown===1&&m.attention.length===1,'Actual unknown alarm must not be hidden as loading');
  results.push('Real NULL alarm remains visible');
  closed();states.set(props.alarmGroupItem,'ON');m=model();assert(f.tone(m).includes('red'),'Aggregate alarm fallback');
  states.set(props.alarmGroupItem,'-');m=model();assert(!m.ready&&f.tone(m).includes('gray'),'Pending aggregate state');
  results.push('Aggregate alarm retained; pending aggregate never claims all-clear');
  for(const mode of [undefined,'live','typo','false'])assert(!f.isDemo(mode)&&f.demo(mode).length===0,'No implicit mixed demo');
  m=model(f.demo('mixed'),true);assert(m.test&&m.alarms===2&&m.attention.length===5,'Explicit mixed demo and shared-alarm deduplication');
  m=model(f.demo('loading'),true);assert(!m.ready&&!m.attention.length,'Explicit loading preview');
  results.push('Demo data only in explicit test modes; shared alarms counted once');
  function find(node,name){
    if(node&&typeof node==='object'){
      if(node.config&&String(node.config.class||'').split(' ').includes(name))return node;
      for(const value of Object.values(node)){const result=find(value,name);if(result)return result;}
    }
    return null;
  }
  function render(node,c){
    const evaluate=x=>typeof x==='string'&&x.startsWith('=')?vm.runInContext(x.slice(1),c):x;
    const cfg=node.config||{};
    if(cfg.visible!==undefined&&!evaluate(cfg.visible))return;
    function fields(x){
      if(typeof x==='string')evaluate(x);
      else if(x&&typeof x==='object')Object.values(x).forEach(fields);
    }
    fields(cfg);
    if(node.component==='oh-repeater'){
      const source=evaluate(cfg.in)||[];
      for(const row of source){const previous=c.loop;c.loop=Object.assign({},previous,{[cfg.for]:row});
        for(const child of (node.slots||{}).default||[])render(child,c);c.loop=previous;}
    }else for(const list of Object.values(node.slots||{}))for(const child of list)render(child,c);
  }
  const shell=find(widget.slots.background,'contact-shell');
  assert(shell&&shell.config.class.includes('card-opened-fade-out'),'Background shell must hide when the cell opens');
  assert(widget.config.animate===false,'Expanded content must not wait for a WebView animation event');
  results.push('Background fades out and native details mount without an opening animation');
  // Same complete closed state and actual bindings, excluding the expanded
  // detail slot, which oh-cell mounts only when it is opened.
  closed();const old=context(oldWidget.slots.background[0].config.functions);old.loop={contacts,equipment};
  reads=0;render(find(oldWidget.slots.background,'contact-compact'),old);const oldReads=reads;
  reads=0;ctx.loop={view:model()};render(find(widget.slots.background,'contact-compact'),ctx);const newReads=reads;
  assert(newReads<oldReads/4,'Repeated reactive Item proxy accesses not sufficiently reduced');
  results.push('Actual collapsed bindings: reactive Item reads reduced from '+oldReads+' to '+newReads);
  return {results,itemReadsBefore:oldReads,itemReadsAfter:newReads,trackedItems:tracked.size};
}
verifyWindowWidget;
