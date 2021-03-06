#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
#
# Copyright (c) 2018 Alex Richardson
# All rights reserved.
#
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory under DARPA/AFRL contract FA8750-10-C-0237
# ("CTSRD"), as part of the DARPA CRASH research programme.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
import atexit
import pexpect
import argparse
import os
import subprocess
import tempfile
import time
import datetime
import signal
import sys
import threading
from multiprocessing import Process, Semaphore, Queue
from pathlib import Path
from run_tests_common import *
import run_remote_lit_test

def setup_libunwind_env(qemu: boot_cheribsd.CheriBSDInstance, args: argparse.Namespace):
    # Copy the libunwind library to both MIPS and CHERI library dirs so that it is picked up
    # Do this instead of setting LD_LIBRARY_PATH to use only the libraries that we actually need
    boot_cheribsd.checked_run_cheribsd_command(qemu, "ln -sfv /build/lib/libunwind.so* /usr/lib/")
    boot_cheribsd.checked_run_cheribsd_command(qemu, "ln -sfv /build/lib/libunwind.so* /usr/libcheri/")
    # We also need libdl from the sysroot:
    boot_cheribsd.checked_run_cheribsd_command(qemu, "ln -sfv /sysroot/usr/lib/libcxxrt.so* /sysroot/usr/lib/libdl.so* /usr/lib/")
    boot_cheribsd.checked_run_cheribsd_command(qemu, "ln -sfv /sysroot/usr/libcheri/libcxxrt.so*  /sysroot/usr/libcheri/libdl.so* /usr/libcheri/")
    # Add a fake libgcc_s link to libunwind (this works now that we build libunwind with version info)
    boot_cheribsd.checked_run_cheribsd_command(qemu, "ln -sfv /usr/lib/libunwind.so /usr/lib/libgcc_s.so.1")
    boot_cheribsd.checked_run_cheribsd_command(qemu, "ln -sfv /usr/libcheri/libunwind.so /usr/libcheri/libgcc_s.so.1")

def run_libunwind_tests(qemu: boot_cheribsd.CheriBSDInstance, args: argparse.Namespace):
    with tempfile.TemporaryDirectory(prefix="cheribuild-libunwind-tests-") as tempdir:
        # run the tests both for shared and static libunwind by setting -Denable_shared=
        # First static binaries
        static_everything_success = run_remote_lit_test.run_remote_lit_tests("libunwind", qemu, args, tempdir,
                                                                  lit_extra_args=["-Dforce_static_executable=True", "-Denable_shared=False"],
                                                                  llvm_lit_path=args.llvm_lit_path)
        # dynamic binary with libunwind linked statically
        static_libunwind_success = run_remote_lit_test.run_remote_lit_tests("libunwind", qemu, args, tempdir,
                                                                  lit_extra_args=["-Denable_shared=False"],
                                                                  llvm_lit_path=args.llvm_lit_path)
        # dynamic binary with libunwind linked shared
        shared_success = run_remote_lit_test.run_remote_lit_tests("libunwind", qemu, args, tempdir,
                                                                  lit_extra_args=["-Denable_shared=True"],
                                                                  llvm_lit_path=args.llvm_lit_path)
        return static_libunwind_success and static_everything_success and shared_success

def add_cmdline_args(parser: argparse.ArgumentParser):
    parser.add_argument("--lit-debug-output", action="store_true")
    parser.add_argument("--llvm-lit-path")
    parser.add_argument("--xunit-output", default="qemu-libunwind-test-results.xml")


def set_cmdline_args(args: argparse.Namespace):
    # We don't support parallel jobs but are reusing libcxx infrastructure -> set the expected vars
    args.internal_shard = None
    args.parallel_jobs = None


if __name__ == '__main__':
    try:
        run_tests_main(test_function=run_libunwind_tests, need_ssh=True, # we need ssh running to execute the tests
                       argparse_setup_callback=add_cmdline_args, argparse_adjust_args_callback=set_cmdline_args,
                       should_mount_sysroot=True, should_mount_builddir=True, test_setup_function=setup_libunwind_env)
    finally:
        print("Finished running ", " ".join(sys.argv))
