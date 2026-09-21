// rvmodel_macros.h
// RVMODEL macro definitions for the BSC Sargantana core tile (bsc-loca/core_tile @ 2528e7df)
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// The tile terminates a simulation and prints to the console through the HTIF
// tohost/fromhost protocol implemented in simulator/models/cxx/dpi_host.cpp:
//   "if (data & 1) return 1; // Simulation finished"
// and otherwise treating the written value as a pointer to an eight-doubleword
// "magicmem" block whose first word is a syscall number.
// https://github.com/bsc-loca/core_tile/blob/2528e7df6507fa06d372f001e55cfd46efae4a4b/simulator/models/cxx/dpi_host.cpp#L15-L29
//
// tohost, fromhost and the syscall block each get their own 64-byte word: the tile
// matches a tohost write by the address of the HPDcache write-buffer request, which is
// the enclosing 64-byte memory word, so anything sharing tohost's word would be
// mistaken for a tohost write.  See the comment in link.ld.
#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                 \
        .balign 64; .global tohost; tohost: .dword 0;        \
        .balign 64; .global fromhost; fromhost: .dword 0;    \
        .balign 64; htif_magicmem: .dword 0,0,0,0,0,0,0,0;   \
        .balign 64; htif_iobuf: .fill 8192,1,0;              \
        .popsection;

// Sargantana implements a conforming M-mode: mstatus/mtvec/mepc/mcause/mtval/mie/mip
// and the delegation registers are all present, so ACT's standard trap prologs and
// M-mode CSR initialization apply.  Without this, RVTEST_BOOT_TO_MMODE skips
// RVTEST_TRAP_PROLOG and mtvec is never written (tests/env/rvtest_setup.h:941).
#define STANDARD_SM_SUPPORTED

// STARTUP //

// No DUT-specific boot state is needed: the boot ROM jumps straight to 0x8000_0000.
//#define RVMODEL_BOOT

//#define RVMODEL_BOOT_TO_MMODE

// TERMINATION //

// A tohost value with bit 0 set ends the simulation; bits [15:1] are the exit code, and
// an exit code of 0 is the only one the tile reports as success:
//   "exit_code = dc_write_req_data_i[15:1];
//    if (exit_code == 0) begin ... $write("Run finished correctly"); $finish;"
// https://github.com/bsc-loca/core_tile/blob/2528e7df6507fa06d372f001e55cfd46efae4a4b/simulator/models/hdl/l2_behav.sv#L447-L462
// A single sd is used rather than a pair of sw so that the doubleword reaches the write
// buffer as one request whose low 64 bits are the tohost value.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sd x1, 0(t0)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

// Exit code 1 (tohost = 3) makes l2_behav.sv print "Simulation ended with error code"
// and call $error, which run-sargantana.sh turns into a nonzero exit status.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sd x1, 0(t0)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

// IO //

// No initialization is needed; the HTIF console is always available.
//#define RVMODEL_IO_INIT(_R1, _R2, _R3)

// Write the whole string with one HTIF SYS_write (64) rather than a character at a time:
// the tile has no character-at-a-time HTIF device protocol, only the syscall block
// ("switch (magicmem[0]) { case SYS_write: ... write(magicmem[1], buf, magicmem[3])"),
// and a per-character syscall would need the settle loop below on every character.
// https://github.com/bsc-loca/core_tile/blob/2528e7df6507fa06d372f001e55cfd46efae4a4b/simulator/models/cxx/dpi_host.cpp#L31-L48
//
// The string is copied into htif_iobuf first because the DPI fetches the buffer with
// word-aligned reads off the buffer base:
//   "uint32_t data = memory_dpi_read_contents(magicmem[2] + (i & ~0b11));"
// and the backing memory asserts on an unaligned address
//   ("assert((addr & 0x3) == 0);", simulator/models/cxx/dpi_perfect_memory.cpp#L194),
// so handing it a string that does not start on a 4-byte boundary aborts the
// simulator.  ACT's message strings are plain .string literals at arbitrary
// alignment, so the copy is not optional.
//
// The settle loop is required too.  dpi_host reads the syscall block out of the DPI
// backing memory at the instant the tohost write request is seen, but the stores that
// filled the block are still in the HPDcache write buffer at that point, so without the
// delay the model reads magicmem[0] == 0 and prints "Unknown tohost syscall 0" instead
// of the string.  Measured on core_tile @ 2528e7df: a four-iteration loop is already
// enough and zero delay always fails; 100 is used for margin.
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)               \
  la _R2, htif_iobuf         ;/* word-aligned staging buffer */ \
  li _R3, 0                  ;/* length */           \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)       ;/* Load byte */        \
  beqz _R1, 2f               ;/* Exit if null */     \
  sb _R1, 0(_R2)             ;                       \
  addi _R2, _R2, 1           ;                       \
  addi _STR_PTR, _STR_PTR, 1 ;                       \
  addi _R3, _R3, 1           ;                       \
  j 1b                       ;                       \
2:                           ;                       \
  beqz _R3, 3f               ;/* Nothing to print */ \
  la _R2, htif_magicmem      ;/* syscall block */    \
  li _R1, 64                 ;/* SYS_write */        \
  sd _R1, 0(_R2)             ;/* magicmem[0] */      \
  li _R1, 1                  ;/* stdout */           \
  sd _R1, 8(_R2)             ;/* magicmem[1] */      \
  la _R1, htif_iobuf         ;                       \
  sd _R1, 16(_R2)            ;/* magicmem[2] = buf */ \
  sd _R3, 24(_R2)            ;/* magicmem[3] = len */ \
  fence                      ;                       \
  li _R3, 100                ;/* settle loop */      \
4:                           ;                       \
  addi _R3, _R3, -1          ;                       \
  bnez _R3, 4b               ;                       \
  la _R1, tohost             ;                       \
  sd _R2, 0(_R1)             ;/* tohost = &magicmem, bit 0 clear -> syscall */ \
3:

// Access Fault //

// Address 0 lies outside every mapped section of the default core configuration
// (InitMappedBase/InitMappedEnd cover 0x40000000-0x3fffffffff, 0x100-0xffff and
// 0x10000-0x10020), so an access to it raises an access fault.
// https://github.com/bsc-loca/sargantana/blob/403975c8a3c64c8eb369021a1ac2a374e5df441b/includes/drac_pkg.sv#L1297-L1305
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

// Interrupt Latency //

#define RVMODEL_INTERRUPT_LATENCY 10

// Machine Timer //

// RVMODEL_MTIME_ADDRESS is deliberately left undefined: the tile has no CLINT, and the
// simulation testbench ties every interrupt and the time input off.
//   "// No support for timer, interrupts, etc in simulation
//    .time_i(64'd0), .irq_i(1'b0), .soft_irq_i(1'b0), .time_irq_i(1'b0),"
// https://github.com/bsc-loca/core_tile/blob/2528e7df6507fa06d372f001e55cfd46efae4a4b/simulator/sim_top.sv#L263-L268
// With it undefined, ACT skips the machine-timer interrupt tests.  RVMODEL_TIMER_INT_SOON_DELAY
// is still required to assemble.
#define RVMODEL_TIMER_INT_SOON_DELAY 100

// Machine and Supervisor Interrupts //

// There is no interrupt controller to poke, so these are empty.  The suites that use
// them (Interrupts*) cannot pass and are listed in EXCLUDE_EXTENSIONS in ci.yaml.
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)
#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
