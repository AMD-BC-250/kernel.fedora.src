#!/usr/bin/python3

import sys

verbose_spec=True

variants = {
    # kernel-zfcpdump (s390 specific kernel for zfcpdump)
    "zfcpdump": {
        "fedora": 0,
        "fedora_arches": [ "s390x" ],
        "rhel": 1,
        "rhel_arches": [ "s390x" ],
        "suffix": "zfcpdump",
        "debug_suffix": "",
        "efiuki": 0,
        "summary": "The Linux kernel compiled for zfcpdump usage",
        "description":
"""The kernel package contains the Linux kernel (vmlinuz) for use by the
zfcpdump infrastructure.""",
        "debug_summary": "",
        "debug_description": "",
    },
    # kernel-rt (x86_64 and aarch64 only PREEMPT_RT enabled kernel)
    "realtime": {
        "fedora": 0,
        "fedora_arches": [ "x86_64", "aarch64" ],
        "rhel": 1,
        "rhel_arches": [ "x86_64", "aarch64" ],
        "suffix": "rt",
        "debug_suffix": "rt-debug",
        "efiuki": 0,
        "summary": "The Linux kernel compiled with PREEMPT_RT enabled",
        "description":
"""This package includes a version of the Linux kernel compiled with the
PREEMPT_RT real-time preemption support""",
        "debug_summary": "The Linux PREEMPT_RT kernel compiled with extra debugging enabled",
        "debug_description":
"""The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system:  memory allocation, process allocation, device
input and output, etc.

This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.""",
    },
    # kernel-16k (aarch64 kernel with 16K page_size)
    "arm64_16k": {
        "fedora": 0,
        "fedora_arches": [ "aarch64" ],
        "rhel": 0,
        "rhel_arches": [ "aarch64" ],
        "suffix": "16k",
        "debug_suffix": "16k-debug",
        "efiuki": 1,
        "summary": "The Linux kernel compiled for 16k pagesize usage",
        "description":
"""The kernel package contains a variant of the ARM64 Linux kernel using
a 16K page size.""",
        "debug_summary": "The Linux kernel compiled for 16k pagesize with extra debugging enabled",
        "debug_description":
"""
The debug kernel package contains a variant of the ARM64 Linux kernel using
a 16K page size.
This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.""",
    },
    # kernel-64k (aarch64 kernel with 64K page_size)
    "arm64_64k": {
        "fedora": 0,
        "fedora_arches": [ "aarch64" ],
        "rhel": 1,
        "rhel_arches": [ "aarch64" ],
        "suffix": "64k",
        "debug_suffix": "64k-debug",
        "efiuki": 1,
        "summary": "The Linux kernel compiled for 64k pagesize usage",
        "description": "The kernel package contains a variant of the ARM64 Linux kernel using a 64K page size",
        "debug_summary": "The Linux kernel compiled with extra debugging enabled",
        "debug_description":
"""The debug kernel package contains a variant of the ARM64 Linux kernel using
a 64K page size.
This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.""",
    },
    # standard kernel
    "up" : {
        "fedora": 1,
        "fedora_arches": [ "x86_64", "aarch64", "ppc64le", "s390x" ],
        "rhel": 1,
        "rhel_arches": [ "x86_64", "aarch64", "ppc64le", "s390x" ],
        "suffix": "",
        "debug_suffix": "debug",
        "efiuki": 1,
        "summary": "The Linux kernel",
        "description":
"""The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system: memory allocation, process allocation, device
input and output, etc.""",
        "debug_summary": "The Linux kernel compiled with extra debugging enabled",
        "debug_description":
"""The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system:  memory allocation, process allocation, device
input and output, etc.

This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.""",
    },
}


def myexec(lineid, block):
    block = block[1:]
    for line in block:
        line = line.strip("\n")
        print("%dnl py:{lineid:d} {line:s}".format(lineid=lineid,line=line))
    code = "".join(block)
    exec(code, globals())
    print("%dnl py:{lineid:d} }}}}".format(lineid=lineid))


def build_var_table():
    for variant_name, variant in variants.items():
        table = []
        table.append(("VARIANT_NAME", str(variant_name)))
        for attr, attr_val in variant.items():
            attr_spec_var = ("VARIANT_%s" % attr).upper()
            if isinstance(attr_val, list):
                attr_val = " ".join(attr_val)
            table.append((attr_spec_var, attr_val))
        table = sorted(table, key = lambda x:x[0], reverse=True)
        variant['var_table'] = table

def for_each_variant(lineid, block):
    cmd = block[0].strip()
    cond = cmd[len("{{for_each_variant"):].strip()
    block = block[1:]

    if verbose_spec:
        print("%dnl py:{lineid:d} {line:s}".format(lineid=lineid,line=cmd))
        for line in block:
            line = line.strip("\n")
            print("%dnl py:{lineid:d} {line:s}".format(lineid=lineid,line=line))

    for variant_name, variant in variants.items():
        if cond:
            if not eval(cond, dict(variant['var_table'])):
                continue

        for line in block:
            line = line.strip("\n")
            for attr_spec_var, attr_val in variant['var_table']:
                line = line.replace(attr_spec_var, str(attr_val))
            print(line)

    if verbose_spec:
        print("%dnl py:{lineid:d} }}}}".format(lineid=lineid))


def main():
    build_var_table()

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    func = None
    block = []
    in_block = False

    def start_block():
        nonlocal in_block
        if in_block:
            raise Warning("Unmatched: ", line, "at", i)
        in_block = True
        block.clear()
        block.append(line)

    def end_block(func):
        nonlocal in_block
        if not in_block:
            raise Warning("Unmatched: ", line, "at", i)
        in_block = False
        func(i, block)
        block.clear()

    for line in lines:
        i = i + 1
        if line.startswith("@@py "):
            line = line[5:]
            myexec(i, line)
            continue

        if line.startswith("{{py"):
            start_block()
            func = myexec
            continue

        if line.startswith("{{for_each_variant"):
            start_block()
            func = for_each_variant
            continue

        if line.startswith("}}"):
            end_block(func)
            continue

        if in_block:
            block.append(line)
        else:
            sys.stdout.write(line)


if __name__ == "__main__":
    main()
