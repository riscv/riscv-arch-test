// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International

// Minimal printf support for bare-metal FeatureExtractorC.
// Supports plain strings, %s, %c, and %%.
// This is enough for YAML output and avoids libgcc division helpers.

#include <stdarg.h>

extern void arch_write_str_asm(const char *s);

static int put_char(char c)
{
    char buf[2];

    buf[0] = c;
    buf[1] = '\0';

    arch_write_str_asm(buf);
    return 1;
}

static int put_str(const char *s)
{
    int count = 0;

    if (s == 0) {
        s = "(null)";
    }

    while (s[count] != '\0') {
        count++;
    }

    arch_write_str_asm(s);
    return count;
}

int printf(const char *fmt, ...)
{
    va_list ap;
    int count = 0;

    va_start(ap, fmt);

    while (*fmt != '\0') {
        if (*fmt != '%') {
            const char *span_start = fmt;
            while (*fmt != '\0' && *fmt != '%')
                fmt++;
            count += (int)(fmt - span_start);
            /* Write span using put_char to avoid VLA stack allocation. */
            const char *p = span_start;
            while (p < fmt)
                put_char(*p++);
            continue;
        }

        fmt++;

        if (*fmt == '\0') {
            count += put_char('%');
            break;
        }

        if (*fmt == 's') {
            const char *s = va_arg(ap, const char *);
            count += put_str(s);
        } else if (*fmt == 'c') {
            char c = (char)va_arg(ap, int);
            count += put_char(c);
        } else if (*fmt == '%') {
            count += put_char('%');
        } else {
            // Unsupported specifier: print literally without consuming
            // a va_arg. Safe because all callsites in this tool only
            // use %s, %c, and %%.
            count += put_char('%');
            count += put_char(*fmt);
        }

        fmt++;
    }

    va_end(ap);
    return count;
}

int puts(const char *s)
{
    int count = put_str(s);
    count += put_char('\n');
    return count;
}
