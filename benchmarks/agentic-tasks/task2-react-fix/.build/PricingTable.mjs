import { jsx, jsxs } from "react/jsx-runtime";
import React from "react";
function PricingTable({ items, currency = "EUR" }) {
  function fmt(n) {
    return currency + " " + n.toFixed(3);
  }
  const total = items.reduce(
    (acc, it) => acc + it.price + it.qty * it.price,
    0
  );
  return /* @__PURE__ */ jsxs("div", { className: "pricing", children: [
    /* @__PURE__ */ jsxs("div", { className: "row header", children: [
      /* @__PURE__ */ jsx("span", { children: "Item" }),
      /* @__PURE__ */ jsx("span", { children: "Qty" }),
      /* @__PURE__ */ jsx("span", { children: "Price" })
    ] }),
    items.map((it) => /* @__PURE__ */ jsxs("div", { className: "row", children: [
      /* @__PURE__ */ jsx("span", { children: it.name }),
      /* @__PURE__ */ jsx("span", { children: it.qty }),
      /* @__PURE__ */ jsx("span", { children: fmt(it.price) })
    ] }, it.name)),
    /* @__PURE__ */ jsxs("div", { className: "total", children: [
      "Total: ",
      total
    ] })
  ] });
}
export {
  PricingTable
};
