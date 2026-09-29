import assert from "node:assert/strict";
import test from "node:test";
import { format, isAfter, isSameDay, parseISO } from "date-fns";

test("date-fns APIs used by appointment and report screens preserve calendar behavior", () => {
  const appointment = parseISO("2025-02-28T12:00:00");
  const nextDay = parseISO("2025-03-01T12:00:00");

  assert.equal(format(appointment, "yyyy-MM-dd"), "2025-02-28");
  assert.equal(isAfter(nextDay, appointment), true);
  assert.equal(isSameDay(appointment, parseISO("2025-02-28T18:00:00")), true);
});
