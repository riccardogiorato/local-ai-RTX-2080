# Task: fix the two bugs in app/metrics.py

Both functions are buggy; `test_metrics.py` defines the exact contract
(`squared_distance` must be the *squared* Euclidean distance, `moving_average`
must include the window ending at the last element). Run the tests, fix
`app/metrics.py`.

You may only edit `app/metrics.py`. Do not modify the tests.
Verify: `bash verify.sh` (uses pytest).