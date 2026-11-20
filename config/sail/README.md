# ACT Configuration Files for Running Tests on RISC-V Sail Model

These configurations are not intended for running on a DUT.
The expected results come from the RISC-V Sail Model, so running those tests again on the RISC-V Sail Model is not going to find a bug in the simulator.
They are useful for debugging self-checking tests and are used to collect test coverage.

For `sail-RVA20S64`, `sail-RVI20U32`, and `sail-RVI20U64`, only required extensions are enabled by default. Optional extensions are commented out in each configuration's YAML file and can be enabled by uncommenting them (along with the matching entries in `sail.json`, and `STANDARD_SM_SUPPORTED` in `rvmodel_macros.h` when enabling `Zicsr`).
