<!--
Copyright (c) 2026 Eclipse Foundation
SPDX-License-Identifier: Apache-2.0
--->

## DUT Configuration for the CV32E40P

Three configurations are provided:

| Config                     | ISA      | Notes                                                  |
| -------------------------- | -------- | ------------------------------------------------------ |
| `cv32e40p_v1.0.0_rv32imc`  | RV32IMC  | Original v1.0.0 release                                |
| `cv32e40p_v1.8.3_rv32imc`  | RV32IMC  | Latest release, logically equivalent to v1.0.0_rv32imc |
| `cv32e40p_v1.8.3_rv32imcf` | RV32IMCF | Latest release with FPU (F + Zcf)                      |

This specific behavior and the rules governing the differences (or lack thereof) between these versions are explained in the [CV32E40P User Manual (v1.8.3)](https://docs.openhwgroup.org/projects/cv32e40p-user-manual/en/latest/core_versions.html). Both configs exist so that certification can be run against either RTL version.

To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:

```
$ make -j$(nproc) CONFIG_FILES=config/cores/cv32e40p/cv32e40p_v1.8.3_rv32imc/test_config.yaml
```
