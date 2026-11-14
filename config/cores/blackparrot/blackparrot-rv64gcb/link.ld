/* Copyright (c) 2026, Harvey Mudd College
 * SPDX-License-Identifier: Apache-2.0
 *
 * Linker script for BlackParrot in the bp_tethered testbench (black-parrot @ 909619a6).
 *
 * The testbench's configuration loader sets the reset PC to the DRAM base:
 *   "write_register(j, cfg_reg_npc_gp, 0, dram_base_addr_gp);"
 *   https://github.com/black-parrot/black-parrot/blob/909619a68f3541a4cd0973767daf2a561d1f8c95/bp_top/test/common/bp_nonsynth_cfg_loader.sv#L88
 * with "localparam dram_base_addr_gp = 40'h00_8000_0000;" (bp_common_addr_pkgdef.svh#L27).
 * The DRAM model holds 64 MiB ("localparam mem_size_p = 2**26;", bp_nonsynth_dram.sv#L95).
 */
RAM_ORIGIN = 0x80000000;
RAM_LENGTH = 0x04000000;
TEST_BASE = RAM_ORIGIN;
NUM_HARTS = 1;

/* Most users should not need to modify anything below this line. */
STACK_SIZE = 0x20000;

OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

MEMORY
{
  ram (rwx) : ORIGIN = RAM_ORIGIN, LENGTH = RAM_LENGTH
}

PROVIDE(__stack_size = STACK_SIZE);
PROVIDE(__num_harts = NUM_HARTS);

SECTIONS
{
  ASSERT(TEST_BASE >= ORIGIN(ram) && TEST_BASE < ORIGIN(ram) + LENGTH(ram), "TEST_BASE is outside RAM; update TEST_BASE and RAM_ORIGIN/RAM_LENGTH in link.ld, and the matching memory.regions entry in sail.json")

  .text.init   TEST_BASE : { *(.text.init) } > ram
  .text.rvtest . : { *(.text.rvtest) *(.text.rvtest.*) } > ram

  . = ALIGN(0x4000);
  .rodata . : { *(.rodata) *(.rodata.*) *(.srodata) *(.srodata.*) } > ram
  .data   . : { *(.data) *(.data.*) *(.sdata) *(.sdata.*) } > ram

  . = ALIGN(16);
  .bss . : {
    __bss_start = .;
    *(.sbss) *(.sbss.*) *(.bss) *(.bss.*) *(COMMON)
    . = ALIGN(16);
    __bss_end = .;
  } > ram

  . = ALIGN(16);
  __stack_bottom = .;
  . += __stack_size * __num_harts;
  __stack_top = .;

  . = ALIGN(0x1000);
  .text.rvmodel . : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) } > ram

  . = ALIGN(0x1000);
  _end = .;

  ASSERT(_end <= ORIGIN(ram) + LENGTH(ram), "ACT ELF exceeds RAM; increase RAM_LENGTH in link.ld and the matching memory.regions size in sail.json")
}
