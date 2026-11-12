// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Offline checks of source utilities, generated YAML utilities and the new template.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

if (process.argv.length !== 3) {
  console.error('Usage: node tools/state-alarms/check.cjs /path/to/library.json');
  process.exit(2);
}
const library = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const temperatureBlock = library.slots.blocks.find(b => b.config.type === 'lhlab_temperature_window_monitor');
assert(temperatureBlock, 'Temperature block must be present');
const template = temperatureBlock.slots.code[0].config.template;
assert.equal(library.slots.blocks.filter(b => b.config.type === temperatureBlock.config.type).length, 1);
assert.equal(library.slots.utilities.filter(u => u.config.name === 'lhlab_temperature_window_monitor').length, 1);
for (const [name, file, checks] of [
  ['lhlab_state_monitor', 'monitor.js', 'verify.js'],
  ['lhlab_temperature_window_monitor', 'temperature-monitor.js', 'verify-temperature.js']
]) {
  const verify = vm.runInNewContext(fs.readFileSync(path.join(__dirname, checks), 'utf8'));
  const source = fs.readFileSync(path.join(__dirname, file), 'utf8');
  const generated = library.slots.utilities.find(u => u.config.name === name).config.code
    .replace('function {{name}}(', 'function ' + name + '(');
  assert.equal(generated, source, 'Generated utility must match its source: ' + name);
  for (const [label, code] of [['source', source], ['generated YAML', generated]]) {
    const results = verify(vm, code, template);
    console.log(name + ' (' + label + '): ' + results.length + ' scenarios passed');
  }
}
