# ACT4 Configuration: StarFive VisionFive 2

> **Status: Work In Progress** — Tracking issue [#1306](https://github.com/riscv/riscv-arch-test/issues/1306)

This directory provides an ACT4 framework configuration for running
RISC-V Architecture Compliance Tests (ACT) on the **StarFive VisionFive 2**
single-board computer (SBC) using its JH7110 SoC.

---

## Board Overview

| Property | Detail |
|---|---|
| **Board** | StarFive VisionFive 2 |
| **SoC** | JH7110 (StarFive) |
| **ISA** | RV64GC (+ Zba, Zbb, Zbs, Sv39, Sv48) |
| **DRAM** | 4 GB or 8 GB LPDDR4, base at `0x40000000` |
| **UART** | NS16550-compatible UART0 at `0x10000000` |
| **Boot** | SPL → OpenSBI (M-mode) → U-Boot → ELF |

---

## Key Design Decision: M-Mode Ownership

OpenSBI claims M-mode at boot time on this board. All software running
after OpenSBI (including our ACT ELFs launched via `go`) runs in **S-mode or U-mode**.

Therefore, `test_config.yaml` sets:
```yaml
include_priv_tests: false
```

This excludes:
- `Sm` (M-mode exception/interrupt tests)
- `ExceptionsSm`, `InterruptsSm`
- Any test requiring direct CLINT access

All other ACT tests (I, M, A, F, D, C, B, S-mode, U-mode) run normally.

---

## File Structure

```
config/cores/starfive/visionfive2/
├── README.md               ← This file
├── test_config.yaml        ← ACT4 framework settings
├── visionfive2-rv64gc.yaml ← UDB architecture description (JH7110)
├── rvmodel_macros.h        ← DUT-specific macros (UART, HALT, tohost)
├── rvtest_config.h         ← Supported extension flags (for C preprocessor)
├── rvtest_config.svh       ← SystemVerilog coverage config
├── sail.json               ← Sail reference model memory map config
└── link.ld                 ← Linker script (ELFs at 0x42000000)
```

---

## Memory Map Used

| Region | Base Address | Size | Notes |
|---|---|---|---|
| OpenSBI firmware | `0x40000000` | 2 MB | Do not overwrite |
| U-Boot | `0x40200000` | ~1 MB | Temporary; reclaimed after `go` |
| **ACT ELF load address** | **`0x42000000`** | up to 64 MB | Load tests here |
| UART0 (NS16550) | `0x10000000` | 64 KB | PASS/FAIL output |
| CLINT | `0x02000000` | 64 KB | Managed by OpenSBI |

---

## How `RVMODEL_HALT_PASS` / `RVMODEL_HALT_FAIL` Work

On this platform, there is no host-side process polling the `tohost` symbol.

The current implementation:
1. Writes to the `tohost` symbol in DRAM (value `1` for pass, `3` for fail) — kept for
   compatibility with any future host-side polling via `/dev/mem`.
2. Spins in an infinite loop (the ACT framework has already printed `RVCP-SUMMARY:` over
   UART before calling halt).

**UART output format** (printed by the ACT framework automatically):
```
RVCP-SUMMARY: TEST PASSED - Test File "add-01.S"
```
or
```
RVCP-SUMMARY: TEST FAILED - Test File "add-01.S"
```

A host script on the UART-connected PC collects these lines and produces a summary.

---

## Prerequisites

### On the VisionFive 2 (U-Boot prompt)

No special setup needed. U-Boot is used purely as an ELF loader.

### On the build host (Linux / WSL2)

```bash
# RISC-V toolchain
sudo apt install gcc-riscv64-unknown-elf

# Or use the prebuilt toolchain from riscv-collab
# https://github.com/riscv-collab/riscv-gnu-toolchain/releases

# ACT4 framework
pip install act4   # or follow README.md in repo root
```

---

## Building ACT ELFs

```bash
cd /path/to/riscv-arch-test

# Generate and compile tests for VisionFive 2
act --config config/cores/starfive/visionfive2/test_config.yaml

# ELFs are placed in: work/visionfive2-rv64gc/elfs/
```

---

## Running Tests on Hardware

### Step 1: Transfer ELF to VisionFive 2

**Via TFTP (recommended):**
```bash
# On build host — serve the ELF directory
python3 -m http.server 8080 --directory work/visionfive2-rv64gc/elfs/
```

**Via SD card:** Copy ELFs to the FAT partition of the boot SD card.

### Step 2: Load and Run from U-Boot

```
# In U-Boot serial console:
VF2# setenv loadaddr 0x42000000
VF2# tftpboot ${loadaddr} add-01.elf
VF2# go ${loadaddr}
```

or from SD card:
```
VF2# fatload mmc 0:3 ${loadaddr} add-01.elf
VF2# go ${loadaddr}
```

### Step 3: Collect Results

Monitor the UART console (115200 baud, 8N1) for `RVCP-SUMMARY:` lines.

A helper script to automate result collection is planned. See issue [#1306](https://github.com/riscv/riscv-arch-test/issues/1306).

---

## Running All Tests (Batch Mode)

A wrapper script will be added to iterate over all ELFs automatically.
The planned workflow:

```bash
# Future: automated batch runner
./scripts/run_vf2_tests.sh \
  --elf-dir work/visionfive2-rv64gc/elfs/ \
  --uart /dev/ttyUSB0 \
  --output work/visionfive2-rv64gc/results.log
```

---

## Known Limitations

| Limitation | Reason | Workaround |
|---|---|---|
| M-mode tests excluded | OpenSBI owns M-mode | Set `include_priv_tests: false` |
| No automated CI | No remote JTAG/serial CI runner | Manual UART-based testing |
| CLINT not directly writable | SBI ecall required | Timer tests excluded |
| `tohost` not monitored | No host-side process | UART-based PASS/FAIL |
| Access fault address TBD | Fully-populated DRAM on some configs | Verify `0x00000000` causes fault |

---

## UART Connection

Connect a USB-UART adapter to the VisionFive 2 GPIO header:

| VisionFive 2 Pin | Signal | USB-UART |
|---|---|---|
| Pin 6 | GND | GND |
| Pin 8 | UART TX (JH7110 → host) | RX |
| Pin 10 | UART RX (host → JH7110) | TX |

Speed: **115200 baud, 8N1, no flow control**

---

## Contributing

This configuration is a work in progress. Contributions welcome:
- Verify extension flags against JH7110 Technical Reference Manual
- Add PMP grain/count corrections if discovered
- Implement host-side UART result collection script
- Test with Milk-V Jupiter (SpacemiT K1, same memory map layout)

See [CONTRIBUTING.md](../../../../CONTRIBUTING.md) for project guidelines.

---

## References

- [StarFive VisionFive 2 Datasheet](https://github.com/starfive-tech/VisionFive2)
- [JH7110 Technical Reference Manual](https://doc-en.rvspace.org/JH7110/TRM/)
- [OpenSBI Firmware](https://github.com/riscv-software-src/opensbi)
- [ACT4 Framework README](../../../../README.md)
- [Tracking Issue #1306](https://github.com/riscv/riscv-arch-test/issues/1306)
