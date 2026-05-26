<!--
Copyright (c) 2026 Eclipse Foundation
SPDX-License-Identifier: Apache-2.0
--->

## DUT Configurations for the CVE4 Family

### CV32E40P

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

### CV32E40S

Four configurations are provided:

| Config                        | ISA      | Notes                              |
| ----------------------------- | -------- | ---------------------------------- |
| `cv32e40s-rv32imc`            | RV32IMC  | Base config, no PMA, no PMP        |
| `cv32e40s-rv32imc-pma`        | RV32IMC  | PMA enabled (1 region)             |
| `cv32e40s-rv32imc-pma-pmp`    | RV32IMC  | PMA and PMP enabled (16 entries)   |
| `cv32e40s-rv32imcb-pma-pmp`   | RV32IMCB | PMA and PMP enabled, B extensions  |

To build the UDB configuration, coverage files and ELFs, run one of the following
commands from the top of your working copy of this repo:

```
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imc/test_config.yaml
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imc-pma/test_config.yaml
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imc-pma-pmp/test_config.yaml
$ make -j$(nproc) CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imcb-pma-pmp/test_config.yaml
```
