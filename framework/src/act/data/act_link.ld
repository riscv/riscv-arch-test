/* act_link.ld -- linker script for ACT certification kits.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Do not edit: the signatures were computed against this exact layout, so any
 * address change invalidates them. The certified sections (.text.init,
 * .text.rvtest, .data) come first at fixed addresses; the customer-supplied,
 * variable-size sections (.tohost, .text.rvmodel) come after .data so their size
 * can't shift a signature-visible symbol. .tohost is placed explicitly here
 * because the per-config scripts leave it as an orphan section.
 */

OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

SECTIONS
{
  . = 0x80000000;

  /* ---- Certified region: addresses are part of the signature contract ---- */
  .text.init    : { *(.text.init) }
  .text.rvtest  : { *(.text.rvtest) *(.text.rvtest.*) }
  . = ALIGN(0x4000);
  .data         : { *(.data) }

  /* ---- Model region: customer-supplied, size may vary freely ------------- */
  . = ALIGN(0x1000);
  .tohost       : { *(.tohost) }
  . = ALIGN(0x1000);
  .text.rvmodel : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) }
  . = ALIGN(0x1000);
  _end = .;
}
