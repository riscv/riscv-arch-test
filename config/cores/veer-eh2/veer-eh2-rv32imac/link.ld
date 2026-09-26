/* Set these to match the DUT memory map and hart count.
 *
 * VeeR EH2 boots from address 0: the testbench hardcodes the reset vector rather
 * than using the RV_RESET_VEC build define.
 *   Quote: "reset_vector = 32'h0;"
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/bd52450b/testbench/tb_top.sv#L505
 * The testbench memory is a sparse associative array over the whole 32-bit space, so
 * RAM_LENGTH is bounded only by the region size, not by a physical array.
 *   Quote: "bit [7:0] mem [bit[31:0]];"
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/bd52450b/testbench/ahb_sif.sv#L43
 * Region 0 is an ordinary system-bus region: it is not the DCCM (0xF004_0000), the
 * ICCM (0xEE00_0000), the PIC (0xF00C_0000) or the console mailbox (0xD058_0000), and
 * the whole image stays inside one 256 MB region so no access can cross a region
 * boundary (which VeeR reports as a misaligned exception).
 */
RAM_ORIGIN = 0x00000000;
RAM_LENGTH = 0x10000000;
TEST_BASE = 0x00001000;
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
