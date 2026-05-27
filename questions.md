# Open questions for the user

(Will be re-checked every 120s and removed once answered.)

1. **Scope for this autopilot session.** Merging vector-testgen into testgen
   while keeping byte-identical output across ~4400 generated `.S` files is a
   multi-day refactor (six+ thousand lines of vector-specific code). Acceptable
   delivery for this session?
   - (a) Stage one — wire vector generators into the unified `testgen` CLI so
     `make tests EXTENSIONS=...` produces both scalar and vector tests with
     shared argument parsing / progress / parallelism; defer deeper sharing
     (register randomization, sigupd buffer, IO) to follow-up tasks.
   - (b) Attempt the full deep merge anyway and ship whatever passes the diff
     check at the end of the session.
   - (c) Something else (please describe).

2. **`SmV`, `SmVF`, `UV` ownership.** These already live in the unified
   `testgen.priv.extensions.*` package (scalar testgen). Should the merge
   treat them as already-merged (leave them alone) or do they also need
   restructuring as part of "vector testgen"?

3. **Coverage validation runtime.** `make coverage` with all listed extensions
   and the Questa/VCS simulator can take a long time. Is it acceptable to skip
   the actual sim run inside this session and only verify via byte-diff of
   generated `.S` files, deferring the sim-based coverage check to a follow-up
   task once a sim host is available?
