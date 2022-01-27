#!/usr/bin/env python
"""Test Agile guider

History:
2009-03-05 ROwen
2012-07-09 ROwen    Modified to use RO.TkUtil.Timer.
"""
import os
import random
import tkinter
from RO.TkUtil import Timer
import RO.Wdg
import TUI.TUIModel
import TUI.TCC.TCCModel
import TUI.Inst.ExposeModel
import TUI.Inst.Agile.AgileModel
import TUI.Guide.GuideModel
from . import AgileGuideWindow
import TUI.Base.TestDispatcher

def makeStarKeyword(
    isFind,
    xyPos,
    randRange,
    centroidRad,
    index = 0,
    xyErr = (1.0, 1.0),
    asymm = 10.0,
    fwhm = 3.0,
    counts = 10000,
    bkgnd = 100,
    ampl = 3000,
):
    """Return a star keyword with values.

    The fields are as follows, where lengths and positions are in binned pixels
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
    if isFind:
        typeChar = "f"
    else:
        typeChar = "c"
    if randRange > 0:
        xyPos = [random.uniform(val - randRange, val + randRange) for val in xyPos]
    
    return "star=%s, %d, %0.2f, %0.2f, %0.2f, %0.2f, %0.0f, %0.0f, %0.1f, %0.1f, 0.0, 5, %0.0f, %0.1f, %0.1f" % \
        (typeChar, index, xyPos[0], xyPos[1], xyErr[0], xyErr[1], centroidRad, asymm, fwhm, fwhm, counts, bkgnd, ampl)

def makeFilesKeyword(
    cmdr,
    fileName,
    host = "localhost",
    commonRoot = "/tmp",
    progSubDir = "/prog/date",
    userSubDir = "/user/",
):
    """Return a files keyword with data

    Fields are:
    - cmdr (progID.username)
    - host
    - common root directory
    - program and date subdirectory
    - user subdirectory
    - file name(s)
    """
    return "agileFiles=%s, %s, %r, %r, %r, %r" % (cmdr, host, commonRoot, progSubDir, userSubDir, fileName)

def makeFindData(numFound, mainXYPos, centroidRad=10, mainCounts=10000, mainAmpl=3000):
    """Return a list of star keyword data
    """
    return [makeStarKeyword(
        isFind=True,
        xyPos = [val + (ind * 10.0) for val in mainXYPos],
        randRange = 0,
        centroidRad = centroidRad,
        index = ind,
        counts = mainCounts / float(ind + 1),
        bkgnd = 100,
        ampl = mainAmpl / float(ind + 1),
    ) for ind in range(numFound)]


class TestGuiderWdg(tkinter.Frame):
    def __init__(self, testDispatcher, master):
        tkinter.Frame.__init__(self, master)
        self.testDispatcher = testDispatcher

        random.seed(0)
   
        self.tuiModel = self.testDispatcher.tuiModel
        self.pollTimer = Timer()
        self.oldPendingCmd = None
        self.fileNum = 0

        gr = RO.Wdg.Gridder(self, sticky="ew")
    
        self.guideWdg = AgileGuideWindow.AgileGuideWdg(self)
        gr.gridWdg(False, self.guideWdg, colSpan=10)
        
        self.imageAvailWdg = RO.Wdg.Button(
            master = self,
            text = "Image is Available",
            callFunc = self.dispatchFileData,
        )
        gr.gridWdg(None, self.imageAvailWdg)
        
        self.starPosWdgSet = []
        for ii in range(2):
            letter = ("X", "Y")[ii]
            starPosWdg = RO.Wdg.FloatEntry(
                master = self,
                label = "Star Pos %s" % (letter,),
                minValue = 0,
                defValue = 100 * (ii + 1),
                maxValue = 5000,
                autoIsCurrent = True,
                autoSetDefault = True,
                helpText = "Star %s position in binned pixels" % (letter,),
            )
            self.starPosWdgSet.append(starPosWdg)
        gr.gridWdg("Star Pos", self.starPosWdgSet, "pix")

        self.centroidRadWdg = RO.Wdg.IntEntry(
            master = self,
            label = "Centroid Rad",
            minValue = 5,
            maxValue = 1024,
            defValue = 10,
            defMenu = "Default",
            autoIsCurrent = True,
            autoSetDefault = True,
            helpText = "Radius of region to centroid in binned pixels; don't skimp",
        )
        gr.gridWdg(self.centroidRadWdg.label, self.centroidRadWdg, "arcsec", sticky="ew")

        self.numToFindWdg = RO.Wdg.IntEntry(
            master = self,
            label = "Num To Find",
            minValue = 0,
            maxValue = 100,
            defValue = 5,
            defMenu = "Default",
            autoIsCurrent = True,
            autoSetDefault = True,
            helpText = "Number of stars to find (0 for findstars to fail)",
        )
        gr.gridWdg(self.numToFindWdg.label, self.numToFindWdg)
        
        self.centroidOKWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Centroid OK",
            defValue = True,
            helpText = "Should centroid command succeed?",
        )
        gr.gridWdg(None, self.centroidOKWdg)
        
        self.offsetOKWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Offset OK",
            defValue = True,
            helpText = "Should offset command succeed?",
        )
        gr.gridWdg(None, self.offsetOKWdg)
        
        self.axesTrackingWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Axes Tracking",
            defValue = True,
            callFunc = self.axesTrackingCallback,
            helpText = "Are axes tracking?",
        )
        gr.gridWdg(None, self.axesTrackingWdg)
        
        self.isInstAgileWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Is Curr Inst Agile?",
            defValue = True,
            callFunc = self.isInstAgileCallback,
            helpText = "Is the current instrument Agile?",
        )
        gr.gridWdg(None, self.isInstAgileWdg)

        self.useWrongCmdrWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Use Wrong Cmdr",
            defValue = False,
            helpText = "Should replies be for a different cmdr?",
        )
        gr.gridWdg(None, self.useWrongCmdrWdg)

        self.useWrongCmdIDWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Use Wrong Cmd ID",
            defValue = False,
            helpText = "Should replies be for a different command?",
        )
        gr.gridWdg(None, self.useWrongCmdIDWdg)

        self.useWrongActorWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Use Wrong Actor",
            defValue = False,
            helpText = "Should replies be for a different actor?",
        )
        gr.gridWdg(None, self.useWrongActorWdg)
        
        self.grid_columnconfigure(9, weight=1)
        
        tccData = (
            "inst=Agile",
            "iimScale=-27784.4, 27569.0",
            "axisCmdState=Tracking, Tracking, Tracking",
        )
        self.testDispatcher.dispatch(tccData, actor="tcc")
        self.testDispatcher.dispatch("bin=1", actor="agile")
        
        self.pollPendingCmd()

    def axesTrackingCallback(self, wdg=None):
        if self.axesTrackingWdg.getBool():
            tccData = "axisCmdState=Tracking, Tracking, Tracking"
        else:
            tccData = "axisCmdState=Tracking, Halted, Tracking"
        self.testDispatcher.dispatch(tccData, actor="tcc")

    def isInstAgileCallback(self, wdg=None):
        if self.isInstAgileWdg.getBool():
            tccData = "inst=Agile"
        else:
            tccData = "inst=SPICam"
        self.testDispatcher.dispatch(tccData, actor="tcc")
        
    def dispatchFileData(self, wdg=None):
        keyArgs = self.getDispatchKeyArgs("agileExpose", cmdID=0)
        fileName = "image%d" % (self.fileNum,)
        self.fileNum += 1
        filesKeyword = makeFilesKeyword(cmdr=keyArgs["cmdr"], fileName=fileName)
        self.testDispatcher.dispatch(filesKeyword, msgCode=":", **keyArgs)

    def dispatchFindData(self, wdg=None):
        keyArgs = self.getDispatchKeyArgs("afocus")

        numToFind = self.numToFindWdg.getNum()

        if numToFind < 1:
            self.testDispatcher.dispatch("text='No stars found'", msgCode="f", **keyArgs)
            return

        mainXYPos = [wdg.getNum() for wdg in self.starPosWdgSet]
        centroidRad = self.centroidRadWdg.getNum()
        findData = makeFindData(numFound=numToFind, mainXYPos=mainXYPos, centroidRad=centroidRad)
        self.testDispatcher.dispatch(findData, msgCode="i", **keyArgs)
        self.testDispatcher.dispatch("", msgCode=":", **keyArgs)

    def dispatchCentroidData(self, wdg=None):
        keyArgs = self.getDispatchKeyArgs("afocus")

        if not self.centroidOKWdg.getBool():
            self.testDispatcher.dispatch("text='No stars found'", msgCode="f", **keyArgs)
            return
        
        xyPos = [wdg.getNum() for wdg in self.starPosWdgSet]
        centroidRad = self.centroidRadWdg.getNum()
        centroidData = makeStarKeyword(isFind=False, xyPos=xyPos, randRange=10, centroidRad=centroidRad)
        self.testDispatcher.dispatch(centroidData, msgCode=":", **keyArgs)

    def getDispatchKeyArgs(self, actor, cmdID=None):
        """Get keyword arguments for the test dispatcher's dispatch command
        """
        if self.useWrongCmdrWdg.getBool():
            cmdr = "APO.other"
        else:
            cmdr = self.tuiModel.getCmdr()

        if cmdID is None:
            if self.guideWdg.pendingCmd:
                cmdID = self.guideWdg.pendingCmd.cmdID or 0
            else:
                cmdID = 0

        if self.useWrongCmdIDWdg.getBool():
            cmdID += 1000
        
        if self.useWrongActorWdg.getBool():
            actor = "other"
        else:
            actor = actor

        return dict(cmdr=cmdr, cmdID=cmdID, actor=actor)

    def pollPendingCmd(self):
        """Poll to see if there's a new pending command and respond accordingly
        """
        self.pollTimer.cancel()

        if self.guideWdg.pendingCmd != self.oldPendingCmd:
            self.oldPendingCmd = self.guideWdg.pendingCmd
            if not self.oldPendingCmd.isDone():
                self.replyToCommand()

        self.pollTimer.start(1.0, self.pollPendingCmd)

    def replyToCommand(self):
        """Issue the appropriate replly to a pending command
        """
#         print "replyToCommand", self.oldPendingCmd
        actor = self.oldPendingCmd.actor.lower()
        cmdStr = self.oldPendingCmd.cmdStr
        cmdID = self.oldPendingCmd.cmdID

        keyArgs = self.getDispatchKeyArgs(actor)
        
        if actor == "tcc":
            if self.offsetOKWdg.getBool():
                self.testDispatcher.dispatch("", msgCode=":", **keyArgs)
            else:
                self.testDispatcher.dispatch("text='Offset failed'", msgCode="f", **keyArgs)
        elif actor == "afocus":
            if cmdStr.startswith("centroid"):
                self.dispatchCentroidData()
            elif cmdStr.startswith("find"):
                self.dispatchFindData()
            else:
                print("Unknown afocus command:", cmdStr)
        else:
            print("Unknown actor:", actor)

if __name__ == "__main__":
    testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="agile", delay=0.5)
    root = testDispatcher.tuiModel.tkRoot
    wdg = TestGuiderWdg(testDispatcher, root)
    wdg.pack()
    root.mainloop()
