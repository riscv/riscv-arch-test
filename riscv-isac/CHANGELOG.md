# CHANGELOG

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Please note the header `WIP-DEV` is to always remain indicating the changes done on the dev branch.
Only when a release to the main branch is done, the contents of the WIP-DEV are put under a
versioned header while the `WIP-DEV` is left empty

## [WIP-DEV]
- Updating CONTRIBUTING.rst to capture the new git strategy adopted to follow a monthly release
  cadence.
- Add pluggy to install\_requires and move pytest to tests\_requirements.txt
- Added `pmpaddr0` to `pmpaddr15` registers for coverage of Physical Memory Protection
- Minor fix to compressed immediate decoding and compressed register decoding
- Modified the regular expression to correctly match and return 'reg_commit' for registers x1 to x9.
- Changed compressed immediate decoding and added comments for readability

## [0.18.0] - 2023-07-26
- Add support to decode compressed instructions

## [0.17.0] - 2022-10-25
- Improve data propagation reports to capture multiple signature updates per coverpoint
- Add a CLI flag to explicitly log the redundant coverpoints while normalizing the CGF files

## [0.16.1] - 2022-10-20
- Fix length of commitval to 32 bits if flen is 32 for f registers in sail parser.

## [0.16.0] - 2022-09-28
- Refactored the instruction object class

## [0.15.0] - 2022-08-25
- Added support for instruction aliases

## [0.14.0] - 2022-08-08
- Add fields to instruction object
- Enable generic coverage evaluation mechanisms for floating point instructions
- Fix coverpoint generation to account for nan boxing of fp instructions.
- Add fields(frm, fcsr, nan_prefix) for fp instructions

## [0.13.2] - 2022-05-23
- Error reporting for missing coverlabel in cgf file

## [0.13.1] - 2022-05-07
- Fix mistune version for doc builds.

## [0.13.0] - 2022-05-02
- Covergroup format revised.
- Added support for Pseudoinstructions for coverage computation.

## [0.12.0] - 2022-04-15
- Parallelized coverage computation.
- Added feature to remove coverpoints when hit.
- Added CLI option to specify number of processes to be spawned.
- Added CLI option to turn on/off feature to remove hit coverpoints.

## [0.11.0] - 2022-04-03
- Added plugins to use new rvopcode format
- Added CLI option to setup rvopcode plugin

## [0.10.2] - 2022-03-15
- Added method to generate data patterns for bitmanip instructions

## [0.10.1] - 2022-02-10
- Added vxsat to supported csr_regs
- Added comments to coverpoint functions for P-ext
- Removed unused tuple type for bit_width parameters in P-ext coverpoint functions

## [0.10.0] - 2022-01-27
- Added support for instructions from B extension.
- Bug fix for bgeu instruction.

## [0.9.0] - 2022-01-07
- Added support for P extension cover point generation and instruction decoding.
- Allowed an instruction to generate results in multiple registers.

## [0.8.0] - 2021-10-30
- Added cross combination coverage support.

## [0.7.3] - 2021-09-02
- Updated logger to enable logging for API calls.

## [0.7.2] - 2021-08-18
- Added decoding support for K extension instructions based on latest spec

## [0.7.1] - 2021-08-12
- Bug fix for error while using byte_count with overlap = Y.

## [0.7.0] - 2021-08-11
- Adding support for floating point extension coverpoints
- Bug fixes for instruction decoder and improved pretty printing.
- fix for uninitialized total_categories variable in coverage.
- fixed CONTRIBUTING.rst file

## [0.6.6] - 2021-08-03
- Bug fix for error while decoding instruction name

## [0.6.5] - 2021-07-14
- Bug fix for error while generating Data Propagation Report.

## [0.6.4] - 2021-07-08
- Added support for CSR coverage and its architectural state
- Updated the merge function to support multiprocessing 
- Added a parameter '-p' ( number of processes ) in merge command 
- Documentation update for CSR coverpoints
- Return value of parsers changed from 5 independent values (hexcode, addr, reg commmit, csr commit, mnemonics) to instruction object updated with these values
- Argument of decode and all decoding functions (in internaldecoder) changed from hexcode and addr to instruction object

## [0.6.3] - 2021-06-24
- Documentation updates to reflect plugin usage.
- Minor bug fixes in coverage reporting.
- Improved CLI help messages.

## [0.6.2] - 2021-06-15
- Added parser plugins for sail and spike 
- Added decoder plugin
- Added arguments in main.py for custom plugin paths and names.

## [0.6.1] - 2021-06-11
- Added initial support for F extension coverpoints based on IBM models.
- Added support for F extension architectural state
- Fixed author information and repo link in setup.py

## [0.6.0] - 2021-05-27
- added support in parsers for K-scalar crypto instructions
- added support for abstract functions: uniform random, byte-count, leading-ones, leading-zeros,
  trailing-ones, trailing-zeros
- now maintain a separate list of instructions which require unsigned interpretation of rs1 and rs2.
- restructured coverage report handling to preserve comments throughout processing and merging.
- switched yaml to a round-trip parser for preserving comments

## [0.5.2] - 2021-02-23
- Moved ci to github actions
- fixed links in docs

## [0.5.1] - 2020-12-14
- Fixed operand signedness for m ext ops.

## [0.5.0] - 2020-11-18
- added support to take multiple cgf files as input. The order matters
- added support for abstract function of special dataset 

## [0.4.0] - 2020-11-10
- added special data set for r-type instructions
- fixed data propagation report generation and templates
- using classes to manage architectural state and statistics
- updated docs

## [0.3.1] - 2020-10-26
  - use logger instead of log in coverage.py


## [0.3.0] - 2020-10-26
- Adding support for Data propagation report generation
- Added 'sig-label' as the new cli option under coverage to capture DP reports
- Added support in sail parsers to extract mnemonics also from the trace file
- added pytablewriter as part of the requirements

## [0.2.0] - 2020-10-23
- Added documentation for CGF and usage
- Added normalization routine as cli
- Added abstract functions
- using click for cli
- adding parsers for sail and spike
- added support for filtering based on labels
- added merge-reports cli command


## [0.1.0] - 2020-06-25
- initial draft
