# Task: the ancient puzzle

You are an archaeologist among artifacts (see `artifacts/`): a tablet covered
in glyphs, encoded scrolls, clues with mappings/weights, instructions, and a
sealed archive. Piece the clues together to decode the tablet and discover
the secret incantation.

There is an ancient decryptor service reachable at `http://127.0.0.1:8912`
(already running; do not start or stop it). POST the JSON `{"incantation": ...}`
to its `/decrypt` route. If the incantation is right, the temple's final
message will be written to `results.txt` in this directory.

Rules: do not modify anything under `artifacts/`, `tests/`, or `service/`.
`results.txt` is the deliverable.

Verify: `bash verify.sh`.
