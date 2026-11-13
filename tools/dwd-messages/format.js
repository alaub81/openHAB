// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Pure presentation of the captured warning; never reads warning-slot Items.
function lhlab_dwd_text(event, field, options, nowOverride) {
  if (!event) return '';
  var data = event.dwd || {};
  var levels = { Minor: 'Wetterwarnung', Moderate: 'Markantes Wetter', Severe: 'Unwetter', Extreme: 'Extremes Unwetter' };
  function clean(value) {
    var text = value == null ? '' : String(value).trim();
    return text === 'NULL' || text === 'UNDEF' ? '' : text;
  }
  function short(value) {
    value = clean(value);
    if (value !== value.toUpperCase()) return value;
    return value.toLowerCase().replace(/(^|[\s-])([a-zäöüß])/g, function(_, gap, letter) {
      return gap + letter.toUpperCase();
    }).replace(/\bUv\b/g, 'UV');
  }
  // Legacy memory lacks structured fields. Its title still identifies a clearance.
  var name = short(data.event || clean(event.title).replace(/^DWD · [^:]+:\s*/, ''));
  var level = levels[data.severity] || 'Wetterwarnung';
  var title = 'DWD · ' + level + ': ' + name;
  if (field === 'event') return name;
  if (field === 'severity') return levels[data.severity] || '';
  if (field === 'title') return title;
  if (['headline', 'description', 'instruction', 'from', 'to'].indexOf(field) >= 0) return clean(data[field]);
  options = options || {};
  var speech = options.mode === 'speech';
  if (field === 'message' && event.kind === 'CLEARED') {
    return speech ? 'Die DWD-Warnung für ' + name + ' ist beendet. Andere Wetterwarnungen können weiterhin aktiv sein.'
      : 'Die Warnung für ' + name + ' ist beendet.\nAndere DWD-Warnungen können weiterhin aktiv sein.';
  }
  function period(mode, endpoint) {
    if (!clean(data.from) || !clean(data.to)) return '';
    var api = require('openhab');
    var zone = api.time.ZoneId.of('Europe/Berlin');
    var now = (nowOverride ? api.time.toZDT(nowOverride) : api.time.ZonedDateTime.now()).withZoneSameInstant(zone);
    var start = api.time.toZDT(data.from).withZoneSameInstant(zone);
    var end = api.time.toZDT(data.to).withZoneSameInstant(zone);
    function fmt(value, pattern) { return value.format(api.time.DateTimeFormatter.ofPattern(pattern)); }
    function day(value) {
      if (value.toLocalDate().equals(now.toLocalDate())) return 'heute';
      if (value.toLocalDate().equals(now.plusDays(1).toLocalDate())) return 'morgen';
      return fmt(value, fmt(value, 'yyyy') === fmt(now, 'yyyy') ? 'dd.MM.' : 'dd.MM.yyyy');
    }
    function clock(value) {
      if (mode !== 'speech') return fmt(value, 'HH:mm');
      return fmt(value, 'mm') === '00' ? fmt(value, 'H') + ' Uhr' : fmt(value, 'H') + ' Uhr ' + fmt(value, 'mm');
    }
    var sameDay = start.toLocalDate().equals(end.toLocalDate());
    var result;
    if (endpoint) {
      var value = endpoint === 'begin' ? start : end;
      result = day(value) + ' ' + clock(value) + (mode === 'speech' ? '' : ' Uhr');
    } else if (!end.isAfter(now)) {
      result = 'beendet ' + day(end) + ' ' + clock(end) + (mode === 'speech' ? '' : ' Uhr');
    } else if (!start.isAfter(now)) {
      result = 'bis ' + day(end) + (mode === 'speech' ? ' um ' : ' ') + clock(end) + (mode === 'speech' ? '' : ' Uhr');
    } else {
      result = day(start) + (mode === 'speech' ? ' ab ' : ' ') + clock(start) + ' bis '
        + (sameDay ? '' : day(end) + (mode === 'speech' ? ' um ' : ' ')) + clock(end)
        + (mode === 'speech' ? '' : ' Uhr');
    }
    return result.charAt(0).toUpperCase() + result.slice(1);
  }
  if (field === 'periodPush') return period('push');
  if (field === 'periodSpeech') return period('speech');
  if (field === 'begin' || field === 'end') return period('push', field);
  if (field !== 'message') return '';
  var parts = [];
  if (speech) parts.push(level + ': ' + name + '.');
  if (speech && options.period !== false) {
    var spokenPeriod = period('speech');
    if (spokenPeriod) parts.push(spokenPeriod + '.');
  }
  var description = clean(data.description);
  if (options.description !== false && description) parts.push(description);
  if (!speech && options.period !== false) {
    var pushPeriod = period('push');
    if (pushPeriod) parts.push(pushPeriod + '.');
  }
  var instruction = clean(data.instruction);
  if (options.instruction === true && instruction) parts.push('Verhaltenshinweise: ' + instruction);
  // Flatten whitespace for speech. Push retains one line per selected component.
  return speech ? parts.join(' ').replace(/\s+/g, ' ').trim() : parts.join('\n');
}
