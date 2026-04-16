# Test Memory Map

The test memory layout is divided into four linker sections, each aligned and ordered so that the DUT ELF and the reference-model ELF produce identical addresses for all test-visible symbols.

## Section Layout

The linker places the following output sections in order:

| Section                             | Permissions | Contents                                                                                                                                   |
| ----------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `.text.init`                        | R X         | Entry point (`rvtest_entry_point`), boot call, and jump to `.text.rvtest`.                                                                 |
| `.text.rvtest`                      | R X         | All test code: initialization, trap handlers, the test body, and failure-reporting code.                                                   |
| `.data` (aligned to 0x4000)         | R W         | All test data and the signature region (see below).                                                                                        |
| `.text.rvmodel` (aligned to 0x1000) | R X         | Out-of-line DUT-specific helpers (`rvmodel_boot`, `rvmodel_halt_pass`, etc.) and catch-all for remaining `.text`/`.text.*` input sections. |

Any additional DUT-specific data sections (such as `.tohost` for HTIF) are emitted via `.pushsection` in the RVMODEL macros and placed by the linker as orphan sections after `.text.rvmodel`.

`.text.rvmodel` must be a separate section that follows `.data` because the `RVMODEL` macros expand to different code sizes in the DUT build versus the Sail reference-model build. If this variable-size code were in `.text.rvtest` (before `.data`), the `.data` section would start at different addresses in the two ELFs. Because some tests write address-dependent values (e.g. `mtval`) into the signature, different `scratch` or `begin_signature` addresses cause signature mismatches. Placing all `RVMODEL` code after `.data` ensures that test code and test data have identical addresses in both builds.

## `.text.init` Section Layout

| Symbol / Region      | Purpose                                                                                                  |
| -------------------- | -------------------------------------------------------------------------------------------------------- |
| `rvtest_entry_point` | Entry point. Calls `rvmodel_boot` (in the `.text.rvmodel` section) then falls through to `.text.rvtest`. |

`.text.init` is intentionally kept in a separate output section so that `.align` directives in test code do not increase `.text.init`'s alignment and shift `rvtest_entry_point` to an unexpected address.

## `.text.rvtest` Section Layout

| Symbol / Region               | Purpose                                                                                                        |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `rvtest_init`                 | Trap prologs, PMP setup, and register initialization. **_ This is going to change with the new boot macros _** |
| `rvtest_code_begin`           | Start of the test body (signature pointer initialized here).                                                   |
| _(test code)_                 | The actual test, generated between `RVTEST_CODE_BEGIN` and `RVTEST_CODE_END`.                                  |
| `rvtest_code_end`             | End of the test body. Switches back to M-mode.                                                                 |
| `cleanup_epilogs`             | Trap epilogs (restore xTVEC, trampoline, and saved registers per mode).                                        |
| `exit_cleanup` / `abort_test` | Test termination paths (calls `rvmodel_halt_pass` or `rvmodel_halt_fail`).                                     |
| Trap handlers                 | One handler per privilege mode (`RVTEST_TRAP_HANDLER`).                                                        |
| Failure code                  | Failure detection and diagnostic reporting (`RVTEST_FAILURE_CODE`).                                            |

## `.text.rvmodel` Section Layout

| Symbol / Region        | Purpose                                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------------------- |
| `rvmodel_boot`         | DUT-specific boot code (`RVMODEL_BOOT`), I/O init (`RVMODEL_IO_INIT`), then jump to `rvtest_init`.        |
| `rvmodel_io_write_str` | Wrapper for `RVMODEL_IO_WRITE_STR`.                                                                       |
| `rvmodel_halt_pass`    | Wrapper for `RVMODEL_HALT_PASS`.                                                                          |
| `rvmodel_halt_fail`    | Wrapper for `RVMODEL_HALT_FAIL`.                                                                          |
| Interrupt helpers      | `rvtest_set_msw_int`, `rvtest_clr_msw_int`, `rvtest_set_mext_int`, etc. (when trap routines are defined). |

This section also acts as a catch-all for any remaining `.text` or `.text.*` input sections that might be provided by the DUT.

## `.data` Section Layout

Within the `.data` section, symbols are laid out in the following order (defined in [`tests/env/rvtest_setup.h`](../tests/env/rvtest_setup.h)):

| Symbol / Region                        | Purpose                                                                                                                                                                                     |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scratch`                              | Scratch memory for loads/stores not part of the signature. Pre-initialized with distinct marker values.                                                                                     |
| Trap save areas                        | One save area per privilege mode trap handler.                                                                                                                                              |
| `rvtest_data_begin`                    | Start of test specific data label.                                                                                                                                                          |
| _(test-specific data)_                 | Data defined by individual tests between `RVTEST_DATA_BEGIN` and `RVTEST_DATA_END`.                                                                                                         |
| Page tables                            | Root page tables for S-mode, H-mode, and VS-mode (when corresponding trap routines are defined).                                                                                            |
| Failure scratch & strings              | Scratch area for failure reporting, followed by diagnostic strings (`successstr`, `failstr`, etc.).                                                                                         |
| `rvtest_data_end`                      | End of test specific data label.                                                                                                                                                            |
| `begin_signature` / `rvtest_sig_begin` | Start of the signature region (aligned to 16 bytes).                                                                                                                                        |
| _(signature data)_                     | Main signature region written by test code via `RVTEST_SIGUPD`.                                                                                                                             |
| _(trap signature)_                     | Trap handler signature region (when `rvtest_mtrap_routine` is defined).                                                                                                                     |
| `end_signature` / `rvtest_sig_end`     | End of the signature region.                                                                                                                                                                |
| `RVMODEL_DATA_SECTION`                 | DUT-specific data defined in `rvmodel_macros.h` (e.g. `tohost`/`fromhost` for HTIF). May be empty. Placed last so variable-size DUT data does not affect any test-visible symbol addresses. |
