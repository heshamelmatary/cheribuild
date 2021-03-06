#
# Copyright (c) 2019 Alex Richardson
#
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory (Department of Computer Science and
# Technology) under DARPA contract HR0011-18-C-0016 ("ECATS"), as part of the
# DARPA SSITH research programme.
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

from .crosscompileproject import *
import os


# XXXAR: duplicated from ICU4C should add a shared variant
def python_dependencies(cls: "typing.Type[CrossCompileProject]", config: CheriConfig):
    deps = crosscompile_dependencies(cls, config)
    target = cls.get_crosscompile_target(config)
    # python needs a native buid to cross-compile:
    if target != CrossCompileTarget.NATIVE:
        deps.append("python-native")
    return deps


class BuildPython(CrossCompileAutotoolsProject):
    repository = GitRepository("https://github.com/CTSRD-CHERI/cpython.git")
    gitBranch = "3.8"
    crossInstallDir = CrossInstallDir.CHERIBSD_ROOTFS
    default_build_type = BuildType.DEBUG
    dependencies = python_dependencies

    # build_in_source_dir = True  # Cannot build out-of-source

    def configure(self, **kwargs):
        # maybe interesting:   --with(out)-pymalloc    disable/enable specialized mallocs
        if self.cross_build_type == BuildType.DEBUG:
            self.configureArgs.append("--with-pydebug")
            # XXXAR: always add assertions?
            self.configureArgs.append("--with-assertions")
        self.configureArgs.append("--with-computed-gotos")
        if not self.compiling_for_host():
            self.configureArgs.append("--without-pymalloc")  # use system malloc
            self.configureArgs.append("--without-doc-strings")  # should reduce size
            self.configureArgs.append("--without-ensurepip")  # fails to cross-compile
            native_python = self.get_instance_for_cross_target(CrossCompileTarget.NATIVE,
                                                               self.config).installDir / "bin/python3"
            if not native_python.exists():
                self.fatal("Native python3 doesn't exist, you must build the `python-native` target first.")
            self.add_configure_vars(
                ac_cv_buggy_getaddrinfo="no",
                # PYTHON_FOR_BUILD=str(native_python), # Doesn't work since that remove all flags, need to set PATH instead
                # PYTHON_FOR_REGEN=str(native_python),
                PATH=str(native_python.parent) + ":" + os.getenv("PATH"),
                READELF=str(self.config.sdkBinDir / "llvm-readelf"),
                AR=str(self.config.sdkBinDir / "llvm-ar"),
                ac_cv_file__dev_ptmx="no",  # no /dev/ptmx file on cheribsd
                ac_cv_file__dev_ptc="no",  # no /dev/ptc file on cheribsd
            )
            # self.configureEnvironment["ac_cv_file__dev_ptmx+set"] = "set"
            # self.configureEnvironment["ac_cv_file__dev_ptc+set"] = "set"
            # TODO: do I need to set? ac_sys_release=13.0
        super().configure(**kwargs)

    def run_tests(self):
        if self.compiling_for_host():
            self.run_cmd(self.buildDir / "python.exe", "-m", "test", cwd=self.buildDir)
        else:
            self.run_cheribsd_test_script("run_python_tests.py", mount_installdir=True, mount_sourcedir=True,
                                          mount_builddir=True)
