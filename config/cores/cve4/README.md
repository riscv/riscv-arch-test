<!--
Copyright (c) 2026 Eclipse Foundation
SPDX-License-Identifier: Apache-2.0
--->

## DUT Configuration for the CV32E40P

Three configurations are provided:

| Config                 | ISA      | Notes                                              |
| ---------------------- | -------- | -------------------------------------------------- |
| `cv32e40p-v1-rv32imc`  | RV32IMC  | v1.0.0 release                                     |
| `cv32e40p-v2-rv32imc`  | RV32IMC  | v1.8.3 release, logically equivalent to v1-rv32imc |
| `cv32e40p-v2-rv32imcf` | RV32IMCF | v1.8.3 release with FPU                            |

The differences (or lack thereof) between versions are explained in the
[CV32E40P User Manual (v1.8.3)](https://docs.openhwgroup.org/projects/cv32e40p-user-manual/en/latest/core_versions.html).
Both v1 and v2 IMC configs exist so that certification can be run against either RTL version.

To build the UDB configuration, coverage files and ELFs, run one of the following
commands from the top of your working copy of this repo:

```
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40p-v2-rv32imc/test_config.yaml
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40p-v2-rv32imcf/test_config.yaml
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40p-v1-rv32imc/test_config.yaml
```
