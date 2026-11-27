/* Sv39x4 test-unit linker script.
 *
 * INCLUDE pulls in the active config's link.ld (resolved through the -L flag
 * that points at the config directory), so the memory map stays owned by the
 * config. What follows are the sections the c_common runtime needs on top of
 * it; link.ld already provides .rodata/.data/.bss and the main stack. */
INCLUDE "link.ld"

SECTIONS
{
    /* TEST_REGISTER() collects the test-case function pointers here. */
    .test_table . : {
        . = ALIGN(8);
        _test_table = .;
        *(.test_table)
        _test_table_end = .;
    } > ram
    _test_table_size = (_test_table_end - _test_table) / (__riscv_xlen / 8);

    /* Names the runtime expects for what link.ld already provides. */
    PROVIDE(_bss_start = __bss_start);
    PROVIDE(_bss_end = __bss_end);
    PROVIDE(__stack_start = __stack_bottom);
    PROVIDE(__stack_end = __stack_top);

    /* VS-stage page table pool. */
    . = ALIGN(0x1000);
    .page_tables . : {
        PROVIDE(__page_tables_start = .);
        . += 64 * 4096;    /* 256KB */
        PROVIDE(__page_tables_end = .);
    } > ram

    /* G-stage page table pool, 16KB-aligned so the first 16KB block may serve
     * directly as the Sv*x4 root table. */
    . = ALIGN(0x4000);
    .gpt_page_tables . : {
        PROVIDE(__gpt_pool_start = .);
        . += 64 * 4096;    /* 256KB */
        PROVIDE(__gpt_pool_end = .);
    } > ram

    /* HS-mode trap handler stack. */
    . = ALIGN(16);
    .smode_stack . : {
        PROVIDE(__smode_stack_start = .);
        . += 16 * 1024;
        PROVIDE(__smode_stack_end = .);
    } > ram

    /*
     * Test region for G-stage tests (8 pages, each 4KB).
     *   Page 0: test_data_area     (read/write tests)
     *   Page 1: test_fault_page    (perm/U-bit/V=0 fault tests)
     *   Page 2: test_exec_page     (executable code tests)
     *   Page 3: test_exec_target   (alternate exec target for fault)
     *   Page 4-7: scratch
     */
    . = ALIGN(0x200000);
    .vm_test_region . : {
        PROVIDE(__vm_test_region_start = .);
        PROVIDE(test_data_area   = .); . += 4096;
        PROVIDE(test_fault_page  = .); . += 4096;
        PROVIDE(test_exec_page   = .); . += 4096;
        PROVIDE(test_exec_target = .); . += 4096;
        . += 4 * 4096;
        PROVIDE(__vm_test_region_end = .);
    } > ram

    /* Zero-size placeholders for the regions pmp_init.S references but the
     * G-stage tests do not use. */
    .pmp_placeholder . : {
        . = ALIGN(8);
        __pmp_test_code = .;
        __pmp_test_nomap = .;
    } > ram

    _end = .;
}
