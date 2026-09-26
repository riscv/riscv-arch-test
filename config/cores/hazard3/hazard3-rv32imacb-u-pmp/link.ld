/* Set these to match the DUT memory map and hart count.
 *
 * The Hazard3 reference testbench models a single flat 16 MB RAM at 0x8000_0000 and
 * an IO window at 0xC000_0000. Nothing else in the 32-bit space responds.
 *   Quote: "#define MEM_BASE 0x80000000"  /  "#define MEM_SIZE (16 * 1024 * 1024)"
 *   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/include/tb_constants.h#L10-L11
 *
 * The image is loaded as a flat binary at MEM_BASE (objcopy -O binary, tb --bin), so the
 * lowest linked address must equal MEM_BASE exactly, and it must also equal the configured
 * reset vector because the testbench has no boot ROM or trampoline.
 *   Quote: "fd.read((char*)mem, bin_size);"  (read straight into mem[0], i.e. MEM_BASE)
 *   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L36
 *   Quote: "localparam RESET_VECTOR = 32'h80000000;"  (config_act.vh, see README.md)
 *
 * 16 MB is the whole backed RAM; addresses at or above 0x8100_0000 are decoded as bus
 * errors, which is what makes 0x9000_0000 a usable RVMODEL_ACCESS_FAULT_ADDRESS.
 */
RAM_ORIGIN = 0x80000000;
RAM_LENGTH = 0x01000000;
TEST_BASE = 0x80000000;
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
