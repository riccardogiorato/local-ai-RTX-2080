// Immovable contract check — SSR-renders PricingTable and asserts the markup.
// This file must NOT be modified by the agent (verify.sh checks its hash first).
import React from "react";
import { renderToString } from "react-dom/server";
import { transformSync } from "esbuild";
import { mkdirSync, writeFileSync } from "node:fs";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

mkdirSync(".build", { recursive: true });
const jsx = readFileSyncText("src/PricingTable.jsx");
const js = transformSync(jsx, { loader: "jsx", jsx: "automatic", format: "esm" }).code;
writeFileSync(".build/PricingTable.mjs", js);
const { PricingTable } = await import("./.build/PricingTable.mjs");

const items = [
  { name: "Espresso", qty: 2, price: 1.5 },
  { name: "Cappuccino", qty: 3, price: 4.0 },
  { name: "Brioche", qty: 1, price: 2.5 },
];
const html = renderToString(React.createElement(PricingTable, { items, currency: "EUR" }));

assert.match(html, /<table[^>]*>/, "must render a <table>");
assert.match(html, /<thead[^>]*>[\s\S]*?<th[^>]*>\s*Item\s*<\/th>[\s\S]*?<th[^>]*>\s*Qty\s*<\/th>[\s\S]*?<th[^>]*>\s*Price\s*<\/th>[\s\S]*?<\/thead>/, "thead must have Item, Qty, Price headers in order");
assert.match(html, /<tbody[^>]*>[\s\S]*?<tr/, "tbody rows must use <tr>");
assert.match(html, /Espresso[\s\S]*?Cappuccino/, "rows keep input order");
assert.match(html, />\s*3\.00\s*EUR\s*</, "Espresso line price 2 x 1.50 = 3.00 EUR, currency after amount, two decimals");
assert.match(html, />\s*12\.00\s*EUR\s*</, "Cappuccino line price 3 x 4.00 = 12.00 EUR");
assert.match(html, />\s*2\.50\s*EUR\s*</, "Brioche line price 1 x 2.50 = 2.50 EUR");
assert.match(html, /Total:\s*18\.00\s*EUR/, "correct grand total 18.00 EUR (qty x price summed)");

console.log("RENDER_CHECK_OK");

function readFileSyncText(p) {
  return createRequire(import.meta.url)("node:fs").readFileSync(p, "utf8");
}