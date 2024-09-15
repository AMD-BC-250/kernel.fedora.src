#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2023 Red Hat, Inc.


import yaml
import glob
import sys

def readvariants():
    i = 1
    variantdir = "variants"

    for file in glob.iglob(f'{variantdir}/*.yaml'):
        vfile=open(file, 'r')
        if i == 1:
            variants = [yaml.safe_load(vfile)]
            i = 0
        else:
            variants.append(yaml.safe_load(vfile))
        vfile.close()
    return variants

def disablelists(variants):
    fedoraonlyvariant = []
    rhelonlyvariant = []
    allvariant = []

    for variant in variants:
        if variant["Flavor"] == "Fedora":
            fedoraonlyvariant.append(variant["Name"])
        elif variant["Flavor"] == "RHEL":
            rhelonlyvariant.append(variant["Name"])
        allvariant.append(variant["Name"])
    return fedoraonlyvariant, rhelonlyvariant, allvariant #archvariants

def archvariants(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        varch = variant["arch"]
        archexclude = (f'%ifnarch {varch}\n'
                       f'%define with_{vname} 0\n'
                       f'%endif')
        specdata = specdata.replace ("%%ARCHVARIANTDISABLE%%", archexclude + "\n%%ARCHVARIANTDISABLE%%")

    specdata = specdata.replace ("%%ARCHVARIANTDISABLE%%", "")
    return specdata

def withvariants(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        if variant["Schedule"] == "Always":
            withline = f'%define with_{vname} %{{?_without_{vname}: 0}} %{{?!_without_{vname}: 1}}'
        # Never is a special case, we want it in the spec, but disabled by default.
        # Typically for community use.  Currently this is used for aarch64 16k
        elif variant["Schedule"] == "Never":
            withline = f'%define with_{vname} %{{?_with_{vname}: 1}} %{{?!_with_{vname}: 0}}'
        specdata = specdata.replace ("%%WITHVARIANTS%%" , withline + "\n%%WITHVARIANTS%%")
        # Print Variant table entry
        if variant["Debug"] == True:
            debug = "X"
        else:
            debug = " "
        vtable = f"# {vname:11}X         {debug}             X"
        specdata = specdata.replace ("%%VARIANTABLE%%" , vtable + "\n%%VARIANTABLE%%")
    specdata = specdata.replace ("%%WITHVARIANTS%%" , "")
    specdata = specdata.replace ("%%VARIANTABLE%%" , "")
    return specdata

def variantdisable(flavor, variantlist, specdata):
    for variant in variantlist:
        disableline = f"%define with_{variant} 0"
        specdata = specdata.replace("%%" + flavor + "VARIANTSDISABLE%%", disableline + "\n%%" + flavor +"VARIANTSDISABLE%%")
    specdata = specdata.replace("%%" + flavor + "VARIANTSDISABLE%%", "")
    return specdata

def variantbase(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        variantbaseline = (f'%if %{{with_{vname}}} && %{{with_base}}\n'
                           f'%define with_{vname}_base 1\n'
                           f'%else\n'
                           f'%define with_{vname}_base 0\n'
                           f'%endif\n')
        specdata = specdata.replace("%%ALLVARIANTBASE%%", variantbaseline + "%%ALLVARIANTBASE%%")
    specdata = specdata.replace("%%ALLVARIANTBASE%%", "")
    return specdata

def variantconfigs(variants, specdata):
    rhelsource = 1000
    fedsource = 1500
    for variant in variants:
        vname = variant["Name"]
        varch = variant["arch"]
        if variant["Flavor"] == "RHEL" or variant["Flavor"] == "All":
             configsource = f'Source{rhelsource}: %{{name}}-{varch}-{vname}-rhel.config'
             specdata = specdata.replace("%%RHELVARIANTCONFIGS%%" , configsource + "\n%%RHELVARIANTCONFIGS%%")
             rhelsource += 1
             if variant["Debug"] == True:
                 configsource = f'Source{rhelsource}: %{{name}}-{varch}-{vname}-debug-rhel.config'
                 specdata = specdata.replace("%%RHELVARIANTCONFIGS%%" , configsource + "\n%%RHELVARIANTCONFIGS%%")
                 rhelsource += 1
        if variant["Flavor"] == "Fedora" or variant["Flavor"] == "All":
             configsource = f'Source{fedsource}: %{{name}}-{varch}-{vname}-fedora.config'
             specdata = specdata.replace("%%FEDORAVARIANTCONFIGS%%" , configsource + "\n%%FEDORAVARIANTCONFIGS%%")
             fedsource += 1
             if variant["Debug"] == True:
                 configsource = f'Source{fedsource}: %{{name}}-{varch}-{vname}-debug-fedora.config'
                 specdata = specdata.replace("%%FEDORAVARIANTCONFIGS%%" , configsource + "\n%%FEDORAVARIANTCONFIGS%%")
                 fedsource += 1
    specdata = specdata.replace("%%FEDORAVARIANTCONFIGS%%" , "")
    specdata = specdata.replace("%%RHELVARIANTCONFIGS%%" , "")
    return specdata

def variantdescription(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        vsummary = variant["Summary"]
        vdesc = variant["Description"]
        variantdata = (f'%if %{{with_{vname}_base}}\n'
                       f'%define variant_summary The Linux kernel compiled for {vsummary}\n'
                       f'%kernel_variant_package {vname}\n'
                       f'%description {vname}-core\n'
                       f'{vdesc}'
                       f'%endif\n')
        specdata = specdata.replace("%%VARIANTSUMMARY%%", variantdata + "\n%%VARIANTSUMMARY%%")
        if variant["Debug"] == True:
            variantdata = (f'%if %{{with_{vname}}} && %{{with_debug}}\n'
                           f'%define variant_summary The Linux kernel compiled for {vsummary} with extra debugging enabled\n'
                           f'%if !%{{debugbuildsenabled}}\n'
                           f'%kernel_variant_package -m {vname}-debug\n'
                           f'%else\n'
                           f'%kernel_variant_package {vname}-debug\n'
                           f'%endif\n'
                           f'%description {vname}-debug-core\n'
                           f'{vdesc}'
                           f'This variant of the kernel has numerous debugging options enabled.\n'
                           f'It should only be installed when trying to gather additional information\n'
                           f'on kernel bugs, as some of these options impact performance noticably.\n'
                           f'%endif\n')
            specdata = specdata.replace("%%VARIANTSUMMARY%%", variantdata + "\n%%VARIANTSUMMARY%%")

    specdata = specdata.replace("%%VARIANTSUMMARY%%", "")
    return specdata

def variantuki(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        vukidata = (f'%if %{{with_{vname}}} && %{{with_debug}} && %{{with_efiuki}}\n'
                    f'%description {vname}-debug-uki-virt\n'
                    f'Prebuilt {vname} debug unified kernel image for virtual machines.\n\n'
                    f'%description {vname}-debug-uki-virt-addons\n'
                    f'Prebuilt {vname} debug unified kernel image addons for virtual machines.\n'
                    f'%endif\n\n'
                    f'%if %{{with_{vname}_base}} && %{{with_efiuki}}\n'
                    f'%description {vname}-uki-virt\n'
                    f'Prebuilt {vname} unified kernel image for virtual machines.\n\n'
                    f'%description {vname}-uki-virt-addons\n'
                    f'Prebuilt {vname} unified kernel image addons for virtual machines.\n'
                    f'%endif\n')
        specdata = specdata.replace("%%VARIANTUKI%%", vukidata + "\n%%VARIANTUKI%%")
    specdata = specdata.replace("%%VARIANTUKI%%", "")
    return specdata

def variantbuildkernel(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        if variant["Debug"] == True:
            vbuildcmd = (f'%if %{{with_{vname}}} && %{{with_debug}}\n'
                         f'echo "building {vname} debug package"\n'
                         f'BuildKernel %make_target %kernel_image %{{_use_vdso}} {vname}-debug\n'
                         f'%endif\n\n')
            specdata = specdata.replace("%%VARIANTBUILDKERNEL%%", vbuildcmd + "\n%%VARIANTBUILDKERNEL%%")
        vbuildcmd = (f'%if %{{with_{vname}_base}}\n'
                     f'echo "building {vname} main package"\n'
                     f'BuildKernel %make_target %kernel_image %{{_use_vdso}} {vname}\n'
                     f'%endif\n')
        specdata = specdata.replace("%%VARIANTBUILDKERNEL%%", vbuildcmd + "\n%%VARIANTBUILDKERNEL%%")

    specdata = specdata.replace("%%VARIANTBUILDKERNEL%%", "")
    return specdata

# We don't want to build tools packages for each variant, so this appends
# the line which only builds tools if not a variant.

def variantofftools(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        vtoolexclude =  f'&& !%{{with_{vname}}}'
        specdata = specdata.replace("%%VARIANTOFFTOOLS%%", vtoolexclude + "%%VARIANTOFFTOOLS%%")

    specdata = specdata.replace("%%VARIANTOFFTOOLS%%", "")
    return specdata

def variantscripts(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        vscriptlines = (f'%if %{{with_{vname}_base}}\n'
                        f'%kernel_variant_preun -v {vname}\n'
                        f'%kernel_variant_post -v {vname}\n'
                        f'%endif\n\n'
                        f'%if %{{with_debug}} && %{{with_{vname}}}\n'
                        f'%kernel_variant_preun -v {vname}-debug\n'
                        f'%kernel_variant_post -v {vname}-debug\n'
                        f'%endif\n\n'
                        f'%if %{{with_{vname}}} && %{{with_debug}} && %{{with_efiuki}}\n'
                        f'%kernel_variant_posttrans -v {vname}-debug -u virt\n'
                        f'%kernel_variant_preun -v {vname}-debug -u virt\n'
                        f'%endif\n\n'
                        f'%if %{{with_{vname}_base}} && %{{with_efiuki}}\n'
                        f'%kernel_variant_posttrans -v {vname} -u virt\n'
                        f'%kernel_variant_preun -v {vname} -u virt\n'
                        f'%endif\n\n')
        specdata = specdata.replace("%%VARIANTSCRIPTS%%", vscriptlines + "\n%%VARIANTSCRIPTS%%")

    specdata = specdata.replace("%%VARIANTSCRIPTS%%", "")
    return specdata

def variantfiles(variants, specdata):
    for variant in variants:
        vname = variant["Name"]
        if variant["Debug"] == True:
            variant_files_debug = (f'%if %{{with_{vname}}}\n'
                                   f'%kernel_variant_files %{{_use_vdso}} %{{with_debug}} {vname}-debug\n'
                                   f'%endif')
            specdata = specdata.replace("%%VARIANTFILESDEBUG%%", variant_files_debug + "\n%%VARIANTFILESDEBUG%%")
            debug_subpkgs = (f'%if %{{with_{vname}}}\n'
                             f'%files {vname}-debug\n'
                             f'%files {vname}-debug-core\n'
                             f'%files {vname}-debug-devel\n'
                             f'%files {vname}-debug-devel-matched\n'
                             f'%files {vname}-debug-modules\n'
                             f'%files {vname}-debug-modules-extra\n'
                             f'%endif')
            specdata = specdata.replace("%%VARIANTSUBPKGDEBUG%%", debug_subpkgs + "\n%%VARIANTSUBPKGDEBUG%%")
        variant_files = f'%kernel_variant_files %{{_use_vdso}} %{{with_{vname}_base}} {vname}'
        specdata = specdata.replace("%%KERNELVARIANTFILES%%", variant_files + "\n%%KERNELVARIANTFILES%%")

    specdata = specdata.replace("%%VARIANTFILESDEBUG%%", "")
    specdata = specdata.replace("%%VARIANTSUBPKGDEBUG%%", "")
    specdata = specdata.replace("%%KERNELVARIANTFILES%%", "")
    return specdata

if __name__ == '__main__':
    specfile = sys.argv[1]
    with open(specfile, 'r') as spec:
        specdata = spec.read()
    spec.close()
    variants = readvariants()
    fedoraonlyvariant, rhelonlyvariant, allvariant = disablelists(variants)
    specdata = variantdisable("FEDORAONLY", fedoraonlyvariant, specdata)
    specdata = variantdisable("RHELONLY", rhelonlyvariant, specdata)
    specdata = variantdisable("ALL", allvariant, specdata)
    specdata = archvariants(variants, specdata)
    specdata = withvariants(variants, specdata)
    specdata = variantbase(variants, specdata)
    specdata = variantconfigs(variants, specdata)
    specdata = variantdescription(variants, specdata)
    specdata = variantuki(variants, specdata)
    specdata = variantbuildkernel(variants, specdata)
    specdata = variantofftools(variants, specdata)
    specdata = variantscripts(variants, specdata)
    specdata = variantfiles(variants, specdata)
    with open(specfile, 'w') as spec:
        spec.write(specdata)
    spec.close()
