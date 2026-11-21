/* Copyright (c) 2026, Harvey Mudd College
 * SPDX-License-Identifier: Apache-2.0
 */

/* Set these to match the DUT memory map and hart count.
 *
 * The core resets to address 0 and sends fetches, loads and stores below 0x2000_0000 to
 * the instruction-bus SRAM, which is 512 KB.
 *   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/smart_run/logical/common/cpu_sub_system_ahb.v#L179-L185
 *   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/E902_RTL_FACTORY/gen_rtl/bmu/rtl/cr_bmu_dbus_if.v#L284
 *   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/smart_run/logical/mem/iahb_mem_ctrl.v#L96
 * The top 4 KB, 0x7_F000-0x7_FFFF, is left out of RAM_LENGTH.  mtvec reads back
 * MODE = 3, so the trap prolog never sees its write take and copies the trap trampoline
 * to the address in mtvec; RVMODEL_BOOT points mtvec there.
 *
 * If RAM_ORIGIN/RAM_LENGTH change here, change memory.regions in sail.json to match.
 */
RAM_ORIGIN = 0x00000000;
RAM_LENGTH = 0x0007F000;
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
