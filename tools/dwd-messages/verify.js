// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Runs with openHAB's real time API and isolated Items, memory and timers.
function verifyDwd(time, sources) {
  var assertions = 0;
  function equal(actual, expected, name) {
    assertions++;
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error(name + ': ' + JSON.stringify(actual) + ' != ' + JSON.stringify(expected));
    }
  }
  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  var data = { event: 'FROST', severity: 'Minor', from: '2026-11-13T20:00:00+01:00',
    to: '2026-11-14T09:00:00+01:00', headline: 'Amtliche WARNUNG vor FROST',
    description: 'Es tritt leichter Frost zwischen 0 °C und -3 °C auf.',
    instruction: 'Hinweis auf: mögliche Frostschäden.\nHandlungsempfehlungen:\nggf. Frostschutzmaßnahmen ergreifen' };
  var event = { kind: 'NEW', title: 'DWD · Wetterwarnung: FROST', dwd: data };
  var formatter = new Function('require', sources.format + '\nreturn lhlab_dwd_text;')(function() { return {time: time}; });
  var now = '2026-11-13T12:00:00+01:00';
  function text(field, options, value, clock) { return formatter(value || event, field, options, clock || now); }
  var push = text('message');
  var speech = text('message', {mode: 'speech'});
  equal(text('title'), 'DWD · Wetterwarnung: Frost', 'readable title');
  equal(push, data.description + '\nHeute 20:00 bis morgen 09:00 Uhr.', 'push order and relative dates');
  equal(speech, 'Wetterwarnung: Frost. Heute ab 20 Uhr bis morgen um 9 Uhr. ' + data.description, 'speech');
  equal(push.indexOf('Verhaltenshinweise'), -1, 'instructions default off');
  equal(text('message', {instruction: true}).indexOf(data.instruction) >= 0, true, 'instructions opt in');
  equal(text('message', {period: false}), data.description, 'period disabled');
  equal(text('message', {description: false}), 'Heute 20:00 bis morgen 09:00 Uhr.', 'description disabled');
  equal(text('message', {description: false, period: false}), '', 'empty push selection');
  equal(text('description'), data.description, 'raw description');
  equal(text('instruction'), data.instruction, 'raw instructions');
  equal(text('from'), data.from, 'ISO onset');
  equal(text('to'), data.to, 'ISO expiry');
  equal(text('headline'), data.headline, 'raw headline');
  equal(text('begin'), 'Heute 20:00 Uhr', 'formatted begin');
  equal(text('end'), 'Morgen 09:00 Uhr', 'formatted end');
  equal(text('periodPush', null, null, '2026-11-13T21:00:00+01:00'), 'Bis morgen 09:00 Uhr', 'already started');
  equal(text('periodPush', null, null, '2026-11-14T10:00:00+01:00'), 'Beendet heute 09:00 Uhr', 'expired period');
  var same = copy(event); same.dwd.to = '2026-11-13T22:30:00+01:00';
  equal(text('periodPush', null, same), 'Heute 20:00 bis 22:30 Uhr', 'same-day push');
  equal(text('periodSpeech', null, same), 'Heute ab 20 Uhr bis 22 Uhr 30', 'same-day speech with minutes');
  var future = copy(event); future.dwd.from = '2026-11-16T20:00:00+01:00'; future.dwd.to = '2026-11-17T09:00:00+01:00';
  equal(text('periodPush', null, future), '16.11. 20:00 bis 17.11. 09:00 Uhr', 'future dates');
  future.dwd.from = '2026-12-31T20:00:00+01:00'; future.dwd.to = '2027-01-01T09:00:00+01:00';
  equal(text('periodPush', null, future), '31.12. 20:00 bis 01.01.2027 09:00 Uhr', 'year boundary');
  var utc = copy(event); utc.dwd.from = '2026-11-13T19:00:00Z'; utc.dwd.to = '2026-11-14T08:00:00Z';
  equal(text('periodPush', null, utc), text('periodPush'), 'UTC conversion');
  var dst = copy(event); dst.dwd.from = '2026-03-28T20:00:00+01:00'; dst.dwd.to = '2026-03-29T09:00:00+02:00';
  equal(text('periodPush', null, dst, '2026-03-28T12:00:00+01:00'), 'Heute 20:00 bis morgen 09:00 Uhr', 'spring DST');
  dst.dwd.from = '2026-10-24T20:00:00+02:00'; dst.dwd.to = '2026-10-25T09:00:00+01:00';
  equal(text('periodPush', null, dst, '2026-10-24T12:00:00+02:00'), 'Heute 20:00 bis morgen 09:00 Uhr', 'autumn DST');
  equal(text('periodPush', null, null, '2026-11-13T23:30:00Z'), 'Bis heute 09:00 Uhr', 'Berlin midnight');
  var clear = copy(event); clear.kind = 'CLEARED';
  equal(text('message', null, clear), 'Die Warnung für Frost ist beendet.\nAndere DWD-Warnungen können weiterhin aktiv sein.', 'clearance');
  equal(text('message', {mode: 'speech'}, clear).indexOf('20 Uhr'), -1, 'clearance omits stale period');
  delete clear.dwd;
  equal(text('message', null, clear).indexOf('Frost') >= 0, true, 'legacy clearance fallback');
  equal(text('description', null, clear), '', 'missing legacy field');
  equal(formatter(null, 'message'), '', 'outside context');

  var cache = {};
  var memory = {type: 'String', state: 'NULL', postUpdate: function(value) { this.state = value; }};
  var rows = {};
  var timers = [];
  var api = { time: time,
    cache: {private: {get: function(k) { return cache[k]; }, put: function(k, v) { cache[k] = v; }, remove: function(k) { delete cache[k]; }}},
    items: {getItem: function(name) { return name === 'Memory' ? memory : {state: rows[name]}; }},
    actions: {ScriptExecution: {createTimer: function(at, fn) {
      var timer = {fn: fn, cancelled: false, cancel: function() { this.cancelled = true; }};
      timers.push(timer); return timer;
    }}}
  };
  var functions = new Function('require', sources.process + '\n' + sources.monitor + '\nreturn {process: lhlab_alarm_process, monitor: lhlab_dwd_monitor};')(function() { return api; });
  var events = [];
  function onEvent(value) { events.push(copy(value)); }
  function row(n, warning) {
    rows['Test_Warning_' + n] = warning ? 'ON' : 'OFF';
    if (!warning) return;
    var suffixes = {Type: 'event', Severity: 'severity', Valid_From: 'from', Valid_To: 'to', Headline: 'headline', Description: 'description', Instruction: 'instruction'};
    Object.keys(suffixes).forEach(function(key) { rows['Test_' + key + '_' + n] = warning[suffixes[key]]; });
  }
  function run() {
    functions.monitor('Test_', 2, 'Memory', 1, false, onEvent, onEvent, onEvent);
    while (timers.length) { var timer = timers.shift(); if (!timer.cancelled) timer.fn(); }
  }
  row(1, data); row(2, null); run();
  equal(events.map(function(e) { return e.kind; }), ['NEW'], 'new warning');
  equal(events[0].dwd, data, 'structured event fields');
  equal(JSON.parse(memory.state).alarms[0].dwd, data, 'persisted fields');
  var originalId = events[0].id;
  row(1, null); row(2, data); run();
  equal(events.length, 1, 'slot move stays silent');
  var oldMemory = JSON.parse(memory.state); delete oldMemory.alarms[0].dwd;
  memory.state = JSON.stringify(oldMemory); cache = {}; run();
  equal(events.length, 1, 'legacy upgrade stays silent');
  equal(JSON.parse(memory.state).alarms[0].dwd, data, 'legacy memory enriched');
  var changed = copy(data); changed.description = 'Geänderte Beschreibung.'; row(2, changed); run();
  equal(events[1].kind, 'CHANGED', 'changed warning');
  equal(events[1].id, originalId, 'stable reference');
  equal(events[1].dwd.description, changed.description, 'changed data');
  cache = {}; row(2, null); run();
  equal(events[2].kind, 'CLEARED', 'clearance after reload');
  equal(events[2].dwd.description, changed.description, 'clearance keeps captured fields');
  equal(JSON.parse(memory.state).alarms.length, 0, 'clearance stored');
  // Generic alarm callers still receive their usual message and identity.
  functions.process('generic', [{id:'one', active:true, title:'Title', message:'Message'}], '', onEvent, onEvent, onEvent, false);
  equal(events[3].message, 'Message', 'generic alarm compatibility');
  equal(events[3].dwd, null, 'generic alarm has no DWD data');
  if (sources.rule) {
    // Execute the prepared/round-tripped Blockly rule with delivery intercepted.
    cache = {}; memory.state = 'NULL'; rows = {}; timers = [];
    row(1, data);
    for (var n = 2; n <= 5; n++) row(n, null);
    api.items.getItem = function(name) {
      return name === 'DWDUnwetterWarnungen_AlarmMemory' ? memory
        : {state: rows[name.replace('DWDUnwetterWarnungen_', 'Test_')]};
    };
    var pushCalls = [], speechCalls = [];
    var actions = {notificationBuilder: function(message) {
      var record = {message: message};
      var builder = {};
      ['Title', 'Icon', 'Tag', 'ReferenceId', 'OnClickAction'].forEach(function(key) {
        builder['with' + key] = function(value) { record[key] = value; return builder; };
      });
      builder.send = function() { pushCalls.push(record); };
      return builder;
    }};
    var rules = {runRule: function(uid, context) { speechCalls.push({uid: uid, message: context.Message}); }};
    var runRule = new Function('require', 'actions', 'rules', 'ctx', sources.rule);
    function evaluateRule() {
      runRule(function() { return api; }, actions, rules, {});
      while (timers.length) { var timer = timers.shift(); if (!timer.cancelled) timer.fn(); }
    }
    evaluateRule();
    equal(pushCalls.length, 1, 'rule new push');
    equal(speechCalls.length, 1, 'rule new speech');
    equal(pushCalls[0].Title, 'DWD · Wetterwarnung: Frost', 'rule field block in title');
    equal(pushCalls[0].message.indexOf(data.description), 0, 'rule push starts with description');
    equal(pushCalls[0].message.indexOf('Verhaltenshinweise'), -1, 'rule push instructions off');
    equal(speechCalls[0].message.indexOf('Wetterwarnung: Frost.'), 0, 'rule speech introduction');
    equal(speechCalls[0].message.indexOf('Verhaltenshinweise'), -1, 'rule speech instructions off');
    equal(speechCalls[0].uid, '9cacbaff96', 'existing Alexa rule');
    equal(pushCalls[0].OnClickAction, 'ui:/overview/', 'existing overview link');
    row(1, changed); evaluateRule();
    equal(pushCalls[1].Title, 'Aktualisiert · DWD · Wetterwarnung: Frost', 'rule updated title');
    equal(pushCalls[1].ReferenceId, pushCalls[0].ReferenceId, 'rule stable update reference');
    row(1, null); evaluateRule();
    equal(pushCalls.length, 3, 'rule clearance push');
    equal(speechCalls.length, 3, 'rule clearance speech');
    equal(pushCalls[2].message.indexOf('Die Warnung für Frost ist beendet.'), 0, 'rule specific clearance');
    equal(speechCalls[2].message.indexOf('Die DWD-Warnung für Frost ist beendet.'), 0, 'rule speech clearance');
  }
  return {passed: true, assertions: assertions, preview: {title: text('title'), push: push, speech: speech}};
}
