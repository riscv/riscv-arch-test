OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

SECTIONS
{
  . = 0x80000000;
  .text : { *(.text.init) *(.text) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x4000);
  .data : { *(.data) }
  .data.string : { *(.data.string)}
  . = ALIGN(0x1000);
  .bss : { *(.bss) }
  . = ALIGN(0x1000);
  .text : { *(.text.main) }
  _end = .;
}
