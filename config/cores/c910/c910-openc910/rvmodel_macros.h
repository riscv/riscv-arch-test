# rvmodel_macros.h
# RVMODEL macro definitions for the XuanTie OpenC910 in its open-source SoC
# Written against T-head-Semi/openc910 commit b91c90914c19f114d35c8f6b73408eb241ed847c
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# Testbench magic addresses.  All three sit in the strongly-ordered device region
# 0x0100_0000-0x01FF_FFFF, so stores to them are never absorbed by the D-cache.
#   Quote (PMA default map, the `FPGA` branch that cpu_cfig.h selects):
#     PA < 0x0100_0000 -> cacheable/bufferable/shareable,
#     0x0100_0000-0x01FF_FFFF -> strongly ordered device
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/mmu/rtl/sysmap.h
#
# C910_CONSOLE is the vendor testbench's character output.
#   Quote: "(cpu_awaddr[31:0] == 32'h01ff_fff0) && cpu_wvalid && `clk_en) ...
#           $write("%c", `SOC_TOP.biu_pad_wdata[7:0]);"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L329-L351
#
# C910_HALT_PASS / C910_HALT_FAIL are added by the ACT testbench patch in
# .github/scripts/setup-c910.sh.  The vendor mechanism they replace snooped the
# integer write-back bus for 64'h444333222 / 64'h2382348720, which cannot be used for
# ACT: a test that legitimately computes 0x444333222 would end the run as a PASS, and
# the fail comparison's third disjunct repeats the PASS constant.
#   Quote: "if(value0 == 64'h444333222 || value1 == 64'h444333222 || value2 == 64'h444333222)
#           ... else if (value0 == 64'h2382348720 || value1 == 64'h2382348720 || value2 == 64'h444333222)"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L304-L327
.EQU C910_CONSOLE,   0x01FFFFF0
.EQU C910_HALT_PASS, 0x01FFFFE0
.EQU C910_HALT_FAIL, 0x01FFFFD0

##### STARTUP #####

# RVMODEL_BOOT does three things, all of them required.
#
# (1) The reset trampoline.  pad_core0_rvba is tied to 0, so hart 0 starts fetching at
#     address 0 in M-mode, but ACT links its tests at TEST_BASE = 0x1000.  A two
#     instruction absolute jump is emitted into .text.reset, which link.ld places at 0.
#     (%hi/%lo rather than `la` so the jump is absolute and independent of the code
#     model.)  This section is empty in the Sail reference build, where RVMODEL_BOOT is
#     #undef'd and the model enters at the ELF entry point.
#       Quote: ".pad_core0_rvba    (40'b0        ),"
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/common/cpu_sub_system_axi.v#L226
#       Quote: "assign mrvbr_value[63:0] = {24'b0, mrvbr_reg[38:0], 1'b0};" -> cp0_ifu_rvbr
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/cp0/rtl/ct_cp0_regs.v#L3065
#
# (2) Clear mxstatus.THEADISAEE (bit 22) and mxstatus.MAEE (bit 21), which BOTH RESET
#     TO 1.  This is the single most important line in this file.
#       Quote: "if (!cpurst_b) begin cskyisaee <= 1'b1; maee <= 1'b1; ... clintee <= 1'b1; ucme <= 1'b1;"
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/cp0/rtl/ct_cp0_regs.v#L2720-L2731
#     THEADISAEE=1 makes the whole XuanTie custom instruction set live in the custom-0
#     opcode, so encodings the architecture requires to be illegal would execute.
#       Quote (user manual 16.1.7.1, p.331): "THEADISAEE-使能扩展指令集：当 THEADISAEE
#       为 0 时，使用 C910 扩展指令集时产生非法指令异常。"
#       ("THEADISAEE - enable the extension instruction set: when THEADISAEE is 0,
#       using the C910 extended instruction set raises an illegal instruction
#       exception.")
#     MAEE=1 reinterprets Sv39 PTE bits 63:59 as XuanTie memory attributes
#     (SO/C/B/SH/Sec) instead of leaving them reserved, so every Sv39 test that writes
#     or checks those bits would diverge.
#       Quote: "assign ptw_ref_pma[4:0] = cp0_mmu_maee ? lsu_data_flop[63:59] : sysmap_mmu_flg3[4:0];"
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/mmu/rtl/ct_mmu_ptw.v#L709-L710
#       Quote (user manual 16.1.7.1, p.331): "MAEE-扩展 MMU 地址属性：当 MAEE 为 0 时，
#       不扩展 MMU 地址属性。当 MAEE 为 1 时，MMU 的 pte 中扩展地址属性位。"
#       ("MAEE - extended MMU address attributes: when MAEE is 0 the MMU address
#       attributes are not extended; when MAEE is 1 the PTE carries extended address
#       attribute bits.")
#     MEASURED: with the two bits left set, the XTheadBa encoding 0x0031108B
#     (th.addsl x1, x2, x3, 0) executes and retires; after this csrc it raises mcause 2
#     and mxstatus bits 22:21 read back 0.
#
#     mxstatus.CLINTEE (17) and mxstatus.UCME (16) also reset to 1 and are LEFT ALONE.
#     CLINTEE=1 is what routes the CLINT's supervisor software and timer interrupts
#     into sip/mip, so ACT's S-mode software-interrupt macros need it.
#       Quote: "assign stip = biu_cp0_st_int && clintee || stip_reg;"
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/cp0/rtl/ct_cp0_regs.v#L2116-L2117
#     UCME has nothing to do with counters despite the name - it gates U-mode execution
#     of the XuanTie custom cache instructions, which THEADISAEE=0 has already made
#     illegal, so it is irrelevant here.  Unprivileged counter access is governed by
#     mcounteren/scounteren in the standard way.
#       Quote: "assign st_ag_prvlg_obey = (cp0_yy_priv_mode[1:0] == 2'b00) &&
#               (st_ag_dcache_inst && !(cp0_lsu_ucme && st_ag_dcache_user_allow_inst) ..."
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/lsu/rtl/ct_lsu_st_ag.v#L1170-L1177
#       Quote (user manual 16.1.7.1, p.330): "UCME-U 态执行扩展 cache 指令"
#       ("UCME - execute extended cache instructions in U state")
#
# (3) Enable the caches.  mcor (0x7C2) = 0x70011 invalidates I-cache, D-cache and BTB;
#     mhcr (0x7C1) |= 0x3 sets IE and DE.  Both reset to 0, i.e. the core boots with
#     every cache off and every fetch going to the AXI SRAM.
#     MEASURED on this build: a 2000-iteration ALU loop takes 102,132 cycles with the
#     caches off and 23,303 with them on - a 4.4x saving on every test in the suite.
#
# Registers: RVMODEL_BOOT runs at label rvmodel_boot before any test state exists, so
# t0 is free.
#define RVMODEL_BOOT                                            \
  .pushsection .text.reset,"ax",@progbits                      ;\
  .globl c910_reset_trampoline                                 ;\
  c910_reset_trampoline:                                       ;\
    lui  t0, %hi(rvtest_entry_point)                           ;\
    addi t0, t0, %lo(rvtest_entry_point)                       ;\
    jr   t0                                                    ;\
  .popsection                                                  ;\
  li   t0, (1 << 22) | (1 << 21)                               ;\
  csrc 0x7c0, t0        /* mxstatus: THEADISAEE=0, MAEE=0 */   ;\
  li   t0, 0x70011                                             ;\
  csrw 0x7c2, t0        /* mcor: invalidate I$, D$ and BTB */  ;\
  li   t0, 0x3                                                 ;\
  csrs 0x7c1, t0        /* mhcr: IE | DE */                    ;

##### TERMINATION #####

# A store to the magic pass/fail address ends the simulation and writes the verdict
# into run_case.report.  The simulator's own exit status is always 0 (sim_main1.cpp
# returns 0 unconditionally and both halt paths reach it through $finish), so
# run-c910.sh derives the verdict from run_case.report plus the RVCP-SUMMARY line.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/sim_main1.cpp
#define RVMODEL_HALT_PASS  \
  li t0, C910_HALT_PASS   ;\
  sw x0, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, C910_HALT_FAIL   ;\
  sw x0, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# The testbench prints the byte lane selected by wstrb, and only recognises the four
# 4-byte lanes of the 16-byte AXI beat (wstrb 0xF, 0xF0, 0xF00, 0xF000).  A byte store
# (sb, wstrb 0x1) is NOT printed, so the character has to go out as a word store to
# the lane-0 address.
#   Quote: "if(cpu_wstrb[15:0] == 16'hf) $write("%c", `SOC_TOP.biu_pad_wdata[7:0]);"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L335-L338
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, C910_CONSOLE     ;                        \
  sw   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access faults #####

# The AXI interconnect routes 0x0200_0000-0x0FFF_FFFF (and everything at or above
# 0x2000_0000 that is not the core's own APB window) to an error responder that
# returns SLVERR, which the core reports as a load/store access fault.
#   Quote: "parameter ERR1_START = 40'h0200_0000;  parameter ERR1_END = 40'h0fff_ffff;"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/axi/axi_interconnect128.v#L362-L363
#   Quote: "assign rresp[1:0] = 2'b10;" (SLVERR)
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/axi/axi_err128.v#L211
# 0x0200_0000 is outside every sail.json memory region too, so the reference model
# faults on it as well.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x02000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

##### Machine Timer #####

# RVMODEL_MTIME_ADDRESS IS DELIBERATELY UNDEFINED, which turns off the whole
# machine-timer-interrupt family.  C910 has no memory-mapped mtime to point it at:
# the CLINT register map contains MSIP, MTIMECMP, SSIP and STIMECMP but no MTIME, and
# the timer's current value is only reachable through the `time` CSR.
#   Quote: "parameter MSIP0 = 16'h0000; ... parameter MTIMECMP0 = 16'h4000; ...
#           parameter SSIP0 = 16'hC000; ... parameter STIMECMP0 = 16'hD000;"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/clint/rtl/ct_clint_func.v#L148-L168
#   Quote (user manual 8.1.3, p.69): "在多核系统中仅存在一个 64 位系统计时器 MTIME ...
#   系统计时器不可写，仅能通过 reset 清 0。系统计时器的当前值可通过读取 PMU 的 TIME
#   寄存器获取。"
#   ("In a multicore system there is only one 64-bit system timer MTIME ... The system
#   timer is not writable and can only be cleared by reset.  Its current value can be
#   obtained by reading the PMU's TIME register.")
# Note that the `time` CSR itself IS implemented natively (TIME_CSR_IMPLEMENTED: true
# in the UDB config), so Zicntr needs no emulation and no RVMODEL_MTIME_ADDRESS; it is
# only the timer INTERRUPT tests that are lost.
#define RVMODEL_TIMER_INT_SOON_DELAY 10000

# The CLINT sits in the core's own 64 KB window inside the APB base the SoC ties to
# 0xB000_0000, so the CLINT is at 0xB400_0000.
#   Quote: "`define CLINT_BASE_START 11'h400 ... assign sel_clint = (apbif_addr[26:16] == `CLINT_BASE_START);"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/ciu/rtl/ct_ciu_apbif.v#L367-L375
#   Quote: "`define APB_BASE_ADDR       40'hb0000000"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L53
# RVMODEL_MTIMECMP_ADDRESS is also left undefined.  It is only reachable together
# with RVMODEL_MTIME_ADDRESS, and defining it alone would make rvtest_setup.h emit
# LA(t0, 0xB4004000) at boot.  LA expands to `la`, which under -mcmodel=medany is
# auipc+addi with a +/-2 GB reach; the tests link at 0x1000 and the CLINT is 2.8 GB
# away, so the assembler reports "offset too large".  Every CLINT access in this file
# therefore goes through `li`, which materialises the full 64-bit constant.
#define CLINT_BASE_ADDRESS 0xB4000000
#define C910_MTIMECMP_ADDRESS (CLINT_BASE_ADDRESS + 0x4000)

##### Machine Interrupts #####

# RVMODEL_MSIP_ADDRESS is deliberately left undefined for the same "offset too large"
# reason: when it is defined, rvtest_setup.h reaches the CLINT with LA rather than li.
# Leaving it undefined makes the framework fall back to RVMODEL_SET_MSW_INT /
# RVMODEL_CLR_MSW_INT below, which do the same thing with an absolute `li`.
#   Quote: "parameter MSIP0      = 16'h0000;"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/clint/rtl/ct_clint_func.v#L148
#define C910_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)

# There is no software-drivable machine external interrupt source in this SoC.  The
# PLIC is present at 0xB000_0000 with 144 sources, but every one of those source pins
# comes from a peripheral that the testbench leaves idle, and the PLIC has no
# software-settable pending register, so ACT cannot raise MEIP or SEIP on demand.
# These hooks are therefore empty and the external-interrupt suites are excluded in
# ci.yaml.
#   Quote: "`define PLIC_INT_NUM   144"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/cpu/rtl/cpu_cfig.h#L254
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)

#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li _R1, 1                          ;\
  li _R2, C910_MSIP_ADDRESS       ;\
  sw _R1, 0(_R2)                     ;

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li _R2, C910_MSIP_ADDRESS       ;\
  sw x0, 0(_R2)                      ;

##### Supervisor Interrupts #####

# The CLINT's supervisor software interrupt register.  It only reaches sip.SSIP while
# mxstatus.CLINTEE is set, which it is out of reset and which RVMODEL_BOOT leaves set.
#   Quote: "parameter SSIP0      = 16'hC000;"
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/clint/rtl/ct_clint_func.v#L162
#define C910_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#define RVMODEL_SET_SSW_INT(_R1, _R2) \
  li _R1, 1                          ;\
  li _R2, C910_SSIP_ADDRESS          ;\
  sw _R1, 0(_R2)                     ;

#define RVMODEL_CLR_SSW_INT(_R1, _R2) \
  li _R2, C910_SSIP_ADDRESS          ;\
  sw x0, 0(_R2)                      ;

#endif // _RVMODEL_MACROS_H
