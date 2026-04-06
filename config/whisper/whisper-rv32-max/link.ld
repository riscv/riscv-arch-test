OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

SECTIONS
{
  . = 0x80000000;
  .text.init : { *(.text.init) }
  .text : { *(.text) *(.text.*) }
  . = ALIGN(0x4000);
  .bss : { *(.bss) }
  . = ALIGN(0x1000);
  .data : { *(.data) }
  . = ALIGN(0x1000);
  _end = .;
}
