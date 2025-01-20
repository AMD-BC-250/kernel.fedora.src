// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef _LINUX_STDARG_H
#define _LINUX_STDARG_H

typedef __builtin_va_list va_list;
#if defined(__STDC_VERSION__) && __STDC_VERSION__ > 201710L
#define va_start(v, ...) __builtin_va_start(v, 0)
#ifdef __has_builtin
#if __has_builtin(__builtin_c23_va_start)
#undef va_start
#define va_start(...)	__builtin_c23_va_start(__VA_ARGS__)
#endif
#endif
#else
#define va_start(v, l)	__builtin_va_start(v, l)
#endif
#define va_end(v)	__builtin_va_end(v)
#define va_arg(v, T)	__builtin_va_arg(v, T)
#define va_copy(d, s)	__builtin_va_copy(d, s)

#endif
