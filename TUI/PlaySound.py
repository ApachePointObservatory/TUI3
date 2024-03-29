#!/usr/bin/env python
"""Play each of the standard sounds for TUI.

Gets the sounds from TUI preferences.

2003-04-28 ROwen    Minimal implementation.
2003-10-30 ROwen    Added msgReceived.
2003-11-24 ROwen    Moved to TUI.Sounds; changed to use sound prefs.
2003-12-03 ROwen    Added exposureBegins, exposureEnds, guidingBegins, guidingEnds. 
2003-12-09 ROwen    Modified to import TUI.TUIModel when it's used; this
                    allows TUI.Sounds to be imported before TUI.TUIModel.
2004-05-18 ROwen    Stopped importing RO.Wdg; it wasn't used.
2005-08-02 ROwen    Moved from Sounds/PlaySounds.py -> PlaySound.py
2006-04-14 ROwen    Added guideModeChanges.
2006-10-24 ROwen    Added logHighlightedText.
2009-11-09 ROwen    Added support for Play Sounds preference.
2011-01-31 ROwen    Added exposureFailed.
"""
import TUI.TUIModel

_Prefs = None
_PlaySoundsPref = None
def _playSound(name):
    if name is None:
        return
    global _Prefs, _PlaySoundsPref
    if _Prefs is None:
        _Prefs = TUI.TUIModel.getModel().prefs
        _PlaySoundsPref = _Prefs.getPrefVar("Play Sounds")
    if _PlaySoundsPref.getValue():
        _Prefs.getPrefVar(name).play()

def axisHalt():
    _playSound("Axis Halt")

def axisSlew():
    _playSound("Axis Slew")

def axisTrack():
    print("PLAYING SOUND")
    _playSound("Axis Track")

def cmdDone():
    _playSound("Command Done")

def cmdFailed():
    _playSound("Command Failed")

def exposureBegins():
    _playSound("Exposure Begins")

def exposureEnds():
    _playSound("Exposure Ends")

def exposureFailed():
    _playSound("Exposure Failed")

def guidingBegins():
    _playSound("Guiding Begins")

def guideModeChanges():
    _playSound("Guide Mode Changes")

def guidingEnds():
    _playSound("Guiding Ends")

def msgReceived():
    _playSound("Message Received")

def noGuideStar():
    _playSound("No Guide Star")

def logHighlightedText():
    _playSound("Log Highlighted Text")
