import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { postedAt } from "../src/format.js";

const v = JSON.parse(readFileSync("node_modules/date-fns/package.json", "utf8")).version;
const [major] = v.split(".").map(Number);
assert.ok(major >= 4, `date-fns must be upgraded to v4+ (found v${v})`);

test("postedAt renders an about-time string with suffix", () => {
  const now = Date.now();
  const out = postedAt(now - 1000 * 60 * 5); // 5 minutes ago
  assert.match(out, /5 minutes ago|about 5 minutes ago/);
});

test("postedAt handles future dates", () => {
  const out = postedAt(Date.now() + 1000 * 60 * 10);
  assert.match(out, /in (about )?10 minutes/);
});

test("postedAt rejects garbage input", () => {
  assert.throws(() => postedAt("not-a-date"));
});