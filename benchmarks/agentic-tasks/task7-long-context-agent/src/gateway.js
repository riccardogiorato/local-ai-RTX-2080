// Simple quota gateway. BUG: missing required headers per the project docs.
function respond(status, quotaRemaining) {
    const headers = {};
    if (quotaRemaining <= 0) {
        headers['RateLimit'] = String(quotaRemaining); // wrong name, missing Retry-After
    } else {
        headers['rate-limit'] = String(quotaRemaining); // wrong case
    }
    return { status, headers };
}
module.exports = { respond };
