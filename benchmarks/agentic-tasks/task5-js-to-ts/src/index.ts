import { lowStock, restockReport, stockValue } from "./inventory.js";

// --- used by the CLI; do not change this file, only migrate inventory ---
const items = [
  { sku: "A1", name: "Anchovies", qty: 12 },
  { sku: "B2", name: "Breadcrumbs", qty: 3 },
];

console.log(stockValue(items, (sku) => (sku === "A1" ? 3.5 : 2.0)));
console.log(lowStock(items));
console.log(restockReport(items, { B2: 40 }));