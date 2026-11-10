/* Copyright (c) 2026, Harvey Mudd College
 * SPDX-License-Identifier: Apache-2.0
 */

/* Set these to match the DUT memory map and hart count.
 *
 * The SoC decodes a 32 MB SRAM at 0x0000_0000, and core 0 resets to address 0.
 *   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/axi/axi_interconnect128.v#L358-L360
 *   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/common/cpu_sub_system_axi.v#L226
 * RAM_LENGTH is 4 MB because the patched testbench loader copies only the first 4 MB
 * of the image.
 *
 * If RAM_ORIGIN/RAM_LENGTH change here, change memory.regions in sail.json to match.
 */
RAM_ORIGIN = 0x00000000;
RAM_LENGTH = 0x00400000;
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
