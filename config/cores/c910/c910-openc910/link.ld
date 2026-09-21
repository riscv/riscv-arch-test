/* Set these to match the DUT memory map and hart count.
 *
 * The open-source OpenC910 SoC decodes a single 32 MB SRAM at 0x0000_0000.
 *   Quote: "parameter SRAM_START = 40'h0000_0000;  parameter SRAM_END = 40'h01ff_ffff;"
 *   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/axi/axi_interconnect128.v#L358-L360
 *
 * RAM_LENGTH is deliberately 4 MB, not 32 MB: the patched testbench image loader
 * copies 0x40000 sixteen-byte rows, i.e. the first 4 MB, so anything the linker puts
 * beyond that would never be written into the SRAM.  The ASSERT at the bottom of this
 * file turns an oversized image into a link error instead of a silent truncation,
 * which is exactly what the unpatched 256 KB loader did.
 *
 * Core 0's reset vector is tied to 0, so the image must have something executable at
 * address 0.  ACT cannot link a test at 0 (TEST_BASE 0 makes .text.init start at the
 * null address and the diagnostics are misleading), so the tests link at 0x1000 and
 * RVMODEL_BOOT emits a two-instruction trampoline into .text.reset, which this script
 * places at 0.  This is the VeeR EH1 precedent.
 *   Quote: ".pad_core0_rvba    (40'b0        ),"
 *   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/common/cpu_sub_system_axi.v#L226
 *
 * For the Sail reference build RVMODEL_BOOT is #undef'd, so .text.reset is empty.
 * It is placed at a fixed address ahead of .text.init, so its presence or absence
 * cannot shift any other section and the DUT and reference ELFs keep identical
 * .data addresses.
 *
 * If RAM_ORIGIN/RAM_LENGTH change here, change memory.regions in sail.json to match.
 */
RAM_ORIGIN = 0x00000000;
RAM_LENGTH = 0x00400000;
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

  /* The hard-wired reset vector. Emitted by RVMODEL_BOOT; empty in the Sail build. */
  .text.reset  RAM_ORIGIN : { *(.text.reset) } > ram

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
