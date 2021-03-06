"""Script to drift along the DIS slit during an exposure.

To do:
- When the hub supports it, get the slit length from the hub.

According to Russet McMillan (email 2004-09-17)
DIS has a slit length of 400", but only the middle 150"
of the slit is visible in the slitviewer.

History:
2004-10-01 ROwen
2006-04-21 ROwen    Changed to a class.
2006-04-27 ROwen    Cannot change exposure params while trailing.
                    Added support for debug mode.
                    Improved handling of drift speed and range by eliminating
                    class attributes that matched the contents of widgets.
2011-07-29 ROwen    Added support for drifting across slit.
2012-11-14 ROwen    Stop using indicatoron=False for Checkbutton (indirectly via showName).
2014-09-16 ROwen    Use waitNext=True for waitKeyVar to eliminate a tight loop that crashed TUI.
"""
import tkinter
import RO.Wdg
import RO.PhysConst
import TUI.TCC.TCCModel
import TUI.Inst.ExposeModel
import TUI.Inst.ExposeStatusWdg
import TUI.Inst.ExposeInputWdg

# constants
InstName = "DIS"
RampTime = 3.0 # time for TCC to ramp up to drift speed
SlitLengthAS = 400.0 # slit length, in arcsec (Russet 2004-09-17)
HelpURL = "Scripts/BuiltInScripts/DISDrift.html"

class ScriptClass(object):  
    def __init__(self, sr):
        """Set up widgets to set input exposure time,
        drift amount and drift speed.
        """
        # if True, run in debug-only mode (which doesn't DO anything, it just pretends)
        sr.debug = False

        self.didMove = False
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.expModel = TUI.Inst.ExposeModel.getModel(InstName)
    
        row=0
        
        # standard exposure status widget
        expStatusWdg = TUI.Inst.ExposeStatusWdg.ExposeStatusWdg(
            master = sr.master,
            instName = InstName,
            helpURL = HelpURL,
        )
        expStatusWdg.grid(row=row, column=0, sticky="news")
        row += 1
    
        # separator
        tkinter.Frame(sr.master,
            bg = "black",
        ).grid(row=row, column=0, pady=2, sticky="ew")
        row += 1
        
        # standard exposure input widget
        self.expWdg = TUI.Inst.ExposeInputWdg.ExposeInputWdg(
            master = sr.master,
            instName = InstName,
            expTypes = "object",
            helpURL = HelpURL,
        )
        self.expWdg.numExpWdg.helpText = "# of exposures during the drift"
        self.expWdg.grid(row=row, column=0, sticky="news")
        row += 1
        
        # add some controls to the exposure input widget
        
        # drift direction; make sure True is along slit!
        self.driftDirWdg = RO.Wdg.Checkbutton(
            master = self.expWdg,
            defValue = True,
            text = "Along Slit",
            helpText = "Drift along slit or across it?",
            helpURL = HelpURL,
        )
        self.expWdg.gridder.gridWdg("Drift Direction", self.driftDirWdg, colSpan=2)
        
        # drift range
        self.driftSpeedWdg = RO.Wdg.FloatEntry (
            master = self.expWdg,
            minValue = 0,
            maxValue = 300,
            width = 10,
            helpText = "Drift speed",
            helpURL = HelpURL,
        )
        self.expWdg.gridder.gridWdg("Drift Speed", self.driftSpeedWdg, '"/sec')
        
        # drift speed
        self.driftRangeWdg = RO.Wdg.FloatEntry (
            master = self.expWdg,
            readOnly = True,
            relief = "flat",
            helpText = "Range of drift (centered on starting point)",
            helpURL = HelpURL,
        )
        self.expWdg.gridder.gridWdg("Drift Range", self.driftRangeWdg, '"', sticky="ew")
        
        self.driftRangePercentWdg = RO.Wdg.FloatEntry (
            master = self.expWdg,
            defFormat = "%.1f",
            readOnly = True,
            relief = "flat",
            width = 5,
            helpText = "Range of drift as % of slit length",
            helpURL = HelpURL,
        )
        self.driftPctWdgSet = self.expWdg.gridder.gridWdg("=", self.driftRangePercentWdg, '%', sticky="w", row=-1, col=3)
        
        self.expWdg.gridder.allGridded()
        
        self.driftSpeedWdg.addCallback(self.updateRange)
        self.expWdg.timeWdg.addCallback(self.updateRange, callNow=True)
        self.driftDirWdg.addCallback(self.doDriftDir, callNow=True)
    
    def doDriftDir(self, dumWdg=None):
        isAlongSlit = self.driftDirWdg.getBool()
        if isAlongSlit:
            for wdg in self.driftPctWdgSet:
                wdg.grid()
        else:
            for wdg in self.driftPctWdgSet:
                wdg.grid_remove()

    def updateRange(self, *args):
        """Compute new drift range.
        Called whenever the drift speed or exposure time is changed.
        """
        expTime = self.expWdg.timeWdg.getNumOrNone()
        driftSpeedAS = self.driftSpeedWdg.getNumOrNone()
        if None in (expTime, driftSpeedAS):
            self.driftRangeWdg.set(None, isCurrent=False)
            self.driftRangePercentWdg.set(None, isCurrent=False)
            return

        driftRangeAS = driftSpeedAS * float(expTime)
        self.driftRangeWdg.set(driftRangeAS)
        
        driftRangePercent = 100.0 * driftRangeAS / float(SlitLengthAS)
        self.driftRangePercentWdg.set(driftRangePercent)
    
    def run(self, sr):
        """Take one or more exposures while moving the object
        
        Depending on drift direction, motion is:
        - Along slit: +X
        - Across slit: +Y
        """
        self.begBoreXY = [None, None]
        self.didMove = False
    
        # make sure the current instrument matches the desired instrument
        if not sr.debug:
            currInst = sr.getKeyVar(self.tccModel.instName)
            if InstName.lower() != currInst.lower():
                raise sr.ScriptError("%s is not the current instrument!" % InstName)
        
        # record the current boresight position (in a global area
        # so "end" can restore it).
        begBorePVTs = sr.getKeyVar(self.tccModel.boresight, ind=None)
        if not sr.debug:
            self.begBoreXY = [pvt.getPos() for pvt in begBorePVTs]
            if None in self.begBoreXY:
                raise sr.ScriptError("Current boresight position unknown")
        else:
            self.begBoreXY = [0.0, 0.0]
        #print "self.begBoreXY=%r" % self.begBoreXY
            
        # get basic exposure command
        expCmdPrefix = self.expWdg.getString(numExp = 1)
        if expCmdPrefix is None:
            raise sr.ScriptError("missing inputs")
        
        # get drift info and related info
        # time is in seconds
        # distance is in arcsec (AS suffix) or degrees (no suffix)
        if self.driftDirWdg.getBool():
            # along slit
            driftAxis = 0
        else:
            driftAxis = 1
        
        driftSpeedAS = self.driftSpeedWdg.getNumOrNone()
        if driftSpeedAS is None:
            raise sr.ScriptError("No drift speed")
        driftSpeed = driftSpeedAS / RO.PhysConst.ArcSecPerDeg
        driftSpeedXY = [0.0, 0.0]
        driftSpeedXY[driftAxis] = driftSpeed

        driftRangeAS = self.driftRangeWdg.getNumOrNone()
        if driftRangeAS is None:
            raise sr.ScriptError("Drift range unknown")
        driftRange = driftRangeAS / RO.PhysConst.ArcSecPerDeg
        
        # compute starting position and velocity
        startOffset = - (driftRange / 2.0) - (driftSpeed * RampTime)
        startPosXY = self.begBoreXY[:]
        startPosXY[driftAxis] += startOffset
        
        # should probably check against axis limits
        # but for now let's assume the user has a clue...
        
        numExpWdg = self.expWdg.numExpWdg
        numExp = numExpWdg.getNum()
        if numExp <= 0:
            sr.showMsg("No exposures wanted, nothing done", 2)
        
        # slew to start position
        sr.showMsg("Slewing to starting position")
    
        tccCmdStr = "offset boresight %.7f, %.7f/pabs/vabs/computed" % \
            (startPosXY[0], startPosXY[1])
        #print "sending tcc command %r" % tccCmdStr
        self.didMove = True
        yield sr.waitCmd(
            actor = "tcc",
            cmdStr = tccCmdStr,
        )
        
        for expNum in range(1, numExp + 1):
            isLast = (expNum == numExp)
            cycleStr = "Exposure %d of %d" % (expNum, numExp)
                
            # start drift
            sr.showMsg("%s: starting drift" % cycleStr)
            tccCmdStr = "offset boresight %.7f, %.7f, %.7f, %.7f/pabs/vabs" % \
                (startPosXY[0], startPosXY[1], driftSpeedXY[0], driftSpeedXY[1])
            #print "sending tcc command %r" % tccCmdStr
            yield sr.waitCmd(
                actor = "tcc",
                cmdStr = tccCmdStr,
            )
            
            # wait for ramp time
            sr.showMsg("%s: waiting %s sec for ramp-up" % (cycleStr, RampTime))
            yield sr.waitMS(RampTime * 1000)
    
            # expose
            sr.showMsg("%s: starting exposure" % cycleStr)
            expCmdStr = "%s startNum=%s totNum=%s" % (expCmdPrefix, expNum, numExp)
            #print "sending %s command %r" % (InstName, expCmdStr)
            expCmdVar = sr.startCmd(
                actor = self.expModel.actor,
                cmdStr = expCmdStr,
                abortCmdStr = "abort",
            )
            
            # wait for integration to end and reading to begin
            if not sr.debug:
                waitNext = False # don't wait the first time
                while True:
                    yield sr.waitKeyVar(self.expModel.expState, ind=1, waitNext=waitNext)
                    waitNext = True # wait after the first read
                    if sr.value.lower() == "reading":
                        break
            else:
                yield sr.waitMS(1000)
            
            if not isLast:
                # slew to start position for next exposure
                sr.showMsg("%s: slewing to start pos. for next exposure" % cycleStr)
            
                tccCmdStr = "offset boresight %.7f, %.7f/pabs/vabs/computed" % \
                    (startPosXY[0], startPosXY[1])
                #print "sending tcc command %r" % tccCmdStr
                self.didMove = True
                yield sr.waitCmd(
                    actor = "tcc",
                    cmdStr = tccCmdStr,
                )
            else:
                # slew back to initial position
                sr.showMsg("Slewing to initial position")
                tccCmdStr = "offset boresight %.7f, %.7f/pabs/vabs/computed" % tuple(self.begBoreXY)
                self.didMove = False
                yield sr.waitCmd(
                    actor = "tcc",
                    cmdStr = tccCmdStr,
                )
                
            # wait for exposure and slew to both end
            sr.showMsg("%s: waiting for exposure to end" % cycleStr)
            yield sr.waitCmdVars(expCmdVar)
            
    def end(self, sr):
        """If telescope moved, restore original boresight position.
        """
        #print "end called"
        if self.didMove:
            # restore original boresight position
            if None in self.begBoreXY:
                return
                
            tccCmdStr = "offset boresight %.7f, %.7f/pabs/vabs/computed" % \
                (self.begBoreXY[0], self.begBoreXY[1])
            #print "sending tcc command %r" % tccCmdStr
            sr.startCmd(
                actor = "tcc",
                cmdStr = tccCmdStr,
            )
