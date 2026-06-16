INCLUDE "link.ld"
ENTRY(rvtest_entry_point)
SECTIONS {
    .rodata : { *(.rodata .rodata.*) }
    .sdata  : { *(.sdata .sdata.*) }
    .bss (NOLOAD) : {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(8);
        __bss_end = .;
    }
    .stack (NOLOAD) : {
        . = ALIGN(16);
        __stack_bottom = .;
        . += 128K;
        _stack_top = .;
    }
    PROVIDE(__global_pointer$ = ADDR(.sdata) + 0x800);
} INSERT AFTER .data;