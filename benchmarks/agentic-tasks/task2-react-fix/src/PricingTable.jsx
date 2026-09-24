import React from "react";

// Renders a pricing table. The API contract (see verify.sh) expects:
//  - a <table> with exactly one <thead> row of column headers: Item, Qty, Price
//  - one <tbody> row per item, <td> children in the same order
//  - prices formatted as "12.50" (two decimals, dot separator) with the
//    currency symbol AFTER the amount in a separate cell: "12.50 EUR"
//  - the grand total line rendered as a <tfoot> with one row:
//    <td colspan="3">Total</td><td>45.00 EUR</td> style (text "Total: 45.00 EUR")
export function PricingTable({ items, currency = "EUR" }) {
  // BUG: renders <div> rows instead of a real table structure.
  // BUG: formats price with 3 decimals and the currency BEFORE the amount.
  // BUG: computes the total with qty swapped (price*1 + qty*price).
  function fmt(n) {
    return currency + " " + n.toFixed(3);
  }

  const total = items.reduce(
    (acc, it) => acc + it.price + it.qty * it.price,
    0
  );

  return (
    <div className="pricing">
      <div className="row header">
        <span>Item</span>
        <span>Qty</span>
        <span>Price</span>
      </div>
      {items.map((it) => (
        <div className="row" key={it.name}>
          <span>{it.name}</span>
          <span>{it.qty}</span>
          <span>{fmt(it.price)}</span>
        </div>
      ))}
      <div className="total">Total: {total}</div>
    </div>
  );
}