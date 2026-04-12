"""
Inspect psutil Process memory info on the current OS.
Run this script on Windows and paste the output back.
"""

import sys
import os
import psutil


def inspect_process(pid: int | None = None):
    proc = psutil.Process(pid or os.getpid())
    name = proc.name()
    print(f"=== psutil version: {psutil.__version__} ===")
    print(f"Platform: {sys.platform}")
    print(f"Process: {name} (PID {proc.pid})")
    print()

    # --- memory_info() (portable across all platforms) ---
    mi = proc.memory_info()
    print("--- memory_info() ---")
    print(f"  Fields: {mi._fields}")
    for field in mi._fields:
        print(f"  {field}: {getattr(mi, field):>15,} bytes  ({getattr(mi, field) / 1024 / 1024:.2f} MB)")
    print()

    # --- memory_full_info() (extended, platform-specific fields) ---
    print("--- memory_full_info() ---")
    try:
        mfi = proc.memory_full_info()
        print(f"  Fields: {mfi._fields}")
        for field in mfi._fields:
            value = getattr(mfi, field)
            if isinstance(value, (int, float)):
                print(f"  {field}: {value:>15,} bytes  ({value / 1024 / 1024:.2f} MB)")
            else:
                print(f"  {field}: {value}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    print()

    # --- Check all children too ---
    children = proc.children(recursive=True)
    if children:
        print(f"--- {len(children)} child process(es) ---")
        for child in children:
            try:
                child_proc = psutil.Process(child.pid)
                child_mfi = child_proc.memory_full_info()
                print(f"  PID {child.pid} ({child_proc.name()}): fields={child_mfi._fields}")
                for field in child_mfi._fields:
                    value = getattr(child_mfi, field)
                    if isinstance(value, (int, float)):
                        print(f"    {field}: {value:>15,} bytes  ({value / 1024 / 1024:.2f} MB)")
                    else:
                        print(f"    {field}: {value}")
            except Exception as e:
                print(f"  PID {child.pid}: ERROR — {type(e).__name__}: {e}")
        print()

    # --- System-wide memory ---
    print("--- virtual_memory() ---")
    vm = psutil.virtual_memory()
    print(f"  Fields: {vm._fields}")
    for field in vm._fields:
        print(f"  {field}: {getattr(vm, field):>15,} bytes  ({getattr(vm, field) / 1024 / 1024:.2f} MB)")
    print()

    # --- Summary table of field availability ---
    print("=== Field availability summary ===")
    portable_fields = {"rss", "vms", "shared", "text", "lib", "data", "dirty"}
    linux_extra = {"pss", "uss", "swap"}
    windows_extra = {"uss", "peak_wset", "wset", "peak_paged_pool", "paged_pool",
                     "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile",
                     "private"}
    macos_extra = {"uss", "pfaults", "pageins"}

    print(f"  Portable (all OS):    {sorted(portable_fields)}")
    print(f"  Linux extras:         {sorted(linux_extra)}")
    print(f"  Windows extras:       {sorted(windows_extra)}")
    print(f"  macOS extras:         {sorted(macos_extra)}")
    print()
    print(f"  ** NOTE: 'uss' appears in BOTH Linux and Windows extras above. **")
    print(f"  ** This means psutil claims to support USS on Windows.            **")
    print(f"  ** Verify with the actual output above.                            **")


if __name__ == "__main__":
    inspect_process()
