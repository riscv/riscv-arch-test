## DUT Configuration for the CV32A65X
The following configuration is provided for the CVA6 core in its 32-bit application-class setup:
| Config     | ISA                               | Notes                                          |
| ---------- | --------------------------------- | ---------------------------------------------- |
| `cv32a65x` | RV32IMC_Zicsr_Zcb_Zba_Zbb_Zbc_Zbs | Formal release version of the CVA6 32-bit core |

This configuration implements a 6-stage in-order, single-issue pipeline compliant with the RISC-V Privileged Architecture v1.13 (Machine-mode only). The specific architectural features, supported exceptions, and parameters for this core version are detailed in the [CV32A65X Design Document](https://docs.openhwgroup.org/projects/cva6-user-manual/04_cv32a65x/design/design.html). This configuration is intended for high-confidence validation using the ACT 4.0 framework.

To build the UDB configuration, coverage files and ELFs run the following command from the top of your working copy of this repo:
```
$ make CONFIG_FILES=config/cores/cva6/cv32a65x/test_config.yaml
```
## DUT Configuration for the CV64A60AX
The following configurations are provided for the CVA6 core in its 64-bit application-class setup:

| Config                 | Notes                                                       |
| ---------------------- | ----------------------------------------------------------- |
| `cv64a60ax`            | RVB23S64 baseline config for the CVA6 64-bit core           |

**ISA (`cv64a60ax`):** RV64IMAFDCB_Zicsr_Zicntr_Zicond_Zifencei_Zihpm_Zaamo_Zalrsc_Zca_Zcd_Zcb_Zba_Zbb_Zbs_Sscounterenw_Sstvala_Sstvecd_Ssu64xl_Sv39_Svbare

The `cv64a60ax` configuration implements a 6-stage in-order, single-issue pipeline compliant with the RISC-V Privileged Architecture v1.13. The supported extensions and parameter values are derived from the RTL configuration in [cv64a60ax_config_pkg.sv](https://github.com/openhwgroup/cva6/blob/master/core/include/cv64a60ax_config_pkg.sv) and cross-referenced with the [CVA6 User Manual](https://docs.openhwgroup.org/projects/cva6-user-manual/01_cva6_user/index.html) and the CVA6 Profile Analysis. Some parameters remain pending confirmation from the CVA6 team.

To build the UDB configuration, coverage files and ELFs for the baseline config:
```
$ make CONFIG_FILES=config/cores/cva6/cv64a60ax/test_config.yaml
```

