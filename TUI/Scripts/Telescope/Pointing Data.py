#!/usr/bin/env python

"""Collect data for the telescope pointing model

To make a quiver plot on a radial plot, simply compute the vectors in x-y
<http://stackoverflow.com/questions/13828800/how-to-make-a-quiver-plot-in-polar-coordinates>
radii = np.linspace(0.5,1,10)
thetas = np.linspace(0,2*np.pi,20)
theta, r = np.meshgrid(thetas, radii)

dr = 1
dt = 1

f = plt.figure()
ax = f.add_subplot(111, polar=True)
ax.quiver(theta, r, dr * cos(theta) - dt * sin (theta), dr * sin(theta) + dt * cos(theta))


@todo:
- Use windowing to speed up centroid exposures.
    At present doWindow=True is broken because of missing variables.

    I propose common code with the focus scripts, and handling multiple instruments identically
    (i.e. either one focus scripts and one pointing data script per instrument,
    or else a single focus script and a single pointing data script, each of which supports all instruments)

    Meanwhile much of this code is borrowed directly from BaseFocusScript,
    even though some of it is not a perfect fit.
- Handle instruments, not just guiders

History:
2014-04-28 ROwen
2014-05-07 ROwen    Change graph to show E left (like the Sky window) and use 15 degree alt lines.
2014-05-15 ROwen    Many bug fixes.
2014-05-19 ROwen    Changed saved azimuth to TPOINT convention.
2014-07-19 ROwen    Added Attended Mode and associated controls.
2014-08-17 ROwen    Update collimation after slewing to each pointing reference star, before taking the guide image.
2014-09-12 ROwen    Stop explicitly updating collimation after each slew, since the TCC now does that near the end of each slew.
                    Broadcast status messages.
                    Bug fix: default rotation type was changed whenever rotExists called back; now it is only set if rotExists changes.
2014-09-15 ROwen    Always clear missing, retry and skip star lists when starting the script.
                    Prevent entering too-large values in the skip and retry star lists.
                    Add an extra check to prevent the grid being changed while running.
2014-10-16 ROwen    Always specify window argument to work around a guider bug that caused too-small images.
                    Show info about each entry in the data file, and append the same info to that entry as a comment.
2015-11-02 ROwen    Make sure to match types when using numpy, for numpy 1.10.
"""
import collections
import glob
import os

import numpy
import matplotlib
import matplotlib.colors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter

import RO.CanvasUtil
import RO.CnvUtil
import RO.MathUtil
from RO.ScriptRunner import ScriptError
from RO.Comm.Generic import Timer
from RO.Astro.Tm import isoDateTimeFromPySec
import RO.OS
import RO.StringUtil
import RO.Wdg
import TUI.TUIModel
import TUI.TCC.TCCModel
import TUI.TCC.UserModel
import TUI.Inst.ExposeModel
import TUI.Guide.GuideModel

MeanLat = 32.780361 # latitude of telescope (deg)

Debug = False
HelpURL = "Scripts/BuiltInScripts/PointingData.html"

EntryWidth = 6

# Dictionary of instrument position: TPOINT rotator name
# See TPOINT manual section 4.5.2 "Option records" for the codes
# See TCSpk manual section 3.1 for the difference between the left and right Nasmyth mount
# Note that the NA1 port has the Echelle, and hence no rotator
InstPosRotDict = dict(
    na2 = "ROTL",
    tr2 = "ROTTEL",    
)

class InstActors(object):
    def __init__(self, instName, exposeActor, guideActor):
        self.instName = instName
        self.exposeActor = exposeActor
        self.guideActor = guideActor


class ListOfIntEntry(RO.Wdg.StrEntry):
    """An Entry widget that accepts space-separated positive integers

    It rejects any characters other than spaces and digits and silently ignores commas and 0s

    Attributes:
    - intSet: the current set of integers. Warning: this is only updated when editing is done;
        intSet will probably not match the current text while a user is editing the field!
    - maxVal: maximum allowed value
    """
    def __init__(self, master, maxVal=0, **kwargs):
        RO.Wdg.StrEntry.__init__(self, master, partialPattern = r"[ 0-9]*$", **kwargs)
        self.intSet = set()
        self.maxVal = int(maxVal)

    def setMaxVal(self, maxVal):
        """Set a new maximum value; rejected if the field contains larger values

        @throw ValueError if maxVal < current maximum value
        """
        maxVal = int(maxVal)
        if self.intSet:
            currMax = max(self.intSet)
            if maxVal < currMax:
                raise ValueError("desired max too small; %s < %s = curr max" % (maxVal, currMax))
        self.maxVal = maxVal

    def neatenDisplay(self):
        """Neaten the display and update intSet

        Remove duplicates and 0, sort and display with one space between each int
        """
        currStrVal = self.var.get()
        self.intSet = self.intsFromStr(currStrVal)
        neatStrVal = self.strFromInts(self.intSet)
        if currStrVal != neatStrVal:
            self.var.set(neatStrVal)

    def strFromInts(self, intSet):
        """Return a formatted string from a collection of integers

        Warning: does not check that intSet contains only integers
        """
        return " ".join(str(val) for val in sorted(intSet))

    def intsFromStr(self, intListStr):
        """Return a set of positive integers from a string of space-separated integers

        Raise ValueError for values that cannot be cast to int or if any values too large
        Non-positive integers are ingored
        """
        intSet = set(int(val) for val in intListStr.split() if int(val) > 0)
        if intSet and max(intSet) > self.maxVal:
            raise ValueError("%s > %s = max" % (max(intSet), self.maxVal))
        return intSet

    def set(self, val):
        intSet = self.intsFromStr(val)
        self.intSet = intSet
        RO.Wdg.StrEntry.set(self, val)

    def addInt(self, intVal):
        """Add an integer value to the currently displayed values

        @throw ValueError if intVal too large
        """
        if intVal > self.maxVal:
            raise ValueError("%s larger than %s" % (intVal, self.maxVal))
        newIntSet = self.intSet | set((intVal,))
        if newIntSet != self.intSet:
            self.set(self.strFromInts(newIntSet))

    def removeInt(self, intVal):
        """Remove an integer value from the current displayed values; do nothing if in absent
        """
        newIntSet = self.intSet - set((intVal,))
        if newIntSet != self.intSet:
            self.set(self.strFromInts(newIntSet))


class ScriptClass(object):
    """Widget to collect pointing data
    """
    def __init__(self, sr):
        """Construct a ScriptClass

        Inputs:
        - sr: a ScriptRunner
        """
        self.sr = sr
        sr.master.winfo_toplevel().resizable(True, True)
        sr.debug = Debug
        self.azAltList = None
        self._nextPointTimer = Timer()
        self._gridDirs = getGridDirs()
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.exposeModel = None
        self.gcamActor = None
        self.guideModel = None
        self.actorData = collections.OrderedDict()
        self.maxFindAmpl = 30000
        self.defRadius = 15.0
        self.helpURL = HelpURL
        defBinFactor = 3
        finalBinFactor = None
        if defBinFactor is None:
            self.defBinFactor = None
            self.binFactor = 1
            self.dispBinFactor = 1
        else:
            self.defBinFactor = int(defBinFactor)
            self.binFactor = self.defBinFactor
            self.dispBinFactor = self.defBinFactor
        self.finalBinFactor = finalBinFactor

        self.gcamActor = "gcam"
        self.guideModel = TUI.Guide.GuideModel.getModel("gcam")

        self.azAltGraph = AzAltGraph(master=sr.master)
        self.azAltGraph.grid(row=0, column=0, sticky="news")
        sr.master.grid_rowconfigure(0, weight=1)
        sr.master.grid_columnconfigure(0, weight=1)

        ctrlFrame = tkinter.Frame(sr.master)
        ctrlGr = RO.Wdg.Gridder(ctrlFrame)
        self.guiderNameWdg = RO.Wdg.StrLabel(
            master = ctrlFrame,
            anchor = "w",
            helpText = "Guider that will be used to measure pointing error",
        )
#        ctrlGr.gridWdg(False, self.guiderNameWdg, colSpan=2, sticky="ew")
        self._gridDict = dict()
        gridFrame = tkinter.Frame(ctrlFrame)
        self.gridWdg = RO.Wdg.OptionMenu(
            master = gridFrame,
            # don't set a label, as this will be displayed instead of the current value
            callFunc = self.setGrid,
            items = (),
            postCommand = self._fillGridsMenu,
            helpText = "az/alt grid",
            helpURL = self.helpURL,
        )
        self.gridWdg.pack(side="left")
        self.numStarsWdg = RO.Wdg.StrLabel(
            master = gridFrame,
            anchor = "w",
            helpText = "number of stars in the grid",
            helpURL = self.helpURL,
        )
        self.numStarsWdg.pack(side="left")
        ctrlGr.gridWdg("Grid", gridFrame, colSpan=5, sticky="w")
        self.minMagWdg = RO.Wdg.FloatEntry(
            master = ctrlFrame,
            defValue = 4.0,
            width = EntryWidth,
            helpText = "minimum magnitude (max brightness)",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Min Mag", self.minMagWdg)
        self.maxMagWdg = RO.Wdg.FloatEntry(
            master = ctrlFrame,
            defValue = 6.0,
            width = EntryWidth,
            helpText = "maximum magnitude (min brightness)",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Max Mag", self.maxMagWdg)

        self.rotTypeWdg = RO.Wdg.OptionMenu(
            master = ctrlFrame,
            items = ("Object", "Horizon", "Mount"),
            defValue = "Mount",
            helpText = "rotation type",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Rot Type", self.rotTypeWdg)

        self.settleTimeWdg = RO.Wdg.FloatEntry(
            master = ctrlFrame,
            defValue = 0.0 if not sr.debug else 0.0,
            minValue = 0.0,
            defFormat = "%.1f",
            width = EntryWidth,
            helpText = "settling time after slewing to a new star (sec)",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Settling Time", self.settleTimeWdg, "sec  ")

        # grid the second column;
        # use setDefCol instead of startNewCol because the grid frame is full width
        # use setNextRow to leave room for the grid frame
        ctrlGr.setDefCol(3)
        ctrlGr.setNextRow(1)
        self.numExpWdg = RO.Wdg.IntEntry(
            master = ctrlFrame,
            label = "Num Exp",
            defValue = 1,
            minValue = 1,
            width = EntryWidth,
            helpText = "number of exposures (and corrections) per star",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg(self.numExpWdg.label, self.numExpWdg)
        self.expTimeWdg = RO.Wdg.FloatEntry(
            master = ctrlFrame,
            label = "Exp Time",
            defValue = 5.0,
            minValue = 0,
            defFormat = "%.1f",
            width = EntryWidth,
            helpText = "exposure time",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg(self.expTimeWdg.label, self.expTimeWdg, "sec")

        self.binFactorWdg = RO.Wdg.IntEntry(
            master = ctrlFrame,
            label = "Bin Factor",
            minValue = 1,
            maxValue = 1024,
            defValue = self.defBinFactor or 1,
            defMenu = "Default",
            width = EntryWidth,
            callFunc = self.updBinFactor,
            helpText = "Bin factor (for rows and columns)",
            helpURL = self.helpURL,
        )
        if self.defBinFactor is not None:
            ctrlGr.gridWdg(self.binFactorWdg.label, self.binFactorWdg)

        self.centroidRadWdg = RO.Wdg.IntEntry(
            master = ctrlFrame,
            label = "Centroid Radius",
            minValue = 5,
            maxValue = 1024,
            defValue = self.defRadius,
            defMenu = "Default",
            width = EntryWidth,
            helpText = "Centroid radius; don't skimp",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg(self.centroidRadWdg.label, self.centroidRadWdg, "arcsec")


        # grid full-width widgets below the other controls
        # (trying to do this before starting the 2nd colum results in widgets that are too narrow)
        ctrlGr.setDefCol(0)

        btnFrame = tkinter.Frame(ctrlFrame)

        self.attendedModeWdg = RO.Wdg.Checkbutton(
            master = btnFrame,
            text = "Attended Mode",
            defValue = True,
            helpText = "pause if a star cannot be measured?",
            helpURL = self.helpURL,
        )
        self.attendedModeWdg.grid(row=0, column=0, sticky="")

        self.skipCurrStarWdg = RO.Wdg.Button(
            master = btnFrame,
            text = "Skip Current Star",
            command = self.doSkipCurrStar,
            helpText = "press to skip the current star",
            helpURL = self.helpURL,
        )
        self.skipCurrStarWdg.grid(row=0, column=1, sticky="")

        self.retryMissingWdg = RO.Wdg.Button(
            master = btnFrame,
            text = "Retry Missing",
            command = self.doRetryMissing,
            helpText = "press to retry all missing stars except stars to skip",
            helpURL = self.helpURL,
        )
        self.retryMissingWdg.grid(row=0, column=2, sticky="")
        for i in range(3):
            btnFrame.grid_columnconfigure(i, weight=1)

        ctrlGr.gridWdg(False, btnFrame, colSpan=8, sticky="ew")

        self.missingStarsWdg = ListOfIntEntry(
            master = ctrlFrame,
            readOnly = True,
            borderwidth = 0,
            helpText = "list of missing stars (read-only)",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Missing Stars", self.missingStarsWdg, colSpan=8, sticky="ew")

        self.starsToSkipWdg = ListOfIntEntry(
            master = ctrlFrame,
            helpText = "list of stars to skip (pause to edit or press Skip Current Star)",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Stars to Skip", self.starsToSkipWdg, colSpan=8, sticky="ew")

        self.starsToRetryWdg = ListOfIntEntry(
            master = ctrlFrame,
            helpText = "list of stars to retry (pause to edit)",
            helpURL = self.helpURL,
        )
        ctrlGr.gridWdg("Stars to Retry", self.starsToRetryWdg, colSpan=8, sticky="ew")

        self.dataIDWdg = RO.Wdg.StrLabel(
            master = ctrlFrame,
            anchor = "w",
            helpText = "ID of most recently saved star measurement",
        )
        ctrlGr.gridWdg("Saved Data ID", self.dataIDWdg, colSpan=8, sticky="ew")

        self.dataPathWdg = RO.Wdg.StrEntry(
            master = ctrlFrame,
            readOnly = True,
            helpText = "path to pointing data file",
        )
        ctrlGr.gridWdg(False, self.dataPathWdg, colSpan=8, sticky="ew")

        ctrlFrame.grid(row=1, column=0, sticky="w")

        # self.tccModel.instName.addIndexedCallback(self._setInstName, callNow=True)
        self.tccModel.rotExists.addIndexedCallback(self._updRotExists, callNow=True)

        if sr.debug:
            self.tccModel.instName.set(["DIS"],)

        self.sr.addCallback(self.enableWdg, callNow=True)

    def _updRotExists(self, rotExists, isCurrent, **kwargs):
        if not isCurrent:
            return
        currDefault = self.rotTypeWdg.getDefault()
        if rotExists:
            newItems = ("Object", "Horizon", "Mount")
            newDefault = "Mount"
        else:
            newItems = ("None",)
            newDefault = "None"

        if currDefault == newDefault:
            # state of rotExists has not changed
            return

        self.rotTypeWdg.setItems(newItems)
        if currDefault not in newItems:
            self.rotTypeWdg.setDefault(newDefault, showDefault=True)

    def _setInstName(self, instName, *args, **kwargs):
        """Call when the TCC reports a new instName
        """
        if instName is None:
            return

        if self.sr.isExecuting() and self.exposeModel and self.exposeModel.instName.lower() != instName.lower():
            self.sr.showMsg(
                "Instrument changed from %r to %r while running" % (self.exposeModel.instName, instName),
                severity = RO.Constants.sevError,
            )
            self.sr.cancel()

        try:
            self.exposeModel = TUI.Inst.ExposeModel.getModel(instName)
        except Exception:
            self.exposeModel = None
            self.sr.showMsg(
                "No model for instrument %r" % (instName,),
                severity = RO.Constants.sevWarning,
            )
            return

        instInfo = self.exposeModel.instInfo
        guiderActor = instInfo.guiderActor
        if guiderActor:
            guiderName = TUI.Inst.ExposeModel.GuiderActorNameDict.get(guiderActor, guiderActor)
            self.gcamActor = guiderActor
            self.guideModel = TUI.Guide.GuideModel.getModel("gcam")
            gcamInfo = self.guideModel.gcamInfo
            self.defBinFactor = gcamInfo.defBinFac
            self.expTimeWdg.setDefault(gcamInfo.defExpTime)
        else:
            guiderName = "(none)"
            self.gcamActor = None
            self.guideModel = None
        self.guiderNameWdg.set(guiderName)

    def _fillGridsMenu(self):
        """Set items of the Grids menu based on available grid files and update self._gridDict
        """
        oldGridNames = set(self._gridDict)
        self._gridDict = self._findGrids()
        gridNames = set(self._gridDict)
        if gridNames != oldGridNames:
            self.gridWdg.setItems(sorted(gridNames))

    def _findGrids(self):
        """Search for available grid files and return as a dict of grid name: file path

        Grid files are *.dat files in TUI/Grids and TUIAdditions/Grids
        """
        gridDict = dict()
        for dirPath in self._gridDirs:
            gridPathList = glob.glob(os.path.join(dirPath, "*.dat"))
            for gridPath in gridPathList:
                gridName = os.path.splitext(os.path.basename(gridPath))[0]
                gridDict[gridName] = gridPath
        return gridDict

    def doSkipCurrStar(self):
        """Skip current star
        """
        if self.currStarNum > 0 and self.sr.isExecuting():
            self.starsToSkipWdg.addInt(self.currStarNum)
            self.starsToRetryWdg.removeInt(self.currStarNum)

    def doRetryMissing(self):
        """Set starsToRetryWdg to all missing stars except those starsToSkipWdg
        """
        starsToAdd = self.missingStarsWdg.intSet - self.starsToSkipWdg.intSet
        self.starsToRetryWdg.set(self.starsToRetryWdg.strFromInts(starsToAdd))

    def enableWdg(self, sr):
        """Enable or disable widgets, as appropriate
        """
        isExecuting = self.sr.isExecuting() # is running or paused
        isPaused = self.sr.isPaused()

        # can only change grids if not executing (one grid must be used for the whole run)
        self.gridWdg.setEnable(not isExecuting)

        # can only skip current star if executing (nothing to skip, otherwise)
        self.skipCurrStarWdg.setEnable(isExecuting)

        # can only edit skip and retry fields if paused or not running
        # (to avoid collisions with auto-entered data)
        canEdit = isPaused or not isExecuting
        self.starsToSkipWdg.setEnable(canEdit)
        self.starsToRetryWdg.setEnable(canEdit)

    def getHeaderStrList(self, currDateStr):
        """Return TPOINT data file header as a list of strings
        """
        instPos = self.tccModel.instPos.getInd(0)[0]
        if self.sr.debug and instPos is None:
            instPos = "NA2"
        if instPos is None:
            raise ScriptError("Instrument position unknown")
        tpointRotCode = InstPosRotDict.get(instPos.lower(), "")
        optionList = ["ALTAZ"]
        if tpointRotCode:
            optionList.append(tpointRotCode)

        meanLatDMS = RO.StringUtil.dmsStrFromDeg(MeanLat).split(":")
        meanLatDMSStr = " ".join(meanLatDMS)
        if len(meanLatDMS) != 3:
            raise ScriptError("Bug: MeanLat=%r split into %r, not 3 fields" % (MeanLat, meanLatDMS))

        optionStr = "\n".join(": %s" % val for val in optionList)

        headerStrList = (
            "! Caption record:",
            "APO 3.5M Pointing Data " + currDateStr,
            "! Option record: ALTAZ followed by rotator code, if applicable",
            optionStr,
            "! Run parameters: telescope latitude deg min sec",
            meanLatDMSStr,
            "! Pointing data (TPOINT format #4):",
            "!",
            "! All angles are in degrees",
            "! Azimuth uses the convention: N=0, E=90 (unlike the TCC, which uses S=0, E=90)",
            "!",
            "!  Desired Phys            Actual Mount          Rot Phys",
            "! Az          Alt         Az          Alt",
        )
        return headerStrList

    def formatBinFactorArg(self, isFinal):
        """Return bin factor argument for expose/centroid/findstars command
        
        Inputs:
        - isFinal: if True then return parameters for final exposure
        """
        binFactor = self.getBinFactor(isFinal=isFinal)
        if binFactor is None:
            return ""
        return "bin=%d" % (binFactor,)
    
    def formatExposeArgs(self, doWindow=True, isFinal=False):
        """Format arguments for exposure command.
        
        Inputs:
        - doWindow: if true, window the exposure (if permitted)
        - isFinal: if True then return parameters for final exposure
        """
        argList = [
            "time=%s" % (self.expTime,),
            self.formatBinFactorArg(isFinal=isFinal),
            self.formatWindowArg(doWindow, isFinal=isFinal),
        ]
        argList = [arg for arg in argList if arg]
        return " ".join(argList)
    
    def formatWindowArg(self, doWindow=True, isFinal=False):
        """Format window argument for expose/centroid/findstars command.
        
        Inputs:
        - doWindow: if true, window the exposure (if permitted)
        """
        if not doWindow or not self.doWindow:
            # specify the window argument anyway, to work around a guider bug
            imSize = self.guideModel.gcamInfo.imSize
            window = numpy.array((0, 0, imSize[0], imSize[1]), dtype=int) // self.getBinFactor(isFinal=isFinal)
            if self.windowIsInclusive:
                for i in (2, 3):
                    window[i] -= 1
        else:
            window = self.window[:]
        if self.windowIsInclusive:
            urOffset = self.windowOrigin
        else:
            urOffset = self.windowOrigin + 1
        windowLL = [window[ii] + self.windowOrigin for ii in range(2)]
        windowUR = [window[ii+2] + urOffset for ii in range(2)]
        return "window=%d,%d,%d,%d" % (windowLL[0], windowLL[1], windowUR[0], windowUR[1])

    def getEntryNum(self, wdg):
        """Return the numeric value of a widget, or raise ScriptError if blank.
        """
        numVal = wdg.getNumOrNone()
        if numVal is not None:
            return numVal
        raise self.sr.ScriptError(wdg.label + " not specified")
    
    def getBinFactor(self, isFinal):
        """Get bin factor (as a single int), or None if not relevant
        
        Inputs:
        - isFinal: if True then return parameters for final exposure
        """
        if self.defBinFactor is None:
            return None

        if isFinal and self.finalBinFactor is not None:
            return self.finalBinFactor
        return self.binFactor

    def getExposeCmdDict(self, doWindow=True, isFinal=False):
        """Get basic command arument dict for an expose command
        
        This includes actor, cmdStr, abortCmdStr

        Inputs:
        - doWindow: if true, window the exposure (if permitted)
        - isFinal: if True then return parameters for final exposure
        """
        return dict(
            actor = self.gcamActor,
            cmdStr = "expose " + self.formatExposeArgs(doWindow, isFinal=isFinal),
            abortCmdStr = "abort",
        )

    def initAll(self):
        """Initialize variables, table and graph.
        """
        # initialize shared variables
        self.windowIsInclusive = True # for guider and slitviewers
        self.doWindow = True # to work around a guider bug where the image may not be full frame
            # unless a window is explicitly specified
        self.windowOrigin = 0
        self.doTakeFinalImage = False
        self.focDir = None
        self.currBoreXYDeg = None
        self.begBoreXYDeg = None
        self.arcsecPerPixel = None
        self.cmdMode = None
        self.expTime = None
        self.absStarPos = None
        self.guideProbeCtrXY = None
        self.binFactor = None
        self.window = None # LL pixel is 0, UL pixel is included
        self.currStarNum = 0
        self.numStarsWritten = 0 # number of star data items written to output
        for wdg in (self.missingStarsWdg, self.starsToSkipWdg, self.starsToRetryWdg, self.dataIDWdg):
            wdg.set("")

        # data from tcc tinst:IP_NA2.DAT; value measured 2011-07-21
        # this is a hack; get from tccModel once we support multiple instruments
        self.gprobeScale = [26629.4, 25808.4]
        self.arcsecPerPixel = 3600.0 * 2 / (abs(self.gprobeScale[0]) + abs(self.gprobeScale[1]))
    
    def recordExpParams(self):
        """Record user-set parameters relating to exposures
        
        Set the following instance variables:
        - expTime
        - binFactor
        - centroidRadPix
        """
        self.expTime = self.getEntryNum(self.expTimeWdg)
        self.binFactor = self.dispBinFactor
        self.guideProbeCtrBinned = [self.guideProbeCtrXY[i] / self.binFactor for i in range(2)]
        centroidRadArcSec = self.getEntryNum(self.centroidRadWdg)
        self.centroidRadPix = centroidRadArcSec / (self.arcsecPerPixel * self.binFactor)

    def run(self, sr):
        """Take a set of pointing data
        """
        self.initAll()

        if self.azAltList is None:
            raise ScriptError("No az/alt grid selected")
        
        ptDataDir = os.path.join(RO.OS.getDocsDir(), "ptdata")
        if not os.path.exists(ptDataDir):
            sr.showMsg("Creating directory %r" % (ptDataDir,))
            os.mkdir(ptDataDir)
        if not os.path.isdir(ptDataDir):
            raise ScriptError("Could not create directory %r" % (ptDataDir,))

        # set self.guideProbeCtrXY to center of pointing error probe
        # (the name is a holdover from BaseFocusScript; the field is the location to centroid stars)
        yield sr.waitCmd("tcc", "show inst/full") # make sure we have current guide probe info
        if sr.debug:
            self.guideProbeCtrXY = [512, 512]
            self.ptErrProbe = 1
        else:
            ptErrProbe = self.tccModel.ptErrProbe.getInd(0)[0]
            if ptErrProbe in (0, None):
                raise ScriptError("Invalid pointing error probe %s; must be >= 1" % (ptErrProbe,))
            guideProbe = self.tccModel.gProbeDict.get(ptErrProbe)
            if guideProbe is None:
                raise ScriptError("No data for pointing error probe %s" % (ptErrProbe,))
            if not guideProbe.exists:
                raise ScriptError("Pointing error probe %s is disabled" % (ptErrProbe,))
            self.guideProbeCtrXY = guideProbe.ctrXY[:]
            self.ptErrProbe = ptErrProbe

        # open log file and write header
        currDateStr = isoDateTimeFromPySec(pySec=None, nDig=1)
        ptDataName = "ptdata_%s.dat" % (currDateStr,)
        ptDataPath = os.path.join(ptDataDir, ptDataName)
        self.dataPathWdg.set(ptDataPath)
        self.dataPathWdg.xview("end") # the interesting part is the end
        with open(ptDataPath, "w") as ptDataFile:
            headerStrList = self.getHeaderStrList(currDateStr)
            for headerStr in headerStrList:
                ptDataFile.write(headerStr)
                ptDataFile.write("\n")
            ptDataFile.flush()

            for starNum in self.starNumIter():
                if starNum is None:
                    # pausing
                    yield
                else:
                    yield self.waitMeasureOneStar(starNum=starNum, ptDataFile=ptDataFile)

    def setGrid(self, wdg=None):
        """Set a particular grid based on the selected name in self.gridWdg

        Inputs:
        - wdg: ignored (allows use as a widget callback)
        """
        if self.sr.isExecuting():
            raise RuntimeError("Cannot change grid while running")

        gridName = self.gridWdg.getString()
        if not gridName:
            return
        gridPath = self._gridDict[gridName]
        azList = []
        altList = []
        with open(gridPath, "r") as gridFile:
            for i, line in enumerate(gridFile):
                line = line.strip()
                if not line or line[0] in ("#", "!"):
                    continue
                try:
                    az, alt = [float(val) for val in line.split()]
                    azList.append(az)
                    altList.append(alt)
                except Exception:
                    self.sr.showMsg("Cannot parse line %s as az alt: %r\n" % (i+1, line),
                        severity = RO.Constants.sevWarning, isTemp=True)
        numPoints = len(azList)
        if len(azList) != len(altList):
            raise RuntimeError("Bug: az and alt list have different length")
        self.azAltList = numpy.zeros([numPoints], dtype=self.azAltGraph.DType)
        self.azAltList["az"] = azList
        self.azAltList["alt"] = altList
        self.numStarsWdg.set(" %s stars" % (numPoints,))
        self.azAltGraph.plotAzAltPoints(self.azAltList)
        for wdg in (self.missingStarsWdg, self.starsToSkipWdg, self.starsToRetryWdg):
            wdg.set("")
            wdg.setMaxVal(numPoints)

    def starNumIter(self):
        """Return number of next star to measure (starNum = grid index + 1)

        If there are any stars in starsToRetryWdg that are not in starsToSkipWdg
        then return the smallest of those, else return next star in grid
        """
        indIter = iter(list(range(len(self.azAltList))))
        while True:
            try:
                retryStarSet = self.starsToRetryWdg.intSet - self.starsToSkipWdg.intSet
                if retryStarSet:
                    retryStarList = sorted(retryStarSet)
                    nextStarNum = retryStarList.pop(0)
                    self.starsToRetryWdg.removeInt(nextStarNum)
                    yield nextStarNum
                else:
                    nextStarNum = next(indIter) + 1
                    if nextStarNum in self.starsToSkipWdg.intSet:
                        self.sr.showMsg("Skipping star %d" % (nextStarNum,))
                        self.missingStarsWdg.addInt(nextStarNum)
                        continue
                    yield nextStarNum
            except StopIteration:
                hasMissingStars = bool(self.missingStarsWdg.intSet - self.starsToSkipWdg.intSet)
                if not self.attendedModeWdg.getBool() and hasMissingStars:
                    yield self.sr.waitPause("Some stars missing; paused to allow retry",
                        severity=RO.Constants.sevWarning)
                else:
                    raise

    def updBinFactor(self, *args, **kargs):
        """Called when the user changes the bin factor"""
        newBinFactor = self.binFactorWdg.getNum()
        if newBinFactor <= 0:
            return
        oldBinFactor = self.dispBinFactor
        if oldBinFactor == newBinFactor:
            return

        self.dispBinFactor = newBinFactor

    def waitCentroid(self):
        """Take an exposure and centroid using 1x1 binning.
        
        If the centroid is found, sets self.sr.value to the FWHM.
        Otherwise sets self.sr.value to None.
        """
        centroidCmdStr = "centroid on=%0.1f,%0.1f cradius=%0.1f %s" % \
            (self.guideProbeCtrBinned[0], self.guideProbeCtrBinned[1],
             self.centroidRadPix, self.formatExposeArgs(doWindow=False))
        self.doTakeFinalImage = True
        yield self.sr.waitCmd(
           actor = self.gcamActor,
           cmdStr = centroidCmdStr,
           keyVars = (self.guideModel.files, self.guideModel.star),
           checkFail = False,
        )
        cmdVar = self.sr.value
        if self.sr.debug:
            starData = makeStarData("c", self.guideProbeCtrXY)
        else:
            starData = cmdVar.getKeyVarData(self.guideModel.star)
        if starData:
            self.sr.value = StarMeas.fromStarKey(starData[0])
            return
        else:
            self.sr.value = StarMeas()

        if not cmdVar.getKeyVarData(self.guideModel.files):
            raise self.sr.ScriptError("exposure failed")

    def waitComputePtErr(self, starMeas):
        measPosUnbinned = [starMeas.xyPos[i] * self.binFactor for i in range(2)]
        yield self.sr.waitCmd(
            actor = "tcc",
            cmdStr = "ptcorr %0.6f, %0.6f %s=%s %0.2f, %0.2f GImage=%s" % (
                self.ptRefStar.pos[0], self.ptRefStar.pos[1],
                self.ptRefStar.coordSysName,
                self.ptRefStar.coordSysDate,
                measPosUnbinned[0], measPosUnbinned[1],
                self.ptErrProbe
            ),
            keyVars = (self.tccModel.ptCorr, self.tccModel.ptData),
        )
        cmdVar = self.sr.value
        ptCorrValueList = cmdVar.getLastKeyVarData(self.tccModel.ptCorr, ind=None)
        if not ptCorrValueList:
            if self.sr.debug:
                # pt err az, alt, pt pos az, alt
                ptCorrValueList = (0.001, -0.002, 0.011, 0.012)
            else:
                raise ScriptError("ptCorr keyword not seen")
        ptDataValueList = cmdVar.getLastKeyVarData(self.tccModel.ptData, ind=None)
        if not ptDataValueList:
            if self.sr.debug:
                # des phys az, alt, real mount az, alt
                ptDataValueList = (20, 80, 20.001, 79.002, 45.0)
            else:
                raise ScriptError("ptData keyword not seen")

        self.sr.value = PtErr(
            ptErr = ptCorrValueList[0:2],
            desPhysPos = ptDataValueList[0:2],
            mountPos = ptDataValueList[2:4],
            rotPhys = ptDataValueList[4],
        )

    def waitFindStar(self, firstOnly=False):
        """Take a full-frame exposure and find the best star that can be centroided.

        Sets self.sr.value to StarMeas.
        Displays a warning if no star found.
        """
        if self.maxFindAmpl is None:
            raise RuntimeError("Find disabled; maxFindAmpl=None")

        self.sr.showMsg("Exposing %s sec to find best star" % (self.expTime,))
        findStarCmdStr = "findstars " + self.formatExposeArgs(doWindow=False)
        
        self.doTakeFinalImage = True
        yield self.sr.waitCmd(
           actor = self.gcamActor,
           cmdStr = findStarCmdStr,
           keyVars = (self.guideModel.files, self.guideModel.star),
           checkFail = False,
        )
        cmdVar = self.sr.value
        if self.sr.debug:
            filePath = "debugFindFile"
        else:
            if not cmdVar.getKeyVarData(self.guideModel.files):
                raise self.sr.ScriptError("exposure failed")
            fileInfo = cmdVar.getKeyVarData(self.guideModel.files)[0]
            filePath = "".join(fileInfo[2:4])

        if self.sr.debug:               
            starDataList = makeStarData("f", (50.0, 75.0))
        else:
            starDataList = cmdVar.getKeyVarData(self.guideModel.star)
        if not starDataList:
            self.sr.value = StarMeas()
            self.sr.showMsg("No stars found", severity=RO.Constants.sevWarning)
            return
        
        if firstOnly:
            starDataList = starDataList[0:1]
        yield self.waitFindStarInList(filePath, starDataList)

    def waitFindStarInList(self, filePath, starDataList):
        """Find best centroidable star in starDataList.

        If a suitable star is found: set starXYPos to position
        and self.sr.value to the star FWHM.
        Otherwise log a warning and set self.sr.value to None.
        
        Inputs:
        - filePath: image file path on hub, relative to image root
            (e.g. concatenate items 2:4 of the guider Files keyword)
        - starDataList: list of star keyword data
        """
        if self.maxFindAmpl is None:
            raise RuntimeError("Find disabled; maxFindAmpl=None")
        
        for starData in starDataList:
            starXYPos = starData[2:4]
            starAmpl = starData[14]
            if (starAmpl is None) or (starAmpl > self.maxFindAmpl):
                continue
                
            self.sr.showMsg("Centroiding star at %0.1f, %0.1f" % tuple(starXYPos))
            centroidCmdStr = "centroid file=%s on=%0.1f,%0.1f cradius=%0.1f" % \
                (filePath, starXYPos[0], starXYPos[1], self.centroidRadPix)
            yield self.sr.waitCmd(
               actor = self.gcamActor,
               cmdStr = centroidCmdStr,
               keyVars = (self.guideModel.star,),
               checkFail = False,
            )
            cmdVar = self.sr.value
            if self.sr.debug:
                starData = makeStarData("f", starXYPos)
            else:
                starData = cmdVar.getKeyVarData(self.guideModel.star)
            if starData:
                self.sr.value = StarMeas.fromStarKey(starData[0])
                return

        self.sr.showMsg("No usable star fainter than %s ADUs found" % self.maxFindAmpl,
            severity=RO.Constants.sevWarning)
        self.sr.value = StarMeas()

    def waitMeasureOneStar(self, starNum, ptDataFile):
        """Slew to one star, measure it numExp times and log the pointing error

        Inputs:
        - starNum: star number (grid index + 1)
        - ptDataFile: pointing data file, for logging the pointing error at this star

        If the star fails then add it to the missing list and (if attendedModeWdg)
        also add it to the retry list.

        Warning: ignores starsToSkipWdg
        Raise an exception if the specified star does not exist
        """
        if starNum in self.starsToSkipWdg.intSet:
            return
        i = starNum - 1
        rec = self.azAltList[i]
        self.currStarNum = starNum
        sr = self.sr

        try:
            self.numStarsWdg.set(" %s of %s stars" % (i + 1, len(self.azAltList)))
            az = rec["az"]
            alt = rec["alt"]
            self.azAltList["state"][i] = self.azAltGraph.Measuring
            self.azAltGraph.plotAzAltPoints(self.azAltList)

            minMag = self.getEntryNum(self.minMagWdg)
            maxMag = self.getEntryNum(self.maxMagWdg)
            rotType = self.rotTypeWdg.getString()

            # tell the world, but don't wait for this command to finish
            sr.startCmd(
                actor = "tcc",
                cmdStr = 'broadcast/type=info "Pointing Data script slewing to star %s of %s"' % \
                    (i + 1, len(self.azAltList)),
                checkFail = False,
            )

            # slew to the pointing reference star
            # use checkFail=False for all commands so the script can continue with the next star
            yield sr.waitCmd(
                actor = "tcc",
                cmdStr = "track %0.7f, %0.7f obs/pterr/rottype=%s/rotang=0/magRange=(%s, %s)" % \
                    (az, alt, rotType, minMag, maxMag),
                keyVars = (self.tccModel.ptRefStar,),
                checkFail = False,
            )
            cmdVar = sr.value
            if cmdVar is None or cmdVar.didFail():
                raise ScriptError("Slew to pointing reference star failed")
            ptRefStarValues = cmdVar.getLastKeyVarData(self.tccModel.ptRefStar, ind=None)
            if not ptRefStarValues:
                if not sr.debug:
                    raise ScriptError("No pointing reference star found")
                else:
                    if self.currStarNum % 2 == 0:
                        raise ScriptError("In debug mode every other star is failed")
                    ptRefStarValues = (20, 80, 0, 0, 0, 0, "ICRS", 2000, 7)
            self.ptRefStar = PtRefStar(ptRefStarValues)

            # wait for the settling time
            settleTime = self.settleTimeWdg.getNumOrNone()
            if settleTime:
                if settleTime > 0.05:
                    sr.showMsg("Waiting %0.1f sec for settling" % (settleTime,))
                yield sr.waitSec(settleTime)
            numExp = self.numExpWdg.getNum()
            for expInd in range(numExp):
                sr.startCmd(
                    actor = "tcc",
                    cmdStr = 'broadcast/type=info "Pointing Data script exposure %s of %s for star %s of %s"' % \
                        (expInd + 1, numExp, i + 1, len(self.azAltList)),
                    checkFail = False,
                )

                self.recordExpParams()
                yield self.waitFindStar(firstOnly=True)
                starMeas = sr.value
                if not starMeas.xyPos:
                    raise ScriptError()

                yield self.waitComputePtErr(starMeas)
                ptErr = sr.value
                if not ptErr:
                    raise ScriptError()

                # correct relative error (using current calib and guide offsets)
                yield sr.waitCmd(
                    actor = "tcc",
                    cmdStr = "offset/computed calib %s, %s" % (-ptErr.ptErr[0], -ptErr.ptErr[1]),
                    checkFail = False,
                )
                cmdVar = sr.value
                if cmdVar is None or cmdVar.didFail():
                    raise ScriptError("Offset command failed")
        except ScriptError as e:
            sr.startCmd(
                actor = "tcc",
                cmdStr = 'broadcast/type=warning "Pointing Data script failed to measure star %s of %s"' % \
                    (i + 1, len(self.azAltList)),
                checkFail = False,
            )

            self.sr.showMsg(str(e), severity=RO.Constants.sevWarning)
            self.missingStarsWdg.addInt(starNum)
            self.azAltList["state"][i] = self.azAltGraph.Failed
            self.azAltGraph.plotAzAltPoints(self.azAltList)
            if self.attendedModeWdg.getBool():
                self.starsToRetryWdg.addInt(starNum)
                yield self.sr.waitPause("Star %s failed; paused so you can retry" % (starNum,),
                    severity = RO.Constants.sevWarning)
            return

        # log pointing error
        # do this after the last measurement of the star, so we have only one entry per star
        # and record the value with the star most accurately centered (we hope)
        currStarName = self.sr.getKeyVar(self.tccModel.objName, defVal="?")
        dataIDStr = "entry %d star %d %s" % (self.numStarsWritten + 1, self.currStarNum, currStarName)
        dataStr = "%s  ! %s\n" % (ptErr.getPtDataStr(), dataIDStr)
        ptDataFile.write(dataStr)
        ptDataFile.flush()
        self.numStarsWritten += 1
        self.dataIDWdg.set(dataIDStr)
        self.missingStarsWdg.removeInt(starNum)
        self.starsToRetryWdg.removeInt(starNum)
        self.azAltList["state"][i] = self.azAltGraph.Measured
        self.azAltGraph.plotAzAltPoints(self.azAltList)


class AzAltGraph(tkinter.Frame):
    """Display points in an Az/Alt grid

    az 0 deg is down, 90 deg is right
    alt 90 deg is in the center
    """
    DType = [("az", float), ("alt", float), ("state", int)]
    Unmeasured = 0
    Measuring = 1
    Measured = 2
    Failed = -1
    AllStates = (Unmeasured, Measuring, Measured, Failed)

    def __init__(self, master):
        tkinter.Frame.__init__(self, master)
        plotFig = matplotlib.figure.Figure(figsize=(5, 5), frameon=False)
        self.figCanvas = FigureCanvasTkAgg(plotFig, self)
        self.figCanvas.get_tk_widget().grid(row=0, column=0, sticky="news")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.axis = plotFig.add_subplot(1, 1, 1, polar=True, autoscale_on=False)
        self._setLimits()

    def _setLimits(self):
        """Update plot limits; must be done for every call to plotAzAltPoints
        """
        self.axis.set_xticklabels(['-90', '-135', 'N 180', '135', 'E 90', '45', '0', '-45'])
        self.axis.set_ylim(0, 90)
        self.axis.set_yticks((0, 15, 30, 45, 60, 75, 90))
        self.axis.set_yticklabels([]) # ['75', '60', '45', '15', '0'])

    def plotAzAltPoints(self, azAltPoints):
        """Plot az/alt points

        Inputs:
        - azAltPoints: data in the form of a numpy array with named columns for az, alt and state,
            where state is one of Unmeasured, Measuring, Measured or Failed
            (use self.DType to construct the array)
        """
        self.axis.clear()

        markerDict = {
            self.Unmeasured: dict(marker="o", markeredgecolor="black", fillstyle="none", markersize=3),
            self.Measuring: dict(marker="*", markeredgecolor="blue", markerfacecolor="blue", markersize=9),
            self.Measured: dict(marker="*", markeredgecolor="green", markerfacecolor="green", markersize=7),
            self.Failed: dict(marker="x", markeredgecolor="red", markersize=7),
        }

        # convert az, alt to r, theta, where r is 0 in the middle and theta is 0 right, 90 up
        for state in self.AllStates:
            markerArgs = markerDict[state]
            az = numpy.compress(azAltPoints["state"] == state, azAltPoints["az"])
            alt = numpy.compress(azAltPoints["state"] == state, azAltPoints["alt"])

            r = numpy.subtract(90.0, alt)
            theta = numpy.deg2rad(numpy.subtract(270.0, az))
            self.axis.plot(theta, r, linestyle="", **markerArgs)


        # plot connecting lines
        az = azAltPoints["az"]
        alt = azAltPoints["alt"]

        r = numpy.subtract(90.0, alt)
        theta = numpy.deg2rad(numpy.subtract(270.0, az))
        self.axis.plot(theta, r, linestyle="-", linewidth=0.4, color="gray")

        self._setLimits()
        self.figCanvas.draw()


def getGridDirs():
    """Return grid directories

    Return order is:
    - built-in
    - local TUIAdditions/Scripts
    - shared TUIAdditions/Scripts
    """
    # look for TUIAddition script dirs
    addPathList = TUI.TUIPaths.getAddPaths()
    addScriptDirs = [os.path.join(path, "Grids") for path in addPathList]
    addScriptDirs = [path for path in addScriptDirs if os.path.isdir(path)]

    # prepend the standard script dir and remove duplicates
    stdScriptDir = TUI.TUIPaths.getResourceDir("Grids")
    scriptDirs = [stdScriptDir] + addScriptDirs
    scriptDirs = RO.OS.removeDupPaths(scriptDirs)
    return scriptDirs


class StarMeas(object):
    def __init__(self,
        xyPos = None,
        sky = None,
        ampl = None,
        fwhm = None,
    ):
        self.xyPos = xyPos
        self.sky = sky
        self.ampl = ampl
        self.fwhm = fwhm
    
    @classmethod
    def fromStarKey(cls, starKeyData):
        """Create an instance from star keyword data.
        """
        return cls(
            fwhm = starKeyData[8],
            sky = starKeyData[13],
            ampl = starKeyData[14],
            xyPos = starKeyData[2:4],
        )

class PtErr(object):
    """Pointing error data
    """
    def __init__(self, ptErr, desPhysPos, mountPos, rotPhys):
        """Construct a PtErr object

        Inputs:
        - ptErr: az, alt pointing error relative to current calibration and guide offsets (deg)
        - desPhysPos: az, alt desired physical position (deg)
        - mountPos: az, alt current mount position (deg)
        - rotPhys: rotator physical position (deg)
        """
        self.ptErr = ptErr
        self.desPhysPos = desPhysPos
        self.mountPos = mountPos
        self.rotPhys = rotPhys

    def getPtDataStr(self):
        """Return pointing model data in a form suitable for TPOINT

        Format is the following values, space-separated, all in deg:
        - az desired physical position, using the modern TPOINT convention (N=90, E=0)
        - alt desired physical position
        - az mount position, using the modern TPOINT convention (N=90, E=0)
        - alt mount position
        - rot physical angle
        """
        return "%11.6f %11.6f %11.6f %11.6f %10.5f" % (
            180 - self.desPhysPos[0],
            self.desPhysPos[1],
            180 - self.mountPos[0],
            self.mountPos[1],
            self.rotPhys,
        )

class PtRefStar(object):
    """Information about a pointing reference star
    """
    def __init__(self, valueList):
        """Construct a PtRefStar from a ptRefStar keyword value list
        """
        if valueList[0] is None:
            raise RuntimeError("Invalid data")
        self.pos = valueList[0:2]
        self.parallax = valueList[2]
        self.pm = valueList[3:5]
        self.radVel = valueList[5]
        self.coordSysName = valueList[6]
        self.coordSysDate = valueList[7]
        self.mag = valueList[8]

def makeStarData(
    typeChar = "f",
    xyPos = (10.0, 10.0),
    sky = 200,
    ampl = 1500,
    fwhm = 2.5,
):
    """Make a list containing one star data list for debug mode"""
    xyPos = [float(xyPos[ii]) for ii in range(2)]
    fwhm = float(fwhm)
    return [[typeChar, 1, xyPos[0], xyPos[1], 1.0, 1.0, fwhm * 5, 1, fwhm, fwhm, 0, 0, ampl, sky, ampl]]
