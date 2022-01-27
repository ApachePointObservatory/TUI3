#!/usr/bin/env python
"""Displays the axis position and various status.

To do:
- Offer some simple way of showing all status bits (as words), e.g.:
    - A ... or More button that appears when there is more than one bit to describe; this opens a new window
    - Right-click to open a new window; this should display ... or something to indicate hidden info
    - A disclosure triangle to expand the boxes vertically as required
      (but if there is one per axis controller, then are they ganged or separate? I'd prefer ganged)

History:
2003-03-26 ROwen    Modified to use the tcc model.
2003-03-31 ROwen    Switched from RO.Wdg.LabelledWdg to RO.Wdg.Gridder
2003-06-09 Rowen    Removed dispatcher arg.
2003-06-12 ROwen    Added helpText entries.
2003-06-25 ROwen    Modified test case to handle message data as a dict.
2003-11-24 ROwen    Modified to play sounds when axis state changes.
2004-02-04 ROwen    Modified _HelpURL to match minor help reorg.
2004-08-11 ROwen    Modified for improved TCCModel.
                    If axis controller status is None, displays "Not responding".
                    Use modified RO.Wdg state constants with st_ prefix.
2004-09-03 ROwen    Modified for RO.Wdg.st_... -> RO.Constants.st_...
2005-01-05 ROwen    Modified for RO.Wdg.Label state->severity and RO.Constants.st_... -> sev...
2005-08-02 ROwen    Modified for TUI.Sounds->TUI.PlaySound.
2005-09-12 ROwen    Put "stop switch" near the end because it really means
                    "axis controller shut itself down for some reason".
                    Bug fix: used TUI.PlaySound without importing it.
2006-03-06 ROwen    Modified to use tccModel.axisCmdState and rotExists instead of tccStatus.
                    Modified to play sounds in a particular order
                    and with some time between them.
                    Modified to hide rotator AxisErrCode when no rotator
                    (and thus shown only one "NotAvailable").
                    Reduced width of commanded state field by one.
2006-03-16 ROwen    Modified to use TestData module for testing.
                    Moved Stop Switch error bit to beginning of ErrorBits
                    to stop display of "overcurrent" when a stop button is in.
2006-03-27 ROwen    Restored Stop Switch error bit's earlier position;
                    the problem is that the stop bit may go on
                    due to overcurrent or other serious problems.
2006-04-27 ROwen    Modified to hide rotator axis position units when no rotator.
                    Removed unused _StateDict (thanks pychecker).
2006-05-09 ROwen    Modified to play "axisHalt" sound when an axis reports an error.
                    Removed old hack that reset controller state to 0,
                    since the TCC reliably reports controller state.
2006-05-18 ROwen    Modified to play axisHalt less often in response to status;
                    now it only plays if the status is newly bad,
                    but not if it changes from one bad state to another.
2008-04-01 ROwen    Updated status bit descriptions for new axis controller.
2009-09-10 ROwen    Modified to use TestData.
                    Updated bit assignments to match new axis controllers.
                    Bug fix: soft position limit bits were swapped.
2009-10-09 ROwen    Changed bit 14 description from "Servo error..." to "Motion error...".
2010-08-26 ROwen    Added new warning bit: slip detected.
2010-10-08 ROwen    Reworded bit 19 (overcurrent) and removed some unused bits.
2010-11-05 ROwen    Added target mount position. Tweaked help URLs.
2011-02-16 ROwen    Shortened some status bit descriptions.
                    Tweaked code to make display expand to the right of the displayed data.
2012-07-10 ROwen    Modified to use RO.TkUtil.Timer
"""
import time
import tkinter
import RO.Constants
import RO.Alg
import RO.BitDescr
import RO.StringUtil
from RO.TkUtil import Timer
import RO.Wdg
import TUI.PlaySound
import TUI.TCC.TCCModel

_CtrllrWaitSec = 1.0 # time for status of all 3 controllers to come in (sec)
_SoundInterval = 0.1 # time (sec) between the start of each sound (if more than one)

_HelpURL = "Telescope/StatusWin.html#Axes"

ErrorBits = (
    ( 6, "Reverse limit switch"),
    ( 7, "Forward limit switch"),
    (12, "Disable switch"),
    
    ( 8, "Overspeed limit"),
    (19, "Motor current limit"),
    (14, "Motion error"),
    (11, "Stop button"),

    ( 2, "Reverse software limit"),
    ( 3, "Forward software limit"),

    (16, "1 Hz clock signal lost"),

    (13, "Motor output disabled"),
)
WarningBits = (
    (18, "Amplifier too hot"),
    ( 0, "Motor control buffer empty"),
    ( 1, "Position update late"),
    (24, "Fiducial error too large"),
    (29, "Motor velocity too large"),
    (15, "Slip detected"),
    (30, "Controller restarted"),
)

# commanded state dictionary:
# - keys are axis commanded state keywords, cast to lowercase
# - values are the severity
_CmdStateDict = {
    "drifting": RO.Constants.sevWarning,
    "halted": RO.Constants.sevError,
    "halting": RO.Constants.sevError,
    "slewing": RO.Constants.sevWarning,
    "tracking": RO.Constants.sevNormal,
    "notavailable": RO.Constants.sevNormal,
}
        
def _getSoundData():
    """Return a collection of sound data:
    - a dictionary of axis comanded state: (index, soundFunc)
      where the sounds should be sorted by index before playing
    
    soundFunc is a function: call it to play the sound
    """
    soundData = (
        (TUI.PlaySound.axisHalt, 'halted', 'halting'),
        (TUI.PlaySound.axisSlew, 'drifting', 'slewing'),
        (TUI.PlaySound.axisTrack, 'tracking'),
    )
    stateIndSoundDict = {}
    for ind in range(len(soundData)):
        item = soundData[ind]
        soundFunc = item[0]
        states = item[1:]
        for state in states:
            stateIndSoundDict[state] = (ind, soundFunc)
    return stateIndSoundDict

_StateIndSoundDict = _getSoundData()    

def _computeBitInfo():
    """Compute bitInfo array for RO.BitDescr module"""
    bitInfo = []
    for (bit, info) in ErrorBits:
        bitInfo.append((bit, (info, RO.Constants.sevError)))
    for (bit, info) in WarningBits:
        bitInfo.append((bit, (info, RO.Constants.sevWarning)))
    return bitInfo
_BitInfo = _computeBitInfo()

class AxisStatusWdg(tkinter.Frame):
    def __init__ (self, master=None, **kargs):
        """Displays information about the axes

        Inputs:
        - master        master Tk widget -- typically a frame or window
        """
        tkinter.Frame.__init__(self, master=master, **kargs)
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.prevSounds = [None]*3 # sounds played last time we received AxisCmdState
        self.prevCtrlStatusOK = [None]*3
        self.ctrlBadTime = 0 # time of last "controller bad" sound
        self._soundTimer = Timer()

        # magic numbers
        PosPrec = 1 # number of digits past decimal point
        PosWidth = 5 + PosPrec  # assumes -999.99... degrees is longest field
        AxisCmdStateWidth = 8
        AxisErrCodeWidth = 13
        CtrlStatusWidth = 25

        self.axisInd = list(range(len(self.tccModel.axisNames)))
        
        # actual axis position widget set
        self.axePosWdgSet = [
            RO.Wdg.FloatLabel(
                master = self,
                precision = PosPrec,
                width = PosWidth,
                helpText = "Current axis position, as reported by the controller",
                helpURL = _HelpURL,
            )
            for axis in self.axisInd
        ]
        self.tccModel.axePos.addROWdgSet(self.axePosWdgSet)

        # target axis position widget set
        self.tccPosWdgSet = [
            RO.Wdg.FloatLabel(
                master = self,
                precision = PosPrec,
                width = PosWidth,
                helpText = "Target axis position",
                helpURL = _HelpURL,
            )
            for axis in self.axisInd
        ]
        self.tccModel.tccPos.addROWdgSet(self.tccPosWdgSet)
        
        # TCC status widget set (e.g. tracking or halted)
        self.axisCmdStateWdgSet = [
            RO.Wdg.StrLabel(
                master = self,
                width = AxisCmdStateWidth,
                helpText = "What the TCC is telling the axis to do",
                helpURL = _HelpURL,
                anchor = "nw",
            )
            for axis in self.axisInd
        ]
        self.tccModel.axisCmdState.addCallback(self.setAxisCmdState)
    
        self.tccModel.rotExists.addIndexedCallback(self.setRotExists)
        
        # axis error code widet set (why the TCC is not moving the axis)
        self.axisErrCodeWdgSet = [
            RO.Wdg.StrLabel(
                master = self,
                width = AxisErrCodeWidth,
                helpText = "Why the TCC halted the axis",
                helpURL = _HelpURL,
                anchor = "nw",
            )
            for axis in self.axisInd
        ]
        self.tccModel.axisErrCode.addROWdgSet(self.axisErrCodeWdgSet)       
    
        # controller status widget set (the status word)
        self.ctrlStatusWdgSet = [
            RO.Wdg.StrLabel(
                master = self,
                width = CtrlStatusWidth,
                helpText = "Status reported by the axis controller",
                helpURL = _HelpURL,
                anchor = "nw",
            )
            for axis in self.axisInd
        ]
        for axis in self.axisInd:
            self.tccModel.ctrlStatusSet[axis].addIndexedCallback(
                RO.Alg.GenericCallback(self.setCtrlStatus, axis), 3)
        
                
        # grid the axis widgets
        gr = RO.Wdg.Gridder(self, sticky="w")
        for axis in self.axisInd:
            unitsLabel1 = tkinter.Label(self, text=RO.StringUtil.DegStr)
            unitsLabel2 = tkinter.Label(self, text=RO.StringUtil.DegStr)
            if axis == 2:
                self.rotUnitsLabel1 = unitsLabel1
                self.rotUnitsLabel2 = unitsLabel2
            gr.gridWdg (
                label = self.tccModel.axisNames[axis],
                dataWdg = (
                    self.axePosWdgSet[axis],
                    unitsLabel1,
                    self.tccPosWdgSet[axis],
                    unitsLabel2,
                    self.axisCmdStateWdgSet[axis],
                    self.axisErrCodeWdgSet[axis],
                    self.ctrlStatusWdgSet[axis],
                )
            )
        
        # widen rotator commanded state widget
        # so there's room to display "NotAvailable"
        # (note that the error code widget will be hidden when this occurs
        # so the text will not overlap anything).
        rotCmdWdg = self.axisCmdStateWdgSet[2]
        rotCmdWdg.grid_configure(columnspan=2)
        rotCmdWdg["width"] = 12

        # allow the last column to grow to fill the available space
        self.columnconfigure(gr.getMaxNextCol(), weight=1)
    
    def setAxisCmdState(self, axisCmdState, isCurrent, keyVar):
        if not isCurrent:
            for wdg in self.axisCmdStateWdgSet:
                wdg.setIsCurrent(False)
            return

        # set axis commanded state widgets
        for axis in self.axisInd:
            cmdState = axisCmdState[axis]
            severity = _CmdStateDict.get(cmdState.lower(), RO.Constants.sevError)
            self.axisCmdStateWdgSet[axis].set(cmdState, severity=severity)

        # play sounds, if appropriate
        indSoundsToPlay = set() # add new sounds to play to a set to avoid duplicates
        for axis in self.axisInd:
            soundInd, soundFunc = _StateIndSoundDict.get(axisCmdState[axis].lower(), (0, None))
            if soundFunc and (soundFunc != self.prevSounds[axis]) and keyVar.isGenuine():
                indSoundsToPlay.add((soundInd, soundFunc))
            self.prevSounds[axis] = soundFunc
        
        if indSoundsToPlay:
            indSoundsToPlay = list(indSoundsToPlay)
            indSoundsToPlay.sort()
            soundsToPlay = list(zip(*indSoundsToPlay)[1])
            soundsToPlay.reverse() # since played from back to front
            self.playSounds(soundsToPlay)
        
    def setCtrlStatus(self, axis, statusWord, isCurrent=True, keyVar=None, *args):
        # print "setCtrlStatus called with axis, statusWord, isCurrent=", axis, statusWord, isCurrent
        if axis == 2 and not self.tccModel.rotExists[0]:
            # rotator does not exist; this is handled by setRotExists
            return
            
        statusOK = True

        ctrlStatusWdg = self.ctrlStatusWdgSet[axis]

        if statusWord is not None:
            infoList = RO.BitDescr.getDescr(_BitInfo, statusWord)
            
            # for now simply show the first status;
            # eventually provide a pop-up list showing all status bits
            if infoList:
                info, severity = infoList[0]
                ctrlStatusWdg.set(info, isCurrent, severity=severity)
                if severity == RO.Constants.sevError:
                    statusOK = False
            else:
                ctrlStatusWdg.set("", isCurrent, severity=RO.Constants.sevNormal)
        elif isCurrent:
            ctrlStatusWdg.set("Not responding", isCurrent, severity=RO.Constants.sevError)
            statusOK = False
        else:
            ctrlStatusWdg.setNotCurrent()
        
        statusNewlyBad = (self.prevCtrlStatusOK[axis] and not statusOK)
        self.prevCtrlStatusOK[axis] = statusOK
        
        if statusNewlyBad and keyVar and keyVar.isGenuine() \
            and (time.time() - self.ctrlBadTime > _CtrllrWaitSec):
            TUI.PlaySound.axisHalt()
            self.ctrlBadTime = time.time()
    
    def setRotExists(self, rotExists, isCurrent=True, **kargs):
        if not isCurrent:
            return
        if rotExists:
            self.rotUnitsLabel1.grid()
            self.rotUnitsLabel2.grid()
            self.axisErrCodeWdgSet[2].grid()
            self.ctrlStatusWdgSet[2].grid()
            self.ctrlStatusWdgSet[2].set("", severity=RO.Constants.sevNormal)
        else:
            self.rotUnitsLabel1.grid_remove()
            self.rotUnitsLabel2.grid_remove()
            self.axisErrCodeWdgSet[2].grid_remove()
            self.ctrlStatusWdgSet[2].grid_remove()
    
    def playSounds(self, sounds):
        """Play one or more of a set of sounds; played in order from last to first.
        """
        if not sounds:
            return
        soundFunc = sounds.pop(-1)
        soundFunc()
        if sounds:
            self._soundTimer.start(_SoundInterval, self.playSounds, sounds)

            
if __name__ == "__main__":
    from . import TestData

    tuiModel = TestData.tuiModel

    testFrame = AxisStatusWdg(tuiModel.tkRoot)
    testFrame.pack()

    TestData.runTest()

    tuiModel.tkRoot.mainloop()
