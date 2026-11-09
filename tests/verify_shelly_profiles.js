// Run generated Shelly Blockly code with simulated Items, MQTT actions, and time.
// Usage: node tests/verify_shelly_profiles.js /tmp/thermostat-library.json
'use strict';
function verifyShellyProfiles(vm, block, baseline) {
  const assert = require('node:assert/strict');
  const template = block.slots.code[0].config.template;
  const input = {
    ZONE_NAME: 'zone', SETPOINT_NORMAL: 'normal', MQTT_BROKER: 'test:broker',
    MQTT_RPC_TOPIC: 'test/device/rpc', MQTT_SRC: 'test/client', PRESENCE: 'presence',
    BOOSTER: 'booster', SG_MODE: 'sg', NIGHTSTART_ITEM: 'nightStart', NIGHTSTOP_ITEM: 'nightStop',
    SCHEDULE_SWITCH: 'schedule', PROFILE_ITEM: 'profile', SETPOINT_BASE: 'base',
    SETPOINT_EFFECTIVE: 'effective', SETPOINT_ABSENCE: 'absenceTemp',
    SETPOINT_SGGREEN: 'greenTemp', SETPOINT_NIGHT: 'nightTemp', SETPOINT_WINDOW: 'windowTemp',
    ABSENCE_DECREASE: 1, SGGREEN_INCREASE: 0.5, NIGHT_DECREASE: 0.5,
    WINDOW_DECREASE: 2, WINDOWCONTACT: 'window'
  };
  const profiles = { PROFILE_WINDOW: 10, PROFILE_ABSENCE: 11, PROFILE_BOOSTER: 12,
    PROFILE_SGGREEN: 13, PROFILE_NIGHT: 14 };
  const logger = {isInfoEnabled:()=>false, isDebugEnabled:()=>false,
    isWarnEnabled:()=>false, isErrorEnabled:()=>false};
  function execute(source, scenario, fields = profiles, inputs = {}) {
    const commands = [], mqtt = [], reads = [], sleeps = [];
    const states = {zone: scenario.enabled === false ? 'OFF' : 'ON', normal:'21 °C', base:'21',
      presence: scenario.presence, booster:scenario.booster, sg:scenario.sg,
      nightStart:'22:00', nightStop:'06:00', window:scenario.window ? 'OPEN' : 'CLOSED'};
    const localTime = text => {
      const [h,m] = text.split(':').map(Number);
      return {minute:h*60+m, isAfter(other){return this.minute>other.minute;},
        isBefore(other){return this.minute<other.minute;}};
    };
    const api = {
      items:{getItem(name){reads.push(name);return {state:states[name], label:name,
        sendCommand(value){commands.push([name,value]);}};}},
      actions:{get(){return {publishMQTT(topic,payload){mqtt.push([topic,JSON.parse(payload)]);}};}},
      things:{getThing(uid){return {uid};}},
      time:{toZDT(text){return {toLocalTime:()=>localTime(text)};},
        ZonedDateTime:{now(){return {toLocalTime:()=>localTime(scenario.night ? '23:00' : '12:00')};}}}
    };
    const actualInputs=Object.assign({},input,inputs);
    const code=source.replace(/\{\{input:([^}]+)\}\}/g,(_,key)=>JSON.stringify(actualInputs[key]))
      .replace(/\{\{field:([^}]+)\}\}/g,(_,key)=>key==='LOGLEVEL' ? 'off' : String(fields[key]));
    let error;
    try {
      vm.runInNewContext(code,{require(name){assert.equal(name,'openhab');return api;},
        ruleUID:'isolated-test', Java:{type(name){return name==='java.lang.Thread' ?
          {sleep(ms){sleeps.push(ms);}} : {getLogger:()=>logger};}}});
    } catch (caught) {error=caught;}
    return {commands,mqtt,reads,sleeps,error};
  }
  let scenarios=0;
  for(const presence of ['ON','OFF']) for(const booster of ['ON','OFF'])
    for(const sg of ['red','orange','green']) for(const window of [false,true])
      for(const night of [false,true]) {
        const scenario={presence,booster,sg,window,night};
        const result=execute(template,scenario);
        assert.equal(result.error,undefined,String(result.error));
        const expected=booster==='ON' ? 12 : window ? 10 : presence==='OFF' && sg==='red' ? 11 :
          sg==='green' ? 13 : night ? 14 : null;
        assert.deepEqual(result.commands.filter(c=>c[0]==='profile'),expected===null ? [] : [['profile',String(expected)]]);
        assert.ok(result.commands.some(c=>c[0]==='schedule' && c[1]===(expected===null?'OFF':'ON')));
        assert.equal(result.mqtt.length,1);
        if(baseline) {
          const old=execute(baseline.slots.code[0].config.template,scenario,{});
          assert.equal(old.error,undefined);
          const remapped=old.commands.map(([name,value])=>[name,name==='profile'?String(Number(value)+10):value]);
          assert.equal(JSON.stringify(result.commands),JSON.stringify(remapped),'Only profile IDs may change');
          assert.equal(JSON.stringify(result.mqtt),JSON.stringify(old.mqtt));
        }
        scenarios++;
      }
  const scenario={presence:'ON',booster:'ON',sg:'orange',window:false,night:false};
  let invalidCases=0;
  for(const field of Object.keys(profiles)) for(const invalid of [-1,1.5,NaN,undefined,'']) {
    const result=execute(template,scenario,Object.assign({},profiles,{[field]:invalid}));
    assert.ok(result.error,'Invalid profile must be rejected');
    assert.equal(result.commands.length+result.mqtt.length+result.reads.length+result.sleeps.length,0);
    invalidCases++;
  }
  for(const key of ['MQTT_BROKER','MQTT_RPC_TOPIC','MQTT_SRC']) {
    const result=execute(template,scenario,profiles,{[key]:''});
    assert.ok(result.error,'Blank MQTT configuration must be rejected');
    assert.equal(result.commands.length+result.mqtt.length+result.reads.length+result.sleeps.length,0);
    invalidCases++;
  }
  const zero=execute(template,scenario,Object.fromEntries(Object.keys(profiles).map(k=>[k,0])));
  assert.equal(zero.error,undefined);
  assert.deepEqual(zero.commands.filter(c=>c[0]==='profile'),[['profile','0']]);
  const off=execute(template,Object.assign({},scenario,{enabled:false}));
  assert.equal(off.error,undefined);assert.equal(off.commands.length+off.mqtt.length+off.sleeps.length,0);
  return {scenarios,invalidCases,zeroProfile:true,thermostatOff:true,baselineCompared:!!baseline};
}
module.exports = verifyShellyProfiles;
if(require.main===module) {
  const document=JSON.parse(require('node:fs').readFileSync(process.argv[2],'utf8'));
  const block=document.blocks.lhlab_thermostat_library.slots.blocks.find(b=>b.config.type==='Shelly Walldisplay Thermostat Control');
  console.log(verifyShellyProfiles(require('node:vm'),block));
}
