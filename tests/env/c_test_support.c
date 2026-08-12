// c_test_support.c
// Minimal ACT runtime support for C tests
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0

// Consider pulling in a printf library instead of this custom implementation
// if it ever becomes insufficient.

#include <stdarg.h>
#include <stdint.h>

// Provided by rvtest_setup.h.
extern void rvmodel_io_write_str_c(const char *str);

// Provided by c_test_start.S.
extern void c_halt_pass(void) __attribute__((noreturn));
extern void c_halt_fail(void) __attribute__((noreturn));

int putchar(int ch)
{
  char buf[2] = {(char)ch, '\0'};
  rvmodel_io_write_str_c(buf);
  return (unsigned char)ch;
}

int puts(const char *s)
{
  while (*s != '\0')
  {
    putchar(*s++);
  }
  putchar('\n');
  return 0;
}

static void print_str(const char *s)
{
  if (s == 0)
  {
    s = "(null)";
  }
  while (*s != '\0')
  {
    putchar(*s++);
  }
}

static void print_uint(uintmax_t val, unsigned base, int upper)
{
  char buf[32];
  const char *digits = upper ? "0123456789ABCDEF" : "0123456789abcdef";
  int i = 0;

  if (val == 0)
  {
    buf[i++] = '0';
  }
  while (val != 0)
  {
    buf[i++] = digits[val % base];
    val /= base;
  }
  while (i != 0)
  {
    putchar(buf[--i]);
  }
}

static void print_int(intmax_t val)
{
  if (val < 0)
  {
    putchar('-');
    print_uint((uintmax_t)(-(val + 1)) + 1, 10, 0);
  }
  else
  {
    print_uint((uintmax_t)val, 10, 0);
  }
}

static void skip_format_modifiers(const char **fmt)
{
  while (**fmt == '-' || **fmt == '+' || **fmt == ' ' || **fmt == '0' || **fmt == '#')
  {
    (*fmt)++;
  }
  while (**fmt >= '0' && **fmt <= '9')
  {
    (*fmt)++;
  }
  if (**fmt == '.')
  {
    (*fmt)++;
    while (**fmt >= '0' && **fmt <= '9')
    {
      (*fmt)++;
    }
  }
}

int vprintf(const char *fmt, va_list ap)
{
  for (; *fmt != '\0'; fmt++)
  {
    if (*fmt != '%')
    {
      putchar(*fmt);
      continue;
    }

    fmt++;
    skip_format_modifiers(&fmt);

    int longcnt = 0;
    int zmod = 0;
    while (*fmt == 'l')
    {
      longcnt++;
      fmt++;
    }
    if (*fmt == 'z')
    {
      zmod = 1;
      fmt++;
    }

    switch (*fmt)
    {
    case 'c':
      putchar((char)va_arg(ap, int));
      break;
    case 's':
      print_str(va_arg(ap, const char *));
      break;
    case 'd':
    case 'i':
      if (longcnt >= 2 || zmod != 0)
      {
        print_int(va_arg(ap, intmax_t));
      }
      else if (longcnt == 1)
      {
        print_int(va_arg(ap, long));
      }
      else
      {
        print_int(va_arg(ap, int));
      }
      break;
    case 'u':
      if (longcnt >= 2 || zmod != 0)
      {
        print_uint(va_arg(ap, uintmax_t), 10, 0);
      }
      else if (longcnt == 1)
      {
        print_uint(va_arg(ap, unsigned long), 10, 0);
      }
      else
      {
        print_uint(va_arg(ap, unsigned), 10, 0);
      }
      break;
    case 'x':
    case 'X':
      if (longcnt >= 2 || zmod != 0)
      {
        print_uint(va_arg(ap, uintmax_t), 16, *fmt == 'X');
      }
      else if (longcnt == 1)
      {
        print_uint(va_arg(ap, unsigned long), 16, *fmt == 'X');
      }
      else
      {
        print_uint(va_arg(ap, unsigned), 16, *fmt == 'X');
      }
      break;
    case 'p':
      putchar('0');
      putchar('x');
      print_uint((uintptr_t)va_arg(ap, void *), 16, 0);
      break;
    case '%':
      putchar('%');
      break;
    case '\0':
      fmt--;
      break;
    default:
      putchar('%');
      putchar(*fmt);
      break;
    }
  }

  return 0;
}

int printf(const char *fmt, ...)
{
  va_list ap;
  va_start(ap, fmt);
  int ret = vprintf(fmt, ap);
  va_end(ap);
  return ret;
}

void __attribute__((noreturn)) rvtest_pass(void)
{
  c_halt_pass();
}

void __attribute__((noreturn)) rvtest_fail(void)
{
  c_halt_fail();
}

void __attribute__((noreturn)) print_error(const char *fmt, ...)
{
  va_list ap;
  va_start(ap, fmt);
  vprintf(fmt, ap);
  va_end(ap);
  rvtest_fail();
}

void __attribute__((noreturn)) c_test_exit(long code)
{
  if (code == 0)
  {
    rvtest_pass();
  }
  print_error("C test main() returned nonzero exit code %ld\n", code);
}
