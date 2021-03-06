#!/usr/bin/env python
"""Graphical offsetter.

History:
2005-05-24 ROwen
2005-05-26 ROwen    Bug fix: updIImScale was totally broken, so the nudger box
                    labels were always to the right and above.
2005-06-03 ROwen    Improved uniformity of indentation.
2005-04-20 ROwen    All offsets are now computed.
2010-11-03 ROwen    Added Calibration offsets.
                    Renamed Object to Object Arc
                    Stopped using anchors within the HTML help file.
2011-01-31 ROwen    Scale Calibration and Guide offsets are now on the sky (scaled by 1/cos(alt)).
                    Use RO.StringUtil.strFromException when formatting command failure messages.
2011-06-17 ROwen    Changed "type" to "msgType" in parsed message dictionaries (in test code only).
2012-07-19 ROwen    Removed Calibration offsets at Russet's sensible request.
2015-06-02 ROwen    Stop scaling Guide and Guide XY offsets by cos(alt); the new TCC doesn't want it.
"""
import tkinter
import RO.Constants
import RO.KeyVariable
import RO.MathUtil
import RO.StringUtil
import RO.Wdg
import TUI.TUIModel
import TUI.TCC.TCCModel

WindowName = "TCC.Nudger"

def addWindow(tlSet):
    """Create the window for TUI.
    """
    tlSet.createToplevel(
        name = WindowName,
        defGeom = "+50+507",
        resizable = False,
        visible = False,
        wdgFunc = NudgerWdg,
    )

_HelpURL = "Telescope/NudgerWin.html"

_CnvRad = 50 # radius of drawing area of canvas
_MaxOffset = 5 # arcsec
_MaxAxisLabelWidth = 4 # chars; 4 is for Long
_ArrowTag = "arrow"

class _FakePosEvt:
    def __init__(self, xyPos):
        self.x, self.y = xyPos
        
class OffsetInfo(object):
    def __init__(self, name, axisLabels, tccName, helpText):
        self.name = name
        self.axisLabels = axisLabels
        self.tccName = tccName
        self.helpText = helpText

# information about the available offsets
_OffsetInfoList = (
    OffsetInfo("Object Arc", None, "arc", "object arc offset"),
    OffsetInfo("Object Arc XY", ("X", "Y"), "arc", "object arc offset in inst. x,y"),
    OffsetInfo("Boresight", ("X", "Y"), "boresight", "boresight offset"),
    OffsetInfo("Guide", ("Az", "Alt"), "guide", "guide offset"),
    OffsetInfo("Guide XY", ("X", "Y"), "guide", "guide offset in inst. x,y"),
)

# mapping from offset type to label; None means use user coordsys labels
_OffsetAxisLabelsDict = dict((offInfo.name, offInfo.axisLabels) for offInfo in _OffsetInfoList)

# mapping from displayed offset type to tcc offset type
_OffsetTCCNameDict = dict((offInfo.name, offInfo.tccName) for offInfo in _OffsetInfoList)

class NudgerWdg (tkinter.Frame):
    def __init__(self, master):
        tkinter.Frame.__init__(self, master)
        
        self.tuiModel = TUI.TUIModel.getModel()
        self.tccModel = TUI.TCC.TCCModel.getModel()
        
        self.arcSecPerPix = None
        self.iimScale = None
        self.xySign = (1, 1)
        self.offPix = None
        self.offArcSec = None
        self.objSysLabels = ("E", "N")
        
        textFrame = tkinter.Frame(self)

        gr = RO.Wdg.Gridder(textFrame, sticky="w")
        
        maxOffNameLen = 0
        for offInfo in _OffsetInfoList:
            maxOffNameLen = max(len(offInfo.name), maxOffNameLen)
        
        self.offTypeWdg = RO.Wdg.OptionMenu(
            master = textFrame,
            items = [offInfo.name for offInfo in _OffsetInfoList],
            defValue = "Guide XY",
            callFunc = self.updOffType,
            width = maxOffNameLen,
            helpText = [offInfo.helpText for offInfo in _OffsetInfoList],
            helpURL = _HelpURL,
        )
        gr.gridWdg(False, self.offTypeWdg, colSpan=3)
        
        self.maxOffWdg = RO.Wdg.IntEntry(
            master = textFrame,
            minValue = 1,
            maxValue = _MaxOffset,
            defValue = 3,
            width = 2,
            callFunc = self.updMaxOff,
            helpText = "Maximum offset",
            helpURL = _HelpURL,
        )
        gr.gridWdg("Max Offset", self.maxOffWdg, '"')
        
        self.offAmtLabelSet = []
        self.offAmtWdgSet = []
        for ii in range(2):
            amtLabelWdg = RO.Wdg.StrLabel(
                master = textFrame,
                width = _MaxAxisLabelWidth + 7, # 7 is for " Offset"
            )
            self.offAmtLabelSet.append(amtLabelWdg)
            
            offArcSecWdg = RO.Wdg.FloatLabel(
                master = textFrame,
                precision = 2,
                width = 5,
                helpText = "Size of offset",
                helpURL = _HelpURL,
            )
            self.offAmtWdgSet.append(offArcSecWdg)
            
            gr.gridWdg(amtLabelWdg, offArcSecWdg, '"')

        textFrame.grid(row=0, column=0)
            
        cnvFrame = tkinter.Frame(self)

        # canvas on which to display center dot and offset arrow
        cnvSize = (2 * _CnvRad) + 1
        self.cnv = tkinter.Canvas(
            master = cnvFrame,
            width = cnvSize,
            height = cnvSize,
            borderwidth = 1,
            relief = "ridge",
            selectborderwidth = 0,
            highlightthickness = 0,
            cursor = "crosshair",
        )
        self.cnv.helpText = "Mouse up to offset; drag outside to cancel"
        self.cnv.grid(row=1, column=1, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        RO.Wdg.addCtxMenu(
            wdg = self.cnv,
            helpURL = _HelpURL,
        )

        # create xyLabelSet:
        # first index is 0 for x, 1 for y
        # second index is 0 for sign=1, 1 for sign=-1 (mirror image)
        xLabelSet = []
        cols = (2, 0)
        for ii in range(2):
            xLabel = RO.Wdg.StrLabel(
                master = cnvFrame,
                width = _MaxAxisLabelWidth,
                anchor = ("w", "e")[ii],
            )
            xLabelSet.append(xLabel)
            xLabel.grid(row=1, column=cols[ii])
            
        yLabelSet = []
        rows = (0, 2)
        for ii in range(2):
            yLabel = RO.Wdg.StrLabel(
                master = cnvFrame,
                width = _MaxAxisLabelWidth,
                anchor = "c",
            )
            yLabelSet.append(yLabel)
            yLabel.grid(row=rows[ii], column=1)
        self.xyLabelSet = (xLabelSet, yLabelSet)

        cnvFrame.grid(row=0, column=1)
        
        # draw gray crosshairs
        kargs = {
            "stipple": "gray50",
        }
        self.cnv.create_line(_CnvRad, 0, _CnvRad, cnvSize, **kargs)
        self.cnv.create_line(0, _CnvRad, cnvSize, _CnvRad, **kargs)
    
        self.statusBar = RO.Wdg.StatusBar(
            master = self,
            dispatcher = self.tuiModel.dispatcher,
            prefs = self.tuiModel.prefs,
            playCmdSounds = True,
            helpURL = _HelpURL,
        )
        self.statusBar.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.cnv.bind('<B1-Motion>', self.drawContinue)
        # the following prevents the display from blanking
        # when the button is pressed once (I tried trapping and
        # discarding <ButtonPress-1>, as a faster solution, but it didn't work)
        self.cnv.bind('<ButtonPress-1>', self.drawBegin)
        self.cnv.bind('<ButtonRelease-1>', self.drawEnd)
        
        self.tccModel.iimScale.addCallback(self.updIImScale)
        self.tccModel.objSys.addIndexedCallback(self.updObjSys, 0)

        self.updMaxOff()
        self.updOffType()

    def pixFromArcSec(self, xyArcSec):
        """Convert a point from x,y arcsec (x right, y up) to canvas x,y.
        """
        if self.arcSecPerPix is None:
            raise RuntimeError("Unknown scale")

        xyPix = (
            _CnvRad + ( self.xySign[0] * xyArcSec[0] / self.arcSecPerPix),
            _CnvRad + (-self.xySign[1] * xyArcSec[1] / self.arcSecPerPix),
        )
        return xyPix

    def arcSecFromPix(self, xyPix):
        """Convert a point from canvas x,y to x,y arcsec (x right, y up).
        """
        if self.arcSecPerPix is None:
            raise RuntimeError("Unknown scale")
        
        xyArcSec = (
            (xyPix[0] - _CnvRad) *  self.xySign[0] * self.arcSecPerPix,
            (xyPix[1] - _CnvRad) * -self.xySign[1] * self.arcSecPerPix,
        )
        return xyArcSec
    
    def clear(self, evt=None):
        self.cnv.delete(_ArrowTag)
        for ii in range(2):
            self.offAmtWdgSet[ii].set(None)
        self.offPix = None
        self.offArcSec = None
    
    def drawBegin(self, evt):
        self.drawContinue(evt)
    
    def drawContinue(self, evt):
        if self.arcSecPerPix is None:
            self.clear()
            return
        
        self.offPix = (evt.x, evt.y)
        maxPix = (_CnvRad*2)
        if (self.offPix[0] < 0) or (self.offPix[1] < 0) \
           or (self.offPix[0] > maxPix) or (self.offPix[1] > maxPix):
            self.clear()
            return

        self.cnv.delete(_ArrowTag)
        self.cnv.create_line(
            _CnvRad, _CnvRad, evt.x, evt.y, arrow="last", tag=_ArrowTag,
        )
        self.updOffAmt()
    
    def drawEnd(self, evt=None):
        if self.offArcSec is None:
            return
    
        offType = self.offTypeWdg.getString()
        tccOffType = _OffsetTCCNameDict[offType]
        offDeg = [val / 3600.0 for val in self.offArcSec]
        
        try:
            # if necessary, rotate offset appropriately
            if offType == "Guide XY":
                offDeg = self.azAltFromInst(offDeg)
            elif offType == "Object Arc XY":
                offDeg = self.objFromInst(offDeg)
        
        except Exception as e:
            self.statusBar.setMsg("Failed: %s" % (RO.StringUtil.strFromException(e),),
                severity=RO.Constants.sevError)
            self.statusBar.playCmdFailed()
            return
        
        cmdStr = "offset/computed %s %.7f, %.7f" % (tccOffType, offDeg[0], offDeg[1])
        cmdVar = RO.KeyVariable.CmdVar (
            actor = "tcc",
            cmdStr = cmdStr,
            timeLim = 10,
            timeLimKeyword="SlewDuration",
            isRefresh = False,
        )
        self.statusBar.doCmd(cmdVar)
    
    def azAltFromInst(self, offVec):
        """Rotates offVec from inst to az/alt coords.
        Raises ValueError if cannot compute.
        """
        spiderInstAngPVT, isCurrent = self.tccModel.spiderInstAng.getInd(0)
        spiderInstAng = spiderInstAngPVT.getPos()
        if not isCurrent or spiderInstAng is None:
            raise ValueError("spiderInstAng unknown")
        if None in offVec:
            raise ValueError("bug: unknown offset")
        return RO.MathUtil.rot2D(offVec, -spiderInstAng)

    def objFromInst(self, offVec):
        """Rotates objPos from inst to obj coords.
        Raises ValueError if cannot compute.
        """
        objInstAngPVT, isCurrent = self.tccModel.objInstAng.getInd(0)
        objInstAng = objInstAngPVT.getPos()
        if not isCurrent or objInstAng is None:
            raise ValueError("objInstAng unknown")
        if None in offVec:
            raise ValueError("bug: unknown offset")
        return RO.MathUtil.rot2D(offVec, -objInstAng)

    def updIImScale(self, iimScale, isCurrent, **kargs):
        if None in iimScale:
            return
    
        if self.iimScale != iimScale:
            # if scale has changed then this is probably a new instrument
            # so clear the existing offset and make sure the labels
            # are displayed on the correct sides of the nudger box
            self.iimScale = iimScale
            self.xySign = [RO.MathUtil.sign(scl) for scl in iimScale]
            self.clear()
            self.updOffType()

    def updObjSys (self, csysObj, *args, **kargs):
        """Updates the display when the coordinate system is changed.
        """
        self.objSysLabels = csysObj.posLabels()
        self.updOffType()
    
    def updMaxOff(self, wdg=None):
        maxOff = self.maxOffWdg.getNum()
        
        if maxOff == 0:
            self.arcSecPerPix = None
            self.clear()
            return
        
        self.arcSecPerPix = float(maxOff) / float(_CnvRad)
        offArcSec = self.offArcSec
        if offArcSec is not None:
            offPix = self.pixFromArcSec(offArcSec)
            self.drawContinue(_FakePosEvt(offPix))
    
    def updOffAmt(self):
        if self.offPix is None:
            self.clear()
            return
            
        self.offArcSec = self.arcSecFromPix(self.offPix)
        for ii in range(2):
            self.offAmtWdgSet[ii].set(self.offArcSec[ii])       

    def updOffType(self, wdg=None):
        offType = self.offTypeWdg.getString()
        xyLab = _OffsetAxisLabelsDict[offType]
        if xyLab is None:
            xyLab = self.objSysLabels
            
        for ii in range(2):
            lab = xyLab[ii]
            sign = self.xySign[ii]
            labSet = self.xyLabelSet[ii]
            
            if sign > 0:
                labSet[0].set(lab)
                labSet[1].set("")
            else:
                labSet[1].set(lab)
                labSet[0].set("")
            self.offAmtLabelSet[ii].set(lab + " Offset")
            self.offAmtWdgSet[ii].helpText = "Size of offset in %s" % (lab.lower())
        self.clear()


if __name__ == '__main__':
    root = RO.Wdg.PythonTk()
    
    kd = TUI.TUIModel.getModel(True).dispatcher

    testFrame = NudgerWdg (root)
    testFrame.pack()

    dataDict = {
        "ObjSys": ("Gal", "2000"),
        "ObjInstAng": ("30.0", "0.0", "1000.0"),
        "SpiderInstAng": ("-30.0", "0.0", "1000.0"),
        "TCCPos": ("0.0", "89.0", "30.0"),
    }
    msgDict = {"cmdr":"me", "cmdID":11, "actor":"tcc", "msgType":":", "data":dataDict}

    kd.dispatch(msgDict)

    root.mainloop()
