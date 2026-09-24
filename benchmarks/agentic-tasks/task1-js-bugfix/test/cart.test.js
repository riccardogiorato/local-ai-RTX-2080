import { test } from "node:test";
import assert from "node:assert/strict";
import { Cart } from "../lib/cart.js";

test("subtotal multiplies price by qty", () => {
  const c = new Cart();
  c.addItem("apple", 0.5, 4);
  c.addItem("pear", 1.2, 2);
  assert.equal(c.subtotal(), 0.5 * 4 + 1.2 * 2);
});

test("subtotal handles single item with qty 1", () => {
  const c = new Cart();
  c.addItem("pen", 3.0);
  assert.equal(c.subtotal(), 3.0);
});

test("total applies discount by subtracting", () => {
  const c = new Cart();
  c.addItem("book", 40, 1);
  c.addItem("mag", 10, 3);
  c.setDiscount(10);
  assert.equal(c.total(), (40 + 30) * 0.9);
});

test("zero discount leaves total unchanged", () => {
  const c = new Cart();
  c.addItem("book", 50, 1);
  assert.equal(c.total(), 50);
});

test("mergeDuplicates keeps unique items unchanged", () => {
  const c = new Cart();
  c.addItem("a", 1, 1);
  c.addItem("b", 2, 1);
  const merged = c.mergeDuplicates();
  assert.equal(merged.length, 2);
  assert.deepEqual(merged[0], { name: "a", price: 1, qty: 1 });
});

test("mergeDuplicates combines same-name items", () => {
  const c = new Cart();
  c.addItem("a", 1, 1);
  c.addItem("a", 1, 2);
  const merged = c.mergeDuplicates();
  assert.equal(merged.length, 1);
  assert.equal(merged[0].qty, 3);
});