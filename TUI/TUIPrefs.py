#!/usr/bin/env python
"""A set of preferences for TUI

To Do:
- Fix the bug that (at least on MacOS X with aqua Tk 8.4.1) the labels
    for the various prefs have their own font, which is not the main font

History:
2002-03-08 ROwen    First release
2002-11-13 ROwen    If the user has a home directory, the prefs file is stored there
2003-02-28 ROwen    Added sanity checking to username and host prefs.
2003-04-09 ROwen    Changed shortDescr to helpText, preperatory to full help implementation.
2003-04-22 ROwen    Fixed the default host.
2003-06-18 ROwen    Modified to test for StandardError instead of Exception
2003-08-07 ROwen    Bug fix: was not setting up prefs in RO.Wdg.
2003-08-11 ROwen    Added auto FTP prefs.
2003-08-25 ROwen    Re-added Misc Font lost in 2003-08 update.
2003-11-24 ROwen    Added sounds.
2003-12-03 ROwen    Added Guiding Begins, Guiding Ends, Exposure Begins, Exposure Ends.
2003-12-23 ROwen    Modified to use .wav instead of .aiff.
2004-02-03 ROwen    Modified to use RO.OS.getPrefsDir and thus to
                    look for the prefs file where it really belongs.
2004-09-09 ROwen    Added "Seq By File" preference.
2005-06-10 ROwen    Added "No Guide Star" sound preference.
2005-07-14 ROwen    Default Save As= user's documents directory.
2005-08-02 ROwen    Modified to find Sounds dir without assuming it is a package.
2005-09-15 ROwen    Renamed preference "Auto FTP" to "Auto Get".
                    Added preference "View Image".
                    Changed "get" to "download" in help text for exposures prefs.
2005-09-23 ROwen    Added anchors to help URLs for exposure and sound prefs.
2005-09-28 ROwen    Modified to use RO.OS.getPrefsDirs instead of getPrefsDir.
2005-10-06 ROwen    getprefsDir needs new inclNone=True argument.
2006-04-14 ROwen    Added "Guide Mode Changes" sound preference.
2006-05-19 ROwen    Added Guide Color prefs.
2006-10-24 ROwen    Added "Debug Color" color pref.
                    Added "Highlight Background" color pref.
                    Added "Log Highlighted Text" sound pref.
2007-09-05 ROwen    Fixed test code.
2007-11-16 ROwen    Modified to allow a port as part of Host address.
2008-07-07 ROwen    Added UMask preference.
2009-05-06 ROwen    Changed Auto Get preference to Get Every.
2009-05-12 ROwen    Changed default Debug Color from gray to purple.
2009-11-09 ROwen    Added Play Sounds preference.
                    Changed name of preferences file from TUIPrefs to <ApplicationName>Prefs.
2010-03-18 ROwen    Moved _getPrefsFile to TUI.TUIPaths.getPrefsFile.
2010-07-02 ROwen    Added "Keep Guide Images" preference.
2011-01-31 ROwen    Added "Exposure Failed" sound preference.
2011-06-28 ROwen    Added " and ctrl-click" to help string for Centroid Color.
2012-07-10 ROwen    Added "Menu Font" preference. This fixes an issue in aqua Tcl/Tk 8.5
                    where menu items showed up in the "Misc Font"..
2012-12-19 ROwen    Changed font preferences to be for font size only and simplifies the settings.
2014-08-31 ROwen    Improved help string for Keep Guide Images
2014-09-17 ROwen    Modified to test for Exception instead of StandardError 
"""
#import pychecker.checker
import os
import sys
import tkinter
import tkinter.font
import TUI
import TUI.TUIPaths
import TUI.Version
import RO.OS
from RO.Prefs import PrefVar, PrefWdg
import RO.Wdg

_HelpURL = "TUIMenu/PreferencesWin.html"
_ExposuresHelpURL = _HelpURL + "#Exposures"
_SoundHelpURL = _HelpURL + "#Sounds"

_SoundsDir = RO.OS.getResourceDir(TUI, "Sounds")

class TUIPrefs(PrefVar.PrefSet):
    def __init__(self,
        defFileName = TUI.TUIPaths.getPrefsFile(),
    ):
        # before messing with the option database
        # create Font objects for the various types of widgets we wish to control
        labelWdg = tkinter.Label()
        textWdg = tkinter.Text()
        menuWdg = tkinter.Menu()
        defMenuFont = tkinter.font.Font(font=menuWdg.cget("font"))
        
        # one must set umask to read it; blecch
        defUMaskInt = os.umask(0)
        os.umask(defUMaskInt)
        defUMaskStr = "%04o" % (defUMaskInt,)
        
        # set up the preference list
        prefList = (
            PrefVar.StrPrefVar(
                name = "User Name",
                category = "Connection",
                defValue = "",
                partialPattern = r"^([a-zA-Z_][-_.a-zA-Z0-9]*)?$",
                helpText = "Your name (no spaces)",
                helpURL = _HelpURL,
            ),
            PrefVar.StrPrefVar(
                name = "Host",
                category = "Connection",
                defValue = "hub35m.apo.nmsu.edu",
                helpText = "IP address of remote computer (and optional port)",
                helpURL = _HelpURL,
                partialPattern = r"^[-_.a-zA-Z0-9]*( +[0-9]*)?$",
                editWidth=24,
            ),
            
            PrefVar.BoolPrefVar(
                name = "Seq By File",
                category = "Exposures",
                defValue = False,
                helpText = "Number files by file name or by directory?",
                helpURL = _ExposuresHelpURL,
            ),
            PrefVar.IntPrefVar(
                name = "Get Every",
                category = "Exposures",
                defValue = 0,
                minValue = -1,
                maxValue = 999,
                helpText = "Automatically download every Nth image (0=none; -1=skip excess)",
                helpURL = _ExposuresHelpURL,
            ),
            PrefVar.BoolPrefVar(
                name = "Get Collab",
                category = "Exposures",
                defValue = True,
                helpText = "Download collaborators' images?",
                helpURL = _ExposuresHelpURL,
            ),
            PrefVar.DirectoryPrefVar(
                name = "Save To",
                category = "Exposures",
                defValue = RO.OS.getDocsDir(),
                helpText = "Directory in which to save images",
                helpURL = _ExposuresHelpURL,
            ),
            PrefVar.BoolPrefVar(
                name = "View Image",
                category = "Exposures",
                defValue = False,
                helpText = "Automatically display image?",
                helpURL = _ExposuresHelpURL,
            ),
            PrefVar.StrPrefVar(
            	name = "UMask",
            	category = "Exposures",
            	defValue = defUMaskStr,
                partialPattern = r"^[0-8]{0,4}$",
                editWidth = 5,
                callFunc = setUMask,
            	helpText = "umask for saved images and other files",
            	helpURL = _ExposuresHelpURL,
            ),
            PrefVar.BoolPrefVar(
                name = "Keep Guide Images",
                category = "Exposures",
                defValue = False,
                helpText = "Keep all guide images, even after TUI quits? (eats disk space!)",
                helpURL = _ExposuresHelpURL,
            ),

            PrefVar.FontSizePrefVar(
                name = "Main Font Size",
                category = "Fonts",
                defWdg = labelWdg,
                optionPatterns = ("*font",),
                helpText = "Font size for most widgets",
                helpURL = _HelpURL,
            ),
            PrefVar.FontSizePrefVar(
                name = "Log Font Size",
                category = "Fonts",
                defWdg = textWdg,
                optionPatterns = ("*Text.font",),
                helpText = "Font size for logs and other text widgets",
                helpURL = _HelpURL,
            ),
# if you want to be able to set the font size for menu items
# then uncomment this PrefVar and comment out option_add("*Menu.font"... below
#             PrefVar.FontSizePrefVar(
#                 name = "Menu Font Size",
#                 category = "Fonts",
#                 defWdg = menuWdg,
#                 optionPatterns = ("*Menu.font",),
#                 helpText = "Font size for menu entries",
#                 helpURL = _HelpURL,
#             ),
            
            PrefVar.ColorPrefVar(
                name = "Background Color",
                category = "Colors",
                defValue = tkinter.Label().cget("background"),
                wdgOption = "background",
                helpText = "Background color for most widgets",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Foreground Color",
                category = "Colors",
                defValue = tkinter.Label().cget("foreground"),
                wdgOption = "foreground",
                helpText = "Color for normal text, etc.",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Debug Color",
                category = "Colors",
                defValue = "#006723",
                helpText = "Color that indicates a debug-level message",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Warning Color",
                category = "Colors",
                defValue = "blue2",
                helpText = "Color that indicates a warning",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Error Color",
                category = "Colors",
                defValue = "red",
                helpText = "Color that indicates an error",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Bad Background",
                category = "Colors",
                defValue = "pink",
                helpText = "Background color for invalid data",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Highlight Background",
                category = "Colors",
                defValue = "#bdffe0",
                helpText = "Background color for highlighted text",
                helpURL = _HelpURL,
            ),
            
            PrefVar.ColorPrefVar(
                name = "Centroid Color",
                category = "Guide Colors",
                defValue = "cyan",
                helpText = "Color for manually centroided stars and ctrl-click",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Found Star Color",
                category = "Guide Colors",
                defValue = "green",
                helpText = "Color for automatically found stars",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Guide Star Color",
                category = "Guide Colors",
                defValue = "magenta",
                helpText = "Color for guide stars",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Boresight Color",
                category = "Guide Colors",
                defValue = "cyan",
                helpText = "Color for boresight",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Saturated Pixel Color",
                category = "Guide Colors",
                defValue = "red",
                helpText = "Color for saturated pixels",
                helpURL = _HelpURL,
            ),
            PrefVar.ColorPrefVar(
                name = "Masked Pixel Color",
                category = "Guide Colors",
                defValue = "green",
                helpText = "Color for masked pixels",
                helpURL = _HelpURL,
            ),
            
            PrefVar.BoolPrefVar(
                name = "Play Sounds",
                category = "Sounds",
                defValue = True,
                helpText = "Play sound cues?",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Axis Halt",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "AxisHalt.wav"),
                bellNum = 3,
                helpText = "Sound cue for axis halt",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Axis Slew",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "AxisSlew.wav"),
                bellNum = 1,
                helpText = "Sound cue for start of axis slew",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Axis Track",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "AxisTrack.wav"),
                bellNum = 2,
                bellDelay = 150,
                helpText = "Sound cue for start of axis tracking",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Command Done",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "CommandDone.wav"),
                bellNum = 1,
                helpText = "Sound cue for command ended successfully",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Command Failed",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "CommandFailed.wav"),
                bellNum = 3,
                bellDelay = 100,
                helpText = "Sound cue for command failed",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Exposure Begins",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "ExposureBegins.wav"),
                bellNum = 1,
                helpText = "Sound cue for start of exposure",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Exposure Ends",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "ExposureEnds.wav"),
                bellNum = 2,
                bellDelay = 100,
                helpText = "Sound cue for end of exposure",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Exposure Failed",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "ExposureFailed.wav"),
                bellNum = 3,
                bellDelay = 100,
                helpText = "Sound cue for failed exposure",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Guiding Begins",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "GuidingBegins.wav"),
                bellNum = 1,
                helpText = "Sound cue for start of guiding",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Guide Mode Changes",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "GuideModeChanges.wav"),
                bellNum = 1,
                helpText = "Sound cue for a change in guide mode",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Guiding Ends",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "GuidingEnds.wav"),
                bellNum = 2,
                bellDelay = 100,
                helpText = "Sound cue for failure of guiding",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Message Received",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "MessageReceived.wav"),
                bellNum = 1,
                helpText = "Sound cue for message received",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "No Guide Star",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "NoGuideStar.wav"),
                bellNum = 2,
                helpText = "Sound cue for guiding loop found no stars",
                helpURL = _SoundHelpURL,
            ),
            PrefVar.SoundPrefVar(
                name = "Log Highlighted Text",
                category = "Sounds",
                defValue = os.path.join(_SoundsDir, "LogHighlightedText.wav"),
                bellNum = 2,
                helpText = "Sound when highlighted text is added to log",
                helpURL = _SoundHelpURL,
            ),
        )
        PrefVar.PrefSet.__init__(self,
            prefList = prefList,
            defFileName = defFileName,
            defHeader = """Preferences for the Telescope User Interface\n""",
        )
        
        # use the default font for menu entries, instead of the basic font preference
        labelWdg.option_add("*Menu.font", "size %s" % (defMenuFont.cget("size"),))

        try:
            self.readFromFile()
        except Exception as e:
            sys.stderr.write ("could not read TUI preferences: %s\n" % (e,))
        
        # set preferences for RO.Wdg objects
        RO.Wdg.WdgPrefs.setWdgPrefs(self)
    
    def getWdg(self, master):
        """Returns a preferences setting widget.
        """
        return PrefWdg.PrefWdg (master = master, prefSet = self)

def getFont(wdgClass, optionPattern=None):
    """Creates a Font object that is initialized to the default value of the specified
    type of widget (e.g. Tkinter.Label). optionPattern is an option database pattern;
    if supplied, an entry to the database is added for this pattern using this new Font.
    Hence the font can be connected up to automatically update a class of widgets.
    
    Not used anymore; delete once auto-update of colors is handled.
    """
    aWdg = wdgClass()
    defFontDescr = aWdg.cget("font")
    theFont = tkinter.font.Font(font=defFontDescr)
    if optionPattern:
        aWdg.option_add(optionPattern, theFont)
    return theFont  

def setUMask(umaskStr, prefVar=None):
	"""Handle changes to the UMask preference.
	
	Inputs:
	- umaskStr: umask value as a string of octal digits (e.g. "0022")
	- prefVar: preference variable (optional)
	"""
	umaskStr = umaskStr or "0" # convert None or "" to "0"
	os.umask(int(umaskStr, 8))

if __name__ == "__main__":
    import RO.Wdg
    root = RO.Wdg.PythonTk()

    prefs = TUIPrefs()

    testFrame = prefs.getWdg(root)
    testFrame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
    root.title("Test Preferences for TUI")

    root.mainloop()
