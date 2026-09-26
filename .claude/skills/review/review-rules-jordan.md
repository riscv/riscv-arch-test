# Review rules

## 1. PR scope and hygiene

- One topic per PR. Split out unrelated changes and stray commits from other PRs.
- Check the file and commit counts and scan the diff for accidents:
  - characters garbled by an encoding round-trip (e.g. `─` → `â”€`)
  - a global rename that hit unrelated text
  - whitespace, reflow, or style churn
- Only change a simulator's config after running that simulator. A config may claim an extension only if the DUT supports it.
  - The UDB yaml, `sail.json`, `run_cmd.txt` and the simulator's own config must agree.
  - Fix any mismatch the PR exposes in the same PR.
- To make the configs agree, change the Sail config rather than another simulator's, unless that other simulator is the wrong one.
- Merge duplicate PRs, and factor out the logic they share.
- A thread is resolved only once the fix is pushed.
- Don't put personal ignores in `.gitignore`. Don't make incidental changes to CI workflows.
- Keep task-specific context out of AGENTS.md; link to a doc instead.

## 2. Comments and docstrings

- Describe the code as it is now. No history ("moved from", "previously", "now passes"), and no explanation of alternatives that didn't work.
- Trim verbose comments down to what a later reader needs. Leave out:
  - simulator internals
  - language-syntax lessons
  - details of other functions that will drift out of sync
- Delete comments that contradict the code, and cross-file "X is defined in Y" notes.
- A docstring says what a function does, not how. List every argument, with the correct name.
- Explain magic numbers. Put a comment on the line it describes or the line before, never after.
- No commented-out code.
- A TODO needs an issue, or a stated condition for removing it (e.g. every `NORUN`).
- A CI or config exclusion gets a one-line reason and an issue link. Remove entries whose issue is closed.
- New files carry the author's own copyright (or RVI's), not one copied from another file.
- Ask what vague words mean ("yet", "not supported", "sibling", "excursion").

## 3. Code simplicity

- Inline indirection that does no work:
  - one-line wrappers
  - constants used once
  - name-mapping dicts
  - aliases like `DRIVER = "Smode"`
  - functions that only forward their arguments
- Don't over-deduplicate. Many tiny helpers (common in AI-written code) make the flow hard to follow. If a function can't be explained after reading it, ask for a rewrite.
- Real duplication across suites belongs in a `*Common.py`.
- Reuse what already exists:
  - `csr_walk_test`, `gen_csr_write_sigupd`, the Sv/PMP helpers, and the register allocator
  - `data/random.py` (seeded) and `data/edges.py`
  - `encoding.h` constants
  - `LI`/`LA`, `DEFAULT_*_REG`, and the `RVTEST_TSBI_*` macros
  - existing coverpoint variants
- Build one `lines.extend([...])` block instead of a chain of `append`/`extend` calls. Put each assembly line in its own list element, with a trailing comma.
- Types:
  - use `Literal`/`Enum` instead of validating strings
  - put real defaults in the signature instead of `None` plus a later check
  - don't annotate constants whose type is obvious
  - no `from __future__ import annotations`
  - don't share mutable sets between callers
- Use consistent, self-explanatory names (`test_data`, never `td`). A function or chunk name must match what it contains.
- Don't branch on coverpoint-name strings. Don't use regex to parse assembly.
- Fail loudly. Don't `continue` past a missing case or return an empty list; raise.
- Allocate registers where they are used and release them there. Don't pass register structs around.
- A helper returns its test chunks instead of mutating a list it was handed.
- A self-contained testcase is worth some repetition. Don't hoist setup out of loops if that couples testcases together.
- Don't use lazy imports to break import cycles; restructure the modules.

## 4. Test design

- Keep `required_extensions` minimal:
  - omit anything another listed extension implies (Sstc implies S; S implies U and Zicsr)
  - don't require I, so the suite also runs on E
  - omit `march_extensions` unless it differs from `required_extensions`
- Use `forbidden_extensions` or a separate suite rather than an `#ifdef` around the whole file. Never generate a file that is entirely ifdef'd out.
- No redundant guards: none for extensions the suite already requires. Guard on the exact feature:
  - Zve64x, not Zvl64b
  - `UDB_MXLEN_64` for `sd`
  - `ZCMOP_SUPPORTED` for the compressed forms
  - `RVMODEL_*_ADDRESS` where one is used

  Extension macros have no `UDB_` prefix. A derived macro must not be named `UDB_*`.

- For privileged tests:
  - use T-SBI only, never legacy `RVTEST_GOTO_*`
  - certification tests trap to S-mode, not M-mode
  - coverpoints that need M-mode go in the `*Sm` suite
  - if T-SBI falls short, fix the handler rather than working around it
- Never weaken a test because a simulator disagrees. Keep the test and the coverage, exclude the failing config, and file an issue there. If the reference model lacks a feature, exclude it in the test but keep the coverpoint, so the miss stays visible.
- Test read-only-zero bits and reserved-but-defined bits; don't mask them out of walks.
- Every testcase checks something with a signature. Examples:
  - the counter value after a wrap
  - that `rd` is unchanged by a fence with `rd != x0`
  - the whole `cbo.zero` block and a little past its end
  - that memory and `rd` are unchanged after a faulting access
  - both interrupts pending before a priority check
- A test must never hang. Use a bounded wait and then a check, and allow for DUT speed and IPC when setting timing windows.
- Allow legal implementation variation:
  - xtval may be 0
  - `mtval` may be read-only 0
  - xtinst may be 0 or the defined value
  - `misa` may be read-only 0
  - the image may be linked at any address
  - unordered stores to the same address have no defined winner

  Use the UDB/Sail parameters that describe these choices.

- Put a testcase label right before the instruction under test. Number testcases in execution order, and use the same names on RV32 and RV64.
- Write shared RV32/RV64 code once (use `LREG`/`SREG`) and put only the XLEN-specific part under `#if`.
- No unexplained `nop`s. Don't add a mode switch when a new chunk already starts in the right mode.
- Touch only the CSR bits the test needs: `csrs`/`csrc` of that field, or `csrci` when the value fits. Don't redo anything the boot code already sets. Enable the M-level `*stateen`/`*envcfg` bits before initializing H CSRs.
- The generator implements every item in the testplan, and generated code must be able to reach every coverpoint bin.
- A change isn't complete until its companions are updated:
  - the coverpoints
  - `coverpoints/norm/*.yaml`
  - the CTP adoc
  - for a new `RVMODEL_*` macro, its documentation, added only in the PR that uses it
- New suites use Python generators, not handwritten tests.
- Users define `RVMODEL_*` macros, never `RVTEST_*`.
- Trap-handler code must be the same size under every option.
- No simulator-specific logic in `run_tests.py`.
- If most users' simulators can't run a new suite, add it to the default exclude list.
- Watch the effect on test count and runtime: `testcases_per_file`, trap-signature sizes, and timeouts.

## 5. Coverpoints

- Use `get_csr_val(..., "csr", "field")` rather than raw bit slices. Use named constants and decoded fields (`ins.current.vs1`) rather than `insn[19:15]`.
- Reuse the standard coverpoints (`priv_mode_s_u`, `priv_mode_m_s_u`).
- Name each coverpoint for what it matches. No duplicate coverpoints, and keep names consistent across related suites.
- Never comment out a bin; use the real encoding names instead. Every `ignore_bins` needs a stated reason.
- Don't write bins that another test already covers trivially.
- Where DUT timing varies, cover the write attempt and let the test check the result.
- Don't repeat an `iff` in both the cross and its component coverpoint.
- Guard vector-only exclusions with `ZVE32X_SUPPORTED`, so non-vector Ssstrict still tests them.
- Keep `disassemble.svh` grouped by extension.

## 6. Spec claims and normative tags

- Quote the spec where the reasoning depends on it, and verify every claim the PR makes about the spec yourself.
- Before accepting "simulator bug", check whether the behavior is legal. Before accepting "passes now", check which versions CI pins.
- Normative tags in the ISA manual:
  - A tagged rule must make sense on its own. Include context such as "On RV32 systems" or the antecedent of "In such cases".
  - Don't tag NOTEs or explanatory text.
  - Turn a "should" into "must" when it is meant as a requirement.
  - Follow the naming conventions: instruction names are hyphenated (`orc-b`), extension capitalization is preserved (Zve64x), and tag names have no meaningless suffixes.
  - Add a summary only when the tagged text isn't clear on its own.
