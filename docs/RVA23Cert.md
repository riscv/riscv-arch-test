# RVA23 Certification

RISC-V International is developing an RVA23 Certification Program. The program is not yet live, but a significant part of obtaining an RVA23 certificate will involve running the subset of ACTs relevant to the RVA23 profile. This page documents that process for those who would like to begin running RVA23 tests now.

The [RVA23S64 and RVA23U64](https://riscv.github.io/riscv-isa-manual/snapshot/spec/#_rva23_profiles) profiles define the supervisor and user-mode requirements to be an RVA23 processor. As described in these profile specifications,
compliance requires that the RV64I base instruction set and all mandatory extensions of the profile must be
implemented. Furthermore, any optional extensions as specified in the profile may be implemented. Any optional portions
of the base ISA and these extensions may be implemented, but if they are
implemented, they must be implemented in their entirety. The instruction set and extensions are defined in the [Ratified ISA Specifications](https://riscv.org/specifications/ratified/).

There is no prohibition against implementing other RISC-V ratified base ISAs or
extensions, custom extensions, or even non-conforming extensions as
long as they don't interfere with the proper functioning of the RVA23 mandatory
and implemented optional extensions. However, these other base ISAs and extensions are not part of RVA23 testing.

Remember that certification testing is not verification. Certification tests are intended to help check that you read and understood the specification, and to promote software interoperability. They do not probe for microarchitectural or logic bugs and are not a substitute for your own comprehensive verification suite.

The RVA23 profile does not specify machine-mode requirements for an RVA23 profile. The ACTs use a Test Supervisor Binary Interface (T-SBI) to abstract access to machine mode, facilitating testing of systems with non-standard machine mode. The ACTs come with a default T-SBI implementation that works for standard M-mode. If your system does not implement standard machine mode, consult the [Certification Requirements Document](https://github.com/riscv/riscv-arch-test/blob/act4/docs/crd/src/rva23_crd.adoc) for information about what your T-SBI must provide.

To run the RVA23 tests, follow the [Getting Started Guide](https://github.com/riscv/riscv-arch-test#getting-started) to install the toolchain, clone the ACT repository, and create configuration files for your Device Under Test. Then generate the tests and compile them into self-checking ELFs in `$WORKDIR/<config_name>/elfs` with:

`CONFIG_FILES=<your_config_directory>/test_config.yaml make CERTIFICATE=RVA23`

The `CERTIFICATE` argument limits the generated tests to those applicable to the certificate. In particular, it excludes machine-mode tests and extensions that are neither mandatory nor optional in the profile. Your UDB configuration must contain at least all of the mandatory extensions for the certificate.
You are highly encouraged to run without the `CERTIFICATE` argument as well, to more comprehensively test RISC-V features outside the certificate requirements.

Run all of the generated ELFs on your DUT. If all is well, each should display

```
RVCP-SUMMARY: TEST PASSED - Test File "<test_name.S>"
```

If not, consult the [Troubleshooting](https://github.com/riscv/riscv-arch-test#troubleshooting) tips.

Once the program is operational, anticipate that obtaining a certificate will involve

- registering at a RISC-V International certification portal
- signing a certification contract
- paying a certification fee
- uploading your configuration files
- receiving ELFs applicable to your configuration
- running the ELFS on your DUT
- uploading your log files for review

Successfully running the ACTs in your local environment is valuable to find errors, promote software compatibility, and ease the process of certification testing, but is not sufficient to obtain a certificate.
