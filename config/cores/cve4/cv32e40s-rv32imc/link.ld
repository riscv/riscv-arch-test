/* Set these to match the DUT memory map and hart count. */
TEST_BASE = 0x00000080;
NUM_HARTS = 1;

/* Most users should not need to modify anything below this line. */
STACK_SIZE = 0x20000;

OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

PROVIDE(__stack_size = STACK_SIZE);
PROVIDE(__num_harts = NUM_HARTS);

SECTIONS
{
  . = TEST_BASE;

  .text.init   : { *(.text.init) }
  .text.rvtest : { *(.text.rvtest) *(.text.rvtest.*) }

  . = ALIGN(0x4000);
  .rodata : { *(.rodata) *(.rodata.*) *(.srodata) *(.srodata.*) }
  .data   : { *(.data) *(.data.*) *(.sdata) *(.sdata.*) }

  . = ALIGN(16);
  .bss : {
    __bss_start = .;
    *(.sbss) *(.sbss.*) *(.bss) *(.bss.*) *(COMMON)
    . = ALIGN(16);
    __bss_end = .;
  }

  . = ALIGN(16);
  __stack_bottom = .;
  . += __stack_size * __num_harts;
  __stack_top = .;

  . = ALIGN(0x1000);
  .text.rvmodel : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) }

  . = ALIGN(0x1000);
  _end = .;
}
