// Utility macros for configuring Hypervisor address translation.
//
// Supports Sv32x4, Sv39x4, Sv48x4 & Sv57x4 G-stage translation and
// Sv32, Sv39, Sv48 & Sv57 VS-stage translation.
//
// Developed by: Umer Shahid, Muhammad Zain, Muhammad Abdullah & Hamza Ali

#define sv32x4 0x00
#define sv39x4 0x01
#define sv48x4 0x02
#define sv57x4 0x03

// Address-space selectors for the macros below. The names are prefixed because
// this header is included by every test on a DUT that implements H, and short
// names such as PA collide with assembler macro parameters in other suites.
#define ADDR_PA  0x0
#define ADDR_GPA 0x1


// Appends 12-bit page offset from PA to VA, and stores it
// to Vsave_area. t0 and t1 are clobbered.
// NOTE: a0 must point to Msave_area.
#define V_SAVE_AREA_SETUP(VA, PA_LBL, _REG_NAME, PAGE_LEVEL)    ;\
    .if (__riscv_xlen == 32)                                    ;\
        .set PAGE_OFFSET_SHIFT, (PAGE_LEVEL*10)+12              ;\
    .else                                                       ;\
        .set PAGE_OFFSET_SHIFT, (PAGE_LEVEL*9)+12               ;\
    .endif                                                      ;\
    LI(  t0, VA)                                                ;\
    srli t0, t0, PAGE_OFFSET_SHIFT                              ;\
    slli t0, t0, PAGE_OFFSET_SHIFT                              ;\
    LA(  t1, PA_LBL)                                            ;\
    slli t1, t1, __riscv_xlen-PAGE_OFFSET_SHIFT                 ;\
    srli t1, t1, __riscv_xlen-PAGE_OFFSET_SHIFT                 ;\
    or   t0, t0, t1                                             ;\
    addi a0, a0, 1*sv_area_sz                                   ;\
    SREG t0, _REG_NAME##_bgn_off+1*sv_area_sz(a0)               ;\
    addi a0, a0, -1*sv_area_sz                                  ;


// Wrapper macro around G_PTE_SETUP_PA_REG.
// PERMS and GPA must be immediate values while Physical
// Address must be a label.
// Loads PA_LBL into a register, clears lower PPN bits based on
// LEVEL for superpage alignment, and passes it to G_PTE_SETUP_PA_REG.
#define SUPERPAGE_G_PTE_SETUP(MODE, PA_LBL, PERMS, GPA, LEVEL)  ;\
    .if (MODE == sv32x4)                                        ;\
        .set PPN_SHIFT, (LEVEL*10)+12                           ;\
    .else                                                       ;\
        .set PPN_SHIFT, (LEVEL*9)+12                            ;\
    .endif                                                      ;\
    LA(t0, PA_LBL)                                              ;\
    srli t0, t0, PPN_SHIFT                                      ;\
    slli t0, t0, PPN_SHIFT                                      ;\
    G_PTE_SETUP_PA_REG(MODE, t0, PERMS, GPA, LEVEL)             ;\


// Wrapper macro around G_PTE_SETUP_PA_REG allowing Physical
// Address to be passed as a label.
// PERMS and GPA must be immediate values.
// Loads PA_LBL into a register and passes it to G_PTE_SETUP_PA_REG.
#define G_PTE_SETUP(MODE, PA_LBL, PERMS, GPA, LEVEL)            ;\
    LA(t0, PA_LBL)                                              ;\
    G_PTE_SETUP_PA_REG(MODE, t0, PERMS, GPA, LEVEL)             ;\


// Create a G-stage page table entry and write it into the appropriate
// page table for the specified translation mode & level.
// Physical Address must be passed in a register while
// PERMS and GPA must be immediate values.
// t0, t1 & t2 are clobbered.
#define G_PTE_SETUP_PA_REG(MODE, PA_REG, PERMS, GPA, LEVEL)     ;\
    srli t0, PA_REG, 12                                         ;\
    slli t0, t0, 10                                             ;\
    LI(t1, PERMS)                                               ;\
    or t0, t0, t1                                               ;\
    .if (MODE == sv32x4)                                        ;\
        .if (LEVEL == 1)                                        ;\
            LA(t1, rvtest_Hroot_pg_tbl)                         ;\
            .set VPN_MASK, 0xFFF                                ;\
        .elseif (LEVEL == 0)                                    ;\
            LA(t1, rvtest_hlvl0_pg_tbl)                         ;\
            .set VPN_MASK, 0x3FF                                ;\
        .endif                                                  ;\
        LI(t2, ((GPA >> ((LEVEL * 10) + 12)) & VPN_MASK) << 2)  ;\
    .else                                                       ;\
        .set VPN_MASK, 0x1FF                                    ;\
        .if (MODE == sv39x4)                                    ;\
            .if (LEVEL == 2)                                    ;\
                LA(t1, rvtest_Hroot_pg_tbl)                     ;\
                .set VPN_MASK, 0x7FF                            ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_hlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_hlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv48x4)                                ;\
            .if (LEVEL == 3)                                    ;\
                LA(t1, rvtest_Hroot_pg_tbl)                     ;\
                .set VPN_MASK, 0x7FF                            ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_hlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_hlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_hlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv57x4)                                ;\
            .if (LEVEL == 4)                                    ;\
                LA(t1, rvtest_Hroot_pg_tbl)                     ;\
                .set VPN_MASK, 0x7FF                            ;\
            .elseif (LEVEL == 3)                                ;\
                LA(t1, rvtest_hlvl3_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_hlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_hlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_hlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .endif                                                  ;\
        LI(t2, ((GPA >> ((LEVEL * 9) + 12)) & VPN_MASK) << 3)   ;\
    .endif                                                      ;\
    add  t1, t1, t2                                             ;\
    SREG t0, 0(t1)                                              ;


// Same as G_PTE_SETUP_PA_REG, but the guest physical address is in a register too, so a
// test can derive its mapping windows at run time. The root table of a G-stage mode is
// four times the size of an ordinary one, which is why its index is two bits wider.
// t0, t1 and t2 are clobbered; GPA_REG is consumed before any of them is written and
// PA_REG before t1, so either may be t0 or t1. Neither may be t2.
#define G_PTE_SETUP_GPA_REG(MODE, PA_REG, PERMS, GPA_REG, LEVEL) ;\
    .if (MODE == sv32x4)                                        ;\
        .if (LEVEL == 1)                                        ;\
            .set VPN_WIDTH, 12                                  ;\
        .elseif (LEVEL == 0)                                    ;\
            .set VPN_WIDTH, 10                                  ;\
        .endif                                                  ;\
        .set VPN_SHIFT, (LEVEL * 10) + 12                       ;\
        .set ENTRY_LOG2, 2                                      ;\
    .else                                                       ;\
        .set VPN_WIDTH, 9                                       ;\
        .if (MODE == sv39x4)                                    ;\
            .if (LEVEL == 2)                                    ;\
                .set VPN_WIDTH, 11                              ;\
            .endif                                              ;\
        .elseif (MODE == sv48x4)                                ;\
            .if (LEVEL == 3)                                    ;\
                .set VPN_WIDTH, 11                              ;\
            .endif                                              ;\
        .elseif (MODE == sv57x4)                                ;\
            .if (LEVEL == 4)                                    ;\
                .set VPN_WIDTH, 11                              ;\
            .endif                                              ;\
        .endif                                                  ;\
        .set VPN_SHIFT, (LEVEL * 9) + 12                        ;\
        .set ENTRY_LOG2, 3                                      ;\
    .endif                                                      ;\
    srli t2, GPA_REG, VPN_SHIFT                                 ;\
    slli t2, t2, (__riscv_xlen - VPN_WIDTH)                     ;\
    srli t2, t2, (__riscv_xlen - VPN_WIDTH - ENTRY_LOG2)        ;\
    srli t0, PA_REG, 12                                         ;\
    slli t0, t0, 10                                             ;\
    LI(t1, PERMS)                                               ;\
    or t0, t0, t1                                               ;\
    .if (MODE == sv32x4)                                        ;\
        .if (LEVEL == 1)                                        ;\
            LA(t1, rvtest_Hroot_pg_tbl)                         ;\
        .elseif (LEVEL == 0)                                    ;\
            LA(t1, rvtest_hlvl0_pg_tbl)                         ;\
        .endif                                                  ;\
    .else                                                       ;\
        .if (MODE == sv39x4)                                    ;\
            .if (LEVEL == 2)                                    ;\
                LA(t1, rvtest_Hroot_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_hlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_hlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv48x4)                                ;\
            .if (LEVEL == 3)                                    ;\
                LA(t1, rvtest_Hroot_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_hlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_hlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_hlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv57x4)                                ;\
            .if (LEVEL == 4)                                    ;\
                LA(t1, rvtest_Hroot_pg_tbl)                     ;\
            .elseif (LEVEL == 3)                                ;\
                LA(t1, rvtest_hlvl3_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_hlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_hlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_hlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .endif                                                  ;\
    .endif                                                      ;\
    add  t1, t1, t2                                             ;\
    SREG t0, 0(t1)                                              ;


// Wrapper macro around VS_PTE_SETUP_ADDR_REG.
// PERMS and VA must be immediate values while Physical
// Address must be a label.
// Loads PA_LBL into a register, clears lower PPN bits based on
// LEVEL for superpage alignment, and passes it to VS_PTE_SETUP_ADDR_REG.
#define SUPERPAGE_VS_PTE_SETUP(MODE, PA_LBL, PERMS, VA, LEVEL)  ;\
    .if (MODE == sv32)                                          ;\
        .set PPN_SHIFT, (LEVEL*10)+12                           ;\
    .else                                                       ;\
        .set PPN_SHIFT, (LEVEL*9)+12                            ;\
    .endif                                                      ;\
    LA(t0, PA_LBL)                                              ;\
    srli t0, t0, PPN_SHIFT                                      ;\
    slli t0, t0, PPN_SHIFT                                      ;\
    VS_PTE_SETUP_ADDR_REG(MODE, t0, PERMS, VA, LEVEL)           ;\


// Wrapper macro around VS_PTE_SETUP_ADDR_REG allowing both
// Physical and Guest Physical Addresses.
// If ADDR_TYPE==ADDR_PA, ADDR must be an address label.
// if ADDR_TYPE==ADDR_GPA, ADDR must be an immediate value. Loads
// ADDR into a register and passes it to VS_PTE_SETUP_ADDR_REG.
// PERMS and VA must be immediate values.
#define VS_PTE_SETUP(MODE, ADDR_TYPE, ADDR, PERMS, VA, LEVEL)   ;\
    .if (ADDR_TYPE == ADDR_PA)                                  ;\
        LA(t0, ADDR)                                            ;\
    .elseif (ADDR_TYPE == ADDR_GPA)                             ;\
        LI(t0, ADDR)                                            ;\
    .endif                                                      ;\
    VS_PTE_SETUP_ADDR_REG(MODE, t0, PERMS, VA, LEVEL)           ;\


// Create a VS-stage page table entry with both the mapped address and the virtual
// address in registers, so a test can derive its mapping windows at run time instead
// of hard-coding them. PERMS is an immediate. t0, t1 and t2 are clobbered; VA_REG is
// consumed before any of them is written and ADDR_REG before t1, so either may be t0
// or t1. Neither may be t2.
#define VS_PTE_SETUP_VA_REG(MODE, ADDR_REG, PERMS, VA_REG, LEVEL) ;\
    .if (MODE == sv32)                                          ;\
        .set VPN_WIDTH, 10                                      ;\
        .set VPN_SHIFT, (LEVEL * 10) + 12                       ;\
        .set ENTRY_LOG2, 2                                      ;\
    .else                                                       ;\
        .set VPN_WIDTH, 9                                       ;\
        .set VPN_SHIFT, (LEVEL * 9) + 12                        ;\
        .set ENTRY_LOG2, 3                                      ;\
    .endif                                                      ;\
    srli t2, VA_REG, VPN_SHIFT                                  ;\
    slli t2, t2, (__riscv_xlen - VPN_WIDTH)                     ;\
    srli t2, t2, (__riscv_xlen - VPN_WIDTH - ENTRY_LOG2)        ;\
    srli t0, ADDR_REG, 12                                       ;\
    slli t0, t0, 10                                             ;\
    LI(t1, PERMS)                                               ;\
    or t0, t0, t1                                               ;\
    .if (MODE == sv32)                                          ;\
        .if (LEVEL == 1)                                        ;\
            LA(t1, rvtest_Vroot_pg_tbl)                         ;\
        .elseif (LEVEL == 0)                                    ;\
            LA(t1, rvtest_vlvl0_pg_tbl)                         ;\
        .endif                                                  ;\
    .else                                                       ;\
        .if (MODE == sv39)                                      ;\
            .if (LEVEL == 2)                                    ;\
                LA(t1, rvtest_Vroot_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_vlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_vlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv48)                                  ;\
            .if (LEVEL == 3)                                    ;\
                LA(t1, rvtest_Vroot_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_vlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_vlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_vlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv57)                                  ;\
            .if (LEVEL == 4)                                    ;\
                LA(t1, rvtest_Vroot_pg_tbl)                     ;\
            .elseif (LEVEL == 3)                                ;\
                LA(t1, rvtest_vlvl3_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_vlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_vlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_vlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .endif                                                  ;\
    .endif                                                      ;\
    add  t1, t1, t2                                             ;\
    SREG t0, 0(t1)                                              ;


// Create a VS-stage page table entry and write it into the appropriate
// page table for the specified translation mode & level.
// Address (PA or GPA) must be passed in a register while
// PERMS and VA must be immediate values.
// t0, t1 & t2 are clobbered.
#define VS_PTE_SETUP_ADDR_REG(MODE, ADDR_REG, PERMS, VA, LEVEL) ;\
    srli t0, ADDR_REG, 12                                       ;\
    slli t0, t0, 10                                             ;\
    LI(t1, PERMS)                                               ;\
    or t0, t0, t1                                               ;\
    .if (MODE == sv32)                                          ;\
        .if (LEVEL == 1)                                        ;\
            LA(t1, rvtest_Vroot_pg_tbl)                         ;\
        .elseif (LEVEL == 0)                                    ;\
            LA(t1, rvtest_vlvl0_pg_tbl)                         ;\
        .endif                                                  ;\
        LI(t2, ((VA >> ((LEVEL * 10) + 12)) & 0x3FF) << 2)      ;\
    .else                                                       ;\
        .if (MODE == sv39)                                      ;\
            .if (LEVEL == 2)                                    ;\
                LA(t1, rvtest_Vroot_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_vlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_vlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv48)                                  ;\
            .if (LEVEL == 3)                                    ;\
                LA(t1, rvtest_Vroot_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_vlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_vlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_vlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .elseif (MODE == sv57)                                  ;\
            .if (LEVEL == 4)                                    ;\
                LA(t1, rvtest_Vroot_pg_tbl)                     ;\
            .elseif (LEVEL == 3)                                ;\
                LA(t1, rvtest_vlvl3_pg_tbl)                     ;\
            .elseif (LEVEL == 2)                                ;\
                LA(t1, rvtest_vlvl2_pg_tbl)                     ;\
            .elseif (LEVEL == 1)                                ;\
                LA(t1, rvtest_vlvl1_pg_tbl)                     ;\
            .elseif (LEVEL == 0)                                ;\
                LA(t1, rvtest_vlvl0_pg_tbl)                     ;\
            .endif                                              ;\
        .endif                                                  ;\
        LI(t2, ((VA >> ((LEVEL * 9) + 12)) & 0x1FF) << 3)       ;\
    .endif                                                      ;\
    add  t1, t1, t2                                             ;\
    SREG t0, 0(t1)                                              ;


// Configure HGATP for the specified translation mode (sv32x4,
// sv39x4, sv48x4 or sv57x4) using rvtest_Hroot_pg_tbl as the
// root page table. t0 and t1 are clobbered.
#define HGATP_SETUP(MODE)                                       ;\
    .if (MODE == sv32x4)                                        ;\
        LI(t1, (HGATP32_MODE) & (HGATP_MODE_SV32X4 << 31))      ;\
    .elseif (MODE == sv39x4)                                    ;\
        LI(t1, (HGATP64_MODE) & (HGATP_MODE_SV39X4 << 60))      ;\
    .elseif (MODE == sv48x4)                                    ;\
        LI(t1, (HGATP64_MODE) & (HGATP_MODE_SV48X4 << 60))      ;\
    .elseif (MODE == sv57x4)                                    ;\
        LI(t1, (HGATP64_MODE) & (HGATP_MODE_SV57X4 << 60))      ;\
    .endif                                                      ;\
    LA(  t0, rvtest_Hroot_pg_tbl)                               ;\
    srli t0, t0, 12                                             ;\
    or   t0, t0, t1                                             ;\
    csrw hgatp, t0                                              ;


// Configure VSATP for the specified translation mode (sv32, sv39,
// sv48 or sv57) using rvtest_Vroot_pg_tbl as the root page table.
// PT_ADDR_SPACE may be ADDR_PA or ADDR_GPA. Use ADDR_PA when the root page
// table is not G-stage translated (hgatp.MODE=Bare), and ADDR_GPA when
// it is mapped through G-stage translation.
// If PT_ADDR_SPACE==ADDR_GPA, gpa_rvtest_Vroot_pg_tbl must be
// defined as an immediate value containing the Guest Physical
// Address of the root page table.
// t0 and t1 are clobbered.
#define VSATP_SETUP(MODE, PT_ADDR_SPACE)                        ;\
    .if (MODE == sv32)                                          ;\
        LI(t1, (SATP32_MODE) & (SATP_MODE_SV32 << 31))          ;\
    .elseif (MODE == sv39)                                      ;\
        LI(t1, (SATP64_MODE) & (SATP_MODE_SV39 << 60))          ;\
    .elseif (MODE == sv48)                                      ;\
        LI(t1, (SATP64_MODE) & (SATP_MODE_SV48 << 60))          ;\
    .elseif (MODE == sv57)                                      ;\
        LI(t1, (SATP64_MODE) & (SATP_MODE_SV57 << 60))          ;\
    .endif                                                      ;\
    .if (PT_ADDR_SPACE == ADDR_PA)                              ;\
        LA(  t0, rvtest_Vroot_pg_tbl)                           ;\
    .elseif (PT_ADDR_SPACE == ADDR_GPA)                         ;\
        LI(  t0, gpa_rvtest_Vroot_pg_tbl)                       ;\
    .endif                                                      ;\
    srli t0, t0, 12                                             ;\
    or   t0, t0, t1                                             ;\
    csrw vsatp, t0                                              ;
