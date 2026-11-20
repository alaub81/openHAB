// Small openHAB time test double. Intl supplies the real Europe/Berlin offsets;
// this is not a replacement for verification with openHAB's installed time API.
const assert = require('node:assert/strict');

class DateValue {
  constructor(epoch, zone = 'Europe/Berlin') {
    assert(Number.isFinite(epoch), 'A valid timestamp is required');
    this.epoch = epoch;
    this.zone = zone;
  }
  parts() {
    return Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
      timeZone: this.zone, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
    }).formatToParts(new Date(this.epoch)).map(p => [p.type, p.value]));
  }
  format(pattern) {
    const p = this.parts();
    return pattern.replace(/yyyy|MM|dd|HH|mm|H/g, token => ({
      yyyy: p.year, MM: p.month, dd: p.day, HH: p.hour, mm: p.minute, H: String(Number(p.hour))
    })[token]);
  }
  withZoneSameInstant(zone) { return new DateValue(this.epoch, zone); }
  toLocalDate() {
    const p = this.parts();
    const value = [p.year, p.month, p.day].join('-');
    return { value, equals: other => value === other.value };
  }
  plusDays(days) {
    // Noon is sufficient for the calendar-day comparisons in these tests.
    // Resolve local noon after adding calendar days, including DST boundaries.
    const p = this.parts();
    const utc = Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day) + days, 12);
    const noon = new DateValue(utc, this.zone);
    return new DateValue(utc + (12 - Number(noon.parts().hour)) * 3600000, this.zone);
  }
  plusSeconds(seconds) { return new DateValue(this.epoch + seconds * 1000, this.zone); }
  isAfter(other) { return this.epoch > other.epoch; }
  toInstant() { return new Date(this.epoch).toISOString(); }
}

module.exports = {
  toZDT: value => new DateValue(Date.parse(value)),
  ZoneId: { of: zone => zone },
  DateTimeFormatter: { ofPattern: pattern => pattern },
  ZonedDateTime: { now: () => new DateValue(Date.parse('2026-11-13T12:00:00+01:00')) }
};
