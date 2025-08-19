#!/usr/bin/env python
"""About TUI window

2003-12-17 ROwen
2004-03-08 ROwen    Expanded the text and made it center-justified.
                    Moved the code to a separate class.
                    Added test code.
2004-05-18 ROwen    Stopped obtaining TUI model in addWindow; it was ignored.
                    Thus stopped importing TUI.TUIModel in the main code.
2005-10-24 ROwen    Updated the acknowledgements to include WingIDE.
2006-06-01 ROwen    Updated the acknowledgements to include Fritz Stauffer.
2007-04-17 ROwen    Updated the acknowledgements to add "scripts".
2009-04-21 ROwen    Updated for tuiModel root->tkRoot.
2010-03-10 ROwen    Added WindowName
2010-03-18 ROwen    Added special file paths to the information.
                    Removed Wingware from the acknowledgements.
2010-04-23 ROwen    Stopped using Exception.message to make Python 2.6 happier.
2011-02-18 ROwen    Acknowledge Joseph Huehnerhoff for the Windows builds.
2012-10-15 ROwen    Assume matplotlib is installed. Report pygame version, if installed.
2013-09-05 ROwen    Change "import Image" to "from PIL import Image" for compatibility with Pillow.
2014-09-16 ROwen    Modified to use astropy instead of pyfits, if available.
2014-10-28 ROwen    Improved version display if pyfits used instead of astropy.
"""
import os.path
import sys
from PIL import Image
import matplotlib
import numpy
try:
    import astropy
    astropyVers = "astropy: %s" % (astropy.__version__,)
except ImportError:
    import pyfits
    astropyVers = "pyfits: %s" % (pyfits.__version__,)
try:
    import pygame
    pygameVersion = pygame.__version__
except ImportError:
    pygameVersion = "not installed"
try:
    import objc
    objcVersion = objc.__version__
except ImportError:
    objcVersion = "not installed"
import RO.Wdg
from RO.StringUtil import strFromException
import TUI.TUIModel
import TUI.TUIPaths
import TUI.Version

WindowName = "%s.About %s" % (TUI.Version.ApplicationName, TUI.Version.ApplicationName)

def addWindow(tlSet):
    tlSet.createToplevel(
        name = WindowName,
        resizable = False,
        visible = False,
        wdgFunc = AboutWdg,
    )

def getInfoDict():
    global astropyVers
    global pygameVersion
    tuiModel = TUI.TUIModel.getModel()
    res = {}
    res["tui"] = TUI.Version.VersionStr
    res["python"] = sys.version.split()[0]
    res["tcltk"] = tuiModel.tkRoot.call("info", "patchlevel")
    res["matplotlib"] = matplotlib.__version__
    res["numpy"] = numpy.__version__
    res["astropy"] = astropyVers
    # Image uses VERSION, but PILLOW supports __version__
    res["pil"] = getattr(Image, "VERSION", getattr(Image, "__version__", "unknown"))
    res["pygame"] = pygameVersion
    res["pyobjc"] = objcVersion
    res["specialFiles"] = getSpecialFileStr()
    return res

def getSpecialFileStr():
    """Return a string describing where the special files are
    """
    def strFromPath(filePath):
        if os.path.exists(filePath):
            return filePath
        return "%s (not found)" % (filePath,)
        
    outStrList = []
    for name, func in (
        ("Preferences", TUI.TUIPaths.getPrefsFile),
        ("Window Geom.", TUI.TUIPaths.getGeomFile),
        ("User Presets", TUI.TUIPaths.getUserPresetsFile)
    ):
        try:
            filePath = func()
            pathStr = strFromPath(filePath)
        except Exception as e:
            pathStr = "?: %s" % (strFromException(e),)
        outStrList.append("%s: %s" % (name, pathStr))

    tuiAdditionsDirs = TUI.TUIPaths.getAddPaths(ifExists=False)
    for ind, filePath in enumerate(tuiAdditionsDirs):
        pathStr = strFromPath(filePath)
        outStrList.append("%sAdditions %d: %s" % (TUI.Version.ApplicationName, ind + 1, pathStr))

    outStrList.append("Error Log: %s" % (sys.stderr.name,))

    return "\n".join(outStrList)
    

class AboutWdg(RO.Wdg.StrLabel):
    def __init__(self, master):
        versDict = getInfoDict()
        RO.Wdg.StrLabel.__init__(
            self,
            master = master,
            text = """APO 3.5m Telescope User Interface
Version %(tui)s
by Russell Owen
Maintained by Gordon MacDonald

Special files:
%(specialFiles)s

Library versions:
Python: %(python)s
Tcl/Tk: %(tcltk)s
matplotlib: %(matplotlib)s
numpy: %(numpy)s
%(astropy)s
PIL: %(pil)s
pygame: %(pygame)s
pyObjC: %(pyobjc)s

With special thanks to:
- Joseph Huehnerhoff for the Windows builds
- Craig Loomis and Fritz Stauffer for the APO hub
- Bob Loewenstein for Remark
- Dan Long for the photograph used for the icon
- APO observing specialists and users
  for suggestions, scripts and bug reports
""" % (versDict),
            justify = "left",
            borderwidth = 10,
        )


if __name__ == "__main__":
    import TUI.TUIModel
    root = RO.Wdg.PythonTk()

    tm = TUI.TUIModel.getModel(True)
    addWindow(tm.tlSet)
    tm.tlSet.makeVisible('TUI.About TUI')
    
    getSpecialFileStr()

    root.lower()

    root.mainloop()
