const { respond } = require('../src/gateway.js');
const assert = require('assert');
assert.strictEqual(respond(200, 42).headers['X-Rate-Limit'], '42', 'normal path: X-Rate-Limit as decimal string');
const limited = respond(429, 0);
assert.strictEqual(limited.status, 429, 'exhausted path: 429');
assert.strictEqual(limited.headers['X-Rate-Limit'], '0', 'exhausted path: X-Rate-Limit present');
assert.strictEqual(limited.headers['Retry-After'], '30', 'exhausted path: Retry-After 30');
assert.strictEqual(limited.headers['RateLimit'], undefined, 'no malformed header names');
console.log('gateway tests OK');
