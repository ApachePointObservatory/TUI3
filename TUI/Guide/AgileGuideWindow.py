#!/usr/bin/env python
"""Guide using Agile science images

History:
2010-03-05 ROwen
2010-03-18 ROwen    Modified to use new afocus actor.
                    Changed output to show sky and measured error and not centroid uncertainty.
2010-03-23 ROwen    Modified to use uncomputed offsets.
                    Modified to log errors in red and play the "command failed" sound cue.
                    Changed default centroid radius and max corr from 5.0 to 8.0.
2010-04-16 ROwen    1.0b6: Changed units of centroid radius from binned pixels to arcsec.
                    Removed user-settable Corr Frac, replacing it with FitErrorScale,
                    which is the hub guider's fitErrorScale.
                    Removed Mac Corr: max correction is already limited by the centroid radius.
                    Added the version number to the window name to allow multiple versions
                    to be available at the same time.
2010-04-16 ROwen    Re-added Corr Frac to handle short exposures.
                    It works in conjunction with the automatic correction factor; so the default is 1.0.
                    Display FWHM in arcsec.
2010-04-22 ROwen    Released as part of TUI.
2010-04-23 ROwen    Stopped using Exception.message to make Python 2.6 happier.
"""
import numpy
import tkinter
import RO.Constants
import RO.MathUtil
from RO.StringUtil import strFromException
import RO.Wdg
import TUI.TUIModel
import TUI.TCC.TCCModel
import TUI.PlaySound
import TUI.Guide.GuideModel
import TUI.Inst.ExposeModel
import TUI.Inst.Agile.AgileModel

WindowName = "Guide.Agile Guider"

HelpURL = "Guiding/AgileGuideWin.html"

_Debug = False

def addWindow(tlSet):
    return tlSet.createToplevel (
        name = WindowName,
        defGeom = "+452+280",
        resizable = False,
        wdgFunc = AgileGuideWdg,
        visible = False,
    )

def formatNum(val, fmt="%0.1f"):
    """Convert a number into a string
    None is returned as NaN
    """
    if val is None:
        return "NaN"
    try:
        return fmt % (val,)
    except TypeError:
        raise TypeError("formatNum failed on fmt=%r, val=%r" % (fmt, val))

class StarMeas(object):
    """Star measurement data
    
    Lengths and positions are in binned pixels and intensities are in ADUs
    """
    def __init__(self,
        typeChar = None,
        xyPos = None,
        xyStdDev = None,
        centroidRad = None,
        sky = None,
        ampl = None,
        fwhm = None,
    ):
        if typeChar is not None:
            typeChar = typeChar.lower()
        self.typeChar = typeChar
        self.xyPos = xyPos
        self.xyStdDev = xyStdDev
        self.centroidRad = centroidRad
        self.sky = sky
        self.ampl = ampl
        self.fwhm = fwhm
    
    def fromStarKey(cls, starKeyData):
        """Create an instance from star keyword data.

        Star data is as follows, where lengths and positions are in binned pixels
        and intensities are in ADUs:
        0       type characer: c = centroid, f = findstars, g = guide star
        1       index: an index identifying the star within the list of stars returned by the command.
        2,3     x,yCenter: centroid
        4,5     x,yError: estimated standard deviation of x,yCenter
        6       radius: radius of centroid region
        7       asymmetry: a measure of the asymmetry of the object;
                the value minimized by PyGuide.centroid.
                Warning: not normalized, so probably not much use.
        8       FWHM major
        9       FWHM minor
        10      ellMajAng: angle of ellipse major axis in x,y frame (deg)
        11      chiSq: goodness of fit to model star (a double gaussian). From PyGuide.starShape.
        12      counts: sum of all unmasked pixels within the centroid radius. From PyGuide.centroid
        13      background: background level of fit to model star. From PyGuide.starShape
        14      amplitude: amplitude of fit to model star. From PyGuide.starShape
        For "g" stars, the two following fields are added:
        15,16   predicted x,y position
        """
        return cls(
            typeChar = starKeyData[0],
            xyPos = starKeyData[2:4],
            xyStdDev = starKeyData[4:6],
            centroidRad = starKeyData[6],
            fwhm = starKeyData[8],
            sky = starKeyData[13],
            ampl = starKeyData[14],
        )
    fromStarKey = classmethod(fromStarKey)

class AgileGuideWdg(tkinter.Frame):
    """Agile guide widget
    """
    # constants
    DefCentroidRadius = 3.0 # default centroid radius, in arcsec
    DefUserCorrFrac = 1.0 # default user correction fraction
    MinCentroidRadiusPix = 2.0 # minimum centroid radius, in binned pixels
    MaxFindAmpl = 45000 # maximum allowed star amplitude
    # FitErrCorrFracList uses the error estimate to scale the generated offsets.
    # The array contains pairs of numbers: an error threshhold, and a scale.
    # If the error is less than a given threshold, the corresponding factor is applied to the offset.
    # If the error exceeds the largest threshold, no correction is applied.
    FitErrCorrFracList = ((0.3, 0.7),
                     (0.7, 0.5),
                     (5.0, 0.3))
    MinCorrArcSec = 0.1 # minimum correction offset to make, in arcsec

    FindTimeLim = 15.0 # time limit to find stars, in sec
    CentroidTimeLim = 10.0 # time limit to centroid a star, in sec
    OffsetTimeLim = 15.0 # time limit to start offset correction, in sec
    
    def __init__(self, master):
        tkinter.Frame.__init__(self, master)
        self.gcamActor = "afocus"
        self.instName = "Agile"

        self.pendingCmd = None
        self.pendingImagePath = None
        
        # get various models
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()
        if self.gcamActor not in TUI.Guide.GuideModel._GCamInfoDict:
            TUI.Guide.GuideModel._GCamInfoDict[self.gcamActor] = TUI.Guide.GuideModel._GCamInfo(imSize = (1024, 1024))
        self.guideModel = TUI.Guide.GuideModel.getModel(self.gcamActor)
            
        self.agileModel = TUI.Inst.Agile.AgileModel.getModel()
        self.exposeModel = TUI.Inst.ExposeModel.getModel(self.instName)
        
        # create and grid widgets
        self.gr = RO.Wdg.Gridder(self, sticky="ew")
        
        self.createStdWdg()
        
        # log version
        self.logMsg("Warning: no more than one user should turn on guiding at any time!",
            severity=RO.Constants.sevWarning)
        
        # add callbacks
        self.exposeModel.files.addCallback(self.exposeFilesCallback)
        self.tccModel.moveItems.addIndexedCallback(self.tccMoveItemsCallback, ind=0)

    def createStdWdg(self):
        """Create the standard widgets.
        """
        numCols = 10 # pick a number larger than the # of data fields to display
        
        self.starPosWdgSet = []
        for ii in range(2):
            letter = ("X", "Y")[ii]
            starPosWdg = RO.Wdg.FloatEntry(
                master = self,
                label = "Star Pos %s" % (letter,),
                minValue = 0,
                maxValue = 5000,
                autoIsCurrent = True,
                autoSetDefault = True,
                helpText = "Star %s position in binned pixels" % (letter,),
                helpURL = HelpURL,
            )
            self.starPosWdgSet.append(starPosWdg)
        self.gr.gridWdg("Star Pos", self.starPosWdgSet, "pixels")
        
        self.centroidRadArcSecWdg = RO.Wdg.FloatEntry(
            master = self,
            label = "Centroid Rad",
            minValue = 0.0,
            maxValue = 99.9,
            defValue = self.DefCentroidRadius,
            defMenu = "Default",
            autoIsCurrent = True,
            autoSetDefault = True,
            helpText = "Radius of region to centroid (arcsec); don't skimp",
            helpURL = HelpURL,
        )
        self.gr.gridWdg(self.centroidRadArcSecWdg.label, self.centroidRadArcSecWdg, "arcsec", sticky="ew")
        
        self.userCorrFracWdg = RO.Wdg.FloatEntry(
            master = self,
            label = "Corr Frac",
            minValue = 0.0,
            maxValue = 1.0,
            defValue = self.DefUserCorrFrac,
            autoIsCurrent = True,
            autoSetDefault = True,
            helpText = "Fraction of correction to apply; reduce if guider is over-correcting",
            helpURL = HelpURL,
        )
        self.gr.gridWdg(self.userCorrFracWdg.label, self.userCorrFracWdg)
        
        # table of measurements (including separate unscrolled header)
        TableWidth = 105
        self.logHeader = RO.Wdg.Text(
            master = self,
            readOnly = True,
            height = 2,
            width = TableWidth,
            tabs = "3c 5c",
            helpText = "Star measurements and applied corrections",
            helpURL = HelpURL,
            relief = "sunken",
            bd = 0,
        )
        Sigma = "\N{GREEK SMALL LETTER SIGMA}"
        self.logHeader.insert("0.0", """image\tfind/\tposX\tposY\tpos %s\tFWHM\tampl\tsky\terrX\terrY\toffX\toffY
\tguide\tpix\tpix\tpix\tarcsec\tADUs\tADUs\tpix\tpix\tarcsec\tarcsec""" % Sigma)
        self.logHeader.setEnable(False)
        self.gr.gridWdg(False, self.logHeader, sticky="ew", colSpan=numCols)
        self.logWdg = RO.Wdg.LogWdg(
            master = self,
            height = 10,
            width = TableWidth,
            tabs = "3c 5c",
            helpText = "Measured results",
            helpURL = HelpURL,
            relief = "sunken",
            bd = 2,
        )
        self.gr.gridWdg(False, self.logWdg, sticky="ew", colSpan=numCols)
        
        # add status bar
        self.statusBar = RO.Wdg.StatusBar(
            master = self,
            dispatcher = self.tuiModel.dispatcher,
            prefs = self.tuiModel.prefs,
            playCmdSounds = False,
            helpURL = HelpURL,
        )
        self.gr.gridWdg(False, self.statusBar, sticky="ew", colSpan=numCols)
        
        # add command buttons
        cmdBtnFrame = tkinter.Frame(self)
        self.doFindBtn = RO.Wdg.Checkbutton(
            master = cmdBtnFrame,
            text = "Find",
            helpText = "Find best star on next Agile image",
            helpURL = HelpURL,
        )
        self.doFindBtn.pack(side="left")

        self.doGuideBtn = RO.Wdg.Checkbutton(
            master = cmdBtnFrame,
            text = "Guide",
            helpText = "Guide on Agile images",
            helpURL = HelpURL,
        )
        self.doGuideBtn.pack(side="left")
        
        self.gr.gridWdg(False, cmdBtnFrame, colSpan=numCols)
        
        self.grid_columnconfigure(numCols - 1, weight=1) 

    def centroidCmdDone(self, msgType, msgDict, cmdVar):
        """Centroid command finished; compute pointing error and start the offset command
        """
        if _Debug:
            print("centroidCmdDone(msgType=%s, msgDict=%s, cmdVar=%s)" % (msgType, msgDict, cmdVar))
        if cmdVar.didFail():
            self.logMsg("%s\tguide\tstar not found" % (self.pendingFileName,), severity=RO.Constants.sevError)
            return
        if not cmdVar.isDone():
            self.logMsg("%s\tguide\tBug: centroidCmdDone called before cmd done", severity=RO.Constants.sevWarning)
            return
            
        starDataList = cmdVar.getKeyVarData(self.guideModel.star)
        
        if not starDataList:
            if _Debug:
                print("Bug: no centroid data for command %r" % (cmdVar,))
            self.statusBar.setMsg("Bug: no centroid data", severity=RO.Constants.sevWarning)
            return

        starMeas = StarMeas.fromStarKey(starDataList[0])
        if (starMeas.ampl is None):
            self.statusBar.setMsg("Centroid failed; no ampl", severity=RO.Constants.sevWarning)
            return

        # compute correction and start correction command
        self.doCorrect(starMeas)
    
    def doClear(self, wdg=None):
        self.logWdg.clearOutput()

    def doCorrect(self, starMeas):
        """Compute correction and start correction command
        
        We are measuring position on the instrument plane, so apply the correction
        as a boresight offset (not ideal, but simplest).
        """
        # positions are in binned pixels unless otherwise noted
        posErr = None
        try:
            instScalePixPerDeg = self.getInstScalePixPerDeg()
            meanInstScalePixPerArcSec = self.getMeanInstScalePixPerArcSec(instScalePixPerDeg)
            desPos = numpy.array([self.getEntryNum(self.starPosWdgSet[ii]) for ii in range(2)], dtype=float)
            measPos = numpy.array(starMeas.xyPos, dtype=float)
            userCorrFrac = self.getEntryNum(self.userCorrFracWdg)
            posErr = measPos - desPos # binned pixels
            azAltCmdState = [str(val).lower() for val in self.getKeyValues(self.tccModel.axisCmdState, 0, 2)]
            if azAltCmdState != ["tracking", "tracking"]:
                raise RuntimeError("not tracking")
        except Exception as e:
            self.logStarMeas(starMeas, posErr=posErr, errMsg=strFromException(e), severity=RO.Constants.sevError)
            return
        
        posErrDeg = posErr / instScalePixPerDeg
        fitErrMagArcSec = vecMag(starMeas.xyStdDev) / meanInstScalePixPerArcSec
        for fitErrThresh, autoCorrFrac in self.FitErrCorrFracList:
            if fitErrMagArcSec < fitErrThresh:
                if _Debug:
                    print('fitErr=%0.1f"; thresh=%0.1f"; autoCorrFrac=%0.1f' % (fitErrMagArcSec, fitErrThresh, autoCorrFrac))
                break
        else:
            self.logStarMeas(starMeas, posErr=posErr, errMsg="fit error too large",
                severity=RO.Constants.sevWarning)
            return
        boresightOffsetDeg = -posErrDeg * autoCorrFrac * userCorrFrac
        
        if vecMag(boresightOffsetDeg) * 3600.0 < self.MinCorrArcSec:
            self.logStarMeas(starMeas, posErr=posErr, errMsg="offset too small")
            if _Debug:
                print("position error=%0.1f, %0.1f arcsec" % tuple(posErrDeg * 3600.0))
                print("boresight offset=%0.1f, %0.1f arcsec" % tuple(boresightOffsetDeg * 3600.0))
            return
            
        self.pendingCmd = RO.KeyVariable.CmdVar(
            actor = "tcc",
            cmdStr = "offset boresight %0.7f, %0.7f" % (boresightOffsetDeg[0], boresightOffsetDeg[1]),
            timeLim = self.OffsetTimeLim,
#            timeLimKeyword = "SlewDuration", # useful for computed offsets
        )
        if _Debug:
            print("pending path = %s; pending command = %s" % (self.pendingPath, self.pendingCmd))
        self.statusBar.doCmd(self.pendingCmd)
         # add callback after doCmd so errors in this callback are reported in status bar
        self.pendingCmd.addCallback(self.offsetCmdDone)
        
        self.logStarMeas(starMeas, posErr=posErr, boresightOffsetDeg=boresightOffsetDeg)
    
    def doFind(self, filePath):
        """Find stars on the specified image
        """
        if _Debug:
            print("doFind(filePath=%r)" % (filePath,))
        self.pendingCmd = RO.KeyVariable.CmdVar(
            actor = self.gcamActor,
            cmdStr = "findstars file=%s" % (filePath,),
            keyVars = (self.guideModel.star,),
            timeLim = self.FindTimeLim,
        )
        self.pendingPath = filePath
        self.statusBar.doCmd(self.pendingCmd)
         # add callback after doCmd so errors in this callback are reported in status bar
        self.pendingCmd.addCallback(self.findCmdDone)

    def doGuide(self, filePath):
        """Centroid star on specified image and apply pointing correction
        """
        if _Debug:
            print("doGuide(filePath=%r)" % (filePath,))
        try:
            starPos = [self.getEntryNum(wdg) for wdg in self.starPosWdgSet]
            centroidRadius = self.getEntryNum(self.centroidRadArcSecWdg) * self.getMeanInstScalePixPerArcSec()
            if centroidRadius < self.MinCentroidRadiusPix:
                centroidRadius = self.MinCentroidRadiusPix
                
        except RuntimeError as e:
            self.statusBar.setMsg("Cannot guide: %s" % (strFromException(e),), severity=RO.Constants.sevError)
            self.doGuideBtn.setBool(False)
            return

        self.pendingCmd = RO.KeyVariable.CmdVar(
            actor = self.gcamActor,
            cmdStr = "centroid file=%r on=%0.1f,%0.1f cradius=%0.1f" % \
                (filePath, starPos[0], starPos[1], centroidRadius),
            keyVars = (self.guideModel.star,),
            timeLim = self.FindTimeLim,
        )
        self.pendingPath = filePath
        if _Debug:
            print("pending path = %s; pending command = %s" % (self.pendingPath, self.pendingCmd))
        self.statusBar.doCmd(self.pendingCmd)
         # add callback after doCmd so errors in this callback are reported in status bar
        self.pendingCmd.addCallback(self.centroidCmdDone)
        
    def exposeFilesCallback(self, fileInfo, isCurrent, keyVar=None):
        """Handle the files keyword

        fileInfo =
        - cmdr (progID.username)
        - host
        - common root directory
        - program and date subdirectory
        - user subdirectory
        - file name(s)
        """
        if _Debug:
            print("exposeFilesCallback(fileInfo=%s, isCurrent=%s)" % (fileInfo, isCurrent))
        if not isCurrent:
            return

        cmdr = fileInfo[0]
        prog = cmdr.split(".", 1)[0]
        filePath = "".join(fileInfo[2:6])
        fileName = fileInfo[5]
        
        try:
            if self.tuiModel.getProgID() not in (prog, "APO"):
                raise RuntimeError("not my image")
            if self.isBusy:
                raise RuntimeError("I'm busy")
            instName = self.getKeyValues(self.tccModel.instName, 0, 1)[0]
            if not instName.lower().startswith(self.instName.lower()):
                raise RuntimeError("current instrument is %s, not %s" % (instName, self.instName))
        except RuntimeError as e:
            self.logMsg("%s\tskipped: %s" % (fileName, strFromException(e)))
            return

        if self.doFindBtn.getBool():
            self.doFind(filePath)
        elif self.doGuideBtn.getBool():
            self.doGuide(filePath)
        else:
            self.logMsg("%s\tskipped: guiding is off" % (fileName,))
    
    def findCmdDone(self, msgType, msgDict, cmdVar):
        """Find command finished; process the data and set inputs accordingly.
        
        Unchecks the Find checkbox if usable star data was found.
        """
        if cmdVar.didFail():
            self.logMsg("%s\tfind\tno stars found" % (self.pendingFileName,), severity=RO.Constants.sevError)
            return
        if not cmdVar.isDone():
            self.logMsg("%s\tfind\tBug: findCmdDone called before cmd done" % (self.pendingFileName,),
                severity=RO.Constants.sevWarning)
            return
            
        starDataList = cmdVar.getKeyVarData(self.guideModel.star)
        
        if not starDataList:
            self.logMsg("%s\tfind\tno stars found" % (self.pendingFileName,), severity=RO.Constants.sevError)
            return

        # log up to 5 usable stars and pick the first one
        nLogged = 0
        starMeas = None
        for starData in starDataList:
            locStarMeas = StarMeas.fromStarKey(starData)
            if (locStarMeas.ampl is None) or (locStarMeas.ampl > self.MaxFindAmpl):
                continue
            if starMeas is None:
                starMeas = locStarMeas
            self.logStarMeas(locStarMeas)
            nLogged += 1
            if nLogged > 4:
                break
        
        if starMeas is None:
            self.logMsg("%s\tfind\tno usable stars found" % (self.pendingFileName,), severity=RO.Constants.sevError)
        
        for ind in (0, 1):
            self.starPosWdgSet[ind].set(starMeas.xyPos[ind])
        self.centroidRadArcSecWdg.set(starMeas.centroidRad / self.getMeanInstScalePixPerArcSec())
        self.doFindBtn.setBool(False)

    def getEntryNum(self, wdg):
        """Return the numeric value of a widget, or raise RuntimeError if blank or invalid.
        """
        strVal = wdg.getDefault()
        if not strVal:
            raise RuntimeError(wdg.label + " not specified")
        return wdg.numFromStr(strVal)

    def getMeanInstScalePixPerArcSec(self, instScalePixPerDeg=None):
        """Get mean instrument scale in binned pixels/arcsec
        
        The optional argument is to avoid needlessly reading keyword values twice
        if instScalePixPerDeg is already known.
        """
        if instScalePixPerDeg is None:
            instScalePixPerDeg = self.getInstScalePixPerDeg()
        return numpy.mean(numpy.abs(instScalePixPerDeg)) / 3600.0

    def getInstScalePixPerDeg(self):
        """Get instrument scale in binned pixels/degree
        """
        binFac = self.getKeyValues(self.agileModel.bin, 0, 1)[0]
        if binFac < 1:
            raise RuntimeError("binFac = %s; must be >= 1" % (binFac,))
        instScaleUnbPixPerDeg = numpy.array(self.getKeyValues(self.tccModel.iimScale, 0, 2), dtype=float)
        return instScaleUnbPixPerDeg / float(binFac)

    def getKeyValues(self, keyVar, startInd, numValues):
        """Return values of a keyword variable (as a list), or raise RuntimeError if None or not current"""
        valList, isCurrent = keyVar.get()
        if not isCurrent:
            raise RuntimeError("%s.%s not current" % (keyVar.actor, keyVar.keyword))
        valList = valList[startInd: startInd + numValues]
        if None in valList:
            raise RuntimeError("%s.%s data unknown" % (keyVar.actor, keyVar.keyword))
        return valList

    @property
    def isBusy(self):
        return self.pendingCmd and not self.pendingCmd.isDone()

    def logMsg(self, outStr, severity=RO.Constants.sevNormal):
        """Log a message to the log widget and play Command Failed if severity >= RO.Constants.sevError
        
        Inputs:
        - outStr: message to log
        - severity: severity of message; an RO.Constants.sevX constant;
            if >= sevError then the CmdFailed sound cue is also played
        """
        self.logWdg.addMsg(outStr, severity=severity)
        if severity >= RO.Constants.sevError:
            TUI.PlaySound.cmdFailed()

    def logStarMeas(self, starMeas, posErr=None, boresightOffsetDeg=None, errMsg=None, severity=RO.Constants.sevNormal):
        """Log a star measurement.
        
        Inputs:
        - starMeas: star measurement object
        - posErr: star position error (measured - desired), in binned pixels
        - boresightOffsetDeg:
            - applied boresight offset (x, y), in degrees
            - if None: no boresight offset applied
        - errMsg: if specified, displayed instead of boresight offset (which is ignored)
        - severity: severity of message; an RO.Constants.sevX constant;
            if >= sevError then the CmdFailed sound cue is also played
        
        If fwhm is None, it is reported as NaN.
        """
        fitStdDev = vecMag(starMeas.xyStdDev)
        try:
            fwhmArcSec = starMeas.fwhm / self.getMeanInstScalePixPerArcSec()
            fwhmStr = "%0.2f" % (fwhmArcSec,)
        except Exception:
            fwhmStr = "%0.1f pix" % (starMeas.fwhm,)
        dataStrs = [
            self.pendingFileName,
            {"c": "guide", "f": "find"}.get(starMeas.typeChar, "?"),
            formatNum(starMeas.xyPos[0], "%0.2f"),
            formatNum(starMeas.xyPos[1], "%0.2f"),
            formatNum(fitStdDev, "%0.2f"),
            fwhmStr,
            formatNum(starMeas.ampl, "%0.0f"),
            formatNum(starMeas.sky, "%0.0f"),
        ]
        if posErr is not None:
            dataStrs += [formatNum(val, "%0.2f") for val in posErr]
        if errMsg:
            dataStrs.append(errMsg)
        elif boresightOffsetDeg is not None:
            offArcSec = boresightOffsetDeg * 3600.0
            dataStrs += [formatNum(val, "%0.2f") for val in offArcSec]
            
        outStr = "\t".join(dataStrs)
        self.logMsg(outStr, severity=severity)
    
    def offsetCmdDone(self, msgType, msgDict, cmdVar):
        if cmdVar.didFail():
            TUI.PlaySound.cmdFailed()

    @property
    def pendingFileName(self):
        if self.pendingPath is None:
            return "?"
        return self.pendingPath.rsplit("/", 1)[-1]

    def tccMoveItemsCallback(self, moveItems, isCurrent, keyVar=None):
        """Turn off guiding if slewing to a new object
        """

        if _Debug:
            print("tccMoveItemsCallback(moveItems=%r, isCurrent=%s)" % (moveItems, isCurrent))
        if moveItems is None or not isCurrent:
            return
        if moveItems[1].lower == "y":
            itemList = []
            if self.doFindBtn.getBool():
                self.doFindBtn.setBool(False)
                itemList.append("Find")
            if self.doGuideBtn.getBool():
                self.doGuideBtn.setBool(False)
                itemList.append("Guide")
            if itemList:
                self.statusBar.setMsg(
                    "%s off; slewing to new object" % (",".join(itemList)),
                    severity=RO.Constants.sevWarning,
                )

def vecMag(vec):
    """Compute the magnitude of a vector
    """
    return numpy.sqrt(numpy.sum(numpy.square(vec)))

if __name__ == "__main__":
    import TUI.Base.TestDispatcher
    
    testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="agile", delay=0.5)
    tuiModel = testDispatcher.tuiModel

    tlSet = tuiModel.tlSet

    addWindow(tlSet)
    tlSet.makeVisible(WindowName)
     
    tuiModel.tkRoot.mainloop()
