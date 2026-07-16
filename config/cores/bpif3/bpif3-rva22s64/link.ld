/*
 * Linker script for SpacemiT K1 / Banana Pi BPI-F3 bare-metal ACT tests.
 *
 * Load address: 0xC8000000 (128 MiB into K1 DRAM, which starts at 0xC0000000).
 *
 * Layout rationale:
 *   0xC0000000 — ACT runner firmware (BOARD_FW_LOAD_ADDR)
 *   0xC1008000 — tohost polling address (BOARD_FIXED_TOHOST_ADDR)
 *   0xC8000000 — test ELF pack + individual ELF load point (here)
 *
 * From 0xC8000000, all K1 peripherals (UART 0xD4017000, CLINT 0xE4000000,
 * PLIC 0xE0000000) are within +-2GB, satisfying the medany code model.
 *
 * Sail simulation: sail.json DRAM-high region covers 0x80000000-0xBFFFFFFF
 * which does NOT include 0xC8000000. Update sail.json memory regions if
 * running Sail simulation against this link address.
 */

OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

SECTIONS
{
  . = 0xC8000000;
  .text.init    : { *(.text.init) }
  .text.rvtest  : { *(.text.rvtest) *(.text.rvtest.*) }
  . = ALIGN(0x4000);
  .data         : { *(.data) }
  . = ALIGN(0x1000);
  .text.rvmodel : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) }
  . = ALIGN(0x1000);
  _end = .;

  /* Peripheral-address stubs: zero-size NOLOAD sections so that
   * RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS expand to
   * relocatable symbols instead of numeric constants. GAS then emits
   * auipc+addi (pc-relative) for la/LA, which avoids the RV64
   * sign-extension problem that lui+addi hits for addresses with bit 31
   * set. The sections hold no bytes; only the symbol VMA matters. */
  .k1_periph_mtimecmp 0xE4004000 (NOLOAD) : { _k1_mtimecmp = .; }
  .k1_periph_mtime    0xE400BFF8 (NOLOAD) : { _k1_mtime    = .; }
}
