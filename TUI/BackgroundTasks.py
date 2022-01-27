#!/usr/bin/env python
"""
Handle background (invisible) tasks for the telescope UI

History:
2003-02-27 ROwen    Error messages now go to the log, not stderr.
2003-03-05 ROwen    Modified to use simplified KeyVariables.
2003-05-08 ROwen    Modified to use RO.CnvUtil.
2003-06-18 ROwen    Modified to test for StandardError instead of Exception
2003-06-25 ROwen    Modified to handle message data as a dict
2004-02-05 ROwen    Modified to use improved KeyDispatcher.logMsg.
2005-06-08 ROwen    Changed BackgroundKwds to a new style class.
2005-06-16 ROwen    Modified to use improved KeyDispatcher.logMsg.
2005-09-28 ROwen    Modified checkTAI to use standard exception handling template.
2006-10-25 ROwen    Modified to use TUIModel and so not need the dispatcher keyword.
                    Modified to log errors using tuiModel.logMsg.
2007-07-25 ROwen    Modified to use time from the TCC model.
                    Modified to not test the clock unless UTCMinusTAI set
                    (but TUI now gets that using getKeys so it normally will
                    see UTCMinusTAI before it sees the current TAI).
2010-07-21 ROwen    Added support for detecting sleep and failed connections.
2010-10-27 ROwen    Fixed "no data seen" message to report correct time interval.
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2011-06-17 ROwen    Changed "type" to "msgType" in parsed message dictionaries (in test code only).
2012-07-18 ROwen    Modified to user RO.Comm.Generic.Timer.
2012-08-10 ROwen    Updated for RO.Comm 3.0.
2012-12-07 ROwen    Improved time keeping so TUI can show the correct time even if the clock is not keeping perfect UTC.
                    Sets time error using RO.Astro.Tm.setClockError(0) based on TAI reported by the TCC.
                    If the clock appears to be keeping UTC or TAI then the clock is assumed to be keeping that time perfectly.
"""
import sys
import time
import RO.Astro.Tm
import RO.CnvUtil
import RO.Constants
import RO.PhysConst
import RO.KeyVariable
from RO.Comm.Generic import Timer
import TUI.PlaySound
import TUI.TUIModel
import TUI.TCC.TCCModel

class BackgroundKwds(object):
    """Processes various keywords that are handled in the background.
    
    Also verify that we're getting data from the hub (also detects computer sleep)
    and try to refresh variables if there is a problem.
    """
    def __init__(self,
        maxTimeErr = 10.0,
        checkConnInterval = 5.0,
        maxEntryAge = 60.0,
    ):
        """Create BackgroundKwds
        
        Inputs:
        - maxTimeErr: maximum clock error (sec) before a warning is printed
        - checkConnInterval: interval (sec) at which to check connection
        - maxEntryAge: maximum age of log entry (sec)
        """
        self.maxTimeErr = float(maxTimeErr)
        self.checkConnInterval = float(checkConnInterval)
        self.maxEntryAge = float(maxEntryAge)

        self.tuiModel = TUI.TUIModel.getModel()
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.connection = self.tuiModel.getConnection()
        self.dispatcher = self.tuiModel.dispatcher
        self.didSetUTCMinusTAI = False
        self.checkConnTimer = Timer()
        self.clockType = None # set to "UTC" or "TAI" if keeping that time system

        self.tccModel.utcMinusTAI.addIndexedCallback(self.setUTCMinusTAI, ind=0, callNow=False)
    
        self.connection.addStateCallback(self.connCallback, callNow=True)

    def connCallback(self, conn):
        """Called when connection changes state

        When connected check the connection regularly,
        when not, don't
        """
        if conn.isConnected:
            self.checkConnTimer.start(self.checkConnInterval, self.checkConnection)
            self.checkClock()
        else:
            self.checkConnTimer.cancel()
    
    def checkConnection(self):
        """Check for aliveness of connection by looking at the time of the last hub message
        """
        doQueue = True
        try:
            entryAge = time.time() - self.dispatcher.readUnixTime
            if entryAge > self.maxEntryAge:
                self.tuiModel.logMsg(
                    "No data seen in %s seconds; testing the connection" % (self.maxEntryAge,),
                    severity = RO.Constants.sevWarning)
                cmdVar = RO.KeyVariable.CmdVar(
                    actor = "hub",
                    cmdStr = "version",
                    timeLim = 5.0,
                    dispatcher = self.dispatcher,
                    callFunc=self.checkCmdCallback,
                )
                doQueue = False
        finally:
            if doQueue:
                self.checkConnTimer.start(self.checkConnInterval, self.checkConnection)
    
    def checkClock(self):
        """Check computer clock by asking the TCC for time
        """
        cmdVar = RO.KeyVariable.CmdVar(
            actor = "tcc",
            cmdStr = "show time",
            timeLim = 2.0,
            dispatcher = self.dispatcher,
            callFunc = self.checkClockCallback,
            keyVars = (self.tccModel.tai,),
        )

    def checkCmdCallback(self, msgType, msgDict, cmdVar):
        if not cmdVar.isDone():
            return
        doQueue = True
        try:
            if cmdVar.didFail():
                self.connection.disconnect(isOK = False, reason="Connection is dead")
                doQueue = False
                TUI.PlaySound.cmdFailed()
            else:
                self.dispatcher.refreshAllVar()
        finally:
            if doQueue:
                self.checkConnTimer.start(self.checkConnInterval, self.checkConnection)
    
    def checkClockCallback(self, msgType, msgDict, cmdVar):
        """Callback from TCC "show time" command
        
        Determine if clock is keeping UTC, TAI or something else, and act accordingly.
        """
        if not cmdVar.isDone():
            return
        if cmdVar.didFail():
            self.tuiModel.logMsg(
                "clock check failed: tcc show time failed; assuming UTC",
                severity = RO.Constants.sevError,
            )
            return
        
        currTAI = cmdVar.getLastKeyVarData(self.tccModel.tai, ind=0)
        if currTAI is None:
            self.tuiModel.logMsg(
                "clock check failed: current TAI unknown; assuming UTC",
                severity = RO.Constants.sevError,
            )
            return
        if not self.didSetUTCMinusTAI:
            self.tuiModel.logMsg(
                "clock check failed: UTC-TAI unknown; assuming UTC",
                severity = RO.Constants.sevError,
            )
            return
        utcMinusTAI = RO.Astro.Tm.getUTCMinusTAI()
        currUTC = utcMinusTAI + currTAI

        RO.Astro.Tm.setClockError(0)
        clockUTC = RO.Astro.Tm.utcFromPySec() * RO.PhysConst.SecPerDay
        
        if abs(clockUTC - currUTC) < 3.0:
            # clock keeps accurate UTC (as well as we can figure); set time error to 0
            self.clockType = "UTC"
            self.tuiModel.logMsg("Your computer clock is keeping UTC")
        elif abs(clockUTC - currTAI) < 3.0:
            # clock keeps accurate TAI (as well as we can figure); set time error to UTC-TAI
            self.clockType = "TAI"
            RO.Astro.Tm.setClockError(-utcMinusTAI)
            self.tuiModel.logMsg("Your computer clock is keeping TAI")
        else:
            # clock system unknown or not keeping accurate time; adjust based on current UTC
            self.clockType = None
            timeError = clockUTC - currUTC
            RO.Astro.Tm.setClockError(timeError)
            self.tuiModel.logMsg(
                "Your computer clock is off by = %f.1 seconds" % (timeError,),
                severity = RO.Constants.sevWarning,
            )
        
    def setUTCMinusTAI(self, utcMinusTAI, isCurrent=1, keyVar=None):
        """Updates UTC-TAI in RO.Astro.Tm
        """
        if isCurrent and utcMinusTAI is not None:
            RO.Astro.Tm.setUTCMinusTAI(utcMinusTAI)
            self.didSetUTCMinusTAI = True
            if self.clockType == "TAI":
                RO.Astro.Tm.setClockError(-utcMinusTAI)


if __name__ == "__main__":
    import TUI.TUIModel
    import RO.Wdg
    root = RO.Wdg.PythonTk()
        
    kd = TUI.TUIModel.getModel(True).dispatcher

    bkgnd = BackgroundKwds()

    msgDict = {"cmdr":"me", "cmdID":11, "actor":"tcc", "msgType":":"}
    
    print("Setting TAI and UTC_TAI correctly; this should work silently.")
    dataDict = {
        "UTC_TAI": (-33,), # a reasonable value
    }
    msgDict["data"] = dataDict
    kd.dispatch(msgDict)

    dataDict = {
        "TAI": (RO.Astro.Tm.taiFromPySec() * RO.PhysConst.SecPerDay,),
    }
    msgDict["data"] = dataDict
    kd.dispatch(msgDict)
    
    # now generate an intentional error
    print("Setting TAI incorrectly; this would log an error if we had a log window up:")
    dataDict = {
        "TAI": ((RO.Astro.Tm.taiFromPySec() * RO.PhysConst.SecPerDay) + 999.0,),
    }
    msgDict["data"] = dataDict

    kd.dispatch(msgDict)

    root.mainloop()
