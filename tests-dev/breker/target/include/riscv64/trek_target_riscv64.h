// trek_target_riscv64.h
// Shared runtime for Breker Trek5 litmus tests in ACT
// Copyright (C) 2026 Breker Verification Systems
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0

#ifndef TREK_TARGET_RISCV64_H
#define TREK_TARGET_RISCV64_H

#include "riscv_arch_test_c.h"

typedef unsigned char      trek_uint8_t;
typedef unsigned int       trek_uint32_t;
typedef unsigned long long trek_uint64_t;

#define trek_read32(addr) (*((volatile trek_uint32_t *)(addr)))
#define trek_write32(value, addr) (trek_read32(addr)=((trek_uint32_t)(value)))
#define trek_read64(addr) (*((volatile trek_uint64_t *)(addr)))
#define trek_write64(value, addr) (trek_read64(addr)=((trek_uint64_t)(value)))

#define trek_mem_barrier_ww()  asm volatile("fence w,w")
#define trek_mem_barrier_rr()  asm volatile("fence r,r")

#define trek_read32_shared(addr) ({             \
      trek_uint32_t __tmp = trek_read32(addr);  \
      trek_mem_barrier_rr();                    \
      __tmp; })
#define trek_write32_shared(value, addr) trek_mem_barrier_ww(); trek_write32(value, addr); trek_mem_barrier_ww()
#define TREK_UNUSED(x) (void)(x)

#define trek_memory_setup()
#define trek_t2c_wait(thread_id) 0
#define trek_t2c_get(thread_id) 0
#define trek_flush_mbox_queue()

// Tests boot into the lowest supported privilege mode, so read mhartid through T-SBI.
#define trek_get_cpu_idx() tsbi_csr_read(CSR_MHARTID)
#define trek_get_timestamp() (0)

volatile int trek_printf_lock = 0;
#define trek_acquire_print_lock() while (!__sync_bool_compare_and_swap(&trek_printf_lock, 0, 1))
#define trek_release_print_lock() while (!__sync_bool_compare_and_swap(&trek_printf_lock, 1, 0))

#define trek_puts(str)                          \
  {                                             \
  trek_acquire_print_lock();                    \
  puts(str);                                    \
  trek_release_print_lock();                    \
  }

#define trek_printf(...)                        \
  {                                             \
  trek_acquire_print_lock();                    \
  printf(__VA_ARGS__);                          \
  trek_release_print_lock();                    \
  }

#define trek_error(...)                         \
  {                                             \
  trek_acquire_print_lock();                    \
  print_error(__VA_ARGS__);                     \
  trek_release_print_lock();                    \
  }

#undef trek_exit
#define trek_exit(status) (status ? rvtest_fail() : rvtest_pass() );

// Each test defines trek_main().
void trek_test_setup(void) {}
void trek_test_teardown(void) {}

int trek_main(void);

int main(void)
{
  return trek_main();
}

#endif // TREK_TARGET_RISCV64_H
