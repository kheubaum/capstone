#!/usr/bin/env python
import glob
import os
import platform
import shutil
import stat
import sys

from distutils import log
from distutils import dir_util
from distutils.command.build_clib import build_clib
from distutils.command.sdist import sdist
from distutils.core import setup
from distutils.sysconfig import get_python_lib


# platform description refers at https://docs.python.org/2/library/sys.html#sys.platform
VERSION = '3.0'
SYSTEM = sys.platform

SITE_PACKAGES = os.path.join(get_python_lib(), "capstone")

SETUP_DATA_FILES = []


class LazyList(list):
    """A list which re-evaluates each time.
    This is used to provide late binding for setup() below.
    """
    def __init__(self, callback):
        super(LazyList, self).__init__()
        self.callback = callback

    def __iter__(self):
        return iter(self.callback())


def copy_sources():
    """Copy the C sources into the source directory.
    This rearranges the source files under the python distribution
    directory.
    """
    src = []

    try:
        dir_util.remove_tree("src/")
    except (IOError, OSError):
        pass

    dir_util.copy_tree("../../arch", "src/arch/")
    dir_util.copy_tree("../../include", "src/include/")
    dir_util.copy_tree("../../msvc/headers", "src/msvc/headers/")

    src.extend(glob.glob("../../*.[ch]"))
    src.extend(glob.glob("../../*.mk"))

    src.extend(glob.glob("../../Makefile"))
    src.extend(glob.glob("../../LICENSE*"))
    src.extend(glob.glob("../../README"))
    src.extend(glob.glob("../../*.TXT"))
    src.extend(glob.glob("../../RELEASE_NOTES"))
    src.extend(glob.glob("../../make.sh"))

    for filename in src:
        outpath = os.path.join("./src/", os.path.basename(filename))
        log.info("%s -> %s" % (filename, outpath))
        shutil.copy(filename, outpath)


class custom_sdist(sdist):
    """Reshuffle files for distribution."""

    def run(self):
        copy_sources()
        return sdist.run(self)


class custom_build_clib(build_clib):
    """Customized build_clib command."""

    def run(self):
        log.info('running custom_build_clib')
        build_clib.run(self)

    def finalize_options(self):
        # We want build-clib to default to build-lib as defined by the "build"
        # command.  This is so the compiled library will be put in the right
        # place along side the python code.
        self.set_undefined_options('build',
                                   ('build_lib', 'build_clib'),
                                   ('build_temp', 'build_temp'),
                                   ('compiler', 'compiler'),
                                   ('debug', 'debug'),
                                   ('force', 'force'))

        build_clib.finalize_options(self)

    def build_libraries(self, libraries):
        if not os.path.exists('src'):
            return

        for (lib_name, build_info) in libraries:
            log.info("building '%s' library", lib_name)

            os.chdir("src")

            # platform description refers at https://docs.python.org/2/library/sys.html#sys.platform
            if SYSTEM != "win32":
                os.chmod("make.sh", stat.S_IREAD|stat.S_IEXEC)
                os.system("CAPSTONE_BUILD_CORE_ONLY=yes ./make.sh")

            if SYSTEM == "darwin":
                SETUP_DATA_FILES.append("src/libcapstone.dylib")
            elif SYSTEM != "win32":
                SETUP_DATA_FILES.append("src/libcapstone.so")

            os.chdir("..")


def dummy_src():
    return []


setup(
    provides=['capstone'],
    packages=['capstone'],
    name='capstone',
    version=VERSION,
    author='Nguyen Anh Quynh',
    author_email='aquynh@gmail.com',
    description='Capstone disassembly engine',
    url='http://www.capstone-engine.org',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    requires=['ctypes'],
    cmdclass=dict(
        build_clib=custom_build_clib,
        sdist=custom_sdist,
    ),

    libraries=[(
        'capstone', dict(
            package='capstone',
            sources=LazyList(dummy_src)
        ),
    )],

    data_files=[(SITE_PACKAGES, SETUP_DATA_FILES)],
)
