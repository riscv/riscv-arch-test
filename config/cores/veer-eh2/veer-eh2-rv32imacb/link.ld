/* Set these to match the DUT memory map and hart count.
 *
 * VeeR EH2 boots from address 0: the testbench hardcodes the reset vector rather
 * than using the RV_RESET_VEC build define.
 *   Quote: "reset_vector = {`RV_XLEN{1'b0}};"
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/tb_top.sv#L505
 * The testbench memory is a sparse associative array over the whole 32-bit space, so
 * RAM_LENGTH is bounded only by the region size, not by a physical array.
 *   Quote: "bit [7:0] mem [bit[`RV_XLEN-1:0]];"
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/ahb_sif.sv#L165
 * Region 0 is an ordinary system-bus region: it is not the DCCM (0xF004_0000), the
 * ICCM (0xEE00_0000), the PIC (0xF00C_0000) or the console mailbox (0xD058_0000). Code,
 * read-only data and the stack stay inside it, and .data stays inside the DCCM, so no
 * access can cross a 256 MB region boundary (which VeeR reports as a misaligned
 * exception).
 *
 * The .data section (scratch, trap save areas, test data and signature) goes in the
 * DCCM, the only memory where EH2 allows AMOs and LR/SC.
 *   Quote: "(lsu_pkt_dc2.valid & lsu_pkt_dc2.atomic & ~addr_in_dccm_dc2)"
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/design/lsu/eh2_lsu_addrcheck.sv#L199-L200
 * The DCCM sits at the default 0xF004_0000 (dccm_region 0xF, dccm_offset 0x40000), and
 * install-veer-eh2.sh builds it at 256 KB (dccm_size=256) rather than the default 64 KB
 * because the largest ACT .data sections exceed 64 KB.
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/configs/veer.config#L262-L265
 * The testbench copies [start, end] of program.hex into the DCCM before reset when the
 * words at 0xFFFF_FFF0 and 0xFFFF_FFF4 hold the start and end addresses.
 *   Quote: "0xffff_fff0 - DCCM start address to load / 0xffff_fff4 - DCCM end address to load"
 *   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/tb_top.sv#L1204-L1257
 */
RAM_ORIGIN = 0x00000000;
RAM_LENGTH = 0x10000000;
DCCM_ORIGIN = 0xF0040000;
DCCM_LENGTH = 0x40000;
TEST_BASE = RAM_ORIGIN;
NUM_HARTS = 1;

/* Most users should not need to modify anything below this line. */
STACK_SIZE = 0x20000;

OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

MEMORY
{
  ram (rwx) : ORIGIN = RAM_ORIGIN, LENGTH = RAM_LENGTH
  dccm (rw) : ORIGIN = DCCM_ORIGIN, LENGTH = DCCM_LENGTH
  dccm_ctl (r) : ORIGIN = 0xFFFFFFF0, LENGTH = 8
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
  __ram_end = .;

  /* .data must fit the DCCM; the linker reports "region `dccm' overflowed" if not. */
  .data DCCM_ORIGIN : { *(.data) *(.data.*) *(.sdata) *(.sdata.*) . = ALIGN(4); } > dccm
  /* DCCM preload window for the testbench: first and last word addresses of .data. */
  .dccm_ctl : { LONG(ADDR(.data)) LONG(ADDR(.data) + SIZEOF(.data) - 4) } > dccm_ctl

  /* The trap handler treats [rvtest_entry_point, _end) as the test image when it checks
   * xtval, so the image extends to the end of .data in the DCCM. */
  _end = ADDR(.data) + SIZEOF(.data);

  ASSERT(__ram_end <= ORIGIN(ram) + LENGTH(ram), "ACT ELF exceeds RAM; increase RAM_LENGTH in link.ld and the matching memory.regions size in sail.json")
}
