/* SPDX-License-Identifier: Apache-2.0 */
/* link.ld — Linker script for StarFive VisionFive 2 (JH7110 SoC)
 *
 * Memory map (JH7110 / VisionFive 2):
 *   0x00000000 - 0x3FFFFFFF : Unmapped / peripheral space
 *   0x40000000 - 0xFFFFFFFF : DRAM (8 GB physical)
 *
 * This linker script places the ELF at 0x42000000, leaving room below
 * for OpenSBI (0x40000000) and U-Boot (0x40200000 default load address).
 *
 * Load via U-Boot:
 *   => tftpboot 0x42000000 <test>.elf; go 0x42000000
 *   OR
 *   => load mmc 0:1 0x42000000 <test>.elf; go 0x42000000
 *
 * The entry point rvtest_entry_point is called directly by 'go'.
 * RVMODEL_BOOT runs first (UART init), then the test body executes.
 */

OUTPUT_ARCH("riscv")
ENTRY(rvtest_entry_point)

SECTIONS
{
  /* -----------------------------------------------------------
   * Base address: 0x42000000
   * Below this: OpenSBI @ 0x40000000, U-Boot @ 0x40200000
   * ----------------------------------------------------------- */
  . = 0x42000000;

  /* Boot/init code — must be first, at the entry point address */
  .text.init    : { *(.text.init) }

  /* ACT test code */
  .text.rvtest  : { *(.text.rvtest) *(.text.rvtest.*) }

  /* 16 KB alignment before data to simplify PMP setup if needed */
  . = ALIGN(0x4000);

  /* Test data and signatures */
  .data         : { *(.data) }

  /* 4 KB alignment for model-specific code */
  . = ALIGN(0x1000);

  /* DUT-specific code (RVMODEL macros, UART routines, etc.)
   * MUST follow .data so variable-size model code does not
   * affect the addresses of test data symbols (begin_signature etc.) */
  .text.rvmodel : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) }

  . = ALIGN(0x1000);
  _end = .;
}
