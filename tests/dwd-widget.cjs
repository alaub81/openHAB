// Verify the actual warning widget's display modes and popup bindings.
const assert = require('node:assert/strict');
const vm = require('node:vm');
module.exports = widget => {
  const context = widget.slots.default[0];
  const props = {testMode: 'live'};
  const items = {};
  const now = Date.parse('2026-11-21T12:00:00Z');
  const dayjs = value => {
    const stamp = value === undefined ? now : Date.parse(value);
    return {isValid: () => Number.isFinite(stamp), valueOf: () => stamp,
      isAfter: other => stamp > other.valueOf()};
  };
  const env = {props, items, dayjs, fn: {}, constants: context.config.constants};
  const evaluate = value => typeof value === 'string' && value.startsWith('=')
    ? vm.runInNewContext(value.slice(1).replace(/\bconst\./g, 'constants.'), env) : value;
  for (const [name, value] of Object.entries(context.config.functions)) env.fn[name] = evaluate(value);
  const fn = env.fn;
  assert.equal(fn.display(), false, 'Existing instances retain the full view');
  props.displayMode = 'overview';
  assert.equal(fn.display(), true);
  props.displayMode = 'compact';
  for (let n = 1; n <= 5; n++) {
    props['alarm' + n] = 'Alarm' + n;
    props['severity' + n] = 'Severity' + n;
    items['Alarm' + n] = {state: 'ON'};
    items['Severity' + n] = {state: ['Minor', 'Extreme', 'Severe', 'Moderate', 'Minor'][n - 1]};
  }
  const warnings = () => fn.warnings(false, fn.live(fn.state), fn.rank, []);
  assert.equal(warnings().length, 5);
  assert.equal(warnings()[0].slot, 2, 'Highest severity remains first');
  assert.equal(fn.unknown(false, fn.live(fn.state)), false);
  items.Alarm1.state = 'UNDEF';
  assert.equal(fn.unknown(false, fn.live(fn.state)), true);
  for (let n = 1; n <= 5; n++) items['Alarm' + n].state = 'OFF';
  assert.equal(warnings().length, 0);
  assert.equal(fn.unknown(false, fn.live(fn.state)), false);
  items.Alarm1.state = '-';
  assert.equal(fn.unknown(false, fn.live(fn.state)), true, 'Loading is not an all-clear');
  assert.match(fn.period('2026-11-22T12:00:00Z', 'end', x => x), /^Ab /);
  assert.equal(fn.period('2026-11-20T12:00:00Z', 'end', x => x), 'Bis end');
  const summary = context.slots.default[0];
  const flatten = node => [node, ...Object.values(node.slots || {}).flat().flatMap(flatten)];
  const repeater = flatten(summary).find(node => node.component === 'oh-repeater');
  for (let n = 1; n <= 5; n++) items['Alarm' + n].state = 'ON';
  props.displayMode = 'overview';
  assert.equal(evaluate(repeater.config.in).length, 3);
  props.displayMode = 'compact';
  assert.equal(evaluate(repeater.config.in).length, 3);
  const moreLabel = flatten(summary).find(node => String(node.config.text).includes("' weitere'"));
  assert.equal(evaluate(moreLabel.config.text), '+2 weitere');
  assert.equal(fn.compactPeriod('2026-11-22T12:00:00Z', 'end', x => x), 'Ab 2026-11-22T12:00:00Z – end');
  assert.equal(fn.compactPeriod('', 'end', x => x), 'Bis end');
  assert.equal(summary.config.actionModal, 'widget:dwd_warnleiste');
  assert.equal(summary.config.actionModalConfig.displayMode, 'full', 'Popup cannot reopen compact mode');
  for (const parameter of widget.props.parameters.filter(p => p.context === 'item')) {
    props[parameter.name] = 'Synthetic_' + parameter.name;
    assert.equal(evaluate(summary.config.actionModalConfig[parameter.name]), props[parameter.name]);
  }
  assert.equal(evaluate(widget.config.style.height), '100%');
  assert.equal(evaluate(summary.config.style.height), '100%');
  props.displayMode = 'overview';
  assert.equal(evaluate(widget.config.style.height), '100%');
  props.displayHeight = 360;
  assert.equal(evaluate(widget.config.style.height), '100%', 'Saved heights must not constrain the canvas');
  assert.equal(widget.props.parameters.some(p => p.name === 'displayHeight'), false);
  props.displayMode = 'full';
  assert.equal(evaluate(widget.config.style.height), 'auto');
  const checkSyntax = node => {
    if (typeof node === 'string' && node.startsWith('=')) new vm.Script('(' + node.slice(1).replace(/\bconst\./g, 'constants.') + ')');
    else if (node && typeof node === 'object') Object.values(node).forEach(checkSyntax);
  };
  checkSyntax(widget);
  return 'display limits, severity order, unknown states, time labels, popup Item forwarding and expressions';
};
