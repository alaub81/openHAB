// SPDX-License-Identifier: MIT
// Copyright (c) 2020-2026 Andreas Laub
// Generic delayed Contact/Switch alarm. Delivery stays in the caller's Blockly.
function lhlab_state_monitor(config, onNotify, onClear) {
  const api = require('openhab');
  const sourceName = String(config.source || '').trim();
  const alarmName = String(config.alarm || '').trim();
  const onState = String(config.active || '');
  const offState = onState === 'OPEN' ? 'CLOSED' : 'OFF';
  const delayMs = Number(config.delayMinutes) * 60000;
  const intervalMs = Number(config.intervalMinutes) * 60000;
  const repeats = Number(config.repeats);
  const title = String(config.title || '').trim();
  if (!sourceName || !alarmName || sourceName === alarmName || !title ||
      !['OPEN', 'ON'].includes(onState) || !Number.isFinite(delayMs) || delayMs < 1000 ||
      !Number.isFinite(intervalMs) || intervalMs < 1000 || !Number.isInteger(repeats) ||
      repeats < 0 || repeats > 20) {
    throw new Error('Zustandsalarm: Quelle, Alarm, Titel oder Zeitangaben ungueltig.');
  }
  const alarmItem = api.items.getItem(alarmName);
  if (alarmItem.type !== 'Switch') throw new Error('Zustandsalarm: Alarm-Item muss Switch sein.');
  const key = 'lhlab.state.v1:' + alarmName;
  const timerKey = key + ':timer';
  const signature = JSON.stringify([sourceName, onState, delayMs, intervalMs, repeats, title]);
  let state = api.cache.private.get(key);
  if (state && state.signature !== signature) {
    throw new Error('Zustandsalarm: Alarm-Item in derselben Script-Aktion unterschiedlich konfiguriert.');
  }
  if (!state) {
    state = { signature, generation: 0, openedAt: null, sent: 0, lastSent: null,
      lastMessage: '', pendingClear: null };
    api.cache.private.put(key, state);
  }
  function writeAlarm(value) {
    if (api.items.getItem(alarmName).state !== value) api.items.getItem(alarmName).postUpdate(value);
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
    const seconds = Math.max(1, Math.ceil(milliseconds / 1000));
    api.cache.private.put(timerKey, api.actions.ScriptExecution.createTimer(
      timerKey, api.time.ZonedDateTime.now().plusSeconds(seconds), function() {
        // A cancelled callback must never remove a newer timer or raise an alarm.
        if (state.generation !== generation || api.cache.private.get(key) !== state) return;
        api.cache.private.remove(timerKey);
        try { evaluate(true); }
        catch (error) {
          console.error('Zustandsalarm ' + alarmName + ': ' + error);
          schedule(60000);
        }
      }));
  }
  function event(kind, label, minutes) {
    const activeText = onState === 'OPEN' ? 'offen' : 'eingeschaltet';
    const inactiveText = onState === 'OPEN' ? 'geschlossen' : 'ausgeschaltet';
    return {
      id: alarmName, group: 'state-monitor', kind, title,
      message: kind === 'CLEARED'
        ? label + ' ist wieder ' + inactiveText + '.'
        : (kind === 'REMINDER' ? 'Erinnerung: ' : 'Achtung! ') + label +
          ' ist seit mindestens ' + minutes + (minutes === 1 ? ' Minute ' : ' Minuten ') + activeText + '.',
      previousMessage: state.lastMessage, previousTitle: title, comparison: sourceName
    };
  }
  function evaluate(fromTimer) {
    const source = api.items.getItem(sourceName);
    const raw = source.state;
    // Missing source data must not become an alarm or an all-clear. A pending
    // first alarm needs a new complete waiting period after a data gap. Already
    // active alarms are retained; reminder deadlines retry once per minute.
    if (raw !== onState && raw !== offState) {
      if (state.sent === 0 && !state.pendingClear) {
        cancel();
        state.openedAt = null;
      } else if (fromTimer) schedule(60000);
      return;
    }
    const now = Date.now();
    const label = source.label || sourceName;
    if (raw === offState) {
      cancel();
      if (api.items.getItem(alarmName).state === 'ON' && !state.pendingClear) {
        state.pendingClear = event('CLEARED', label, 0);
      }
      writeAlarm('OFF');
      state.openedAt = null;
      state.sent = 0;
      state.lastSent = null;
      if (state.pendingClear) {
        onClear(state.pendingClear);
        state.pendingClear = null;
      }
      return;
    }
    // Do not send a delayed clearance after the source has become active again.
    state.pendingClear = null;
    if (state.openedAt === null) {
      state.openedAt = now;
      // After reload, retain an already active persisted alarm without replaying
      // its notifications or granting it a new set of reminders.
      if (api.items.getItem(alarmName).state === 'ON') state.sent = repeats + 1;
      else writeAlarm('OFF');
    }
    if (state.sent > 0) writeAlarm('ON');
    if (state.sent > repeats) return;
    const due = state.sent === 0 ? state.openedAt + delayMs : state.lastSent + intervalMs;
    if (!fromTimer || now < due) { schedule(due - now); return; }
    const minutes = Math.max(1, Math.floor((now - state.openedAt) / 60000));
    const notification = event(state.sent === 0 ? 'NEW' : 'REMINDER', label, minutes);
    writeAlarm('ON');
    onNotify(notification);
    state.sent++;
    state.lastSent = now;
    state.lastMessage = notification.message;
    if (state.sent <= repeats) schedule(intervalMs);
  }
  try { evaluate(false); }
  catch (error) {
    schedule(60000);
    throw error;
  }
}
