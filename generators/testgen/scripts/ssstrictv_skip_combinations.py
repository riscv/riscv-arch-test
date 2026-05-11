"""SsstrictV simulator-failure skip table.

This module is the single source of truth for (coverpoint-column, instruction)
combinations that are intentionally OMITTED from SsstrictV covergroup
generation and priv test generation.

POLICY: the ONLY acceptable reason to add an entry here is a documented,
reproducible direct contradiction between the reference simulator (sail) and
the RISC-V V spec, captured in a numbered file under ``simulator-issues/``.

A reserved encoding "anything is allowed" — the processor may legally do
nothing, trap, catch fire, etc. Coverpoints must therefore only require what
is necessary to *exercise* the reserved behaviour, never what the processor
does after. Generator/framework limitations do NOT belong in this table; fix
the generator instead. Coverpoints that over-constrain (e.g. require a trap or
a particular mcause) must be relaxed in the template, not skipped here.

Consumed by:
  - generators/coverage/src/covergroupgen/generate.py  (skips covergroup
    emission so the bins do not count against coverage), and
  - generators/testgen/scripts/vector-testgen-priv.py  (skips test generation
    for coverpoints we cannot exercise).

Each entry maps a CSV column name from testplans/priv/SsstrictV.csv to the
list of instructions for which that column should be ignored. Every entry
MUST cite a `simulator-issues/NNN-...md` file in a comment.
"""

SKIP_COMBINATIONS: dict[str, list[str]] = {
    # (intentionally empty — populate only with citations to simulator-issues/)
}
