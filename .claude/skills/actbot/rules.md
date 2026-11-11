# ACTBot review rules

These rules are distilled from maintainer reviews of ACT PRs. Each is a default, not a law: report a departure when it
makes the change harder to read, maintain or trust, and say which rule it breaks. Apply only the sections that match
the files the change touches.

## 1. Scope and hygiene

- One topic per PR. Flag unrelated changes and commits that belong to another PR.
- Scan the diff for accidents:
  - characters garbled by an encoding round-trip (e.g. `─` → `â”€`);
  - a global rename that hit unrelated text;
  - whitespace, reflow or style churn in lines the PR doesn't otherwise change.
- Generator, testplan or template changes come with the regenerated files under `tests/` and `coverpoints/`. Hand
  edits to generated files are wrong even when CI would catch them.
- No personal ignores in `.gitignore`. No incidental CI workflow changes.
- AGENTS.md holds project-wide guidance. Task-specific context goes in a doc that AGENTS.md links to.
- The PR description matches the diff and is short (AGENTS.md).

## 2. Comments and docstrings

- Comments describe the code as it is now. No history ("moved from", "previously", "now passes") and no account of
  alternatives that didn't work.
- Keep only what a later reader needs. Leave out simulator internals, language-syntax lessons, and details of other
  functions that will drift out of sync.
- Delete comments that contradict the code, and cross-file "X is defined in Y" notes.
- A docstring says what a function does, not how, and names every argument correctly.
- Explain magic numbers. A comment goes on the line it describes or the line before, not after.
- No commented-out code.
- A TODO needs an issue link or a stated condition for removing it.
- A `ci.yaml` exclusion gets a short reason and an issue link against the simulator or DUT. Flag entries whose issue
  is closed.
- New files carry their author's copyright (or RVI's), not one copied from another file.
- Ask what vague words mean ("yet", "not supported", "sibling").

## 3. Code simplicity

- Inline indirection that does no work: one-line wrappers, constants used once, name-mapping dicts, aliases like
  `DRIVER = "Smode"`, functions that only forward their arguments, and gate aliases like
  `MISA_GATE = "UDB_MISA_CSR_IMPLEMENTED"`. Guards name the UDB parameter or `*_SUPPORTED` macro directly.
- Don't over-deduplicate. Many tiny helpers make the flow hard to follow; if a function can't be explained after
  reading it, ask for a rewrite. Real duplication across suites belongs in a `*Common.py`.
- Reuse what exists, for example:
  - `csr_walk_test` and `gen_csr_write_sigupd` (`testgen/asm/csr.py`), `load_constant` (`testgen/asm/helpers.py`);
  - the Sv and PMP helpers and the `TestData` register allocators;
  - `testgen/data/random.py` (seeded) and `testgen/data/edges.py`;
  - `encoding.h` constants, `LI()`/`LA()`, `DEFAULT_*_REG`, and the T-SBI calls;
  - existing coverpoints and coverpoint variants.
- Build one `lines.extend([...])` block rather than a chain of `append`/`extend` calls, with each assembly line in its
  own list element and a trailing comma.
- Types: `Literal` or `Enum` rather than validated strings; real defaults in the signature rather than `None` plus a
  later check; no annotations on constants whose type is obvious; no `from __future__ import annotations`; no mutable
  sets shared between callers.
- Names are consistent and self-explanatory (`test_data`, not `td`). A function or chunk name matches its contents.
- Don't branch on coverpoint-name strings. Don't parse assembly with regexes.
- Fail loudly: raise on a missing case rather than `continue` or returning an empty list.
- Allocate registers where they are used and release them there. Don't hard-code registers, even to match a shared
  helper; pass allocated registers into the helper instead.
- A helper returns its test chunks rather than mutating a list it was handed.
- A self-contained testcase is worth some repetition. Don't hoist setup out of a loop if that couples testcases.
- Don't use lazy imports to break import cycles; restructure the modules.

## 4. Test design

- `required_extensions` is minimal. Omit extensions another listed one implies (Sstc implies S; S implies U and
  Zicsr). Don't list I when the test also makes sense on E. Omit `march_extensions` unless it differs.
- Use `forbidden_extensions` or a separate suite rather than an `#ifdef` around a whole file. Never generate a file
  that is entirely ifdef'd out.
- Guard on the exact feature, and not on something the suite already requires: Zve64x rather than Zvl64b,
  `UDB_MXLEN_64` for `sd`, `RVMODEL_*_ADDRESS` where one is used. Extension macros have no `UDB_` prefix, and a
  derived macro must not be named `UDB_*`.
- Prefer modeling over gating. If Sail or UDB can't describe a legal configuration, the fix is a Sail option or UDB
  parameter, not an ACT gate that hides the behavior. Gate a HINT (e.g. `prefetch.*`) only if the spec says it can
  behave differently.
- S- and U-mode test content doesn't guard on `STANDARD_SM_SUPPORTED`; T-SBI exists to hide a nonstandard M-mode.
- Privileged tests boot into their intended mode and use T-SBI for higher-privilege work. Coverpoints that need
  M-mode go in an `*Sm` suite. If T-SBI falls short, fix it rather than working around it.
- Never weaken a test because a simulator disagrees. Keep the test and its coverage, exclude the failing config, and
  file an issue against the simulator. If the reference model lacks a feature, skip the case in the test but keep the
  coverpoint so the miss stays visible.
- Test read-only-zero and reserved-but-defined bits rather than masking them out of walks.
- Every testcase checks its result with a signature update or the trap signature. Examples: the counter after a wrap;
  `rd` unchanged by a fence with `rd != x0`; the whole `cbo.zero` block and a little past it; memory and `rd`
  unchanged after a faulting access; both interrupts pending before a priority check. Writing a value and not
  reading it back is not a test.
- A test never hangs: a bounded wait followed by a check, with margins for slow DUTs.
- Allow legal implementation variation: xtval may be 0, `mtval` may be read-only zero, xtinst may be 0 or the defined
  value, `misa` may be read-only zero, the image may be linked anywhere, unordered stores to one address have no
  defined winner. WARL fields may legalize a write to another value. Use the UDB/Sail parameters that describe these
  choices, and where the spec allows a discrete set of outcomes, check that one of them happened.
- A testcase label sits right before the instruction under test. Testcases are numbered in execution order, with the
  same names on RV32 and RV64.
- Shared RV32/RV64 code is written once (`LREG`/`SREG`); only the XLEN-specific part goes under `#if`.
- No unexplained `nop`s. No mode switch when a chunk already starts in the right mode.
- Touch only the CSR bits a test needs (`csrs`/`csrc` of that field, `csrci` when the value fits). Don't redo setup
  the boot code already does.
- The generator implements every testplan item the change touches, and its output can reach every bin of the
  coverpoints it targets.
- A change updates its companions: coverpoints, `coverpoints/norm/*.yaml`, the CTP adoc in `docs/ctp/src/`, and for a
  new `RVMODEL_*` macro its documentation, added in the PR that first uses it.
- New suites use Python generators, not handwritten tests.
- DUTs define `RVMODEL_*` macros, never `RVTEST_*`.
- Trap-handler code is the same size under every option.
- No simulator-specific logic in `run_tests.py`.
- Watch test count and runtime: `testcases_per_file`, trap-signature size, long dynamic instruction counts.

## 5. Coverpoints

- Read CSRs with `get_csr_val(ins.hart, ins.issue, <when>, CSR_X)` or
  `get_csr_field(ins.hart, ins.issue, <when>, CSR_X, "field")`, not `ins.current.csr[...]` or raw bit slices. Use
  decoded fields (`ins.current.vs1`), not `insn[19:15]`.
- Reuse the standard coverpoints (`priv_mode_s_u`, `priv_mode_m_s_u`).
- Name each coverpoint for what it matches. No duplicates, and consistent names across related suites.
- Write coverpoints inline in the covergroup. Don't hide coverpoint blocks, bin lists or gates in `` `define``
  macros.
- Never comment out a bin. `ignore_bins` is only for architecturally unreachable bins and needs a stated reason;
  never use it for a legal bin a tool can't reach yet. Prefer a single-bin coverpoint to `ignore_bins` in a cross.
- Don't add bins another test already covers trivially.
- Coverpoints cover stimulus, not expected results; tests check results. Where DUT timing varies, cover the attempt.
- Don't repeat an `iff` in a cross and in its component coverpoint.
- Flag crosses with many bins for little benefit, and suggest simpler coverpoints that still exercise the testplan.

## 6. Spec claims, normative mapping and configs

- Verify every claim the change makes about the spec against the ISA manual, and quote it where a finding depends on
  it. Before accepting "simulator bug", check whether the behavior is legal.
- Normative mapping (`coverpoints/norm/*.yaml`): the coverpoints listed for a rule reasonably exercise it; about four
  at most, marked representative if more apply. A rule the change touches but can't cover in ACT scope says why.
- Normative tags in the ISA manual make sense on their own (include "On RV32 systems" and the like), don't tag NOTEs,
  and follow naming conventions (hyphenated instruction names like `orc-b`, extension capitalization kept).
- Configs: the UDB yaml, `sail.json`, linker script, `run_cmd.txt` and the DUT must agree. A config claims an
  extension only if the DUT supports it. When fields are copied from another DUT, ask whether each was checked. When
  configs disagree, change the wrong one (usually not Sail's unless Sail's is wrong).
