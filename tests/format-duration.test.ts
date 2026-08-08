import assert from "node:assert/strict";
import test from "node:test";

import { formatDurationSeconds } from "../lib/format-duration";

test("formats run durations without sub-second precision", () => {
  assert.equal(formatDurationSeconds(6515.886), "1h 48m 36s");
  assert.equal(formatDurationSeconds(3209.419), "53m 29s");
  assert.equal(formatDurationSeconds(45.4), "45s");
});

test("keeps zero-valued units when they clarify a longer duration", () => {
  assert.equal(formatDurationSeconds(3600), "1h 0m 0s");
  assert.equal(formatDurationSeconds(60), "1m 0s");
});

test("handles missing and invalid durations safely", () => {
  assert.equal(formatDurationSeconds(null), "0s");
  assert.equal(formatDurationSeconds(Number.NaN), "0s");
  assert.equal(formatDurationSeconds(-10), "0s");
});
