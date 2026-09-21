// picorv32-act-main.cc
// Verilator harness for running ACT self-checking ELFs on PicoRV32.
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
//
// This replaces picorv32's own testbench.cc, which ends in an unconditional
// exit(0) and imposes no cycle limit at all under Verilator (the 1,000,000-cycle
// timeout in testbench.v lives inside the `ifndef VERILATOR` Icarus wrapper).
// With the stock harness a hung test, a failing test and a passing test are all
// indistinguishable from the shell. See
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/testbench.cc#L42
// and
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/testbench.v#L28-L33
//
// Exit codes:
//   0  the core trapped with the picorv32 pass token (123456789 written to
//      0x2000_0000) latched, i.e. RVMODEL_HALT_PASS ran
//   1  the core trapped without the pass token (RVMODEL_HALT_FAIL, an illegal
//      instruction, or a misaligned access)
//   2  the cycle limit expired without the core ever trapping (hang)
//   3  the testbench ended the simulation without the core trapping, which for
//      this testbench means an out-of-bounds bus access

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "Vpicorv32_wrapper.h"
#include "verilated.h"

// Roughly 25x the longest ACT test observed on this core, and still only a few
// seconds of wall time. Override with +max-cycles=<n>.
static const long DEFAULT_MAX_CYCLES = 20000000L;

// The core is held in reset for this many cycles, matching the ~20 half-cycle
// reset of picorv32's own testbench.cc.
static const long RESET_CYCLES = 20L;

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);

  long max_cycles = DEFAULT_MAX_CYCLES;
  const char *plusarg = Verilated::commandArgsPlusMatch("max-cycles=");
  if (plusarg != NULL && plusarg[0] != '\0') {
    const char *eq = strchr(plusarg, '=');
    if (eq != NULL) {
      max_cycles = strtol(eq + 1, NULL, 0);
    }
  }

  Vpicorv32_wrapper *top = new Vpicorv32_wrapper;
  top->clk = 0;
  top->resetn = 0;

  long cycle = 0;
  for (; cycle < max_cycles && !Verilated::gotFinish(); cycle++) {
    if (cycle == RESET_CYCLES) {
      top->resetn = 1;
    }
    top->clk = 0;
    top->eval();
    if (Verilated::gotFinish()) {
      break;
    }
    top->clk = 1;
    top->eval();
  }

  const bool finished = Verilated::gotFinish();
  const bool trapped = top->trap != 0;
  const bool passed = top->tests_passed != 0;

  top->final();

  int rc;
  if (!finished) {
    printf("\nPICORV32-ACT: FAIL - cycle limit of %ld reached with no trap; the test hung\n", max_cycles);
    rc = 2;
  } else if (!trapped) {
    printf("\nPICORV32-ACT: FAIL - simulation ended after %ld cycles without the core trapping\n", cycle);
    printf("PICORV32-ACT: this testbench only $finishes early on an out-of-bounds bus access\n");
    rc = 3;
  } else if (!passed) {
    printf("\nPICORV32-ACT: FAIL - core trapped after %ld cycles without the pass token\n", cycle);
    rc = 1;
  } else {
    printf("\nPICORV32-ACT: PASS - core trapped after %ld cycles with the pass token\n", cycle);
    rc = 0;
  }

  delete top;
  fflush(stdout);
  return rc;
}
