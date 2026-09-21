/* Copyright (c) 2026, Harvey Mudd College
 * SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
 *
 * Linker script for the BSC Sargantana core tile (bsc-loca/core_tile @ 2528e7df).
 *
 * The tests link at 0x8000_0000 because that is where the tile's boot ROM jumps:
 *   "#define DRAM_BASE 0x80000000 ... _start: li s0, DRAM_BASE ... jr s0"
 *   https://github.com/bsc-loca/core_tile/blob/2528e7df6507fa06d372f001e55cfd46efae4a4b/simulator/bootrom/bootrom.S#L1-L7
 * 0x8000_0000 also sits inside the first mapped memory section of the default core
 * configuration, InitMappedBase[0] = 0x0040000000 .. InitMappedEnd[0] = 0x3fffffffff:
 *   https://github.com/bsc-loca/sargantana/blob/403975c8a3c64c8eb369021a1ac2a374e5df441b/includes/drac_pkg.sv#L1297-L1299
 */
RAM_ORIGIN = 0x80000000;
RAM_LENGTH = 0x10000000;
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

  /* The HTIF block is placed explicitly, and 64-byte aligned, because the tile
   * recognises a tohost write by comparing the L2 write-request address against the
   * address of the `tohost` symbol:
   *   "assign is_tohost = dc_write_req_valid_i & dc_write_req_data_valid_i &&
   *    dc_write_req_addr_i == tohost_addr;"
   *   https://github.com/bsc-loca/core_tile/blob/2528e7df6507fa06d372f001e55cfd46efae4a4b/simulator/models/hdl/l2_behav.sv#L441
   * Stores leave the write-through data cache through the HPDcache write buffer, whose
   * requests carry the address of the enclosing 64-byte memory word ("#define
   * BUS_ADDR_BITS 6 // Bits needed to address a byte within the bus",
   * simulator/models/cxx/dpi_perfect_memory.h#L6-L8).  A `tohost` that is not at the
   * start of such a word therefore never compares equal and every test runs to the
   * cycle limit instead of terminating.  rvmodel_macros.h keeps `fromhost` and the HTIF
   * syscall buffer in later 64-byte words for the same reason: a store to either of
   * them must not produce a write request at `tohost`'s address.
   */
  . = ALIGN(64);
  .tohost . : { *(.tohost) } > ram

  . = ALIGN(0x1000);
  _end = .;

  ASSERT(_end <= ORIGIN(ram) + LENGTH(ram), "ACT ELF exceeds RAM; increase RAM_LENGTH in link.ld and the matching memory.regions size in sail.json")
}
