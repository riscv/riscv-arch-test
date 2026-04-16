# Test Memory Map

The test memory layout is divided into four linker sections, each aligned and ordered so that the DUT ELF and the reference-model ELF produce identical addresses for all test-visible symbols.

The test memory map has several requirements:

- Place the beginning of the test code at the right place (usually the reset vector, unless the DUT has a separate boot loader)
- Ensure that the addresses of the test code body are the same when running it on the RISC-V Sail model to produce expected results and on a DUT to check against the expected results.
- Ensure the addresses of test data are the same when running on the RISC-V Sail model and on a DUT so expected results do not differ for address-dependent results.

The second requirement is subtle. The program is compiled twice, once to run on the RISC-V Sail model to produce an expected signature (the results), and once to run on a DUT to check against the expected signature. The `RVMODEL` macros may differ between the Sail model and DUT because the two targets might use different methods of printing to the console, terminating a simulation, etc.

The address of the test code body (the part that tests a feature and checks expected results) must be the same because some instructions (such as `auipc`) produce an expected result that depends on the address. Moreover, instructions that trap record the trap address in `xepc`, which should match on the Sail model and the DUT. Therefore, the `RVMODEL` macros cannot be called directly in the test code body because they might expand to different sizes for Sail vs. the DUT. Instead, they go in a different section placed after the test code body and are called from the test body via `jal`.

Some instructions (such as AMOs) may use the address of the scratch region of memory as part of the result, so the `.data` section must have constant addresses between the Sail model and DUT as well.

## Section Layout

The linker places the following output sections in order:

| Section                             | Permissions | Contents                                                                                                                                   |
| ----------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `.text.init`                        | R X         | Entry point (`rvtest_entry_point`), boot call, and jump to `.text.rvtest`.                                                                 |
| `.text.rvtest`                      | R X         | All test code: initialization, trap handlers, the test body, and failure-reporting code.                                                   |
| `.data` (aligned to 0x4000)         | RWX         | All test data and the signature region (see below).                                                                                        |
| `.text.rvmodel` (aligned to 0x1000) | R X         | Out-of-line DUT-specific helpers (`rvmodel_boot`, `rvmodel_halt_pass`, etc.) and catch-all for remaining `.text`/`.text.*` input sections. |

Any additional DUT-specific data sections (such as `.tohost` for HTIF) are emitted via `.pushsection` in the RVMODEL macros and placed by the linker as orphan sections after `.text.rvmodel`.

`rvtest_entry_point` is the first symbol in the `.text.init` section (which is the first section), so its address is set to the starting address specified in the linker script with `. = 0x...`. For most DUTs, this should be set to the reset vector of your processor and will be the only think in the linker script that needs to be customized. Advanced users can set the starting address to a different address, run a custom bootloader, and then jump to `rvtest_entry_point` to start the test.

Additional details on what each section contains and why each section is needed are provided below.

## `.text.init` Section Layout

| Symbol / Region      | Purpose                                                                                                  |
| -------------------- | -------------------------------------------------------------------------------------------------------- |
| `rvtest_entry_point` | Entry point. Calls `rvmodel_boot` (in the `.text.rvmodel` section) then falls through to `.text.rvtest`. |

`.text.init` is intentionally kept in a separate output section so that `.align` directives in test code do not increase `.text.init`'s alignment and shift `rvtest_entry_point` to an unexpected address. For example, [CV32E20](../config/cores/cve2/cv32e20/link.ld) has a reset vector of 0x4000 (`. = 0x00004000` in the linker script). Some tests (e.g. `I-jal-00`) have large `.align` directives (`.align 14`). Output sections are aligned to the maximum internal alignment of all input sections, so if the test code was in the same section as the entry point, then the entry point would need to be aligned to 16K and the CV32E20 reset vector would not line up.

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

`.text.rvtest` contains all of the actual test code that is common across all DUTs. For any DUT-specific operations, the DUT jumps to a function in the `.text.rvmodel` section to ensure the `.text.rvtest` section remains constant length.

## `.data` Section Layout

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

All addresses in the `.data` section are constant and DUT-independent except for the contents of `RVMODEL_DATA_SECTION`, which is why it is placed last. This ensures the rest of the `.data` section has addresses that are the same for both the reference model and DUT.

## `.text.rvmodel` Section Layout

| Symbol / Region        | Purpose                                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------------------- |
| `rvmodel_boot`         | DUT-specific boot code (`RVMODEL_BOOT`), I/O init (`RVMODEL_IO_INIT`), then jump to `rvtest_init`.        |
| `rvmodel_io_write_str` | Wrapper for `RVMODEL_IO_WRITE_STR`.                                                                       |
| `rvmodel_halt_pass`    | Wrapper for `RVMODEL_HALT_PASS`.                                                                          |
| `rvmodel_halt_fail`    | Wrapper for `RVMODEL_HALT_FAIL`.                                                                          |
| Interrupt helpers      | `rvtest_set_msw_int`, `rvtest_clr_msw_int`, `rvtest_set_mext_int`, etc. (when trap routines are defined). |

This section also acts as a catch-all for any remaining `.text` or `.text.*` input sections that might be provided by the DUT.

`.text.rvmodel` must be a separate section at the end of the test that follows `.data` because the `RVMODEL` macros expand to different code sizes in the DUT build versus the Sail reference-model build. If this variable-size code were in `.text.rvtest` (before `.data`), the `.data` section would start at different addresses in the two ELFs. Because some tests write address-dependent values (e.g. `mtval`) into the signature, different `scratch` or `begin_signature` addresses cause signature mismatches. Placing all `RVMODEL` code after `.data` ensures that test code and test data have identical addresses in both builds.
