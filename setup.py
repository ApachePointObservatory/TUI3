"""A platform-independent Python script that builds TUI.
Adapted from Russel Owen's build script.

Usage:
For MacOS:      % python setup.py [--quiet] py2app
For Windows:    % python setup.py [--quiet] py2exe 
For Linux       % python setup.py install

History:
2022-12-01 GMac     Initial.
"""
import os
import platform
import shutil
import subprocess
import sys
from setuptools import setup


def doSetup( platformOptions ):
    setup(
            name = appName,
            version = shortVersStr,
            url = "https://github.com/ApachePointObservatory/TUI3",
            **platformOptions,
            )

# add tuiRoot to sys.path before importing RO or TUI
tuiRoot = os.path.dirname(os.path.abspath(__file__))
roRoot = os.path.join(tuiRoot, "RO")
sys.path = [roRoot, tuiRoot] + sys.path
import TUI.Version

# packages to include recursively
inclModules = ()
inclPackages = (
    "matplotlib",
    "numpy",
    "astropy",
    "PIL",
)
appName = TUI.Version.ApplicationName
mainProg = os.path.join(tuiRoot, "runtuiWithLog.py")
iconFile = "%s.icns" % appName
fullVersStr = TUI.Version.VersionStr
shortVersStr = fullVersStr.split(None, 1)[0]

platformSystem = platform.system()

if platformSystem == "Darwin":
    
    plist = dict(
        CFBundleName                = appName,
        CFBundleShortVersionString  = shortVersStr,
        CFBundleGetInfoString       = "%s %s" % (appName, fullVersStr),
        CFBundleExecutable          = appName,
        LSMinimumSystemVersion      = "10.6.0"
        )
    
    platformOptions = dict(
            app = [mainProg],
            setup_requires = ["py2app"],
            options = dict(
                py2app = dict (
                    plist = plist,
                    iconfile = iconFile,
                    includes = inclModules,
                    packages = (*inclPackages,
                        "Foundation",
                        "TUI",
                        "RO"),
                    )
                ),
            )

    doSetup( platformOptions )

    print("*** Creating disk image ***")
    appPath = os.path.join("dist", "%s.app" % (appName,))
    appName = "%s_%s_Mac" % (appName, shortVersStr)
    destFile = os.path.join("dist", appName)
    args=("hdiutil", "create", "-srcdir", appPath, destFile)
    retCode = subprocess.call(args=args)
    print("*** Done building %s ***" % (appName,))

elif platformSystem == "Windows":
    
    import py2exe
    
    platformOptions = dict(
            windows = [mainProg],
            setup_requires = ["py2exe"],
            install_requires = ("matplotlib", "numpy", "astropy", "pillow"),
            packages = ("TUI", "RO"),
            )

    doSetup( platformOptions )

elif platformSystem == "Linux":
    platformOptions = dict(
        scripts = [mainProg],
        install_requires = ("matplotlib", "numpy", "astropy", "pillow"),
        packages=("TUI", "RO"),
    )

    doSetup( platformOptions )

