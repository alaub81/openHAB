// Evaluates the exact generated JavaScript with isolated Item, cache and DB mocks.
// The caller supplies node:vm and the generated code. No live Item is touched.
function verifyDailyRule(vm, code) {
  const names = ['Shelly_Warmepumpe_HTTP_Gesamtverbrauch_1',
    'Shelly_Warmepumpe_HTTP_Gesamtverbrauch_2', 'Shelly_Warmepumpe_MGMT_Gesamtverbrauch'];
  function assert(test, message) { if (!test) throw new Error(message); }
  class Q {
    constructor(value) {
      if (value instanceof Q) { this.wh = value.wh; return; }
      const match = String(value).match(/^(-?[\d.]+)\s*(kWh|Wh)$/);
      if (!match) throw new Error('Invalid quantity: ' + value);
      this.wh = Number(match[1]) * (match[2] === 'kWh' ? 1000 : 1);
    }
    add(value) { return new Q((this.wh + new Q(value).wh) + ' Wh'); }
    equal(value) { return Math.abs(this.wh - new Q(value).wh) < 0.000001; }
    toString() { return this.wh + ' Wh'; }
  }
  let day = '2026-10-30', map = new Map(), queries = [], updates = [];
  const states = ['100 kWh', '200000 Wh', '30 kWh'];
  let deltas = ['1 kWh', '500 Wh', '0.2 kWh'];
  const failed = new Set();
  let target = 'NULL';
  function zdt() {
    return { day, hour: 12, minute: 0, second: 0, nano: 0,
      format() { return this.day; },
      withHour(n) { return Object.assign(Object.create(Object.getPrototypeOf(this)), this, {hour:n}); },
      withMinute(n) { return Object.assign(Object.create(Object.getPrototypeOf(this)), this, {minute:n}); },
      withSecond(n) { return Object.assign(Object.create(Object.getPrototypeOf(this)), this, {second:n}); },
      withNano(n) { return Object.assign(Object.create(Object.getPrototypeOf(this)), this, {nano:n}); }
    };
  }
  const env = {
    Quantity: value => new Q(value),
    cache: { private: { get: key => map.get(key), exists: key => map.has(key),
      put: (key, value) => map.set(key, value) } },
    time: { ZonedDateTime: { now: zdt }, DateTimeFormatter: {ofPattern: p => p} },
    items: { getItem(name) {
      if (name === 'Waermepumpe_Tagesverbrauch') return { state: target, postUpdate(q) {
        updates.push(new Q(q).wh); target = String(q);
      } };
      const i = names.indexOf(name);
      assert(i >= 0, 'Unknown item ' + name);
      return {state: states[i], persistence: { deltaSince(start) {
        assert(start.day === day && !start.hour && !start.minute && !start.second && !start.nano,
          'Query must start at local midnight');
        queries.push(i);
        if (failed.has(i)) return undefined;
        return { quantityState: new Q(deltas[i]) };
      } } };
    } }
  };
  function run() { queries = []; updates = []; vm.runInNewContext(code, env, {timeout:1000}); }
  const results = [];
  run(); assert(queries.length === 3 && updates[0] === 1700, 'Initial mixed-unit calculation');
  results.push('First run: three DB queries, correct mixed-unit sum');
  run(); assert(!queries.length && !updates.length, 'Unchanged counters must be free of queries and updates');
  results.push('Unchanged: no DB queries and no Item update');
  states[2] = '30.01 kWh'; deltas[2] = '0.21 kWh';
  run(); assert(queries.join() === '2' && updates[0] === 1710, 'Only management changed');
  results.push('Management changed: one DB query and correct sum');
  states[0] = '100.1 kWh'; states[1] = '200100 Wh'; deltas[0] = '1.1 kWh'; deltas[1] = '600 Wh';
  run(); assert(queries.join() === '0,1' && updates[0] === 1910, 'Two changed counters');
  results.push('Two changed counters: exactly two DB queries');
  day = '2026-10-31'; deltas = ['0 Wh', '0 Wh', '0 Wh'];
  run(); assert(queries.length === 3 && updates[0] === 0, 'Day rollover without counter changes');
  results.push('New day: refresh all counters even without changes');
  map = new Map();
  run(); assert(queries.length === 3 && !updates.length, 'Empty cache with unchanged output');
  results.push('Cache loss: reload all; suppress unchanged sum');
  states[2] = '30.02 kWh'; deltas[2] = '20 Wh'; failed.add(2);
  run(); assert(queries.join() === '2' && !updates.length, 'Failed DB query must not publish partial sum');
  run(); assert(queries.join() === '2' && !updates.length, 'Failed DB query must retry');
  failed.clear();
  run(); assert(queries.join() === '2' && updates[0] === 20, 'Recovery must calculate correct sum');
  results.push('Missing DB result: no partial sum, retry and recovery');
  states[0] = 'UNDEF';
  run(); assert(!queries.length && !updates.length, 'Invalid sensor state must not query or publish');
  states[0] = '100.1 kWh';
  results.push('UNDEF counter: no invalid or partial sum');
  day = '2026-11-01'; deltas = ['0 Wh', '0 Wh', '0 Wh']; failed.add(0);
  run(); assert(queries.length === 3 && !updates.length, 'Partial rollover must not publish');
  run(); assert(queries.join() === '0' && !updates.length, 'Only failed day rollover query retries');
  failed.clear(); run(); assert(queries.join() === '0' && updates[0] === 0, 'Rollover recovery');
  results.push('Partial day rollover: retry only failed source, no yesterday/today mixture');
  target = 'UNDEF'; run(); assert(!queries.length && updates[0] === 0, 'Restore output from valid cache');
  results.push('UNDEF output: restore from cache without DB queries');
  return results;
}
verifyDailyRule;
