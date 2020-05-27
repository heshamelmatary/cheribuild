#
# Copyright (c) 2018 James Clarke
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

from .crosscompileproject import CrossCompileAutotoolsProject
from .gdb import BuildGDB
from ..project import *
from .cheribsd import BuildCHERIBSD


# Using GCC not Clang, so can't use CrossCompileAutotoolsProject
class BuildBBLBase(CrossCompileAutotoolsProject):
    doNotAddToTargets = True
    repository = GitRepository("https://github.com/CTSRD-CHERI/riscv-pk",
    #repository = GitRepository("https://github.com/riscv/riscv-pk.git")
        force_branch=True, default_branch="cheri_purecap",  # Compilation fixes for clang and support for CHERI
        old_urls=[b"https://github.com/jrtc27/riscv-pk.git"])
        #per_target_branches={
        #    CompilationTargets.CHERIBSD_RISCV_NO_CHERI: TargetBranchInfo("master", "riscv-pk")
        #    })
    make_kind = MakeCommandKind.GnuMake
    _always_add_suffixed_targets = True
    is_sdk_target = False
    kernel_class = None
    cross_install_dir = DefaultInstallDir.ROOTFS
    without_payload = False
    mem_start = "0x80000000"

    @classmethod
    def dependencies(cls, config: CheriConfig):
        xtarget = cls.get_crosscompile_target(config)
        # We need GNU objcopy which is installed by gdb-native
        result = [cls.kernel_class.get_class_for_target(xtarget).target, "gdb-native"]
        return result

    def setup(self):
        super().setup()
        self.COMMON_LDFLAGS.extend(["-nostartfiles", "-nostdlib", "-static"])
        self.COMMON_FLAGS.append("-nostdlib")

        if self.crosscompile_target.is_hybrid_or_purecap_cheri():
            # We have to build a purecap if we want to support CHERI
            self.configureArgs.append("--with-abi=l64pc128")
            # Enable CHERI extensions
            self.configureArgs.append("--with-arch=rv64imafdcxcheri")
            self.configureArgs.append("--with-mem-start=" + self.mem_start)
        else:
            self.configureArgs.append("--with-abi=lp64")
            self.configureArgs.append("--with-arch=rv64imafdc")
            self.configureArgs.append("--with-mem-start=" + self.mem_start)

        if self.build_type == BuildType.DEBUG:
            self.configureArgs.append("--enable-logo")  # For debugging

        # BBL build uses weird objcopy flags and therefore requires GNU objcopy which we can get from GDB
        self.add_configure_and_make_env_arg("OBJCOPY",
            BuildGDB.getInstallDir(self, cross_target=CompilationTargets.NATIVE) / "bin/gobjcopy")
        # Otherwise use LLVM tools
        self.add_configure_and_make_env_arg("READELF", self.sdk_bindir / "llvm-readelf")
        self.add_configure_and_make_env_arg("RANLIB", self.sdk_bindir / "llvm-ranlib")
        self.add_configure_and_make_env_arg("AR", self.sdk_bindir / "llvm-ar")

        if self.without_payload:
            # Build an OpenSBI fw_jump style BBL
            assert self.kernel_class is None
            self.configureArgs.append("--without-payload")
        else:
            # Add the kernel as a payload:
            assert self.kernel_class is not None
            kernel_path = self.kernel_class.get_installed_kernel_path(self, cross_target=self.crosscompile_target)
            self.configureArgs.append("--with-payload=" + str(kernel_path))

    def compile(self, **kwargs):
        self.run_make("bbl")

    def install(self, **kwargs):
        self.installFile(self.buildDir / "bbl", self.real_install_root_dir / "bbl")

    @classmethod
    def get_installed_kernel_path(cls, caller, config: CheriConfig = None,
                                  cross_target: CrossCompileTarget = CompilationTargets.NONE):
        return cls.get_instance(caller, config=config, cross_target=cross_target).real_install_root_dir / "bbl"


def bbl_no_payload_install_dir(config: CheriConfig, project: SimpleProject):
    return


# Build BBL without an embedded payload
class BuildBBLNoPayload(BuildBBLBase):
    target = "bbl"
    project_name = "bbl"
    without_payload = True
    # For some reason BBL needs a sysroot, so we use the CheriBSD one
    dependencies = ["cheribsd"]
    cross_install_dir = DefaultInstallDir.CUSTOM_INSTALL_DIR
    supported_architectures = [CompilationTargets.CHERIBSD_RISCV_PURECAP, CompilationTargets.CHERIBSD_RISCV_HYBRID,
                               CompilationTargets.CHERIBSD_RISCV_NO_CHERI]

    _default_install_dir_fn = ComputedDefaultValue(
        function=lambda config, project: config.cheri_sdk_dir / "bbl" / project.crosscompile_target.generic_suffix,
        as_string="$SDK_ROOT/bbl/riscv{32,64}{c,-hybrid}")


class BuildBBLNoPayloadGFE(BuildBBLNoPayload):
    mem_start = "0xc0000000"
    target = "bbl-gfe"
    project_name = "bbl"  # reuse same source dir
    build_dir_suffix = "-gfe"  # but not the build dir
    default_build_type = BuildType.DEBUG

    _default_install_dir_fn = ComputedDefaultValue(
        function=lambda config, project: config.cheri_sdk_dir / "bbl-gfe" / project.crosscompile_target.generic_suffix,
        as_string="$SDK_ROOT/bbl-gfe/riscv{32,64}{c,-hybrid}")

# class BuildBBLFreeBSDRISCV(BuildBBLBase):
#     project_name = "bbl"  # reuse same source dir
#     target = "bbl-freebsd"
#     build_dir_suffix = "freebsd"
#     supported_architectures = [CompilationTargets.FREEBSD_RISCV]
#     kernel_class = BuildFreeBSD
#
#
# class BuildBBLFreeBSDWithDefaultOptionsRISCV(BuildBBLBase):
#     project_name = "bbl"  # reuse same source dir
#     target = "bbl-freebsd-with-default-options"
#     build_dir_suffix = "freebsd-with-default-options"
#     supported_architectures = [CompilationTargets.FREEBSD_RISCV]
#     kernel_class = BuildFreeBSDWithDefaultOptions
#
#
class BuildBBLCheriBSDRISCVGFE(BuildBBLBase):
     project_name = "bbl"  # reuse same source dir
     target = "bbl-cheribsd-gfe"
     mem_start = "0xc0000000"
     dependencies = ["cheribsd"]
     without_payload = False
     build_dir_suffix = "-gfe"  # but not the build dir
     supported_architectures = [CompilationTargets.CHERIBSD_RISCV_NO_CHERI]
     kernel_class = BuildCHERIBSD

     #_default_install_dir_fn = ComputedDefaultValue(
     #   function=lambda config, project: config.cheri_sdk_dir / "bbl-gfe" / project.crosscompile_target.generic_suffix,
     #   as_string="$SDK_ROOT/bbl-gfe-/riscv{32,64}{c,-hybrid}")

class BuildBBLCheriBSDRISCV(BuildBBLBase):
     project_name = "bbl"  # reuse same source dir
     target = "bbl-cheribsd"
     build_dir_suffix = "cheribsd"
     supported_architectures = [CompilationTargets.CHERIBSD_RISCV_HYBRID, CompilationTargets.CHERIBSD_RISCV_NO_CHERI]
     kernel_class = BuildCHERIBSD
