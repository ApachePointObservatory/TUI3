#!/usr/bin/env python
"""Displays time, airmass, instrument name, focus...

History:
2003-03-26 ROwen    Modified to use the tcc model.
2003-03-31 ROwen    Switched from RO.Wdg.LabelledWdg to RO.Wdg.Gridder.
2003-04-24 ROwen    Modified to use Gridder startNewCol.
2003-06-09 Rowen    Removed dispatcher arg.
2003-06-12 ROwen    Added helpText entries.
2003-06-25 ROwen    Modified test case to handle message data as a dict
2003-10-29 ROwen    Modified to accommodate moved TelConst.
2003-12-03 ROwen    Added guide status, including sound cues.
2004-02-04 ROwen    Modified _HelpURL to match minor help reorg.
2004-08-26 ROwen    Made the instrument name field wider (8->10).
2004-09-23 ROwen    Modified to allow callNow as the default for keyVars.
2005-06-07 ROwen    Disabled guide state display (until I figure out how
                    to make it work with the new guide system).
2005-06-10 ROwen    Rewrote guide state display to work with new guide system.
2005-06-15 ROwen    Updated for guide model change guiding->guideState.
2005-08-02 ROwen    Modified for TUI.Sounds->TUI.PlaySound.
2008-02-01 ROwen    Modified GC Focus to get its value from the new gmech actor.
                    Improved guide state output to show camera (if state not Off or unknown).
2008-03-25 ROwen    Actually modified GC Focus to get its value from the new gmech actor
                    (somehow that change did not actually occur on 2008-02-01).
2009-09-09 ROwen    Modified to use TestData.
2010-11-04 ROwen    Tweaked help URLs.
2010-11-05 ROwen    Show UTC date as well as time.
2011-02-16 ROwen    Made the display expand to the right of the displayed data.
2012-07-10 ROwen    Modified to use RO.TkUtil.Timer
2012-12-07 ROwen    Modified to use RO.Astro.Tm clock correction to show correct time
                    even if user's clock is keeping TAI or is drifting.
                    Improve timing of next clock update to avoid lag.
"""
import time
import tkinter
import RO.Astro.Tm
import RO.Astro.Sph
import RO.Constants
import RO.PhysConst
import RO.StringUtil
from RO.TkUtil import Timer
import RO.Wdg
import TUI.PlaySound
import TUI.TCC.TelConst
import TUI.TCC.TCCModel
import TUI.Guide.GuideModel
import TUI.Guide.GMechModel

# add instrument angles

_HelpURL = "Telescope/StatusWin.html#Misc"

class MiscWdg (tkinter.Frame):
    def __init__ (self, master=None, **kargs):
        """Displays miscellaneous information, such as current time and az/alt

        Inputs:
        - master        master Tk widget -- typically a frame or window
        """
        tkinter.Frame.__init__(self, master=master, **kargs)
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.gmechModel = TUI.Guide.GMechModel.getModel()
        
        self._clockTimer = Timer()
        
        gr = RO.Wdg.Gridder(self, sticky="e")

        # magic numbers
        AzAltRotPrec = 1    # number of digits past decimal point
        
        self.haWdg = RO.Wdg.DMSLabel(
            master = self,
            precision = 0,
            nFields = 3,
            cvtDegToHrs = 1,
            width = 8,
            helpText = "Hour angle of the object",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "HA",
            dataWdg = self.haWdg,
            units = "hms",
        )
        
        self.lmstWdg = RO.Wdg.DMSLabel(
            master = self,
            precision = 0,
            nFields = 3,
            width = 8,
            justify="right",
            helpText = "Local mean sidereal time at APO",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "LMST",
            dataWdg = self.lmstWdg,
            units = "hms",
        )
        
        self.utcWdg = RO.Wdg.StrLabel(
            master = self,
            width = 19,
            helpText = "Coordinated universal time",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "UTC",
            dataWdg = self.utcWdg,
            colSpan = 2,
        )
        
        # start the second column of widgets
        gr.startNewCol(spacing=1)
        
        self.guideWdg = RO.Wdg.StrLabel(
            master = self,
            width = 13,
            anchor = "w",
            helpText = "State of guiding",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "Guiding",
            dataWdg = self.guideWdg,
            colSpan = 4,
            units = False,
            sticky = "ew",
        )
        gr._nextCol -= 2 # allow overlap with widget to the right
        self.guideModelDict = {} # guide camera name: guide model
        for guideModel in TUI.Guide.GuideModel.modelIter():
            gcamName = guideModel.gcamName
            if gcamName.endswith("focus"):
                continue
            self.guideModelDict[guideModel.gcamName] = guideModel
            guideModel.locGuideStateSummary.addIndexedCallback(self._updGuideStateSummary, callNow=False)
        self._updGuideStateSummary()

        # airmass and zenith distance
        self.airmassWdg = RO.Wdg.FloatLabel(
            master = self,
            precision=3,
            width=5,
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "Airmass",
            dataWdg = self.airmassWdg,
            units = "",
        )
#       self.tccModel.axePos.addCallback(self.setAxePos)
        
        self.zdWdg = RO.Wdg.FloatLabel(
            master = self,
            precision=AzAltRotPrec,
            helpText = "Zenith distance",
            helpURL = _HelpURL,
            width=5,
        )
        gr.gridWdg (
            label = "ZD",
            dataWdg = self.zdWdg,
            units = RO.StringUtil.DegStr,
        )
        
        # start the third column of widgets
        gr.startNewCol(spacing=1)
        
        self.instNameWdg = RO.Wdg.StrLabel(
            master = self,
            width = 10,
            anchor = "w",
            helpText = "Current instrument",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "Inst",
            dataWdg = self.instNameWdg,
            colSpan = 3,
            units = False,
            sticky = "w",
        )
        self.tccModel.instName.addCallback(self.updateInstName)
        
        self.secFocusWdg = RO.Wdg.FloatLabel(
            master = self,
            precision=0,
            width=5,
            helpText = "Secondary mirror focus",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "Focus",
            dataWdg = self.secFocusWdg,
            units = "\N{MICRO SIGN}m",
        )
        self.tccModel.secFocus.addROWdg(self.secFocusWdg)
        
        self.gcFocusWdg = RO.Wdg.FloatLabel(
            master = self,
            precision=0,
            width=5,
            helpText = "NA2 guide camera focus",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "GC Focus",
            dataWdg = self.gcFocusWdg,
            units = "\N{MICRO SIGN}m",
        )
        self.gmechModel.focus.addROWdg(self.gcFocusWdg)
        
        # all widgets are gridded
        gr.allGridded()
        
        # add callbacks that deal with multiple widgets
        self.tccModel.axePos.addCallback(self.setAxePos)
        
        # start clock updates       
        self.updateClock()
        
        # allow the last+1 column to grow to fill the available space
        self.columnconfigure(gr.getMaxNextCol(), weight=1)

    def updateInstName(self, *args, **kwargs):
        instName, isCurrent = self.tccModel.instName.getInd(0)
        if instName == "?":
            severity = RO.Constants.sevError
        else:
            severity = RO.Constants.sevNormal
        self.instNameWdg.set(instName, severity=severity, isCurrent=isCurrent)
    
    def updateClock(self):
        """Automatically update the time displays in this widget.
        Call once to get things going
        """
        # update utc
        currPythonSeconds = RO.Astro.Tm.getCurrPySec()
        currUTCTuple= time.gmtime(currPythonSeconds)
        self.utcWdg.set(time.strftime("%Y-%m-%d %H:%M:%S", currUTCTuple))
        currUTCMJD = RO.Astro.Tm.mjdFromPyTuple(currUTCTuple)
    
        # update local (at APO) mean sidereal time, in degrees
        currLMST = RO.Astro.Tm.lmstFromUT1(currUTCMJD, TUI.TCC.TelConst.Longitude) * RO.PhysConst.HrsPerDeg
        self.lmstWdg.set(currLMST)
        
        # schedule the next event
        clockDelay = 1.01 - (currPythonSeconds % 1.0)
        self._clockTimer.start(clockDelay, self.updateClock)
    
    def setAxePos(self, axePos, isCurrent=True, keyVar=None):
        """Updates ha, dec, zenith distance and airmass
        axePos values are: (az, alt, rot)
        """
        az, alt = axePos[0:2]

        if alt is not None:
            airmass = RO.Astro.Sph.airmass(alt)
            zd = 90.0 - alt
        else:
            airmass = None
            zd = None
        
        # set zd, airmass widgets
        self.zdWdg.set(zd, isCurrent=isCurrent)
        self.airmassWdg.set(airmass, isCurrent=isCurrent)
        
        # set hour angle (set in degrees, display in hours)
        try:
            (ha, dec), atPole = RO.Astro.Sph.haDecFromAzAlt((az, alt), TUI.TCC.TelConst.Latitude)
            if atPole:
                ha = None
        except (TypeError, ValueError):
            ha = None
        self.haWdg.set(ha, isCurrent=isCurrent)
    
    def _updGuideStateSummary(self, *args, **kargs):
        """Check state of all guiders.
        Display "best" state as follows:
        - is current and not off
        - is current and off
        - not current and not off
        - not current and off
        """
        stateInfo = [] # each element = (is current, not off, state str, actor)
        for gcamName, guideModel in self.guideModelDict.items():
            state, isCurr = guideModel.guideState.getInd(0)
            if state is None:
                stateLow = ""
            else:
                stateLow = state.lower()
            notOff = stateLow != "off"
            stateInfo.append((isCurr, notOff, stateLow, gcamName))
        stateInfo.sort()
        bestCurr, bestNotOff, bestStateLow, bestActor = stateInfo[-1]
        if bestStateLow in ("on", "off"):
            severity = RO.Constants.sevNormal
        else:
            severity = RO.Constants.sevWarning
        if bestStateLow in ("", "off"):
            stateText = bestStateLow.title()
        else:
            stateText = "%s %s" % (bestStateLow.title(), bestActor)
        self.guideWdg.set(stateText, isCurrent = bestCurr, severity = severity)


if __name__ == "__main__":
    from . import TestData

    tuiModel = TestData.tuiModel

    testFrame = MiscWdg(tuiModel.tkRoot)
    testFrame.pack()

    dataList = (
        "AxePos=-350.999, 45, NaN",
        "SecFocus=570",
        "GCFocus=-300",
        "Inst=DIS",
        "TCCStatus=TTT, NNN",
    )

    TestData.testDispatcher.dispatch(dataList)

    tuiModel.tkRoot.mainloop()
