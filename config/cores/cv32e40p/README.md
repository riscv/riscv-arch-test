<!--
Copyright (c) 2026, OpenHW Foundation
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E40P

Three configurations are provided:

| Config | ISA | Notes |
|--------|-----|-------|
| `cv32e40p_v1.0.0_rv32imc` | RV32IMC | Original v1.0.0 release |
| `cv32e40p_v1.8.3_rv32imc` | RV32IMC | Latest release, integer-only |
| `cv32e40p_v1.8.3_rv32imcf` | RV32IMCF | Latest release with FPU (F + Zcf) |

v1.0.0 and v1.8.3 (without FPU) should behave identically for integer
instructions. The v1.8.3 release added the optional FPU and PULP custom
extensions but did not change the base RV32IMC behavior. Both configs
exist so that certification can be run against either RTL version.

The v1.8.3 IMCF config adds the F extension and Zcf (compressed
floating-point loads/stores), which requires the FPU parameter enabled
at synthesis.

To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:

```
$ make -j$(nproc) CONFIG_FILES=config/cores/cv32e40p/cv32e40p_v1.8.3_rv32imc/test_config.yaml
```
