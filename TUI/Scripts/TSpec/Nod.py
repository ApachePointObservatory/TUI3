"""Script to nod between two fixed points in pattern ABBA.

History:
2008-04-23 ROwen
2008-07-24 ROwen    Fixed PR 852: end did not always restore the original boresight.
2011-08-02 ROwen    Added variable offset and test for minimum offset.
2012-11-13 ROwen    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
"""
import math
import numpy
import tkinter
import RO.Wdg
import RO.PhysConst
import TUI.TCC.TCCModel
import TUI.Inst.ExposeModel
import TUI.Inst.ExposeStatusWdg
import TUI.Inst.ExposeInputWdg

# constants
InstName = "TSpec"
# Offset from A to B in x, y pixels
# (85, 1) is from Matt Nelson 2008-04
ABOffsetPix = (85, 1)
MaxCycles = 9999
 # Instrument scale in unbinned pixels/degree on the sky
# as measured by APO 2008-03-21 but averaged x and y
InstScale = (-14352, 14342)
ABOffsetArcSec = tuple(ABOffsetPix[i] * 3600.0 / InstScale[i] for i in range(2))
MinOffsetArcSec = 0.1 # minimum offset in arcsec
HelpURL = "Scripts/BuiltInScripts/TSpecNod.html"

class ScriptClass(object):  
    def __init__(self, sr):
        """Set up widgets to set input exposure time,
        drift amount and drift speed.
        """
        # if True, run in debug-only mode (which doesn't DO anything, it just pretends)
        sr.debug = False
        self.sr = sr

        self.begOffset = numpy.array((numpy.nan, numpy.nan))
        self.currOffset = self.begOffset[:]

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
        self.expWdg.numExpWdg.helpText = "# of exposures at each point"
        self.expWdg.grid(row=row, column=0, sticky="news")
        row += 1
        
        # add some controls to the exposure input widget
        
        self.offsetEnableWdg = RO.Wdg.Checkbutton (
            master = self.expWdg,
            text = "Offset",
            defValue = False,
            helpText = "Enable/disable manual control of offset",
            helpURL = HelpURL,
        )
        self.offsetArcSecWdgSet = []
        offsetFrame = tkinter.Frame(self.expWdg)
        for i, axis in enumerate(("x", "y")):
            offsetWdg = RO.Wdg.FloatEntry(
                master = offsetFrame,
                callFunc = self._doOffsetWdg,
                helpText = "Amount of %s offset in arcsec" % (axis,),
                helpURL = HelpURL,
            )
            offsetWdg.pack(side="left")
            self.offsetArcSecWdgSet.append(offsetWdg)
        RO.Wdg.Label(master=offsetFrame, text="arcsec").pack(side="left")
        self.offsetPixWdg = RO.Wdg.Label(
            master = offsetFrame,
            helpText = "Amount of x,y offset in pixels",
            helpURL = HelpURL,
        )
        self.offsetPixWdg.pack(side="left")
        self.expWdg.gridder.gridWdg(self.offsetEnableWdg, offsetFrame, colSpan=5)
            

        # number of cycles
        self.numCyclesWdg = RO.Wdg.IntEntry (
            master = self.expWdg,
            minValue = 1,
            maxValue = MaxCycles,
#            width = 10,
            helpText = "Number of ABBA cycles",
            helpURL = HelpURL,
        )
        self.expWdg.gridder.gridWdg("Cycles", self.numCyclesWdg)

        
        self.expWdg.gridder.allGridded()

        if sr.debug:
            # set useful debug defaults
            self.expWdg.timeWdg.set("1.0")
            self.expWdg.numExpWdg.set(2)
            self.expWdg.fileNameWdg.set("debug")
            self.numCyclesWdg.set(2)
        
        self.offsetEnableWdg.addCallback(self._doOffsetEnable, callNow=True)
    
    def _doOffsetEnable(self, wdg=None):
        """Handle toggle of offsetEnableWdg
        """
        if self.offsetEnableWdg.getBool():
            for wdg in self.offsetArcSecWdgSet:
                wdg.setEnable(True)
        else:
            for i, wdg in enumerate(self.offsetArcSecWdgSet):
                wdg.set(ABOffsetArcSec[i])
                wdg.setEnable(False)
    
    def _doOffsetWdg(self, wdg=None):
        """Handle changes in offset in arcsec by updating offset in pixels
        """
        if self.isOffsetOK():
            offsetArcSec = self.getOffsetArcSec()
            offsetPix = tuple(offsetArcSec[i] * InstScale[i] / 3600.0 for i in range(2))
            self.offsetPixWdg.set("= %0.1f, %0.1f pix" % offsetPix, severity=RO.Constants.sevNormal)
        else:
            self.offsetPixWdg.set("offset too small", severity=RO.Constants.sevError)
    
    def getOffsetArcSec(self):
        """Return current x,y offset in arcsec; 0 if field is empty
        """
        return [wdg.getNum() for wdg in self.offsetArcSecWdgSet]
    
    def isOffsetOK(self):
        """Is offset acceptably large? The test right now is 0
        """
        return math.hypot(*self.getOffsetArcSec()) >= MinOffsetArcSec

    def end(self, sr):
        """If telescope offset, restore original position.
        """
        # restore original boresight position, if changed
        if self.needMove(self.begOffset):
            tccCmdStr = "offset boresight %.7f, %.7f/pabs/vabs/computed" % tuple(self.begOffset)
            #print "sending tcc command %r" % tccCmdStr
            sr.startCmd(
                actor = "tcc",
                cmdStr = tccCmdStr,
            )

    def needMove(self, desOffset):
        """Return True if telescope not at desired offset"""
        if numpy.any(numpy.isnan(self.currOffset)):
            return False
        return not numpy.allclose(self.currOffset, desOffset)         

    def run(self, sr):
        """Take one or more exposures while moving the object
        in the +X direction along the slit.
        """
        # make sure the current instrument matches the desired instrument
        if not sr.debug:
            currInst = sr.getKeyVar(self.tccModel.instName)
            if InstName.lower() != currInst.lower():
                raise sr.ScriptError("%s is not the current instrument!" % InstName)
        
        # record the current boresight position
        begBorePVTs = sr.getKeyVar(self.tccModel.boresight, ind=None)
        if not sr.debug:
            begOffset = [pvt.getPos() for pvt in begBorePVTs]
            if None in begOffset:
                raise sr.ScriptError("Current boresight position unknown")
            self.begOffset = numpy.array(begOffset, dtype=float)
        else:
            self.begOffset = numpy.zeros(2, dtype=float)
        self.currOffset = self.begOffset[:]
        #print "self.begOffset=%r" % self.begOffset
            
        numCycles = self.numCyclesWdg.getNum()
        if not numCycles:
            raise sr.ScriptError("Must specify number of cycles")
            
        # exposure command without startNum and totNumExp
        # get it now so that it will not change if the user messes
        # with the controls while the script is running
        numExpPerNode = self.expWdg.numExpWdg.getNumOrNone()
        if numExpPerNode is None:
            raise sr.ScriptError("must specify #Exp")

        nodeNames = ("A1", "B1", "B2", "A2")
        numNodes = len(nodeNames)
        totNumExp = numCycles * numNodes * numExpPerNode
        expCmdPrefix = self.expWdg.getString(totNum = totNumExp)
        if expCmdPrefix is None:
            raise sr.ScriptError("missing inputs")
        
        NodeOffsetDict = dict (
            A = numpy.zeros(2, dtype=float),
            B = numpy.array(self.getOffsetArcSec(), dtype=float) / 3600.0,
        )
        
        if not self.isOffsetOK():
            raise sr.ScriptError("offset too small")
        
        numExpTaken = 0
        for cycle in range(numCycles):
            for nodeName in nodeNames:
                iterName = "Cycle %s of %s, Pos %s" % (cycle + 1, numCycles, nodeName)
                nodeOffset = NodeOffsetDict[nodeName[0]]                
                desOffset = self.begOffset + nodeOffset
                if self.needMove(desOffset):
                    sr.showMsg("%s: Offsetting" % (iterName,))
                    yield self.waitOffset(desOffset)
        
                # expose
                sr.showMsg("%s: Exposing" % (iterName,))
                startNum = numExpTaken + 1
                expCmdStr = "%s startNum=%s" % (expCmdPrefix, startNum)
                #print "sending %s command %r" % (InstName, expCmdStr)
                yield sr.waitCmd(
                    actor = self.expModel.actor,
                    cmdStr = expCmdStr,
                    abortCmdStr = "abort",
                )
                numExpTaken += numExpPerNode
    
    def waitOffset(self, desOffset):
        """Offset the telescope"""
        tccCmdStr = "offset boresight %.7f, %.7f/pabs/vabs/computed" % tuple(desOffset)
        self.currOffset = desOffset[:]
        yield self.sr.waitCmd(
            actor = "tcc",
            cmdStr = tccCmdStr,
        )
