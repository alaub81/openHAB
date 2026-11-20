// Run public widget and Blockly behavior checks with synthetic Items only.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const bundlePath = process.argv[2];
const bundle = JSON.parse(fs.readFileSync(bundlePath, 'utf8'));
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
function evaluate(file, symbol) {
  return vm.runInNewContext(read(file) + (symbol ? '\n' + symbol + ';' : ''), {}, {filename: file});
}
for (const [directory, uid] of [
  ['battery-widget', 'batterie_ladestaende_cell'],
  ['humidity-widget', 'luftfeuchtigkeit_alarm_cell']
]) {
  // The historical CLI accepts a document with a widgets wrapper.
  const file = path.join(path.dirname(bundlePath), directory + '.json');
  fs.writeFileSync(file, JSON.stringify({widgets: {[uid]: bundle[uid]}}));
  console.log(directory + ': ' + require('../tools/' + directory + '/verify.js')([file]));
}
const thermostat = bundle.lhlab_thermostat_library.slots.blocks.find(
  b => b.config.type === 'Shelly Walldisplay Thermostat Control');
console.log('Shelly profiles:', require('./verify_shelly_profiles.js')(vm, thermostat));

const contacts = Array.from({length: 16}, (_, i) => ({
  name: 'SyntheticContact' + i, type: 'Contact', label: 'Contact ' + i,
  groupNames: ['Fenster_ALL']
}));
const metadata = contacts.map((c, i) => ({name: c.name, after: {
  value: 'SyntheticAlarm' + i, config: {kind: i < 2 ? 'door' : 'window'}
}}));
const windowResult = evaluate('tools/window-widget/verify.js')(
  vm, bundle.fenster_tueren_cell, null, contacts, metadata);
console.log('Window widget: ' + windowResult.results.length + ' scenarios passed');

const humidityCheck = evaluate('tools/humidity-alarms/test-monitor.js');
console.log('Humidity source:', humidityCheck(read('tools/humidity-alarms/monitor.js'), vm));
const humidityLibrary = bundle.lhlab_humity_alarm_library;
const humiditySource = humidityLibrary.slots.utilities.find(
  u => u.config.name === 'lhlab_humidity_monitor').config.code
  .replace(/\{\{name\}\}/g, 'lhlab_humidity_monitor');
console.log('Humidity YAML:', humidityCheck(humiditySource, vm));

const alarmLibrary = bundle.lhlab_alarm_library;
function utility(name) {
  const result = alarmLibrary.slots.utilities.find(u => u.config.name === name);
  assert(result, 'Missing utility ' + name);
  return result.config.code.replace(/\{\{name\}\}/g, name)
    .replace(/\{\{(lhlab_\w+)\}\}/g, '$1');
}
const sources = {format: utility('lhlab_dwd_text'), process: utility('lhlab_alarm_process'),
  monitor: utility('lhlab_dwd_monitor')};
assert.equal(sources.format, read('tools/dwd-messages/format.js'), 'DWD source and YAML must match');
const dwd = evaluate('tools/dwd-messages/verify.js', 'verifyDwd')(require('./time-double.cjs'), sources);
console.log('DWD with time double: ' + dwd.assertions + ' assertions passed');
