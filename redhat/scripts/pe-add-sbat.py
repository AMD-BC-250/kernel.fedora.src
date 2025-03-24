#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-2.1-or-later
# Mostly based on https://github.com/chenxiaolong/random-scripts/blob/master/pe-add-sections.py
# which is based on systemd's ukify logic

import sys
import pefile

def align_to(value, page_size):
    if bin(page_size).count("1") != 1:
        raise ValueError(f'Page size is not a power of 2: {page_size}')

    return (value + page_size - 1) // page_size * page_size

def pe_add_sections(input: str, output: str, sections: dict[str, bytes]):
    pe = pefile.PE(input, fast_load=True)

    for s in pe.sections:
        if (name := s.Name.rstrip(b"\x00").decode('ascii')) in sections.keys():
            raise ValueError(f'Section {name} already exists')

    security = pe.OPTIONAL_HEADER.DATA_DIRECTORY[
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_SECURITY']]
    if security.VirtualAddress != 0:
        raise ValueError('Cannot modify signed file')

    # Try to make room for the new headers by eating into the existing padding
    pe.OPTIONAL_HEADER.SizeOfHeaders = align_to(
        pe.OPTIONAL_HEADER.SizeOfHeaders,
        pe.OPTIONAL_HEADER.FileAlignment,
    )
    pe = pefile.PE(data=pe.write(), fast_load=True)

    warnings = pe.get_warnings()
    if warnings:
        raise Exception(f'Warnings when adjusting size of headers: {warnings}')

    for name, data in sections.items():
        new_section = pefile.SectionStructure(
            pe.__IMAGE_SECTION_HEADER_format__, pe=pe)
        new_section.__unpack__(b'\0' * new_section.sizeof())

        offset = pe.sections[-1].get_file_offset() + pe.sections[-1].sizeof()
        if offset + new_section.sizeof() > pe.OPTIONAL_HEADER.SizeOfHeaders:
            raise Exception(f'Not enough header space for {name}')

        new_section.set_file_offset(offset)
        new_section.Name = name.encode('ascii')
        new_section.Misc_VirtualSize = len(data)
        # Start at previous EOF + padding for alignment
        new_section.PointerToRawData = align_to(
            len(pe.__data__),
            pe.OPTIONAL_HEADER.FileAlignment,
        )
        new_section.SizeOfRawData = align_to(
            len(data),
            pe.OPTIONAL_HEADER.FileAlignment,
        )
        new_section.VirtualAddress = align_to(
            pe.sections[-1].VirtualAddress + pe.sections[-1].Misc_VirtualSize,
            pe.OPTIONAL_HEADER.SectionAlignment,
        )

        new_section.IMAGE_SCN_MEM_READ = True
        new_section.IMAGE_SCN_CNT_INITIALIZED_DATA = True

        # Append:
        # - Padding from previous EOF to new aligned section
        # - New section data
        # - Padding from end of section to EOF
        pe.__data__ = pe.__data__[:] \
            + bytes(new_section.PointerToRawData - len(pe.__data__)) \
            + data \
            + bytes(new_section.SizeOfRawData - len(data))

        pe.FILE_HEADER.NumberOfSections += 1
        pe.OPTIONAL_HEADER.SizeOfInitializedData += \
            new_section.Misc_VirtualSize
        pe.__structures__.append(new_section)
        pe.sections.append(new_section)

    pe.OPTIONAL_HEADER.CheckSum = 0
    pe.OPTIONAL_HEADER.SizeOfImage = align_to(
        pe.sections[-1].VirtualAddress + pe.sections[-1].Misc_VirtualSize,
        pe.OPTIONAL_HEADER.SectionAlignment,
    )

    pe.write(output)

def main():
    if len(sys.argv) != 2:
        print("Usage: %s <filename>.efi")

    sections = {'.sbat': sys.stdin.read().encode('ascii')+b'\0'}

    pe_add_sections(sys.argv[1], sys.argv[1], sections)

if __name__ == '__main__':
    main()
