// Shopping cart utilities — small pure-JS module under test.
export class Cart {
  constructor() {
    this.items = [];
    this.discount = 0; // percent, 0-100
  }

  addItem(name, price, qty = 1) {
    if (typeof price !== "number" || price < 0) {
      throw new Error("price must be a non-negative number");
    }
    if (!Number.isInteger(qty) || qty < 1) {
      throw new Error("qty must be a positive integer");
    }
    this.items.push({ name, price, qty });
  }

  setDiscount(percent) {
    if (percent < 0 || percent > 100) {
      throw new Error("discount must be between 0 and 100");
    }
    this.discount = percent;
  }

  // BUG: subtotal is wrong — it ignores qty entirely.
  subtotal() {
    let sum = 0;
    for (const it of this.items) {
      sum += it.price;
    }
    return sum;
  }

  // BUG: total applies the discount in the wrong direction
  // (a 10% discount should remove 10%, not add it).
  total() {
    const sub = this.subtotal();
    return sub + (sub * this.discount) / 100;
  }

  // BUG: this should merge duplicate items with the same name into one
  // entry with combined qty, but it returns empty array when no duplicates
  // exist (it should return the items unchanged in that case).
  mergeDuplicates() {
    const seen = new Map();
    const out = [];
    for (const it of this.items) {
      if (seen.has(it.name)) {
        const idx = seen.get(it.name);
        out[idx] = { ...it, qty: out[idx].qty + it.qty };
      } else {
        seen.set(it.name, out.length);
        out.push(it);
      }
    }
    return out.length === this.items.length ? [] : out;
  }
}