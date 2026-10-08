/* Set these to match the DUT memory map and hart count.
 *
 * Ibex Simple System has a 1 MB RAM at 0x0010_0000. The core boots at boot_addr_i
 * (0x0010_0000) with 0x80 as the least significant byte, so TEST_BASE is 0x0010_0080.
 *   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L118-L119
 *   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L247
 *   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/doc/03_reference/exception_interrupts.rst#L17
 */
RAM_ORIGIN = 0x00100000;
RAM_LENGTH = 0x00100000;
TEST_BASE = 0x00100080;
NUM_HARTS = 1;

/* Most users should not need to modify anything below this line. */
STACK_SIZE = 0x8000;

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
