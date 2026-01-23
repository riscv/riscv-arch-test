# CHANGELOG

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


Please note the header `WIP-DEV` is to always remain indicating the changes done on the dev branch.
Only when a release to the main branch is done, the contents of the WIP-DEV are put under a
versioned header while the `WIP-DEV` is left empty

## [0.12.2] - 2024-03-06
- Add Zfa support. (PR#60)
- Initial covergroups for Zvk* instructions (PR#61)

## [0.12.1] - 2024-02-27
- Fix test.yml

## [0.12.0] - 2024-02-22
- Update generator.py to take care of hard coded register testcases only if a hard coded register is assigned in the op_comb node of a coverpoint of an instruction.
- Add hardcoded register testcases to dataset.cgf and rv32im.cgf
- Define rs1_val_data for c.ldsp in imc.yaml
- Update "opcode" to "mnemonics" in the cgf files
- Delete main.yml 
- Update test.yml for CI
- Define rs1_val_data for instructions from zicfiss.cgf in template.yaml
- Add "warning" in the verbose definition
- Add unratified Zicfiss extension
- Add unratified Zicfilp extension
- Add corner case of division for division operations for RV64
- Fix csr_comb to write test information
- Add unratified Zaamo subcomponent of A extension
- Add unratified B extension
- Fix issues with csr_comb
- Minor fix in kslraw.u in rv32ip 
- Fix incorrect 'sig:' entry in aes32dsi in template.yaml
- Add sig and sz for instructions in template.yaml
- Minor change of rd definition in c.lui in rv32ec
- Minor fix in rv32i_k
- Add rs1_val_data, rs2_val_data, imm_val_data for instructions in template.yaml
- Comment xlenlim out of val_comb in rv32i_b, rv64i_b
- Fix the formats of leading_ones, leading_zeros, trailing_ones, trailing_zeros for instructions in rv32i_b, rv32e_b
- Add op_comb for instructions in rv32i_zcb
- Add rs1_val_data for instructions in imc.yaml
- Add op_comb and val_comb for instructions in rv32ic, rv64ic, rv32ec
- Add corner case of division for division operations for RV32
- Comment print statements out from generator.py
- Fix whitespaces on empty lines in yaml template files.
- Add unratified Zabha extension
- Add support for unratified Zcmop extension
- Add support for unratified Zimop extension
- Add missing coverage for hard coded register testcases
- Updated CONTRIBUTING.rst to capture the new git strategy adopted to follow a monthly release cadence.
- Add Zifencei, Bit Manipulation and Privilege tests cgf files for RV32E
- Add unratified Zacas extension
- Add support for standard Atomic(A) extension

## [0.11.1] - 2023-08-15
- Fixed hex values handling for K extensions
- Fixed set indexing error during opcomb gen
- Fixed whitespaces on empty lines in yaml template files.

## [0.11.0] - 2022-12-11
- Added support for csr_comb test generation

## [0.10.4] - 2023-03-28
- Adding Zicond support

## [0.10.3] - 2022-11-22
- Fixed canary definition

## [0.10.2] - 2022-10-20
- Fixed use of lowercase LI.
- Fixed correctval to ?? in comments. 
- Fixed sw to SREG for K tests.
- Added canaries and signature boundary labels.

## [0.10.1] - 2022-09-30
- Added support for evaluating derived fields for evaluating coverpoints using the instruction object class

## [0.10.0] - 2022-09-05
- Added support for bitmanip and crypto scalar coverpoint test generation

## [0.9.0] - 2022-08-25
- Added support for cross_comb coverpoint test generation

## [0.8.0] - 2022-08-08
- Added support for a distributed template database.
- Added generic mechanisms to generate data sections based on test instances.
- Update templates for floating point tests.
- Fix test generation and macros for floating point tests.

## [0.7.2]
- Fix errors related to global variables across processes.

## [0.7.1] - 2022-02-07
- Fixed mistune version for doc build.

## [0.7.0] - 2022-02-05
- Included support for pseudoinstructions

## [0.6.3] - 2022-03-14
- Read the vxsat.OV flag before updating signatures in TEST_PKRR_OP() macro
- Use RDOV() macro to read the vxsat.OV flag.

## [0.6.2] - 2022-03-15
- Added method to generate data patterns for bitmanip instructions.

## [0.6.1] - 2022-03-04
- Check the vxsat.OV flag for P-extension instructions that saturate their results.
- Correct test generation of P-extension instructions affected by the template.yaml ISA node change in 0.6.0.
- update SIGUPD macros to automatically adjust base and offset if offset gets too big

## [0.6.0] - 2022-01-27
- Add CGFs for B extensions.
- Modify ISA node in template.yaml to support multiple ISAs per instruction.

## [0.5.9] - 2021-12-20
- Add CGFs for P extensions
- Add support for P extension test generation

## [0.5.8] - 2021-10-21
- Updated and added bitmanip_real_world.py script to generate test with real world patterns.

## [0.5.7] - 2021-09-20
- Fix the generation of rv32ec/cswsp test

## [0.5.6] - 2021-09-19
- rvtest\_data section now includes 16 bytes of rotated versions of `0xbabecafe`

## [0.5.5] - 2021-09-10
- Add CGFs for F&D extensions
- Add support for F & D extension test generation
- Add support for test splitting based on number of macro instances
- Add macro based signature entry sizes

## [0.5.4] - 2021-09-02
- Updated logger to enable logging for API calls.

## [0.5.3] - 2021-08-12

- Update instruction format of aes32 and sm4 instructions for K extensions.
- Improve the coverage of S-boxes for sm4 instructions by setting overlap = "Y" in byte_count.

## [0.5.2] - 2021-08-09
- Fix sign of immediate value for branching instructions while filtering.
- Fix instruction generation while result shadowing.

## [0.5.1] - 2021-07-16
- Update the sample cgf for RV32E
- fix the generation of RV32E Tests

## [0.5.0] - 2021-05-27
- support for K extension and subextension instructions
- support for comments in coverpoints
- added std_op field in template.yaml to indicate is standard-instruction the pseudo op belongs to.
- added support for parsing #nosat in coverpoint which disables the solvers for the current resolution.
- added sample cgf files for rv64ik and rv32ik

## [0.4.5] - 2021-05-15
- Minor code restructure to support API calls.
- Fixes to include env files in pip package.

## [0.4.4] - 2021-02-23
- Added missing coverpoints for JALR
- fixed CI to run main.yml on pushes to master.
- added version check for PRs in test.yml

## [0.4.3] - 2021-02-23
- Updated CI to actions

## [0.4.2] - 2021-01-15
- Fixed header base_isa argument
- Change header configuration argument list
- Remove first empty line in assembler output
- Add header randomization argument

## [0.4.1] - 2020-12-13
- Fixed correctval generation for existing ops.
- Fixed signedness of operand values for m ext instructions.
- Added operation strings for m and c extensions.

## [0.4.0] - 2020-11-19
- Added base_isa as option in cli
- Added support for register set based on base isa.
- Reformatted output values in tests to be hex strings.
- change compliance_model to model_test

## [0.3.0] - 2020-11-18
- minor doc updates
- renamed compliance_test.h to arch_test.h
- added aliasing macros for v0.1 compliance framework
- split datasets and coverpoints into multiple cgfs
- support for multiple cgf as inputs
- added support for special datasets to relevant instructions
- adding explicit entry point label to all tests
- remove x2 as coverpoint in cswsp and csdsp

## [0.2.0] - 2020-11-10
- initial draft of CTG
- parallelization support added
- random solvers can be used
- support rv32/64imc instructions
- docs updated

## [0.1.0] - 2020-07025
- initial draft

