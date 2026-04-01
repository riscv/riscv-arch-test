OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

/*
 * CV32E40S PMA+PMP enabled memory map
 *
 * PMP: 16 regions, G=0 (byte granularity). At reset all regions are OFF
 * and mseccfg={rlb=0,mmwp=0,mml=0}, so M-mode has unrestricted access
 * by default (no PMP setup needed in RVMODEL_BOOT).
 *
 * Testbench PMA configuration required (PMA_NUM_REGIONS=1):
 *
 *   Region 0 (main memory): 0x00000000 – 0x003FFFFF  (4 MB)
 *     word_addr_low  = 32'h00000000
 *     word_addr_high = 32'h00100000
 *     main=1, bufferable=0, cacheable=0, integrity=0
 *
 * All code and data sections below must stay within this region.
 * Addresses outside PMA regions default to I/O (no instruction fetch,
 * no misaligned access, no modified transactions, no PUSH/POP).
 *
 * I/O peripherals (no PMA region needed — I/O by default):
 *   0x10000000          MMADDR_PRINT      (virtual printer)
 *   0x15000000          MMADDR_TIMERREG   (timer config)
 *   0x15000004          MMADDR_TIMERVAL   (timer value)
 *   0x20000000          MMADDR_TESTSTATUS (write 123456789=pass, 1=fail)
 *   0x20000004          MMADDR_EXIT       (signal halt)
 *   0x20000008          MMADDR_SIGBEGIN   (signature start addr)
 *   0x2000000C          MMADDR_SIGEND     (signature end addr)
 *   0x20000010          MMADDR_SIGDUMP    (dump signature + halt)
 *
 * The .tohost section (tohost/fromhost symbols) is for the SAIL reference
 * model only — it lives inside the PMA main region, not at 0x20000000.
 *
 * Unmapped / fault region:
 *   0x80000000          ACCESS_FAULT_ADDRESS (testbench must return OBI bus error)
 */

SECTIONS
{
  . = 0x00000080;
  .text : { *(.text.init) *(.text) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x4000);
  .bss : { *(.bss) }
  . = ALIGN(0x1000);
  .data : { *(.data) }
  . = ALIGN(0x1000);
  _end = .;
}
