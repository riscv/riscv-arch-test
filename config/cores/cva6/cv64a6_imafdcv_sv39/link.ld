/* Set these to match the DUT memory map and hart count.
 *
 * RAM_ORIGIN / TEST_BASE = 0x8000_0000 is the DRAM window base and is also the
 * CVA6 reset vector, so an ACT ELF runs from its first instruction with no boot
 * stub.  Quote: "DRAMBase = 64'h8000_0000" and ".boot_addr_i  (DRAMBase ), // start fetching from DRAM"
 *   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_soc.sv#L83
 *   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_soc.sv#L545
 *
 * RAM_LENGTH = 0x0100_0000 (16 MiB), NOT the 1 GiB DRAMLength the address decoder
 * claims.  The physical L2 behind the decoder is a single tc_sram of L2NumWords =
 * (2**22)/NrLanes words of AxiDataWidth = 32*NrLanes bits, i.e. 2**24 bytes regardless
 * of the lane count, and the SRAM is indexed with the low address bits only, so
 * anything above 16 MiB aliases back into it instead of faulting.
 *   Quote: "parameter  int           unsigned L2NumWords   = (2**22) / NrLanes,"
 *   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_soc.sv#L30
 *   Quote: ".addr_i (l2_addr[$clog2(L2NumWords)-1+$clog2(AxiDataWidth/8):$clog2(AxiDataWidth/8)])"
 *   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_soc.sv#L252
 *
 * Keep this in sync with memory.regions in sail.json and with the Verilator
 * testbench ELF loader window that setup-ara.sh widens to the same 16 MiB.
 */
RAM_ORIGIN = 0x80000000;
RAM_LENGTH = 0x1000000;
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
