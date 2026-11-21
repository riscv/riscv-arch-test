/* Hypervisor x Svnapot cross test-unit linker script.
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

    /* G-stage page table pool, 16KB-aligned for the Sv*x4 root table. */
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

    /* NAPOT test region: 2MB-aligned so a superpage boundary can be exercised,
     * 128 KiB total, laid out as two 64 KiB NAPOT regions.
     *   Pages 0-15:  first 64 KiB NAPOT region
     *   Pages 16-31: second 64 KiB NAPOT region
     * This suite addresses the region through __vm_test_region_start/_end only,
     * so it needs none of the per-page symbols the other suites use. */
    . = ALIGN(0x200000);
    .vm_test_region . : {
        PROVIDE(__vm_test_region_start = .);
        . += 32 * 4096;
        PROVIDE(__vm_test_region_end = .);
    } > ram

    _end = .;
}
