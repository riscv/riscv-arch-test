---
name: review
description: Use when asked to review a suite, PR, testplan, coverpoints, or normative rules in riscv-arch-test. Reviews every layer of a suite (ISA manual, testplan, coverpoints, generator, generated tests, normative-rule mapping, CTP), runs it on the reference models and DUTs, and reports verified findings.
---

# Reviewing ACT suites and PRs

This skill supplements the normal review process; it does not replace it.
AGENTS.md rules (LI/LA macros, register clobbering, PR hygiene, prek) also apply and are not repeated here.
`review-rules-jordan.md` in this directory holds the detailed rules, distilled from maintainer reviews. Read it before step 5.

Take a critical view and assume nothing is correct.
Be especially skeptical of code that looks AI-generated.
Such code can tweak tests and expectations until they pass, instead of testing what the spec requires.

**Out of scope:** XLEN and endianness don't need to be exercised, although tests that are otherwise in scope may touch them. Custom instruction and CSR space is out of scope.

## Workflow

### 1. Scope and checkout

- **Suite review:** the suite is `<Suite>`. For a privileged suite, that is the name registered with `add_priv_test_generator`. For an unprivileged suite, it is the testplan name.
- **PR review:**
  - Check out the PR in its own worktree, so neither your work nor the builds mix with it: `git worktree add ../act-pr-N && cd ../act-pr-N && gh pr checkout N`.
  - List the suites and files touched with `gh pr view N` and `gh pr diff N`.
  - Check that the description matches the diff.
  - Watch for stray commits, churn, and config changes the PR does not need.

### 2. History

- Keep review records in your personal `~/reviews/act/`, never in this repository.
  - Use `<Suite>/` for suite reviews and `pr-<N>/` for PR reviews.
  - Write one dated file per review, starting with the head SHA reviewed. Record the findings and what was run, with the results.
- On a re-review:
  - Read the previous record.
  - Review the delta with `git range-diff` or `git diff <old-sha>..<new-sha>`, and look hardest at the commits added since then.
  - Check each earlier finding against the new code.
  - Pull the review threads with `gh api repos/riscv/riscv-arch-test/pulls/N/comments`. A thread marked resolved is not necessarily fixed.

### 3. Generate, then start the runs in the background

Run the build in one background job, in this order. The coverage and simulator runs share `work/` and `tests/`, so running them concurrently corrupts both.

```bash
EXTENSIONS=<Suite> make tests && git status --short tests coverpoints   # tracked generated files must not change
make coverage EXTENSIONS=<Suite>                                        # sail-rv32-max and sail-rv64-max, with coverage
EXTENSIONS=<Suite> DEBUG=True make -k spike whisper qemu imperas cores  # DUT configs; `cores` includes cvw
```

- Drop any simulators you don't have installed.
- Add `sail` (all 13 Sail configs, including the profile and clang variants) only when the PR touches those configs. Otherwise just do `sail-rv64-max-clang` to test the clang compiler.
- Where Sail coverage is incomplete, also collect functional coverage on cvw-rv64gc with Verilator.
- If `tests/priv/` or `work/` holds output from an older checkout, run `make clean` first. Generated priv tests are not tracked, so stale suites linger.
- `DEBUG=True` is what produces each config's trap report. A trap report is **not** the DUT's traps. It is the Sail run, under that DUT's configuration, that produces the expected signature. Comparing trap reports across configs therefore shows where configurations make the expected behavior diverge.
  - Keep `DEBUG=True` on every config whose traps you want to compare.
  - A DUT whose actual traps differ from its reference shows up as a signature mismatch in its run log instead.

### 4. Mechanical checks

These take seconds. Run them first, and again once the runs finish, to find where to look:

```bash
.claude/skills/review/review_checks.py <Suite>
```

The script reports:

- **Sources:**
  - a missing generator or testplan
  - stale generated tests
  - tests that reference a covergroup no coverpoint file defines
- **Suite type:**
  - a boot define that doesn't match the suite name
  - `RVTEST_TSBI_GOTO_MMODE` in a suite that boots to S or U
  - T-SBI calls in an unprivileged suite
  - legacy `RVTEST_GOTO_*` macros
- **Coverpoint text:** commented-out bins or coverpoints, and `ignore_bins` without a reason comment.
- **Guard names:** every `#ifdef`, `` `ifdef `` and `defined()` name that no config, header, or UDB parameter defines. These are likely typos.
- **UDB parameters:**
  - parameters defined by the suite's extension that the suite neither uses (`UDB_*`) nor maps in `coverpoints/param/<Suite>.yaml`
  - parameters it uses without mapping them
  - The script takes the parameter list from the pinned `udb` gem. To check against a riscv-unified-db checkout instead, pass `--udb-param-dir <udb>/spec/std/isa/param`. The canonical list is <https://github.com/riscv/riscv-unified-db/tree/main/spec/std/isa/param>; each YAML's `definedBy` names the extensions a parameter belongs to.
- **Normative-rule mapping:** entries in `coverpoints/norm/<Suite>.yaml` that point to coverpoints that don't exist, and the number of rules with no coverpoint.
- **Coverage:** covergroups below 100%.
- **Traps:**
  - any trap in an unprivileged suite
  - each config whose trap sequence (mode, cause, and testcase label) differs from `sail-rv32-max` or `sail-rv64-max`, with the first divergence

Every line is a lead to confirm in step 6, not a finding. `li`/`la` misuse is caught by prek, not by this script.

### 5. Static review

Read each layer, then check it against the layers before it:

1. **ISA manual:** read the whole chapters that define the feature from a riscv-isa-manual checkout (`src/unpriv/*.adoc`, `src/priv/*.adoc`); clone one with `git clone --depth 1` if needed. Where necessary, also read the parts of other chapters that affect the feature.
2. **Testplan:** `testplans/<Suite>.csv`, or the priv testplan YAML/CSV.
3. **Coverpoints:** the files the script lists, or the templates under `generators/coverage/src/covergroupgen/templates/` for unprivileged suites.
4. **Generator:** the file the script lists and any `*Common.py` it uses, or the coverpoint generators and formatters for unprivileged suites.
5. **Generated tests:** `tests/priv/<Suite>/` or `tests/rv*/<Suite>/`.
6. **Normative-rule mapping:** `coverpoints/norm/<Suite>.yaml`.
7. **CTP:** the matching `docs/ctp/src/*.adoc`.
8. **Configs**, where the PR touches them:
   - `config/*/ci.yaml` exclusions
   - the UDB yaml, `sail.json` and `run_cmd.txt` for each affected config

**Subagents.** When a suite has more than about 1,000 lines of generator plus coverpoints, or a PR touches several suites, split the review across parallel subagents:

- (a) spec vs testplan vs normative rules
- (b) coverpoints vs generator vs generated tests, taking the testplan as the statement of intent (so the manual is read only once)
- (c) runs, coverage and traps

Rules for the split:

- Only agent (c) builds or runs anything; parallel builds in one tree collide.
- Each agent gets the mechanical-check output and returns only its candidate findings.

### 6. Verify each finding

- For each potential problem, check critically whether it really breaks a rule. Unverified findings make reviews noisy.
- Confirm each finding by one of:
  - citing the spec text
  - running something
  - reproducing it in the generated test or the trace
- Before reporting a behavior as wrong, check that the spec doesn't allow it.
- Before reporting a failure, check whether it is already excluded in `ci.yaml` with a sensible issue link.
- Drop any finding that can't be verified, or label it as a question.

### 7. Report

- Write the report into the history file. Post to GitHub only when the user asks.
- Order the findings:
  1. **Blocking**
  2. **Should fix**
  3. **Fine for now, open an issue**
- Each finding gets:
  - a `file:line`
  - the rule or spec text it rests on
  - a concrete fix (a `suggestion` block if the fix is mechanical)
- Say when a comment applies everywhere ("Global comment"), so the author fixes every instance.
- Don't list routine checks that passed.

## What to check

### Overall

- **Testplan:**
  - It should exercise every feature the ISA manual describes, with reasonable crosses of whatever affects those features.
  - Flag missing features.
  - Do not test reserved instructions, CSRs/fields, or values, or UNSPECIFIED behavior.
- **Coverpoints:**
  - They cover the input stimulus for a testplan item, not the expected outputs. The outputs are checked by SIGUPDs or the trap signature.
  - Flag coverpoints with so many crosses that they produce many bins for little benefit, and suggest how to split them into simpler coverpoints that still exercise the testplan.
- **Tests:**
  - They align with the coverpoints.
  - Every result that could be wrong is detected, by a SIGUPD, the trap signature, or some other check.
  - Where the spec allows a discrete set of outcomes, the test checks that one of the legal outcomes happened.
- **Normative-rule mapping:** the coverpoints listed for a rule should reasonably exercise it. Several coverpoints are fine, but no more than about four. If more apply, list representative ones with a comment saying they are representative.
- **CTP:** it links to the suite's coverpoints and normative rules, and the links are correct.
- **Names:** consistent across testplan, coverpoints, generator, tests, mapping and CTP.
- **Robustness:** a test must pass on any legal DUT, not only the DUTs in CI. Watch for:
  - WARL fields legalizing one value into another
  - writes of illegal values to WLRL fields
  - writes that touch WPRI fields
  - state that changes eventually but not immediately, which the test must wait for before relying on it
- **Mistakes in `RVMODEL_*` macros** should be flagged, not left to produce wrong values.

### Suite types

- Every suite is one of M-mode, privileged, or unprivileged, and its name should match its type.
- Classify a suite by its boot define (`#define BOOT_TO_MMODE`, `BOOT_TO_SMODE`, `BOOT_TO_UMODE`, set via `extra_defines`). The script checks the define against the name.
- **M-mode suites** contain `BOOT_TO_MMODE`, so they start in M-mode.
  - They test features that rely on M-mode: code that runs mostly in M-mode, or behavior that depends on `m*deleg`, PMP, or M-mode interrupts not accessed through T-SBI.
  - Name: starts with `Sm`, ends with `Sm`, contains `PMP`, or otherwise names a feature that needs M-mode.
  - Only M-mode suites may use `RVTEST_TSBI_GOTO_MMODE`.
- **Privileged suites** contain `BOOT_TO_SMODE` or `BOOT_TO_UMODE`, so they start in that mode.
  - They test features that rely on S, U, or VS/VU mode, and possibly lower modes.
  - They use `RVTEST_TSBI_*` to reach CSRs or memory that need more privilege.
  - Name: starts with `Ss`, `Sv`, or `Su`, or ends with `S` or `U`.
  - They never contain `RVTEST_TSBI_GOTO_MMODE`.
- **Unprivileged suites** contain no `BOOT_TO_*MODE`.
  - They boot to the lowest available mode: U if it exists, M otherwise.
  - They test only features that don't need privileged access.
  - They contain no `RVTEST_TSBI_*` calls.
  - They access no CSRs except the F/V user-mode ones.
  - They never trap.

### Code and coverpoint style

Beyond `review-rules-jordan.md`:

- **Never use `li`:** different compilers can emit different instruction sequences, and then a DUT can't exactly match Sail.
- **State:** `RVTEST_BOOT_TO_*` initializes CSRs to a known state. Each test file must set up any other state it depends on.
- **Testcase labels:** each testcase has a label naming the bin, coverpoint and covergroup it targets. The label sits right before the instruction under test, so a failure points at it.
- **RV32/RV64:** one set of coverage files serves both.
- **Randomness:** seeded deterministically, so tests are reproducible.

### Normative rules

- Every normative rule related to the suite is listed in the mapping YAML.
- If a rule is missing and an existing coverpoint obviously covers it, recommend adding it.
- If a rule can't be covered within the scope of the ACTs (e.g. it needs memory with I/O PMAs, which DUTs aren't required to have), say why it isn't covered.
- Otherwise, leave the rule in the mapping with an empty coverpoint list (`coverpoint: [""]`) as a TODO.

### Parameters

Start from the script's parameter list. Each parameter falls into one of three kinds:

- **Trap-handler only:** it affects only trap-handler behavior.
- **Expected results only:** it works as long as the DUT and the reference model see the same value. Check that the UDB yaml and `sail.json` agree.
- **Whether a test runs at all:** it must appear in `#ifdef`s in both the tests and the coverpoints.

### Verification

- **Scope:** run every suite being reviewed or affected by the change.
- **Warnings and errors:** flag any that appear while building or running.
- **Coverage:** flag coverage below 100%. The missing bins are listed in `work/<config>/reports/<Suite>_uncovered.txt`.
- **Mismatches:**
  - Flag every test mismatch, unless it is in the config's `ci.yaml` with a link to a sensible issue against the DUT.
  - Each failing log names the first divergent testcase on its `bin:` line.
- **Traps:**
  - Compare the expected traps against the testplan. Flag traps the testplan doesn't expect, or that go against the spirit of the test.
  - A configuration whose expected traps differ from the others can point to an error in that config's UDB yaml or `sail.json`, even when the DUT matches.
