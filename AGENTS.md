# AGENTS.md

## Communication

- Use clear, concise language. Keep sentences short and direct.
- Explain RISC-V behavior with precise architectural terms. Separate specification requirements from project conventions.
- Add comments only when the code is not clear without them. Describe what the code does, not the history of a change.
- Keep changes focused. Do not add speculative abstractions or unrelated refactors.
- Keep PR descriptions short and direct. State what changed and why. Do not add large summary or validation sections, and do not list routine checks unless something unusual occurred.

## Repository

- This repository implements ACT4. It generates RISC-V architectural certification tests and builds self-checking ELFs with expected signatures from a reference model.
- Python is a `uv` workspace with three packages: `framework/` provides `act`, `generators/testgen/` provides `testgen`, and `generators/coverage/` provides `covergroupgen`.
- Files under `tests/` and generated parts of `coverpoints/` can be generated but checked in. Do not edit generated files directly. Change `testplans/`, generators, or templates, run `make tests`, and commit the tracked generated results.
- `work/` contains build output. `make clean` removes most artifacts but preserves `extensions.txt` and `.validated` files.
- Configurations are under `config/`. A directory with `run_cmd.txt` creates Make run targets for its directory name and each ancestor name, such as `make spike-rv64-max`, `make spike`, and `make cores`.

## Tooling

- Prefer `mise`; `.mise.toml` pins `uv`, Ruby, Bundler, and `prek`.
- Use `uv run` or Make targets for Python commands. Do not use bare `python` or `pip`.
- Keep Python compatible with 3.10. CI tests the oldest supported version.
- UDB Ruby dependencies are in `framework/src/act/data/Gemfile*`. The first ACT/UDB run can install them.
- Python must pass Ruff and Pyright. Ruff uses a 120-character line length. Pyright uses standard mode.
- `.editorconfig` uses two spaces by default, four spaces for Python, and tabs for Make recipes.
- Use `mise run prek-install` to install hooks and `mise run prek` to run all hooks.
- Add an SPDX license header to new source files.

## Common Commands

- `make help`: list supported targets and variables.
- `make tests`: generate assembly tests and coverpoints without compiling them.
- `make`: generate tests and build ELFs for the default Spike RV32 and RV64 configurations.
- `CONFIG_FILES=config/cores/<vendor>/<config>/test_config.yaml make`: build tests for one DUT configuration.
- `make <config-target>`: build and run one or more configurations discovered from `run_cmd.txt`.
- `EXTENSIONS=I,M make tests` or `EXTENSIONS=I make <config-target>`: restrict work to selected suites. `EXCLUDE_EXTENSIONS=Sm` applies a negative filter.
- `FAST=True make`: omit objdump output. `DEBUG=True make EXTENSIONS=<suite>`: emit signature objdumps, reference-model traces, and trap reports. `VERBOSE=True` also serializes the build.
- Let the project select parallelism for normal work. Use `JOBS=1` only to debug a hang or another parallel execution problem.
- `make coverage EXTENSIONS=<suite>`: run focused coverage. Full `make coverage` is expensive.
- Build CTP or CRD documentation from its directory. The builds use the `docs/docs-resources` submodule and Docker unless `SKIP_DOCKER=true`.

## Test Development

- Unprivileged tests use `testplans/<suite>.csv`, coverpoint templates under `generators/coverage/src/covergroupgen/templates/`, and generators under `generators/testgen/src/testgen/coverpoints/`.
- Privileged test generators are under `generators/testgen/src/testgen/priv/extensions/`. They write assembly under `tests/priv/`. Handwritten privileged functional coverage is under `coverpoints/priv/`.
- A testcase checks one coverpoint bin. A `TestChunk` is an unsplittable group of testcases. A test file is one `.S` or `.c` file. A test suite is one extension directory.
- Test headers are strict YAML between `START_TEST_CONFIG` and `END_TEST_CONFIG`. Supported keys are `REQUIRED_EXTENSIONS`, `FORBIDDEN_EXTENSIONS`, `MARCH`, `NEEDS_SIGNATURE`, `MIN_HARTS`, and `params`. Unknown keys fail validation.
- CSV columns start with `Instruction`, `Type`, `RV32`, and `RV64`, followed by coverpoints. `Type` must name a registered formatter. Coverpoint columns must name registered generators. Use `testplans/I.csv` as a reference.
- Registry modules are discovered automatically. Use the registry decorators and do not add manual imports. Files with names that start with `_` are not discovered.

| Subsystem              | Decorator                                    | Directory                                          |
| ---------------------- | -------------------------------------------- | -------------------------------------------------- |
| Coverpoint generators  | `@add_coverpoint_generator("cp_name")`       | `generators/testgen/src/testgen/coverpoints/`      |
| Instruction formatters | `@add_instruction_formatter("TYPE", config)` | `generators/testgen/src/testgen/formatters/types/` |
| Privileged generators  | `@add_priv_test_generator("Suite", ...)`     | `generators/testgen/src/testgen/priv/extensions/`  |

- Keep expected architectural behavior explicit. Each generated testcase must map to meaningful functional coverage.
- The framework installs trap handlers for unprivileged tests when standard machine mode is available. Unexpected traps fail the test.
- Privileged tests should boot into their intended mode. Use T-SBI calls for operations that require a higher privilege level. Use `tsbi_call()` for supported CSR or memory instructions and `RVTEST_TSBI_GOTO_*` for mode changes.
- Allocate registers through `TestData` register allocators. Do not hard-code or separately exclude registers already reserved by the framework. Framework routines and T-SBI can clobber `ra` and `a0` through `a2`.
- In generated assembly, use Python loops to emit repeated code. Avoid assembly loops so testcase labels and debug strings stay unique.
- Do not use the target-dependent `.align` directive in assembly. Use `.p2align` or `.balign`.
- Do not use the `la` or `li` pseduoinstructions. Use the `LA()` and `LI()` macros.
- Do not hand-edit `framework/src/act/fcov/coverage/RISCV_imported_decode_pkg.svh`; it is generated from `riscv-opcodes`.

## Configurations And CI

- `test_config.yaml` references the UDB configuration, linker script, DUT include directory, compiler, and reference model. Paths are relative to `test_config.yaml`.
- Audit every field copied from another DUT. The UDB configuration, `sail.json`, linker script, and DUT behavior must agree. For example, mismatched `mtvec` modes or alignment can break trap-handler setup.
- Use a nonzero `TEST_BASE`. If a DUT starts at address zero, use a runner boot stub to jump to the test image.
- Keep `.text.rvmodel` after `.data` in linker scripts. Otherwise, DUT and reference-model ELFs can assign different addresses to test data. If the ELF base changes, update the memory map in `sail.json`.
- `run_cmd.txt` contains one command. `run_tests.py` appends the ELF path. Use `{debug:...}` for debug-only arguments, `__TRACEFILE__` for a separate trace, and `__SUMMARYFILE__` for redirected console summaries.
- CI discovers matrices from `config/*/ci.yaml` and `run_cmd.txt`. Run `make tests` before `.github/scripts/ci_config.py` because generated tests determine shard weights.
- CI verifies that checked-in generated files under `tests/` and `coverpoints/` match their generators.
- Branch from and target `act4`. Documentation release workflows also use `act4`.

## Before Committing

- Run `mise run prek` and fix all failures. Some hooks modify files, so inspect the result.
- Run the narrowest relevant regression. For test or generator changes, build and run the affected suite with `EXTENSIONS=<suite> make <config-target>`. For coverage changes, use `make coverage EXTENSIONS=<suite>`.
- Use `make regression` for broad framework or configuration changes when the required simulators are available.
- After generator or testplan changes, run `make tests` and inspect the tracked generated diff.
- Check that changed documentation builds.

## Debugging

- Run summaries are in `work/<config>/summary.log`. Simulator logs are in `work/<config>/logs/`.
- Passing tests print `RVCP-SUMMARY: TEST PASSED - Test File "<test_name>"`. Failures print `TEST FAILED`. `SIGRUN` means the ELF is not self-checking.
- `DEBUG=True` adds `.sig.elf.objdump`, `.sig.log`, and `.sig.trap_report` files under `work/<config>/build/`.
- Triage failures in this order: UDB and DUT configuration, reference-model configuration, generated objdump and trace, then DUT behavior.
- By default, ACT stops after the first failed build task and cancels active tasks. The `succeeded` value counts DAG tasks, not tests. Use `-k` to continue independent tasks.
- To test one suite across simulators, use `EXTENSIONS=<suite> DEBUG=True make -k sail spike whisper qemu imperas cvw`. Each failing simulator log names the first divergent testcase on its `bin:` line.
- Simulator (not RTL) tests normally finish in seconds. If they run for much longer, inspect the simulation for a hang.
