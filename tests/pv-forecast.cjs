// Exercise shared PV forecast logic and day selection with synthetic Item states.
const assert = require('node:assert/strict');
const vm = require('node:vm');
module.exports = widget => {
  const ctx = widget.slots.default[0];
  const props = {};
  const items = {Forecast: {state: '11000 Wh'}};
  const fn = {};
  const env = {props, items, fn};
  const evaluate = text => vm.runInNewContext(text.slice(1), env);
  for (const [name, value] of Object.entries(ctx.config.functions)) fn[name] = evaluate(value);
  assert.equal(fn.energy('Forecast', 99), 11);
  for (const [state, expected] of [['0 kWh', 0], ['1,5 kWh', 1.5], ['0.01 MWh', 10], ['1000 Wh', 1]]) {
    items.Forecast.state = state;
    assert.equal(fn.energy('Forecast', 99), expected);
  }
  for (const state of ['NULL', 'UNDEF', '-', '-1 kWh', 'NaN', '5 W']) {
    items.Forecast.state = state;
    assert.equal(Number.isNaN(fn.energy('Forecast', 99)), true);
  }
  assert.equal(fn.status(11, 10), 'green');
  assert.equal(fn.status(7, 10), 'orange');
  assert.equal(fn.status(6.9, 10), 'red');
  assert.equal(fn.status(0, 0), 'unknown');
  assert.equal(fn.format(0), '0,0');
  assert.equal(fn.format(Number.NaN), '—');
  assert.deepEqual(Array.from(fn.dayIndices()), [0, 1, 2, 3]);
  for (const start of [0, 1]) for (const count of [1, 2, 3, 4]) {
    assert.deepEqual(Array.from(fn.dayIndices(start, count)), [0, 1, 2, 3].slice(start, start + count));
  }
  assert.deepEqual(Array.from(fn.dayIndices(1, 0)), [1, 2, 3]);
  const display = ctx.slots.default[0];
  const days = display.slots.default[0].slots.default;
  for (const count of [1, 2, 3]) {
    props.startDay = 1;
    props.dayCount = count;
    assert.equal(days.filter(day => evaluate(day.config.visible)).length, count);
  }
  props.startDay = 0;
  props.dayCount = 4;
  assert.equal(days.filter(day => evaluate(day.config.visible)).length, 4);
  const footer = display.slots.default.find(node => node.config.class.includes('smab-fc-display-footer'));
  assert.equal(evaluate(footer.config.visible), true);
  assert.equal(evaluate(display.config.style['--fc-footer-height']), 'var(--fc-footer-space)');
  props.showRemaining = false;
  props.showAverage = false;
  assert.equal(evaluate(footer.config.visible), false);
  assert.equal(evaluate(display.config.style['--fc-footer-height']), '0px');
  props.showRemaining = true;
  assert.equal(evaluate(footer.config.visible), true);
  props.showRemaining = false;
  props.showAverage = true;
  assert.equal(evaluate(footer.config.visible), true);
  assert.equal(fn.formatDisplay(12.34), '12,3');
  assert.equal(fn.formatRemaining(12.34), '12,3');
  assert.equal(fn.formatAverage(12.34), '12,3');
  for (const day of days) {
    assert.equal(day.config.action, 'analyzer', 'Display details must not expand inside a fixed canvas');
    assert.equal(day.slots.default[1].slots.default.length, 1);
    assert.doesNotMatch(day.slots.default[1].slots.default[0].config.text, /kWh/);
  }
  assert.equal(footer.slots.default[0].slots.default[1].config.text, 'Prognosen in kWh');
  assert.equal(evaluate(widget.config.expandable), true);
  props.displayMode = 'display';
  assert.equal(evaluate(widget.config.expandable), false);
  props.displayHeight = 60;
  assert.equal(evaluate(widget.config.style.height), '100%');
  props.displayHeight = 120;
  assert.equal(evaluate(widget.config.style.height), '100%', 'Old instance heights must not constrain the canvas');
  props.displayMode = 'cell';
  assert.equal(evaluate(widget.config.style.height), 'auto');
  assert.equal(widget.props.parameters.some(p => p.name === 'displayHeight'), false);
  props.demoMode = true;
  assert.equal(fn.energy('Forecast', 99), 99);
  const check = value => {
    if (typeof value === 'string' && value.startsWith('=')) new vm.Script('(' + value.slice(1) + ')');
    else if (value && typeof value === 'object') Object.values(value).forEach(check);
  };
  check(widget);
  return 'energy units, missing states, traffic thresholds, day ranges, optional footer, display actions and expressions';
};
