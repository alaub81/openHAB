// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Execute with virtual Items, time and delivery; never contacts a live server.
function verifyTemperatureWindow(vm, source, template) {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const results = [];
  function fixture(overrides = {}) {
    let now = 1000000, limit = 20.5, thresholdReads = 0;
    const items = new Map(), cache = new Map(), timers = [], notices = [], clears = [], writes = [], reads = [], errors = [];
    const cfg = Object.assign({ source: 'contact', temperature: 'temperature', alarm: 'alarm',
      delayMinutes: 10, repeats: 2, intervalMinutes: 10, title: 'Fensteralarm',
      threshold: () => { thresholdReads++; return limit; } }, overrides);
    items.set(cfg.source, { type: 'Contact', state: 'OPEN', label: 'Testfenster' });
    items.set(cfg.temperature, { type: 'Number:Temperature', value: 20, unit: '°C' });
    items.set(cfg.alarm, { type: 'Switch', state: 'OFF' });
    const api = {
      items: { getItem(name) {
        reads.push(name);
        const item = items.get(name);
        if (!item) throw Error('Unknown Item: ' + name);
        return { type: item.type, label: item.label, get state() { return item.state; },
          get numericState() { return item.value; },
          get quantityState() {
            if (!Number.isFinite(item.value)) return null;
            return { toUnit(unit) {
              assert(unit === '°C', 'Temperature must be converted to Celsius');
              if (!['°C', '°F', 'K'].includes(item.unit)) return null;
              return { float: item.unit === '°F' ? (item.value - 32) * 5 / 9
                : item.unit === 'K' ? item.value - 273.15 : item.value };
            } };
          },
          postUpdate(value) { item.state = value; writes.push([name, value]); }
        };
      } },
      cache: { private: { get: k => cache.get(k), put: (k, v) => cache.set(k, v), remove: k => cache.delete(k) } },
      time: { ZonedDateTime: { now: () => ({ plusSeconds: s => ({ at: now + s * 1000 }) }) } },
      actions: { ScriptExecution: { createTimer(name, when, callback) {
        const timer = { name, at: when.at, callback, active: true,
          isActive() { return this.active; }, cancel() { this.active = false; } };
        timers.push(timer); return timer;
      } } }
    };
    const sandbox = { require: name => { assert(name === 'openhab', 'Unexpected import'); return api; },
      Date: { now: () => now }, console: { error: e => errors.push(e) }, testThreshold: cfg.threshold };
    const monitor = vm.runInNewContext(source + '\nlhlab_temperature_window_monitor;', sandbox);
    const notify = e => notices.push(e), clear = e => clears.push(e);
    function run(onNotify = notify, onClear = clear, config = cfg) { monitor(config, onNotify, onClear); }
    function advance(minutes) {
      const end = now + minutes * 60000;
      let count = 0;
      while (true) {
        const next = timers.filter(t => t.active && t.at <= end).sort((a, b) => a.at - b.at)[0];
        if (!next) break;
        assert(++count < 1000, 'Timer loop');
        now = next.at; next.active = false; next.callback();
      }
      now = end;
    }
    return { cfg, items, cache, timers, notices, clears, writes, reads, errors, sandbox,
      run, advance, notify, clear, active: () => timers.filter(t => t.active),
      source: v => { items.get(cfg.source).state = v; },
      temperature: v => { items.get(cfg.temperature).value = v; },
      threshold: v => { limit = v; }, thresholdReads: () => thresholdReads,
      alarm: () => items.get(cfg.alarm).state };
  }
  let f = fixture(); f.run(); f.advance(5);
  for (let n = 0; n < 100; n++) f.run();
  assert(f.timers.length === 1, 'Frequent temperature changes must reuse the deadline');
  f.advance(4.9); assert(!f.notices.length, 'No early warning');
  f.advance(.1); assert(f.notices.length === 1 && f.alarm() === 'ON', 'First alarm at ten minutes');
  f.advance(20); assert(f.notices.map(e => e.kind).join() === 'NEW,REMINDER,REMINDER', 'Two reminders');
  f.advance(100); f.run(); assert(!f.active().length && f.notices.length === 3, 'Budget exhausted without polling');
  assert(f.notices.every(e => e.id === 'alarm' && e.message.includes('20.5 °C')), 'Stable identity and threshold');
  f.source('CLOSED'); f.run(); f.run();
  assert(f.clears.length === 1 && f.clears[0].clearanceReason === 'CLOSED' && f.alarm() === 'OFF', 'One closure clearance');
  results.push('Fixed deadline, at most one timer, two reminders, exhausted budget and one clearance');

  f = fixture(); f.source('CLOSED');
  for (let n = 0; n < 1000; n++) f.run();
  assert(f.reads.length === 2000 && !f.reads.includes('temperature') && !f.thresholdReads(), 'Closed fast path reads only contact and alarm');
  assert(!f.timers.length && !f.writes.length && !f.notices.length && !f.clears.length, 'Closed idle state creates no work');
  results.push('1,000 closed evaluations: zero temperature/threshold reads, timers, writes or messages');

  f = fixture(); f.temperature(22); f.run(); f.advance(60);
  assert(!f.timers.length && !f.notices.length, 'Open but warm is idle');
  f.temperature(20.5); f.run(); f.advance(10);
  assert(f.notices.length === 1, 'Equality is cold, matching old rules');
  f.temperature(20.6); f.run(); f.advance(60);
  assert(f.alarm() === 'OFF' && f.clears.length === 1 && !f.active().length, 'Warmth clears and cancels reminders');
  assert(f.clears[0].message.includes('weiterhin offen') && f.clears[0].clearanceReason === 'WARM', 'Warm clearance never claims closed');
  results.push('Warm idle, inclusive threshold, distinct temperature clearance and stopped reminders');

  f = fixture(); f.run(); const stale = f.timers[0]; f.advance(5); f.temperature(22); f.run();
  assert(!f.active().length && !f.clears.length, 'Warmth cancels pending delay without clearance');
  f.temperature(19); f.run(); stale.callback();
  assert(f.active().length === 1 && !f.notices.length, 'Cancelled callback cannot remove a newer timer');
  f.advance(9.9); assert(!f.notices.length, 'Cold recovery gets complete delay');
  f.advance(.1); assert(f.notices.length === 1, 'Cold recovery deadline');
  results.push('Warm cancellation, full fresh cold delay and stale callback protection');

  for (const change of ['closed', 'warm', 'threshold']) {
    f = fixture(); f.run();
    if (change === 'closed') f.source('CLOSED');
    if (change === 'warm') f.temperature(23);
    if (change === 'threshold') f.threshold(18);
    f.advance(10);
    assert(!f.notices.length && !f.active().length, 'Timer re-reads ' + change + ' without its event');
  }
  results.push('Timers re-read contact, temperature and dynamic threshold even if events were missed');

  f = fixture(); f.threshold(18); f.run(); f.threshold(20.5); f.run(); f.advance(10);
  assert(f.notices.length === 1, 'Season/setpoint change can start the delay');
  f.threshold(18); f.run(); assert(f.clears[0].clearanceReason === 'WARM', 'Threshold change can clear the alarm');
  results.push('Dynamic seasonal/setpoint thresholds start and clear without signature errors');

  for (const [type, unit, value] of [['Number:Temperature', '°F', 68], ['Number:Temperature', 'K', 293.15], ['Number', '', 20]]) {
    f = fixture(); Object.assign(f.items.get('temperature'), { type, unit, value }); f.run(); f.advance(10);
    assert(f.notices.length === 1 && f.notices[0].message.includes('20 °C'), 'Unit conversion or unitless Celsius');
  }
  results.push('Fahrenheit/Kelvin conversion and plain Number Celsius support');

  for (const value of [NaN, null, undefined, Infinity, 'UNDEF', '20 °C', '']) {
    f = fixture(); f.temperature(value); f.run(); f.advance(60);
    assert(!f.timers.length && !f.notices.length && !f.clears.length, 'Unknown temperature must remain idle');
    f = fixture(); f.threshold(value); f.run(); f.advance(60);
    assert(!f.timers.length && !f.notices.length && !f.clears.length, 'Unknown threshold must remain idle');
  }
  f = fixture(); f.items.get('temperature').unit = '%'; f.run(); assert(!f.timers.length, 'Invalid unit is not Celsius');
  f.items.get('temperature').type = 'Number:Humidity'; f.run(); assert(!f.timers.length, 'Wrong dimension cannot alarm');
  results.push('Invalid numbers, missing values, units and dimensions never generate warnings or polling');

  for (const invalidContact of [false, true]) {
    f = fixture(); f.run(); f.advance(5);
    if (invalidContact) f.source('UNDEF'); else f.temperature(null);
    f.run(); f.advance(30);
    assert(!f.active().length && !f.notices.length, 'Data gap cancels pending warning');
    f.source('OPEN'); f.temperature(20); f.run(); f.advance(9.9);
    assert(!f.notices.length, 'Data recovery needs full delay');
    f.advance(.1); assert(f.notices.length === 1, 'Full delay after data recovery');
    f.temperature(null); f.run(); f.advance(60);
    assert(f.alarm() === 'ON' && !f.clears.length && !f.active().length, 'Active data gap preserves alarm without polling');
    f.temperature(20); f.run(); f.advance(1 / 60);
    assert(f.notices.length === 2, 'Valid data resumes remaining reminder budget');
    f.temperature(null); f.source('CLOSED'); f.run();
    assert(f.clears.length === 1 && f.alarm() === 'OFF', 'Confirmed closure clears despite missing temperature');
  }
  results.push('Data gaps stop timers, retain active alarms and resume on events; closure needs no temperature');

  for (const state of ['CLOSED', 'OPEN']) {
    f = fixture(); f.items.get('alarm').state = 'ON'; f.source(state); f.run(); f.advance(60);
    if (state === 'OPEN') {
      assert(!f.notices.length && !f.active().length && f.alarm() === 'ON', 'Restored cold alarm gets no new budget');
      f.temperature(22); f.run();
    }
    assert(f.clears.length === 1 && f.alarm() === 'OFF', 'Restored alarm still clears');
  }
  f = fixture(); f.items.get('alarm').state = 'ON'; f.temperature(22); f.run();
  assert(f.clears[0].clearanceReason === 'WARM', 'Restored warm alarm clears immediately');
  results.push('Restored active alarms do not replay or gain reminders and still clear on closure/warmth');

  f = fixture(); let attempts = 0;
  f.run(e => { if (++attempts === 1) throw Error('Delivery failed'); f.notices.push(e); });
  f.advance(11);
  assert(attempts === 2 && f.notices.length === 1 && f.errors.length === 1 && f.active().length === 1, 'Failed notification retries once per minute');
  f.advance(20); assert(f.notices.length === 3, 'Failures do not consume successful reminder budget');
  results.push('Failed action retry keeps one timer and preserves the successful-delivery budget');

  f = fixture(); f.run(); f.advance(10); f.temperature(22); let clearAttempts = 0;
  try { f.run(f.notify, e => { if (++clearAttempts === 1) throw Error('Clear failed'); f.clears.push(e); }); } catch (error) {}
  f.temperature(23); f.advance(1);
  assert(f.clears.length === 1 && f.clears[0].message.includes('22 °C') && !f.active().length, 'Retry keeps frozen clearance message');
  results.push('Failed clearance retries preserve the original event and stop after success');

  f = fixture(); f.run(); f.advance(10); f.source('CLOSED');
  try { f.run(f.notify, () => { throw Error('Clear failed'); }); } catch (error) {}
  f.source('OPEN'); f.run(); f.advance(9.9);
  assert(!f.clears.length && f.notices.length === 1, 'Reopening discards obsolete clearance and waits');
  f.advance(.1); assert(f.notices.length === 2 && f.notices[1].kind === 'NEW', 'New opening starts a new cycle');
  results.push('Reopening discards obsolete failed clearance and starts a complete new cycle');

  f = fixture(); const other = Object.assign({}, f.cfg, { source: 'other', temperature: 'otherTemperature', alarm: 'otherAlarm' });
  f.items.set('other', { type: 'Contact', state: 'OPEN', label: 'Other window' });
  f.items.set('otherTemperature', { type: 'Number', value: 19 }); f.items.set('otherAlarm', { type: 'Switch', state: 'OFF' });
  f.run(); f.run(f.notify, f.clear, other); f.source('CLOSED'); f.run(); f.advance(10);
  assert(f.notices.length === 1 && f.notices[0].id === 'otherAlarm', 'Windows use independent timer/cache keys');
  results.push('Two windows in one script remain independent');

  for (const change of [{ alarm: 'contact' }, { temperature: 'alarm' }, { delayMinutes: 0 },
    { intervalMinutes: Infinity }, { repeats: 1.5 }, { repeats: 21 }, { threshold: 20 }, { title: '' }]) {
    f = fixture(); let thrown = false;
    try { f.run(f.notify, f.clear, Object.assign({}, f.cfg, change)); } catch (error) { thrown = true; }
    assert(thrown && !f.timers.length && !f.writes.length, 'Bad configuration rejected before side effects');
  }
  results.push('Invalid configuration is rejected before timers or Item updates');

  if (template) {
    f = fixture();
    const inputs = { SOURCE: "'contact'", TEMPERATURE: "'temperature'", ALARM: "'alarm'",
      THRESHOLD: 'testThreshold()', TITLE: "'Fensteralarm'" };
    const fields = { DELAY: 10, REPEATS: 2, INTERVAL: 10 };
    const generated = template.replace(/\{\{utility:lhlab_temperature_window_monitor\}\}/g, 'lhlab_temperature_window_monitor')
      .replace(/\{\{input:(\w+)\}\}/g, (_, key) => inputs[key])
      .replace(/\{\{field:(\w+)\}\}/g, (_, key) => fields[key])
      .replace('{{statements:NOTIFY}}', 'onNotify(lhlabAlarmEvent);')
      .replace('{{statements:CLEAR}}', 'onClear(lhlabAlarmEvent);');
    const run = vm.runInNewContext(source + '\n(function(onNotify, onClear) {' + generated + '\n})', f.sandbox);
    run(f.notify, f.clear); f.threshold(18); f.advance(10);
    assert(!f.notices.length && !f.active().length, 'Generated threshold expression is lazy and re-evaluated by timer');
    f.threshold(20.5); run(f.notify, f.clear); f.advance(10); f.source('CLOSED'); run(f.notify, f.clear);
    assert(f.notices.length === 1 && f.clears.length === 1, 'Generated template supplies both current-alarm callbacks');
    results.push('Expanded Blockly template executes with live threshold expression and current-alarm callbacks');
  }
  return results;
}
verifyTemperatureWindow;
