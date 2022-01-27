#!/usr/bin/env python
"""Exposure status widget

History:
2003-07-25 ROwen
2003-07-30 ROwen    Modified to be generic for all instruments and to use Inst.ExposeModel
2003-08-01 ROwen    Added comment field even though the hub does not yet send me the necessary info.
2003-09-30 ROwen    Updated the help prefix.
2003-10-01 ROwen    Modified to use new versions of seqState and expState (for new hub).
2003-10-06 ROwen    Modified to use unified progID, etc. naming convention.
2003-10-16 ROwen    Bug fix: was not ignoring files named None.
2003-12-04 ROwen    Added sound cues for exposure begins and ends.
2004-01-29 ROwen    Bug fix: exposure countdown timer restarted on refresh;
                    fixed by not messing with timer for data from the cache.
2004-05-18 ROwen    In _updExpState local variable expState (string repr. of state)
                    masked argument expState (a tuple of state info).
2004-08-11 ROwen    Use modified RO.Wdg state constants with st_ prefix.
2004-09-10 ROwen    Modified for RO.Wdg.st_... -> RO.Constants.st_...
                    Increased field width and use a constant for it.
                    Added __all__.
                    Removed some unused import statements.
2004-09-23 ROwen    Moved prefs display here from ExposeInputWdg.
2004-09-28 ROwen    Finally added callback for comment field.
2005-01-05 ROwen    Modified for RO.Wdg.Label state->severity and RO.Constants.st_... -> sev...
2005-08-02 ROwen    Modified for TUI.Sounds->TUI.PlaySound.
2005-09-15 ROwen    Moved prefs back to ExposeInputWdg, since users can set them again.
2007-07-02 ROwen    Added helpURL argument.
2008-04-23 ROwen    Modified to accept expState durations of None as unknown.
2008-02-24 ROwen    Modified to only play ExposureBegins occasionally.
2008-02-26 ROwen    Bug fix: wasExposing was not updated from cached exposure state;
                    this should make the first "exposure begins" sound more reliable.
2009-03-02 ROwen    Increased MinExposureBeginsSoundInterval from 9.9 to 29.9 seconds at Russet's request.
2010-03-01 ROwen    Made master argument explicit for all RO Widgets.
2011-01-19 ROwen    Play exposureFailed sound cue if exposure sequence fails.
2011-07-21 ROwen    Renamed _updFiles to _updNewFiles for clarity.
2015-11-05 ROwen    Changed ==/!= True/False to is/is not True/False to modernize the code.
"""
__all__ = ["ExposeStatusWdg"]

import time
import tkinter
import RO.Constants
import RO.Wdg
import TUI.PlaySound
from . import ExposeModel

MinExposureBeginsSoundInterval = 29.9 # shortest time between "exposure begins" sounds (sec)
_HelpURL = "Instruments/ExposeWin.html"
_DataWidth = 40

class ExposeStatusWdg (tkinter.Frame):
    def __init__(self,
        master,
        instName,
        helpURL = None,
    **kargs):
        tkinter.Frame.__init__(self, master, **kargs)
        if helpURL is None:
            helpURL = _HelpURL

        self.expModel = ExposeModel.getModel(instName)
        self.tuiModel = self.expModel.tuiModel
        self.wasExposing = None # was last exposure state integrating or resume? True, False or None if unknown
        self.wasFailed = None # was last exposure state failed or failing? True, False or None if unknown
        self.minExposureBeginsSoundTime = 0
        gr = RO.Wdg.Gridder(master=self, sticky="w")

        self.seqStateWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "Status of exposure sequence",
            helpURL = helpURL,
            anchor="w",
            width = _DataWidth,
        )
        gr.gridWdg("Seq Status", self.seqStateWdg, sticky="ew")
        
        stateFrame = tkinter.Frame(self)
        self.expStateWdg = RO.Wdg.StrLabel(
            master = stateFrame,
            helpText = "Status of current exposure",
            helpURL = helpURL,
            anchor="w",
            width = 11
        )
        self.expStateWdg.pack(side="left")
        self.expTimer = RO.Wdg.TimeBar(
            master = stateFrame,
            valueFormat = "%3.1f sec",
            isHorizontal = True,
            autoStop = True,
            helpText = "Status of current exposure",
            helpURL = helpURL,
        )
        gr.gridWdg("Exp Status", stateFrame, sticky="ew")

        self.userWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "Who is taking this exposure",
            helpURL = helpURL,
            anchor="w",
            width = _DataWidth,
        )
        gr.gridWdg("User", self.userWdg, sticky="ew")

        self.commentWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "User's comment, if any",
            helpURL = helpURL,
            anchor="w",
            width = _DataWidth,
        )
        gr.gridWdg("Comment", self.commentWdg, sticky="ew")
        self.expModel.comment.addROWdg(self.commentWdg)

        self.fileNameWdgs = []
        for camName in self.expModel.instInfo.camNames:
            if camName:
                helpSuffix = " from %s camera" % (camName.lower())
                labelStr = "%s File" % (camName.capitalize())
            else:
                helpSuffix = ""
                labelStr = "File"

            wdg = RO.Wdg.StrLabel(
                master = self,
                helpText = "File for current exposure" + helpSuffix,
                helpURL = helpURL,
                anchor = "w",
                width = _DataWidth,
            )
            self.fileNameWdgs.append(wdg)

            gr.gridWdg(labelStr, wdg, sticky="ew")
        
        self.columnconfigure(1, weight=1)

        self.expModel.newFiles.addCallback(self._updNewFiles)
        self.expModel.expState.addCallback(self._updExpState)
        self.expModel.seqState.addCallback(self._updSeqState)
        
    def _updNewFiles(self, fileInfo, isCurrent, **kargs):
        """newFiles has changed.
        
        newFiles lists file(s) that will be saved at the end of the current exposure:
        - cmdr (progID.username)
        - host
        - common root directory
        - program subdirectory
        - user subdirectory
        - file name(s)
        """
#       print "ExposeStatusWdg._updNewFiles(%r, %r)" % (fileInfo, isCurrent)
        if not isCurrent:
            for wdg in self.fileNameWdgs:
                wdg.setNotCurrent()
            return
        
        subdir = "".join(fileInfo[3:5])
        names = fileInfo[5:]
        for ii in range(self.expModel.instInfo.getNumCameras()):
            if names[ii] != "None":
                self.fileNameWdgs[ii].set(subdir + names[ii])
            else:
                self.fileNameWdgs[ii].set("")
    
    def _updExpState(self, expState, isCurrent, keyVar):
        """exposure state has changed. expState is:
        - program ID
        - user name
        - exposure state string (e.g. flushing, reading...)
        - start time (huh?)
        - remaining time for this state (sec; 0 or None if short or unknown)
        - total time for this state (sec; 0 or None if short or unknown)
        """
        if not isCurrent:
            self.expStateWdg.setNotCurrent()
            self.wasExposing = None
            return

        cmdr, expStateStr, startTime, remTime, netTime = expState
        if not expStateStr:
            return
        lowState = expStateStr.lower()
        remTime = remTime or 0.0 # change None to 0.0
        netTime = netTime or 0.0 # change None to 0.0

        isFailed = False
        if lowState in ("failing", "failed"):
            errState = RO.Constants.sevError
            isFailed = True
        elif lowState in ("paused", "aborting", "aborted"):
            errState = RO.Constants.sevWarning
        else:
            errState = RO.Constants.sevNormal
        self.expStateWdg.set(expStateStr, severity = errState)
        isNewFailure = isFailed and (self.wasFailed is not True)

        isExposing = lowState in ("integrating", "resume")
        
        if not keyVar.isGenuine():
            # data is cached; don't mess with the countdown timer or sounds
            self.wasExposing = isExposing
            return
        
        if netTime > 0:
            # print "starting a timer; remTime = %r, netTime = %r" % (remTime, netTime)
            # handle a countdown timer
            # it should be stationary if expStateStr = paused,
            # else it should count down
            if isExposing:
                # count up exposure
                self.expTimer.start(
                    value = netTime - remTime,
                    newMax = netTime,
                    countUp = True,
                )
            elif lowState == "paused":
                # pause an exposure with the specified time remaining
                self.expTimer.pause(
                    value = netTime - remTime,
                )
            else:
                # count down anything else
                self.expTimer.start(
                    value = remTime,
                    newMax = netTime,
                    countUp = False,
                )
            self.expTimer.pack(side="left", expand="yes", fill="x")
        else:
            # hide countdown timer
            self.expTimer.pack_forget()
            self.expTimer.clear()
        
        if self.wasExposing is not None \
            and self.wasExposing != isExposing \
            and self.winfo_ismapped():
            # play the appropriate sound
            if isExposing:
                currTime = time.time()
                if currTime > self.minExposureBeginsSoundTime:
                    TUI.PlaySound.exposureBegins()
                    self.minExposureBeginsSoundTime = currTime + MinExposureBeginsSoundInterval
            else:
                if self.expModel.instInfo.playExposureEnds:
                    TUI.PlaySound.exposureEnds()

        if isNewFailure:
            TUI.PlaySound.exposureFailed()
        
        self.wasExposing = isExposing
        self.wasFailed = isFailed
        
    def _updSeqState(self, seqState, isCurrent, **kargs):
        """sequence state has changed; seqState is:
            - cmdr (progID.username)
            - exposure type
            - exposure duration
            - exposure number
            - number of exposures requested
            - sequence status (a short string)
        """
        if not isCurrent:
            self.seqStateWdg.setNotCurrent()
            self.userWdg.setNotCurrent()
            self.prevSequenceState = None
            return
        
        cmdr, expType, expDur, expNum, totExp, status = seqState
        progID, username = cmdr.split('.')
                
        lowState = status.lower()
        if lowState == "failed":
            severity = RO.Constants.sevError
        elif lowState in ("paused", "stopped", "aborted"):
            severity = RO.Constants.sevWarning
        else:
            severity = RO.Constants.sevNormal
        self.seqStateWdg.set(
            "%s, %.1f sec, %d of %d %s" % (expType, expDur, expNum, totExp, status),
            severity = severity,
        )
        if cmdr == self.tuiModel.getCmdr():
            userStr = "Me"
        elif progID == self.tuiModel.getProgID():
            userStr = "%s: collaborator" % (username,)
        else:
            userStr = "%s" % (cmdr,)
        self.userWdg.set(userStr)


if __name__ == '__main__':
    root = RO.Wdg.PythonTk()

    from . import ExposeTestData

    testFrame = ExposeStatusWdg(root, "DIS")
    testFrame.pack(side="top", expand="yes")

    tkinter.Button(text="Demo", command=ExposeTestData.animate).pack(side="top")

    ExposeTestData.dispatch()

    root.mainloop()
