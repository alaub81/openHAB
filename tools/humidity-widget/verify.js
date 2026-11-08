// Run with: osascript -l JavaScript tools/humidity-widget/verify.js /tmp/widget.json
// Export YAML to JSON first. Restrict globals to the values MainUI exposes.
ObjC.import('Foundation');
function run(argv) {
  var doc=JSON.parse($.NSString.stringWithContentsOfFileEncodingError(argv[0],$.NSUTF8StringEncoding,null).js);
  var widget=doc.widgets.luftfeuchtigkeit_alarm_cell;
  var defs=widget.slots.background[0].config.functions;
  var assertions=0;
  function check(v,msg){assertions++;if(!v)throw Error(msg);}
  // MainUI supplies Number and Math, but does not expose global parseFloat.
  function compile(source,items){
    return Function('items','parseFloat','parseInt','return ('+source.slice(1)+')')(items,undefined,undefined);
  }
  var states={},tracked={};
  var items=new Proxy({}, {get:function(_,name){tracked[name]=true;return {state:states[name] || '-'};}});
  var f={};Object.keys(defs).forEach(function(k){f[k]=compile(defs[k],items);});
  var original=compile(defs.humidity.replace(/Number\.parseFloat/g,'parseFloat'),items);
  check(original('-')==='— %','Original placeholder branch');
  var failed=false;try{original('78 %');}catch(e){failed=true;}
  check(failed,'Reproduce original failure when a real value arrives');
  [['78 %','78 %'],['65.34 %','65.3 %'],['65,2 %','65.2 %'],['0 %','0 %'],['100 %','100 %'],['NULL','— %'],['UNDEF','— %'],['-','— %'],['','— %'],['101 %','— %'],['-1 %','— %'],['50 °C','— %']].forEach(function(t){check(f.humidity(t[0])===t[1],'Format '+t[0]);});
  function semantic(config){return {semantics:{config:config}};}
  var members=[{name:'alarm',type:'Switch',label:'Badezimmer Luftfeuchtigkeit Alarm',metadata:semantic({hasLocation:'room'})}];
  var equipment={name:'equipment',type:'Group',metadata:semantic({hasLocation:'room'})};
  var sensor={name:'sensor',type:'Number:Dimensionless',groupNames:['sensors'],metadata:semantic({isPointOf:'equipment'})};
  var index=[equipment,sensor];
  function resolve(a,list,all){return f.resolve(a,f.sensors(list,'sensors',f.room,f.semantics),f.room(a,all,f.semantics,f.room,[]));}
  function model(){return f.summary(f.rows(members,f.sensors(index,'sensors',f.room,f.semantics),index,f.room,f.semantics,f.resolve,f.read,f.humidity),f.rank);}
  var v=model();check(!v.ready,'Cold alarm state loads');
  states.alarm='OFF';v=model();
  check(v.ready && v.rows[0].humidity==='— %','Pending sensor does not block known alarm');
  states.sensor='78 %';v=model();
  check(v.ready && v.rows[0].humidity==='78 %','Real value does not break rendering');
  check(f.brief(v.rows[0])==='78 % · OK','Compact view');
  states.alarm='ON';v=model();
  check(v.alarms===1 && f.brief(v.rows[0])==='78 % · Alarm','Live alarm');
  check(f.detail(v.rows[0]).indexOf('78 %')>=0,'Detail value');
  states.sensor='UNDEF';v=model();
  check(v.ready && v.alarms===1 && v.rows[0].humidity==='— %','Invalid measurement preserves alarm');
  check(tracked.sensor,'Mapped sensor is tracked');
  check(resolve({name:'override',metadata:{humidityOverview:{value:'Custom'}}},[],[]).sensor==='Custom','Metadata override');
  check(resolve({name:'missing'},index,index).issue==='Raumzuordnung fehlt','Missing room');
  check(resolve(members[0],[],index).issue==='Kein Feuchtesensor im Raum','Missing sensor');
  var second=Object.assign({},sensor,{name:'newSensor'});
  check(resolve(members[0],index.concat([second]),index).issue==='Zuordnung mehrdeutig','Ambiguous room');
  check(resolve(members[0],[equipment,second],[equipment,second]).sensor==='newSensor','Renamed sensor maps automatically');
  var nested={name:'childEquipment',type:'Group',metadata:semantic({isPartOf:'equipment'})};
  var nestedSensor=Object.assign({},sensor,{metadata:semantic({isPointOf:'childEquipment'})});
  check(resolve(members[0],[equipment,nested,nestedSensor],[equipment,nested,nestedSensor]).sensor==='sensor','Nested equipment');
  var cycleA={name:'a',metadata:semantic({isPointOf:'b'})},cycleB={name:'b',metadata:semantic({isPartOf:'a'})};
  check(f.room(cycleA,[cycleA,cycleB],f.semantics,f.room,[])==='','Semantic cycle safe');
  check(f.flatten([{name:'a',members:[{name:'b',members:[{name:'c'}]}]}],f.flatten,0).length===3,'Recursive model');
  check(f.sensors(index.concat([sensor]),'sensors',f.room,f.semantics).length===1,'Duplicate group paths deduplicated');
  if(argv[1]) {
    var actual=JSON.parse($.NSString.stringWithContentsOfFileEncodingError(argv[1],$.NSUTF8StringEncoding,null).js);
    var alarms=actual.filter(function(s){return (s.groupNames || []).indexOf('Humidity_Alarm')>=0 && s.type==='Switch';});
    var sensors=f.sensors(actual,'Humidity_Innen_ALL',f.room,f.semantics);
    var actualRows=f.rows(alarms,sensors,actual,f.room,f.semantics,f.resolve,function(n){var i=actual.find(function(s){return s.name===n;});return i?i.state:'-';},f.humidity);
    check(actualRows.length===18,'18 archived room alarms');
    actualRows.forEach(function(r){check(!r.issue && !!r.sensor,'Archived room maps: '+r.name);});
  }
  check(!/BadOG|Shelly|LaubRaspi|Schlafzimmmer/.test(JSON.stringify(defs)),'No installation-specific Item mappings');
  check(JSON.stringify(defs)===JSON.stringify(widget.slots.default[0].config.functions),'Both views use identical functions');
  return assertions+' Prüfungen bestanden; ursprünglicher Fehler reproduziert, Korrektur geprüft.';
}
