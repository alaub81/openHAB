// Run the real utility against a virtual clock; no openHAB command/message is sent.
function verifyStateMonitor(vm, source) {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const results = [];
  function fixture(overrides = {}) {
    let now = 1000000;
    const values = new Map(), stored = new Map(), timers = [], notices = [], clears = [], writes = [], errors = [];
    const cfg = Object.assign({source:'contact',alarm:'alarm',active:'OPEN',delayMinutes:15,
      repeats:2,intervalMinutes:5,title:'Fensteralarm'}, overrides);
    values.set(cfg.source,{type:cfg.active==='OPEN'?'Contact':'Switch',label:'Testfenster',state:cfg.active});
    values.set(cfg.alarm,{type:'Switch',state:'OFF'});
    const api = {
      items: {getItem(name) {
        const item = values.get(name); if (!item) throw new Error('Unknown Item: '+name);
        return {type:item.type,label:item.label,get state(){return item.state;},postUpdate(v){item.state=v;writes.push([name,v]);}};
      }},
      cache: {private:{get:k=>stored.get(k),exists:k=>stored.has(k),put:(k,v)=>stored.set(k,v),
        remove:k=>{const v=stored.get(k);stored.delete(k);return v;}}},
      time: {ZonedDateTime:{now:()=>({plusSeconds:s=>({at:now+s*1000})})}},
      actions: {ScriptExecution:{createTimer(name,when,callback){
        const timer={name,at:when.at,callback,active:true,isActive(){return this.active;},cancel(){this.active=false;}};
        timers.push(timer);return timer;
      }}}
    };
    const monitor=vm.runInNewContext(source+'\nlhlab_state_monitor;',{
      require:name=>{assert(name==='openhab','Unexpected require');return api;},
      Date:{now:()=>now},console:{error:v=>errors.push(v)}
    });
    const notify=e=>notices.push(e),clear=e=>clears.push(e);
    function run(config=cfg,onNotify=notify,onClear=clear){monitor(config,onNotify,onClear);}
    function advance(minutes){
      const end=now+minutes*60000;let limit=0;
      while(true){
        const next=timers.filter(t=>t.active&&t.at<=end).sort((a,b)=>a.at-b.at)[0];
        if(!next)break;
        assert(++limit<1000,'Timer loop');now=next.at;next.active=false;next.callback();
      }
      now=end;
    }
    return {cfg,values,stored,timers,notices,clears,writes,errors,run,advance,monitor,notify,clear,
      source:value=>values.get(cfg.source).state=value,alarm:()=>values.get(cfg.alarm).state};
  }
  let f=fixture();f.run();f.advance(10);f.run();f.advance(4.9);
  assert(!f.notices.length,'Must not warn early or reset deadline on repeated active states');
  f.advance(.1);assert(f.notices.length===1&&f.alarm()==='ON','First deadline');
  f.advance(30);assert(f.notices.length===3&&!f.timers.some(t=>t.active),'Exactly one alarm plus two reminders');
  assert(f.notices.map(n=>n.kind).join()==='NEW,REMINDER,REMINDER','Event kinds');
  assert(f.notices.every(n=>n.id===f.cfg.alarm),'Stable notification identity');
  f.source('CLOSED');f.run();f.run();assert(f.alarm()==='OFF'&&f.clears.length===1,'One clearance');
  results.push('15-minute deadline, no sliding reset, two five-minute reminders, one clearance');

  f=fixture({delayMinutes:30,intervalMinutes:10});f.run();f.advance(29.9);
  assert(!f.notices.length,'Thirty-minute alarm must not warn early');
  f.advance(.1);assert(f.notices.length===1,'Thirty-minute first alarm');
  f.advance(9.9);assert(f.notices.length===1,'Ten-minute reminder must not warn early');
  f.advance(.1);assert(f.notices.length===2,'First ten-minute reminder');
  f.advance(10);assert(f.notices.length===3,'Second ten-minute reminder');
  f.advance(20);assert(f.notices.length===3&&!f.timers.some(t=>t.active),'Reminder budget exhausted');
  f.source('CLOSED');f.run();assert(f.clears.length===1&&f.alarm()==='OFF','Thirty-minute alarm clears');
  results.push('30/40/50-minute alarm sequence, no early notifications and no further reminders');

  f=fixture();f.run();const stale=f.timers[0];f.advance(5);f.source('CLOSED');f.run();
  f.source('OPEN');f.run();stale.callback();assert(!f.notices.length,'Stale callback must not raise alarm');
  assert(f.timers.filter(t=>t.active).length===1,'Stale callback must preserve new timer');
  f.advance(15);assert(f.notices.length===1,'Reopened window gets a complete new deadline');
  results.push('Early closure cancels; reopening starts fresh; stale callback cannot affect new timer');

  f=fixture();const other=Object.assign({},f.cfg,{source:'other',alarm:'otherAlarm'});
  f.values.set('other',{type:'Contact',state:'OPEN',label:'Other window'});f.values.set('otherAlarm',{type:'Switch',state:'OFF'});
  f.run();f.run(other);f.source('CLOSED');f.run();f.advance(15);
  assert(f.notices.length===1&&f.notices[0].id==='otherAlarm'&&f.alarm()==='OFF','Independent alarm keys');
  results.push('Two windows in one script: cancelling one preserves the other');

  f=fixture({active:'ON',delayMinutes:2,repeats:0,title:'Lichtalarm'});f.run();f.advance(10);
  assert(f.notices.length===1&&f.notices[0].message.includes('eingeschaltet'),'Light alarm');
  f.source('OFF');f.run();assert(f.clears.length===1&&f.alarm()==='OFF','Light clearance');
  results.push('ON/OFF light source and zero reminders');

  f=fixture({active:'ON',delayMinutes:30,intervalMinutes:5,title:'Lichtalarm'});
  f.run();f.advance(29.9);assert(!f.notices.length,'Bathroom light must not warn before thirty minutes');
  f.advance(.1);assert(f.notices.length===1,'Bathroom first warning at thirty minutes');
  f.run();f.advance(5);assert(f.notices.length===2,'Bathroom reminder at thirty-five minutes');
  f.advance(5);assert(f.notices.length===3,'Bathroom reminder at forty minutes');
  f.advance(20);assert(f.notices.length===3,'Bathroom reminder limit');
  f.source('OFF');f.run();assert(f.alarm()==='OFF'&&f.clears.length===1&&!f.timers.some(t=>t.active),'Bathroom OFF clears alarm and timers');
  results.push('Bathroom ON/OFF light: 30/35/40-minute sequence and one OFF clearance');

  f=fixture();f.run();f.advance(10);f.source('UNDEF');f.run();f.advance(10);
  assert(!f.notices.length&&f.alarm()==='OFF','Unknown source must cancel pending first alarm');
  f.source('OPEN');f.run();f.advance(14);assert(!f.notices.length,'Recovery needs full waiting period');
  f.advance(1);assert(f.notices.length===1,'Recovery deadline');
  f.source('NULL');f.run();f.advance(6);assert(f.alarm()==='ON'&&!f.clears.length&&f.notices.length===1,'Unknown source retains active alarm without reminders');
  f.source('CLOSED');f.run();assert(f.clears.length===1&&f.alarm()==='OFF','Valid closure clears');
  results.push('NULL/UNDEF never cause alarm/clearance; pending delay restarts after a data gap');

  f=fixture();f.run();f.source('CLOSED');f.advance(15);
  assert(!f.notices.length&&f.alarm()==='OFF','Callback must re-read source even if close trigger was missed');
  results.push('Timer re-reads source before notifying');

  f=fixture();f.values.get('alarm').state='ON';f.run();f.advance(60);
  assert(!f.notices.length&&f.alarm()==='ON','Reload must not replay persisted active alarm');
  f.source('CLOSED');f.run();assert(f.clears.length===1,'Persisted active alarm still clears');
  results.push('Reload with active Alarm Item: no replay; confirmed closure clears');

  f=fixture();let attempts=0;
  f.run(f.cfg,e=>{if(++attempts===1)throw Error('Delivery failure');f.notices.push(e);});
  f.advance(16);assert(attempts===2&&f.notices.length===1&&f.errors.length===1,'Failed callback retries');
  results.push('Failed notification callback retries with same identity');

  f=fixture();f.run();f.advance(15);let clearAttempts=0;f.source('CLOSED');
  try{f.run(f.cfg,f.notify,e=>{if(++clearAttempts===1)throw Error('Clear failure');f.clears.push(e);});}catch(e){}
  f.source('OPEN');f.run();f.advance(1);assert(!f.clears.length,'Reopening discards obsolete pending clearance');
  results.push('Reopening suppresses an obsolete failed clearance');

  f=fixture();let invalid=false;
  try{f.run(Object.assign({},f.cfg,{source:'alarm'}));}catch(e){invalid=true;}
  assert(invalid&&!f.timers.length&&!f.writes.length,'Invalid configuration must be rejected');
  results.push('Invalid configuration rejected before changes');
  return results;
}
verifyStateMonitor;
