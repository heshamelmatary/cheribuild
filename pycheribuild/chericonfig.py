import os
import shutil
from .configloader import ConfigLoader
from pathlib import Path


def defaultNumberOfMakeJobs():
    makeJobs = os.cpu_count()
    if makeJobs > 24:
        # don't use up all the resources on shared build systems
        # (you can still override this with the -j command line option)
        makeJobs = 16
    return makeJobs


def defaultSshForwardingPort():
    # chose a different port for each user (hopefully it isn't in use yet)
    return 9999 + ((os.getuid() - 1000) % 10000)


def defaultDiskImagePath(conf: "CheriConfig"):
    if conf.cheriBits == 128:
        return conf.outputRoot / "cheri128-disk.qcow2"
    return conf.outputRoot / "cheri256-disk.qcow2"


def defaultClang37Tool(basename: str):
    # TODO: also accept 3.8, 3.9, etc binaries
    # TODO: search through path and list all clang++.* and clang.* binaries
    # try to find clang 3.7, otherwise fall back to system clang
    guess = shutil.which(basename + "37")
    if not guess:
        guess = shutil.which(basename + "-3.7")
    if not guess:
        guess = shutil.which(basename)
    return guess


class CheriConfig(object):
    # boolean flags
    pretend = ConfigLoader.addBoolOption("pretend", "p", help="Only print the commands instead of running them")
    quiet = ConfigLoader.addBoolOption("quiet", "q", help="Don't show stdout of the commands that are executed")
    verbose = ConfigLoader.addBoolOption("verbose", "v", help="Print all commmands that are executed")
    clean = ConfigLoader.addBoolOption("clean", "c", help="Remove the build directory before build")
    force = ConfigLoader.addBoolOption("force", "f", help="Don't prompt for user input but use the default action")
    skipUpdate = ConfigLoader.addBoolOption("skip-update", help="Skip the git pull step")
    skipConfigure = ConfigLoader.addBoolOption("skip-configure", help="Skip the configure step")
    skipInstall = ConfigLoader.addBoolOption("skip-install", help="Skip the install step (only do the build)")
    listTargets = ConfigLoader.addBoolOption("list-targets", help="List all available targets and exit")
    dumpConfig = ConfigLoader.addBoolOption("dump-configuration", help="Print the current configuration as JSON."
                                            " This can be saved to ~/.config/cheribuild.json to make it persistent")
    includeDependencies = ConfigLoader.addBoolOption("include-dependencies", "d", help="Also build the dependencies "
                                                     "of targets passed on the command line. Targets passed on the"
                                                     "command line will be reordered and processed in an order that "
                                                     "ensures dependencies are built before the real target. (run "
                                                     " with --list-targets for more information)")
    disableTMPFS = ConfigLoader.addBoolOption("disable-tmpfs", help="Don't make /tmp a TMPFS mount in the CHERIBSD system image. This is a workaround in case TMPFS is not working correctly")
    noLogfile = ConfigLoader.addBoolOption("no-logfile", help="Don't write a logfile for the build steps")

    _buildCheri128 = ConfigLoader.addBoolOption("cheri-128", "-128", group=ConfigLoader.cheriBitsGroup,
                                                help="Shortcut for --cheri-bits=128")
    _buildCheri256 = ConfigLoader.addBoolOption("cheri-256", "-256", group=ConfigLoader.cheriBitsGroup,
                                                help="Shortcut for --cheri-bits=256")
    _cheriBits = ConfigLoader.addOption("cheri-bits", type=int, group=ConfigLoader.cheriBitsGroup, choices=["128", "256"],
                                        default=256, help="Whether to build the whole software stack for 128 or 256 bit"
                                        " CHERI. The output directories will be suffixed with the number of bits to"
                                        " make sure the right binaries are being used."
                                        " WARNING: 128-bit CHERI is still very unstable.")

    createCompilationDB = ConfigLoader.addBoolOption("compilation-db", "-cdb",
                                                     help="Create a compile_commands.json file in the build dir "
                                                          "(requires Bear for non-CMake projects")
    qemuUseTelnet = ConfigLoader.addBoolOption("qemu-monitor-telnet",
                                               help="Use telnet to connect to QEMU monitor instead of CTRL+A,C")

    # configurable paths
    sourceRoot = ConfigLoader.addPathOption("source-root", default=Path(os.path.expanduser("~/cheri")),
                                            help="The directory to store all sources")
    outputRoot = ConfigLoader.addPathOption("output-root", default=lambda p: (p.sourceRoot / "output"),
                                            help="The directory to store all output (default: '<SOURCE_ROOT>/output')")
    buildRoot = ConfigLoader.addPathOption("build-root", default=lambda p: (p.sourceRoot / "build"),
                                           help="The directory for all the builds (default: '<SOURCE_ROOT>/build')")
    extraFiles = ConfigLoader.addPathOption("extra-files", default=lambda p: (p.sourceRoot / "extra-files"),
                                            help="A directory with additional files that will be added to the image "
                                                 "(default: '<SOURCE_ROOT>/extra-files')")
    clangPath = ConfigLoader.addPathOption("clang-path", default=defaultClang37Tool("clang"),
                                           help="The Clang C compiler to use for compiling LLVM+Clang (must be at "
                                                "least version 3.7)")
    clangPlusPlusPath = ConfigLoader.addPathOption("clang++-path", default=defaultClang37Tool("clang++"),
                                                   help="The Clang C++ compiler to use for compiling LLVM+Clang (must "
                                                        "be at least version 3.7)")
    # TODO: only create a qcow2 image?
    diskImage = ConfigLoader.addPathOption("disk-image-path", default=defaultDiskImagePath, help="The output path for"
                                           " the QEMU disk image (default: '<OUTPUT_ROOT>/cheri256-disk.qcow2')")

    # other options
    makeJobs = ConfigLoader.addOption("make-jobs", "j", type=int, default=defaultNumberOfMakeJobs(),
                                      help="Number of jobs to use for compiling")  # type: int
    sshForwardingPort = ConfigLoader.addOption("ssh-forwarding-port", "s", type=int, default=defaultSshForwardingPort(),
                                               help="The port to use on localhost to forward the QEMU ssh port. "
                                                    "You can then use `ssh root@localhost -p $PORT` connect to the VM",
                                               metavar="PORT")  # type: int
    # allow overriding the git revisions in case there is a regression
    cheriBsdRevision = ConfigLoader.addOption("cheribsd-revision", type=str, metavar="GIT_COMMIT_ID",
                                              help="The git revision or branch of CHERIBSD to check out",
                                              group=ConfigLoader.revisionGroup)  # type: str
    llvmRevision = ConfigLoader.addOption("llvm-revision", type=str, metavar="GIT_COMMIT_ID",
                                          help="The git revision or branch of LLVM to check out",
                                          group=ConfigLoader.revisionGroup)  # type: str
    clangRevision = ConfigLoader.addOption("clang-revision", type=str, metavar="GIT_COMMIT_ID",
                                           help="The git revision or branch of clang to check out",
                                           group=ConfigLoader.revisionGroup)  # type: str
    lldbRevision = ConfigLoader.addOption("lldb-revision", type=str, metavar="GIT_COMMIT_ID",
                                          help="The git revision or branch of clang to check out",
                                          group=ConfigLoader.revisionGroup)  # type: str
    qemuRevision = ConfigLoader.addOption("qemu-revision", type=str, metavar="GIT_COMMIT_ID",
                                          help="The git revision or branch of QEMU to check out",
                                          group=ConfigLoader.revisionGroup)  # type: str

    # To allow building CHERI software on non-FreeBSD systems
    freeBsdBuildMachine = ConfigLoader.addOption("freebsd-builder-hostname", type=str, metavar="SSH_HOSTNAME",
                                                 help="This string will be passed to ssh and be something like "
                                                      "user@hostname of a FreeBSD system that can be used to build "
                                                      "CHERIBSD. Can also be the name of a host in  ~/.ssh/config.",
                                                 group=ConfigLoader.remoteBuilderGroup)  # type: str
    # TODO: query this from the remote machine instead of needed an options
    freeBsdBuilderOutputPath = ConfigLoader.addOption("freebsd-builder-output-path", type=str, metavar="PATH",
                                                      help="The path where the cheribuild output is stored on the"
                                                           " FreeBSD build server.",
                                                      group=ConfigLoader.remoteBuilderGroup)  # type: str
    freeBsdBuilderCopyOnly = ConfigLoader.addBoolOption("freebsd-builder-copy-only", help="Only scp the SDK from the"
                                                        "FreeBSD build server and don't build the SDK first.",
                                                        group=ConfigLoader.remoteBuilderGroup)

    # Deprecated options:
    skipDependencies = ConfigLoader.addBoolOption("skip-dependencies", "t", group=ConfigLoader.deprecatedOptionsGroup,
                                                  help="This option no longer does anything and is only included to"
                                                       "allow running existing command lines")

    def __init__(self, availableTargets: list):
        ConfigLoader._cheriConfig = self
        self.targets = ConfigLoader.loadTargets(availableTargets)
        self.makeJFlag = "-j" + str(self.makeJobs)

        if self._buildCheri128:
            self.cheriBits = 128
        elif self._buildCheri256:
            self.cheriBits = 256
        else:
            self.cheriBits = self._cheriBits
        self.cheriBitsStr = str(self.cheriBits)

        if not self.quiet:
            print("Sources will be stored in", self.sourceRoot)
            print("Build artifacts will be stored in", self.outputRoot)
            print("Extra files for disk image will be searched for in", self.extraFiles)
            print("Disk image will saved to", self.diskImage)

        # now the derived config options
        self.cheribsdRootfs = self.outputRoot / ("rootfs" + self.cheriBitsStr)
        self.cheribsdSources = self.sourceRoot / "cheribsd"
        self.cheribsdObj = self.buildRoot / ("cheribsd-obj-" + self.cheriBitsStr)
        self.sdkDirectoryName = "sdk" + self.cheriBitsStr
        self.sdkDir = self.outputRoot / self.sdkDirectoryName  # qemu and binutils (and llvm/clang)
        self.otherToolsDir = self.outputRoot / "bootstrap"
        self.dollarPathWithOtherTools = str(self.otherToolsDir / "bin") + ":" + os.getenv("PATH")
        self.sdkSysrootDir = self.sdkDir / "sysroot"
        self.sysrootArchiveName = "cheri-sysroot.tar.gz"

        # for i in ConfigLoader.options:
        #   i.__get__(self, CheriConfig)  # force loading of lazy value
        if self.verbose:
            # for debugging purposes print all the options
            print("cheribuild.py configuration:", dict(ConfigLoader.values))
