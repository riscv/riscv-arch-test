# CV32E40S RV32IMC — ACT4 Configuration

**Status:** Stub — parameters not yet verified.

CV32E40S is a security-hardened variant of CV32E40P (CORE-V, OpenHW Group).
RV32IMC + Smepmp + U-mode. RTL pinned to `103056f0`.

## Usage

```
uv run act config/cores/cv32e40s/cv32e40s_rv32imc/test_config.yaml --extensions I
```

## TODO (before running tests)

- [ ] Verify `sail.json`: `impid`, HPM counter config, mtval behavior, PMP count
- [ ] Verify `rvtest_config.h`/`.svh`: `RVMODEL_NUM_PMPS` (default param is 0, set to 16 for Smepmp)
- [ ] Verify `rvmodel_macros.h`: HTIF/CLINT addresses match simulation environment
- [ ] Verify `link.ld`: boot address `0x00000080` matches testbench `boot_addr_i`
- [ ] Add Smepmp + U-mode to `cv32e40s_rv32imc.yaml` `implemented_extensions`
- [ ] Fill `cv32e40s_rv32imc.yaml` parameter stubs from RTL source

## Key RTL values confirmed

| Field | Value | Source |
|-------|-------|--------|
| `marchid` | 0x15 (21) | `rtl/include/cv32e40s_pkg.sv:599` |
| `mvendorid` | 0x602 (1538) | `rtl/include/cv32e40s_pkg.sv:595-596` |
| `mimpid` | TBD | supplied via `mimpid_i` port |
| `PMP_NUM_REGIONS` | 0 (default) | `rtl/cv32e40s_core.sv:45` |
