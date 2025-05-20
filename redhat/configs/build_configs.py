#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path
import locale
from multiprocessing import Pool
import argparse

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# --- Helper Functions ---
def cleanup():
    for f in Path('.').glob('config-*'):
        f.unlink(missing_ok=True)
    Path('.flavors').unlink(missing_ok=True)

def die(msg):
    print(msg)
    cleanup()
    sys.exit(1)

def combine_config_layer(dir_path):
    dir_path = Path(dir_path)
    file_name = f"config-{str(dir_path).replace('/', '-')}"
    config_files = sorted([f for f in dir_path.glob('CONFIG_*') if not f.name.endswith('~')])
    if not config_files:
        Path(file_name).touch()
        return
    with open(file_name, 'w') as outfile:
        for cf in config_files:
            outfile.write(cf.read_text())

def merge_configs(archvar, configs, order, flavor, count, output_dir, specpackage_name, enable_werror):
    arch = archvar.split('-')[0]
    name = os.path.join(output_dir, f"{specpackage_name}-{archvar}-{flavor}.config")
    print(f"Building {name} ... ")
    merging_file = f"config-merging.{count}"
    merged_file = f"config-merged.{count}"
    Path(merging_file).touch()
    Path(merged_file).touch()
    skip_if_missing = False
    for o in order:
        for config in configs:
            cfile = f"config-{o}-{config}"
            if skip_if_missing and not Path(cfile).exists():
                continue
            try:
                result = subprocess.run([sys.executable, 'merge.py', cfile, merging_file], 
                                     capture_output=True, text=True, check=True)
                with open(merged_file, 'w') as mf:
                    mf.write(result.stdout)
                shutil.move(merged_file, merging_file)
            except subprocess.CalledProcessError as e:
                die(f"Failed to merge {cfile}: {e.stderr}")
            except FileNotFoundError:
                die(f"merge.py not found in {os.getcwd()}")
            except PermissionError:
                die(f"Permission denied when trying to merge {cfile}")
            except Exception as e:
                die(f"Unexpected error while merging {cfile}: {str(e)}")
        skip_if_missing = True
    arch_headers = {
        'aarch64': '# arm64',
        'ppc64le': '# powerpc',
        's390x': '# s390',
        'riscv64': '# riscv',
    }
    try:
        with open(name, 'w') as out:
            out.write(arch_headers.get(arch, f"# {arch}") + '\n')
            with open(merging_file, 'r') as mf:
                lines = sorted(mf.readlines())
                out.writelines(lines)
        if enable_werror:
            with open(name, 'r') as f:
                content = f.read()
            content = content.replace('# CONFIG_WERROR is not set', 'CONFIG_WERROR=y')
            content = content.replace('# CONFIG_KVM_WERROR is not set', 'CONFIG_KVM_WERROR=y')
            with open(name, 'w') as f:
                f.write(content)
    except IOError as e:
        die(f"Failed to write config file {name}: {str(e)}")
    finally:
        Path(merged_file).unlink(missing_ok=True)
        Path(merging_file).unlink(missing_ok=True)
    print(f"Building {name} complete")

def build_flavor(flavor, output_dir, specpackage_name, arch_mach, enable_werror, rhjobs):
    control_file = f"priority.{flavor}"
    count = 0
    order = []
    tasks = []
    
    try:
        with open(control_file, 'r') as cf:
            for line in cf:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('EMPTY'):
                    empty = line.split('=')[1]
                    for a in empty.split():
                        try:
                            with open(os.path.join(output_dir, f"{specpackage_name}-{a}-{flavor}.config"), 'w') as f:
                                f.write('# EMPTY\n')
                        except IOError as e:
                            die(f"Failed to write empty config for {a}: {str(e)}")
                elif line.startswith('ORDER'):
                    order = line.split('=')[1].split()
                    for o in order:
                        for d in Path(o).glob('**/'):
                            combine_config_layer(d)
                else:
                    try:
                        arch, configs = line.split('=')
                    except ValueError:
                        die(f"Invalid line format in {control_file}: {line}")
                    if arch_mach and not arch.startswith(arch_mach):
                        continue
                    configs_list = configs.split(':')
                    tasks.append((arch, configs_list, order, flavor, count, output_dir, specpackage_name, enable_werror))
                    count += 1
    except FileNotFoundError:
        die(f"Control file {control_file} not found")
    except IOError as e:
        die(f"Error reading control file {control_file}: {str(e)}")

    # Use a process pool to handle the tasks
    with Pool(processes=rhjobs) as pool:
        try:
            pool.starmap(merge_configs, tasks)
        except Exception as e:
            die(f"Error in process pool: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Merge kernel config files for RHEL builds.')
    parser.add_argument('specpackage_name', nargs='?', default='kernel', help='Package name (default: kernel)')
    parser.add_argument('flavor', nargs='?', help='Flavor to build (default: all in flavors file)')
    parser.add_argument('--arch-mach', default='', help='ARCH_MACH filter')
    parser.add_argument('--enable-werror', action='store_true', help='Enable WERROR configs')
    parser.add_argument('--rhjobs', type=int, default=4, help='Number of parallel jobs (default: 4)')
    args = parser.parse_args()

    output_dir = os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    try:
        if args.flavor is None or args.flavor == "":
            try:
                with open('flavors', 'r') as f:
                    flavors = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                die("flavors file not found")
            except IOError as e:
                die(f"Error reading flavors file: {str(e)}")
        else:
            flavors = [args.flavor]
        try:
            with open('.flavors', 'w') as f:
                f.write('\n'.join(flavors) + '\n')
        except IOError as e:
            die(f"Error writing .flavors file: {str(e)}")
        for flavor in flavors:
            build_flavor(flavor, output_dir, args.specpackage_name, args.arch_mach, args.enable_werror, args.rhjobs)
    finally:
        cleanup()

if __name__ == '__main__':
    if os.environ.get('RHTEST'):
        sys.exit(0)
    main() 