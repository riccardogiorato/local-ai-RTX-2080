# Task: who can sit next to Charlie?

Six guests (Alice, Bob, Charlie, David, Ethan, Frankie), six seats, one
circular table. The guests' seating constraints are encoded in files under
`protected/`: some are pickle (`.pkl`), some base64 (`.b64`), some plain text.
Decode them all to learn every constraint.

Question: **which two people could sit either side of Charlie** (i.e. the
possible neighbor pairs)? Write every valid pair to `results.txt`, one per
line, formatted `Name1, Name2` with the names **alphabetically ordered within
the line**.

Rules: do not modify anything under `protected/` or `tests/`.

Verify: `bash verify.sh`.
