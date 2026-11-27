-- neorv32-act-top.vhd
-- NEORV32 processor configuration for ACT, converted to Verilog with `ghdl synth`.
-- Copyright (c) 2026, Harvey Mudd College
-- SPDX-License-Identifier: Apache-2.0
--
-- The generics ACT depends on are set here and explained in config/cores/neorv32/README.md; the
-- rest keep their defaults. The internal IMEM and DMEM are disabled, so every access outside the
-- internal IO region (0xFFE00000-0xFFFFFFFF) goes to the external bus (XBUS), where
-- neorv32-act-tb.sv provides RAM and the testbench registers. Machine timer and software
-- interrupts come from the internal CLINT at 0xFFF40000.

library ieee;
use ieee.std_logic_1164.all;

library neorv32;
use neorv32.neorv32_package.all;

entity neorv32_act_top is
  generic (
    TRACE_EN : boolean := false -- simulation only: write the trace log neorv32_trace0.log
  );
  port (
    clk_i      : in  std_ulogic;
    rstn_i     : in  std_ulogic;
    xbus_adr_o : out std_ulogic_vector(31 downto 0);
    xbus_dat_o : out std_ulogic_vector(31 downto 0);
    xbus_we_o  : out std_ulogic;
    xbus_sel_o : out std_ulogic_vector(3 downto 0);
    xbus_stb_o : out std_ulogic;
    xbus_cyc_o : out std_ulogic;
    xbus_dat_i : in  std_ulogic_vector(31 downto 0);
    xbus_ack_i : in  std_ulogic;
    xbus_err_i : in  std_ulogic;
    irq_mei_i  : in  std_ulogic
  );
end entity;

architecture neorv32_act_top_rtl of neorv32_act_top is
begin

  neorv32_top_inst: neorv32_top
  generic map (
    -- General --
    CLOCK_FREQUENCY     => 100_000_000,
    DUAL_CORE_EN        => false,
    TRACE_PORT_EN       => TRACE_EN,
    TRACE_SIMLOG_EN     => TRACE_EN,
    -- Boot Configuration --
    BOOT_MODE_SELECT    => 1,           -- start at BOOT_ADDR_CUSTOM
    BOOT_ADDR_CUSTOM    => x"80000000",
    -- On-Chip Debugger --
    OCD_EN              => false,
    -- RISC-V CPU Extensions --
    RISCV_ISA_C         => true,
    RISCV_ISA_E         => false,
    RISCV_ISA_M         => true,
    RISCV_ISA_U         => true,
    RISCV_ISA_Zaamo     => true,
    RISCV_ISA_Zalrsc    => true,
    RISCV_ISA_Zba       => true,
    RISCV_ISA_Zbb       => true,
    RISCV_ISA_Zbc       => true,
    RISCV_ISA_Zbkb      => true,
    RISCV_ISA_Zbkc      => true,
    RISCV_ISA_Zbkx      => true,
    RISCV_ISA_Zbs       => true,
    RISCV_ISA_Zcb       => true,
    RISCV_ISA_Zcmop     => true,
    RISCV_ISA_Zfinx     => false,
    RISCV_ISA_Zibi      => false,
    RISCV_ISA_Zicntr    => true,
    RISCV_ISA_Zicond    => true,
    RISCV_ISA_Zihpm     => true,
    RISCV_ISA_Zimop     => true,
    RISCV_ISA_Zknd      => true,
    RISCV_ISA_Zkne      => true,
    RISCV_ISA_Zknh      => true,
    RISCV_ISA_Zksed     => true,
    RISCV_ISA_Zksh      => true,
    RISCV_ISA_Zmmul     => false,
    RISCV_ISA_Smcntrpmf => true,
    RISCV_ISA_Xcfu      => false,
    -- Tuning Options --
    CPU_CONSTT_BR_EN    => false,
    CPU_FAST_MUL_EN     => true,
    CPU_FAST_MUL_REGS   => 1,
    CPU_FAST_SHIFT_EN   => true,
    CPU_RF_ARCH_SEL     => 0,
    -- Physical Memory Protection --
    PMP_NUM_REGIONS     => 16,
    PMP_MIN_GRANULARITY => 4,
    PMP_TOR_MODE_EN     => true,
    PMP_NAP_MODE_EN     => true,
    -- Hardware Performance Monitors --
    HPM_NUM_CNTS        => 4,
    HPM_CNT_WIDTH       => 64,
    -- Internal Memories --
    IMEM_EN             => false,
    DMEM_EN             => false,
    -- CPU Caches --
    ICACHE_EN           => true,
    ICACHE_NUM_BLOCKS   => 64,
    DCACHE_EN           => false,
    CACHE_BLOCK_SIZE    => 64,
    CACHE_BURSTS_EN     => true,
    CACHE_UC_BASE       => x"F0000000",
    -- External Bus Interface --
    XBUS_EN             => true,
    XBUS_TIMEOUT        => 2048,
    XBUS_REGSTAGE_EN    => false,
    -- Core-Local Interruptor --
    IO_CLINT_EN         => true
  )
  port map (
    clk_i      => clk_i,
    rstn_i     => rstn_i,
    xbus_adr_o => xbus_adr_o,
    xbus_dat_o => xbus_dat_o,
    xbus_we_o  => xbus_we_o,
    xbus_sel_o => xbus_sel_o,
    xbus_stb_o => xbus_stb_o,
    xbus_cyc_o => xbus_cyc_o,
    xbus_dat_i => xbus_dat_i,
    xbus_ack_i => xbus_ack_i,
    xbus_err_i => xbus_err_i,
    irq_mei_i  => irq_mei_i
  );

end architecture;
