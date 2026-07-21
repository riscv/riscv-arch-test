/* act_link.ld
 *
 * Canonical linker script for ACT certification kits.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * This script is framework-owned and is shipped to the customer as part of the
 * kit. It is NOT customisable: the golden signatures were computed by the
 * reference model against exactly this layout, so changing any address below
 * invalidates every signature in the kit.
 *
 * The ordering invariant that makes the kit work:
 *
 *   .text.init / .text.rvtest / .data   <- certified, fixed addresses
 *   ---------------------------------------------------------------
 *   .tohost / .text.rvmodel             <- customer-supplied, variable size
 *
 * Everything the signature can observe lives above the line. Everything whose
 * size depends on the customer's private rvmodel_macros.h lives below it, so a
 * larger or smaller macro expansion can never shift a signature-visible symbol.
 *
 * .tohost is placed EXPLICITLY here. In the per-config scripts under config/ it
 * is an orphan section, and the linker happens to place it after .data, which is
 * benign but unspecified. A kit cannot rely on "happens to".
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
