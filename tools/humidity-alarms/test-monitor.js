// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Evaluate this file in a Node VM and call the resulting function with monitor.js.
// All Items, timers and notifications are simulated; nothing reaches openHAB.
(function testHumidityMonitor(source, vm) {
  let assertions = 0;
  function equal(actual, expected, message) {
    assertions++;
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error(message + ': ' + JSON.stringify(actual) + ' != ' + JSON.stringify(expected));
    }
  }
  function harness() {
    let instant = 1800000000000;
    const store = new Map(), commands = [], messages = [], timers = [];
    const rooms = {
      kitchen: { getName: () => 'kitchen', getLabel: () => 'Küche' },
      bath: { getName: () => 'bath', getLabel: () => 'Badezimmer' },
      tech: { getName: () => 'tech', getLabel: () => 'Technikraum' },
    };
    const members = {}, values = {};
    function item(name, room, state) {
      const object = { name, room, state, rawItem: { room },
        sendCommandIfDifferent(value) { if (this.state !== value) commands.push([this.name, value]); },
      };
      Object.defineProperty(object, 'quantityState', { configurable: true, get() {
        if (object.state === 'NULL' || object.state === 'UNDEF') return null;
        const value = Number(String(object.state).replace(' %', ''));
        return { toUnit: () => ({ float: value }) };
      }});
      values[name] = object; return object;
    }
    const sensorMembers = [item('kh', 'kitchen', '50 %'), item('bh', 'bath', '50 %'), item('th', 'tech', '40 %')];
    const alarmMembers = [item('ka', 'kitchen', 'OFF'), item('ba', 'bath', 'OFF'), item('ta', 'tech', 'OFF')];
    values.humidities = { name: 'humidities', members: sensorMembers };
    values.alarms = { name: 'alarms', members: alarmMembers };
    const api = {
      items: { getItem(name) { if (!values[name]) throw new Error('Missing item ' + name); return values[name]; },
        metadata: { getMetadata: () => null } },
      cache: { private: { get: key => store.get(key), put: (key, value) => store.set(key, value), remove: key => store.delete(key) } },
      actions: {
        Semantics: { getLocation: raw => rooms[raw.room] || null },
        ScriptExecution: { createTimer(deadline, fn) {
          const timer = { active: true, isActive() { return this.active; }, fire() { this.active = false; fn(); } };
          timers.push(timer); return timer;
        } },
      },
      time: { ZonedDateTime: { now: () => ({ plusSeconds: seconds => instant + seconds * 1000 }) } },
    };
    const context = { require: () => api, Date: { now: () => instant }, console: { warn() {}, error(e) { throw new Error(e); } } };
    vm.runInNewContext(source + '\nthis.monitor = lhlab_humidity_monitor;', context);
    const config = { sensorGroup: 'humidities', alarmGroup: 'alarms', threshold: 75,
      overrides: [{ sensor: 'bh', threshold: 80 }], externalAlarms: ['ta'], repeatHours: 12, delaySeconds: 2 };
    function run(name, dry = false) {
      return context.monitor(config, name ? { itemName: name } : null,
        event => messages.push(['ALARM', event.message]), event => messages.push(['CLEAR', event.message]), dry);
    }
    function settle() {
      for (const [name, state] of commands.splice(0)) { values[name].state = state; run(name); }
    }
    function flush() { timers.filter(timer => timer.active).forEach(timer => timer.fire()); }
    return { run, values, commands, messages, timers, store, config, api, settle, flush,
      advance: hours => { instant += hours * 3600000; } };
  }
  {
    const h = harness();
    const report = h.run(null, true);
    equal(report.managed, ['kh', 'bh'], 'dry run maps managed rooms');
    equal(report.external, ['th'], 'external MQTT alarm stays external');
    equal(h.commands.length, 0, 'dry run has no commands');
    equal(h.timers.length, 0, 'dry run has no timers');
    equal(h.store.size, 0, 'dry run does not modify cache');
    h.run('kh'); equal(h.commands.length, 0, 'unchanged humidity sends no command');
    equal(h.timers.length, 0, 'normal humidity creates no timer');
    h.values.kh.state = '75 %'; const one = h.run('kh');
    equal(one.managed, ['kh'], 'event evaluates only its room');
    equal(h.commands, [['ka', 'ON']], 'threshold includes exact boundary');
    equal(h.messages.length, 0, 'command does not assume immediate state update');
    h.settle(); h.flush(); equal(h.messages, [['ALARM', 'Achtung! Luftfeuchtigkeit im Küche ist zu hoch.']], 'warn after alarm state change');
    h.run('kh'); h.flush(); equal(h.messages.length, 1, 'warning is suppressed during cooldown');
    h.advance(12); h.run('kh'); h.flush(); equal(h.messages.length, 2, 'new measurement after 12 hours permits reminder');
    h.values.kh.state = '74 %'; h.run('kh'); h.settle(); h.flush();
    equal(h.messages.at(-1)[0], 'CLEAR', 'recovery sends clearance');
    h.run('kh'); h.flush(); equal(h.messages.length, 3, 'recovery does not repeat');
  }
  {
    const h = harness(); h.values.bh.state = '79.9 %'; h.run('bh');
    equal(h.commands.length, 0, 'bathroom override keeps 79.9 below limit');
    h.values.bh.state = '80 %'; h.run('bh'); equal(h.commands, [['ba', 'ON']], 'bathroom threshold remains 80');
    h.values.kh.state = '90 %'; h.run('kh'); h.settle();
    equal(h.timers.length, 1, 'simultaneous alarms share one short timer');
    h.flush(); equal(h.messages.length, 1, 'simultaneous rooms produce one notification');
    equal(h.messages[0][1].includes('Badezimmer und Küche'), true, 'batched notification names both rooms');
    h.advance(13); h.values.kh.state = '60 %'; h.run('kh'); h.settle(); h.flush();
    equal(h.messages.some(message => message[0] === 'CLEAR'), true, 'clearance still works after cooldown expired');
  }
  {
    const h = harness(); h.values.ka.state = 'ON';
    for (const invalid of ['NULL', 'UNDEF', 'NaN', '-1 %', '101 %']) {
      h.values.kh.state = invalid; const report = h.run('kh');
      equal(report.invalid, ['kh'], 'invalid sensor is reported: ' + invalid);
      equal(h.commands.length, 0, 'invalid sensor does not clear existing alarm: ' + invalid);
    }
    h.values.kh.state = '0.75';
    Object.defineProperty(h.values.kh, 'quantityState', { configurable: true, get: () => ({ toUnit: unit => ({ float: unit === '%' ? 75 : 0.75 }) }) });
    const report = h.run('kh'); equal(report.invalid, [], 'dimensionless quantity is converted to percent');
  }
  {
    const h = harness(); h.values.th.state = '99 %'; h.run('th');
    equal(h.commands.length, 0, 'MQTT-managed alarm is never overwritten');
    h.values.ta.state = 'ON'; h.run('ta'); h.flush();
    equal(h.messages[0][1].includes('Technikraum'), true, 'external alarm still notifies');
    h.advance(12); h.run('th'); h.flush();
    equal(h.messages.length, 2, 'external alarm can remind on a new measurement without replacing MQTT evaluation');
    h.values.ta.state = 'OFF'; h.run('ta'); h.flush(); equal(h.messages.at(-1)[0], 'CLEAR', 'external alarm clears');
  }
  {
    const h = harness(); h.values.kh.room = null; h.values.kh.rawItem.room = null;
    equal(h.run('kh').missing, ['kh'], 'missing semantic mapping is safe');
    equal(h.commands.length, 0, 'unmapped sensor sends no command');
    h.values.kh.room = 'kitchen'; h.values.kh.rawItem.room = 'kitchen';
    h.values.kh.state = '90 %'; h.run('kh'); equal(h.commands, [['ka', 'ON']], 'newly repaired mapping is discovered immediately');
  }
  {
    const h = harness();
    h.api.actions.Semantics.getLocation = () => null;
    h.values.kitchenRoom = { name: 'kitchenRoom', label: 'Küche' };
    h.values.kitchenEquipment = { name: 'kitchenEquipment' };
    h.api.items.metadata.getMetadata = name => ({ configuration: {
      kh: { isPointOf: 'kitchenEquipment' },
      kitchenEquipment: { hasLocation: 'kitchenRoom' },
      ka: { hasLocation: 'kitchenRoom' },
    }[name] || {} });
    h.values.kh.state = '90 %'; h.run('kh');
    equal(h.commands, [['ka', 'ON']], 'equipment and room metadata work when the standard semantic action returns null');
  }
  {
    const h = harness(); h.config.overrides.push({ sensor: 'bh', threshold: 90 });
    let rejected = false; try { h.run('bh'); } catch (e) { rejected = true; }
    equal(rejected, true, 'ambiguous threshold overrides fail before commands');
    equal(h.commands.length, 0, 'invalid configuration leaves alarms alone');
  }
  return { assertions, status: 'passed' };
})
