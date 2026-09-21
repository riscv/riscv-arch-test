/* Set these to match the DUT memory map and hart count.
 *
 * SERV's servant SoC has one RAM, `memsize` bytes deep, starting at address 0, and the
 * core resets to PC 0: servile's reset_pc parameter defaults to 0 and servant.v does not
 * plumb it through, so it cannot be moved without patching the RTL.  The tests therefore
 * link at 0 and need no boot stub.
 *   Quote: "parameter     reset_pc = 32'h00000000,"
 *   https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servile/servile.v#L12
 *   Quote: "o_ibus_adr <= i_rst ? RESET_PC : {new_pc, o_ibus_adr[31:W]};"
 *   https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/rtl/serv_ctrl.v#L112
 *
 * RAM_LENGTH is the 8 MiB that SERV's own compliance flow builds, and must match the
 * -Gmemsize= passed to verilator (see .github/scripts/install-serv.sh) and the MainMemory
 * region in sail.json.  servant_ram has no bounds check - it indexes with
 * i_wb_adr[$clog2(memsize)-1:2] - so an access past the end silently wraps instead of
 * faulting, which is why the image must fit.
 *   Quote: "wire [aw-3:0]  addr = i_wb_adr[aw-1:2];"
 *   https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servant/servant_ram.v#L22
 *
 * Everything at or above 0x4000_0000 is off-core: GPIO below 0x8000_0000, the timer at or
 * above it, plus the two simulation hooks at 0x8000_0000 and 0x9000_0000.
 */
RAM_ORIGIN = 0x00000000;
RAM_LENGTH = 0x800000;
TEST_BASE = 0x00000000;
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
