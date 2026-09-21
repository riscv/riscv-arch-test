// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// console.h: minimal printf for the UDB feature extractor (see console.c).
// %d takes a long and %x an unsigned long.

#ifndef CONSOLE_H
#define CONSOLE_H

int printf(const char *fmt, ...);

#endif
