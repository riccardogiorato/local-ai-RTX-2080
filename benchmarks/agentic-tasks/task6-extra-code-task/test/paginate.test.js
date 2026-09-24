import { test } from "node:test";
import assert from "node:assert/strict";
import { paginate } from "../lib/paginate.js";

const rows = Array.from({ length: 25 }, (_, i) => ({ id: i + 1 }));
const letters = [
  { name: "c", n: 3 },
  { name: "a", n: 1 },
  { name: "b", n: 2 },
];

test("page 1 returns the first perPage items", () => {
  const out = paginate(rows, { page: 1, perPage: 10 });
  assert.equal(out.items.length, 10);
  assert.equal(out.items[0].id, 1);
  assert.equal(out.items[9].id, 10);
});

test("page 2 returns the next perPage items", () => {
  const out = paginate(rows, { page: 2, perPage: 10 });
  assert.equal(out.items[0].id, 11);
  assert.equal(out.items.length, 10);
});

test("last partial page returns the remainder", () => {
  const out = paginate(rows, { page: 3, perPage: 10 });
  assert.equal(out.items.length, 5);
  assert.equal(out.items[4].id, 25);
  assert.equal(out.hasNext, false);
});

test("hasPrev/hasPrev flags", () => {
  assert.equal(paginate(rows, { page: 1 }).hasPrev, false);
  assert.equal(paginate(rows, { page: 2 }).hasPrev, true);
  assert.equal(paginate(rows, { page: 2, perPage: 10 }).hasNext, true);
});

test("out-of-range page is empty but well-formed", () => {
  const out = paginate(rows, { page: 99, perPage: 10 });
  assert.deepEqual(out.items, []);
  assert.equal(out.hasNext, false);
  assert.equal(out.hasPrev, true);
  assert.equal(out.total, 25);
});

test("sortKey sorts ascending before paginating", () => {
  const out = paginate(letters, { page: 1, perPage: 2, sortKey: "n" });
  assert.deepEqual(out.items.map((x) => x.name), ["a", "b"]);
});

test("per-item contract on tiny inputs", () => {
  const out = paginate([1], { page: 1, perPage: 10 });
  assert.deepEqual(out.items, [1]);
  assert.equal(out.hasNext, false);
});