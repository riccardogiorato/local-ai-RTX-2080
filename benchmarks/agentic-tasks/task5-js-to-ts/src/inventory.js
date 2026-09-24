// Product inventory helpers — routinely used across the app.

export function stockValue(items, priceOf) {
  let total = 0;
  for (const it of items) {
    total += it.qty * priceOf(it.sku);
  }
  return total;
}

export function lowStock(items, threshold = 5) {
  return items
    .filter((it) => it.qty <= threshold)
    .map((it) => it.sku)
    .sort();
}

export function restockReport(items, wanted) {
  // wanted: { sku -> qty to buy }
  const lines = [];
  for (const sku of Object.keys(wanted)) {
    const item = items.find((it) => it.sku === sku);
    const name = item ? item.name : "unknown";
    lines.push(`${name}: +${wanted[sku]}`);
  }
  return lines.join("\n");
}