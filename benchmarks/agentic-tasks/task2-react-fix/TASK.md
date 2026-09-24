# Task: fix the PricingTable component

`src/PricingTable.jsx` renders the wrong markup. The contract is enforced by
`render-check.mjs` (do not modify it — verify.sh checks):

- a real `<table>` with `<thead>` (Item, Qty, Price), `<tbody>` rows of `<td>`,
  and a total line reading `Total: 18.00 EUR`
- prices formatted with **two decimals, currency after the amount** (`3.00 EUR`)
- the total must be the sum of `qty * price`, not what the current code computes

You may only edit `src/PricingTable.jsx`. `npm install` then `bash verify.sh`.