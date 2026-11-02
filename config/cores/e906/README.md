<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
--->

# ACT Configuration for the XuanTie OpenE906

[OpenE906](https://github.com/T-head-Semi/opene906) is T-Head's open-source 32-bit, 5-stage
in-order microcontroller core. The configuration runs the `smart_run/` SoC testbench under
Verilator 5.052, pinned to `c5b8789`.

| Config                 | ISA                                   | Modes              |
| ---------------------- | ------------------------------------- | ------------------ |
| `e906-rv32imafc-u-pmp` | RV32IMAFC_Zicsr_Zifencei_Zicntr_Zihpm | M + U, 8 PMP, CLIC |

## Configuration as delivered

The release is generated RTL. `cpu_cfig.h` only sizes the caches, the branch history table and the
debug unit; everything else is fixed. The delivered options are:

- RV32IMAFC. F is single precision (`FPU_DOUBLE` is not defined). misa is `0x40901125`; the user
  manual gives `0x40901105`, without F.
- No P (DSP) extension: `DSP` is not defined, misa.P is 0, and no decoder matches the P opcode. The
  T-Head toolchain's `pzp64` option is for E906 builds that have one.
- 16 KB 2-way instruction and data caches with 32-byte lines (`ICACHE_16K`, `DCACHE_16K`); 8 Kbit
  BHT, 16-entry BTB and a 4-entry return stack; 8 PMP regions with a 128-byte grain; a CLIC with 128
  external interrupts; the debug module.
- mxstatus.MM resets to 1, so misaligned loads and stores are split in hardware.
- The caches, BHT, BTB and return stack reset disabled (mhcr = 0).
- The XuanTie custom instructions (cache maintenance, multiply-accumulate, indexed loads and
  stores, and the rest) raise illegal instruction while mxstatus.THEADISAEE is 0, its reset value.
  misa.X still reads 1. They are not ratified, so the UDB yaml does not claim them.
- The debug trigger CSRs (tselect, tdata1-3, tinfo, tcontrol) follow the debug specification
  0.13.2, not Sdtrig 1.0, so Sdtrig is not declared.

E906 implements privileged specification 1.11 without mstatush, menvcfg or mconfigptr, so `Sm` is
declared at 1.11.0.

## Testbench patch and build

- `setup-e906.sh` patches only the SoC testbench under `smart_run/logical`. It loads one image,
  `mem.pat`, into the instruction-bus SRAM; enlarges that SRAM from 256 KB to 1 MB, still with no
  wait states; prints the cycle count at the end; takes `MAX_RUN_TIME` and `LAST_CYCLE` from the
  Verilator command line; declares the `uart0_sout` net; skips the no-retire watchdog on cycle 0;
  and, with `+define+ACT_TRACE`, prints every retired PC. The core RTL is not changed.
- `install-e906.sh` verilates the testbench with `--timing`, because the vendor
  `smart_run/Makefile` supports only iverilog, VCS and irun, and the testbench uses delays, `wait`
  and `force`. It caps a test at 20 M cycles. The model runs at about 45,000 cycles per second, so
  the whole suite takes under a minute on 8 cores.

## Building and running

```bash
.github/scripts/install-e906.sh ~/e906-install
export PATH=~/e906-install/bin:$PATH
export E906_SNAPSHOT=~/e906-install/opene906/smart_run/work
make e906-rv32imafc-u-pmp
```

## Platform

- The core resets to address 0 and sends fetches, loads and stores below `0x2000_0000` to the
  instruction-bus SRAM, so tests link at 0. The top 4 KB, `0xF_F000`, is kept out of the image for
  the trap trampoline.
- The testbench prints the low byte of every store to `0x6000_FFF8` and ends the simulation when
  the stored word is `0xFFF` (pass) or `0xEEE` (fail).
- The system bus answers addresses outside its SRAM and APB windows with an error, so
  `RVMODEL_ACCESS_FAULT_ADDRESS` is `0x3000_0000`.
- Interrupts reach the core only through the CLIC, and mie and mip read 0, so the interrupt macros
  are undefined.
- `RVMODEL_BOOT` points mtvec at the trampoline, writes mhcr = `0x103F` (caches, write-back,
  write-allocate and branch prediction on, as the vendor startup code `crt0.s` does), and sets
  mhint.AEE so that load bus errors are precise.

## Deviations from the specifications

- mtvec.MODE is hardwired to 3 (CLIC mode). Exceptions go to BASE, which a write sets from bits
  31:6, so the configuration declares direct mode with 64-byte alignment, and the trap prolog copies
  its trampoline to the mtvec target.
- In CLIC mode mcause bits 29:27 alias mstatus.MPP and MPIE, so an M-mode trap reads
  `0x3000_000x`. Writing mcause also writes MPP and MPIE.
- mhpmcounter3-31 count and take writes only while their mhpmevent holds that counter's one event
  code, and mhpmevent accepts only 0 or that code. ACT never programs an event, so the yaml declares
  no HPM counters (`HPM_COUNTER_EN` all false).
- `ci.yaml` lists the suites that fail and why: fmin/fmax with a signaling NaN, FMA underflow,
  the mcause alias, imprecise store and LR bus errors, LR exception causes, mstatus.MPP and TW,
  minstret counting its own write and ECALL, and mret keeping MPRV (privileged 1.11 behavior that
  Sail does not model).

## UDB feature extractor

The UDB feature extractor (riscv-arch-test PR 2442) agrees with the yaml on every declared
extension. Its other differences, each checked by RTL reading or a directed probe, are kept:

- It reports Zcb, Smcsrind and Sdtrig. The Zcb encodings retire without effect (c.zext.b and c.mul
  leave rd unchanged), CSR 0x350 is the CLIC mclicbase and 0x351 traps, and the triggers are debug
  0.13.2 (see above).
- It reports TRAP_ON_EBREAK, TRAP_ON_ECALL_FROM_M and TRAP_ON_UNIMPLEMENTED_CSR as false because it
  expects mcause 3, 11 and 2, and gets them with the CLIC alias bits set (`0x3000_0003` and so on).
- It measures MTVEC_ILLEGAL_WRITE_BEHAVIOR as `retain`, but a write of `0x144` to mtvec reads back
  `0x143`: BASE takes bits 31:6 of any write, so the yaml says `custom`.
- It does not measure MTVEC_MODES, MTVEC_BASE_ALIGNMENT_DIRECT, MISALIGNED_LDST_EXCEPTION_PRIORITY,
  LRSC_MISALIGNED_BEHAVIOR, REPORT_VA_IN_MTVAL_ON_BREAKPOINT, PMA_GRANULARITY or
  PRECISE_SYNCHRONOUS_EXCEPTIONS, and assumes common values. The yaml's values come from the RTL
  and the user manual.
