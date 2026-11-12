// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Event-driven window alarm. No polling, group scans or notification delivery.
function lhlab_temperature_window_monitor(config, onNotify, onClear) {
  const api = require('openhab');
  const sourceName = String(config.source || '').trim();
  const temperatureName = String(config.temperature || '').trim();
  const alarmName = String(config.alarm || '').trim();
  const title = String(config.title || '').trim();
  const delayMs = Number(config.delayMinutes) * 60000;
  const intervalMs = Number(config.intervalMinutes) * 60000;
  const repeats = Number(config.repeats);
  if (!sourceName || !temperatureName || !alarmName || !title ||
      new Set([sourceName, temperatureName, alarmName]).size !== 3 ||
      typeof config.threshold !== 'function' ||
      !Number.isFinite(delayMs) || delayMs < 60000 ||
      !Number.isFinite(intervalMs) || intervalMs < 60000 ||
      !Number.isInteger(repeats) || repeats < 0 || repeats > 20) {
    throw new Error('Temperatur-Fensteralarm: Items, Titel oder Zeitangaben ungueltig.');
  }
  const key = 'lhlab.temperatureWindow.v1:' + alarmName;
  const timerKey = key + ':timer';
  const signature = JSON.stringify([sourceName, temperatureName, delayMs, intervalMs, repeats, title]);
  let state = api.cache.private.get(key);
  if (state && state.signature !== signature) {
    throw new Error('Temperatur-Fensteralarm: Alarm-Item unterschiedlich konfiguriert.');
  }
  if (!state) {
    state = { signature, generation: 0, coldSince: null, sent: 0, lastSent: null,
      lastMessage: '', pendingClear: null };
    api.cache.private.put(key, state);
  }
  function cancel() {
    state.generation++;
    const timer = api.cache.private.get(timerKey);
    if (timer) timer.cancel();
    api.cache.private.remove(timerKey);
  }
  function schedule(milliseconds) {
    const existing = api.cache.private.get(timerKey);
    if (existing && existing.isActive()) return;
    const generation = state.generation;
    api.cache.private.put(timerKey, api.actions.ScriptExecution.createTimer(
      timerKey, api.time.ZonedDateTime.now().plusSeconds(Math.max(1, Math.ceil(milliseconds / 1000))), function() {
        if (state.generation !== generation || api.cache.private.get(key) !== state) return;
        api.cache.private.remove(timerKey);
        try { evaluate(true); }
        catch (error) { console.error('Temperatur-Fensteralarm ' + alarmName + ': ' + error); }
      }));
  }
  function event(kind, message, reason) {
    return { id: alarmName, group: 'temperature-window', kind, title, message,
      previousMessage: state.lastMessage, previousTitle: title,
      comparison: sourceName, clearanceReason: reason || '' };
  }
  function deliver(callback, notification) {
    try { callback(notification); }
    catch (error) {
      // Retry failed actions only. Missing sensor data never starts a polling loop.
      schedule(60000);
      throw error;
    }
  }
  function suspend(alarm) {
    cancel();
    // Retain existing alarms and their reminder budget. A pending first warning
    // needs a fresh complete delay after valid data returns.
    if (alarm.state !== 'ON') state.coldSince = null;
  }
  function finish(alarm, label, reason, temperature, threshold) {
    cancel();
    if (alarm.state === 'ON' || state.pendingClear) {
      if (!state.pendingClear || state.pendingClear.clearanceReason !== reason) {
        state.pendingClear = event('CLEARED', reason === 'CLOSED'
          ? label + ' ist wieder geschlossen.'
          : 'Entwarnung: ' + label + ' ist weiterhin offen, aber die Temperatur liegt mit ' +
            temperature + ' °C wieder über der Grenze von ' + threshold + ' °C.', reason);
      }
    }
    if (alarm.state !== 'OFF') alarm.postUpdate('OFF');
    state.coldSince = null;
    state.sent = 0;
    state.lastSent = null;
    if (state.pendingClear) {
      deliver(onClear, state.pendingClear);
      state.pendingClear = null;
    }
  }
  function evaluate(fromTimer) {
    const source = api.items.getItem(sourceName);
    if (source.type !== 'Contact') throw new Error('Temperatur-Fensteralarm: Quelle muss Contact sein.');
    const raw = source.state;
    const alarm = api.items.getItem(alarmName);
    if (alarm.type !== 'Switch') throw new Error('Temperatur-Fensteralarm: Alarm-Item muss Switch sein.');
    // This path deliberately does not read the sensor or evaluate the threshold.
    if (raw === 'CLOSED') { finish(alarm, source.label || sourceName, 'CLOSED'); return; }
    if (raw !== 'OPEN') { suspend(alarm); return; }
    if (state.coldSince === null && alarm.state === 'ON' && !state.pendingClear) {
      // A restored active alarm must not replay notifications or receive a new budget.
      state.sent = repeats + 1;
    }
    const sensor = api.items.getItem(temperatureName);
    let temperature = NaN;
    let threshold;
    try {
      if (sensor.type === 'Number:Temperature') {
        const quantity = sensor.quantityState;
        const converted = quantity == null ? null : quantity.toUnit('°C');
        if (converted != null) temperature = converted.float;
      } else if (sensor.type === 'Number') {
        temperature = sensor.numericState;
      }
      // The generator wraps the input expression in a function. Timers therefore
      // re-read seasonal/setpoint inputs instead of retaining an old numeric limit.
      threshold = config.threshold();
    } catch (error) { suspend(alarm); return; }
    if (!Number.isFinite(temperature) || !Number.isFinite(threshold)) { suspend(alarm); return; }
    const label = source.label || sourceName;
    if (temperature > threshold) { finish(alarm, label, 'WARM', temperature, threshold); return; }
    state.pendingClear = null;
    const now = Date.now();
    if (state.coldSince === null) state.coldSince = now;
    if (state.sent === 0 && alarm.state !== 'ON' && alarm.state !== 'OFF') alarm.postUpdate('OFF');
    if (state.sent > repeats) return;
    const due = state.sent === 0 ? state.coldSince + delayMs : state.lastSent + intervalMs;
    if (!fromTimer || now < due) { schedule(due - now); return; }
    const minutes = Math.max(1, Math.floor((now - state.coldSince) / 60000));
    const kind = state.sent === 0 ? 'NEW' : 'REMINDER';
    const notification = event(kind, (kind === 'NEW' ? 'Achtung! ' : 'Erinnerung: ') + label +
      ' ist seit mindestens ' + minutes + (minutes === 1 ? ' Minute' : ' Minuten') +
      ' bei höchstens ' + threshold + ' °C offen. Aktuelle Temperatur: ' + temperature + ' °C.');
    if (alarm.state !== 'ON') alarm.postUpdate('ON');
    deliver(onNotify, notification);
    state.sent++;
    state.lastSent = now;
    state.lastMessage = notification.message;
    if (state.sent <= repeats) schedule(intervalMs);
  }
  evaluate(false);
}
