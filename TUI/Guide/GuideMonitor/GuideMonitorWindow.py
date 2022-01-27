#!/usr/bin/env python
"""Guide monitor

History:
2010-09-27 ROwen    Initial version.
2010-09-28 ROwen    Modified to use new showY method, e.g. to always show the 1" line.
2010-09-30 ROwen    Fixed FWHM units: they are pixels, not arcsec. Thanks to Joe F.
2010-10-01 ROwen    Modified to use TUI.Base.StripChartWdg.
                    Turned off frame on legend.
2010-10-18 ROwen    Changed timespan to 1 hour (at Russet's request).
                    Combined guide and seeing monitor (since they now have the same timespan).
                    Changed guide star brightness chart to only include star data of type "g"
                    (guider-reported star data); formerly it also showed "c" (manually centroided stars).
2010-12-10 ROwen    Reduced the memory leak by increasing updateInterval from its default value of 1.8 sec
                    to 20 seconds. Return to the default value again once the matplotlib bug is fixed.
2010-12-23 ROwen    Modified to use new version of StripChartWdg.
2014-06-06 ROwen    Fix a traceback caused by unknown tccModel.guideOff.
"""
import math
import tkinter
import matplotlib
import RO.Wdg
import TUI.Base.StripChartWdg
import TUI.Guide.GuideModel
import TUI.TCC.TCCModel

WindowName = "Guide.Guide Monitor"

def addWindow(tlSet):
    """Create the window for TUI.
    """
    tlSet.createToplevel(
        name = WindowName,
        defGeom = "+434+22",
        visible = False,
        resizable = True,
        wdgFunc = GuideMonitorWdg,
    )

class GuideMonitorWdg(tkinter.Frame):
    """Monitor guide star FWHM, focus and guide corrections.
    """
    def __init__(self, master, timeRange=3600, width=10, height=6):
        """Create a GuideMonitorWdg
        
        Inputs:
        - master: parent Tk widget
        - timeRange: range of time displayed (seconds)
        - width: width of plot (inches)
        - hiehgt: height of plot (inches)
        """
        tkinter.Frame.__init__(self, master)
        
        self.tccModel = TUI.TCC.TCCModel.getModel()
        
        self.stripChartWdg = TUI.Base.StripChartWdg.StripChartWdg(
            master = self,
            timeRange = timeRange,
            updateInterval = 20,
            numSubplots = 4,
            width = width,
            height = height,
            cnvTimeFunc = TUI.Base.StripChartWdg.TimeConverter(useUTC=True),
        )
        self.stripChartWdg.grid(row=0, column=0, sticky="nwes")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # the default ticks are not nice, so be explicit
        self.stripChartWdg.xaxis.set_major_locator(matplotlib.dates.MinuteLocator(byminute=list(range(0, 60, 15))))

        spInd = 0
        
        # FWHM
        self.stripChartWdg.subplotArr[spInd].yaxis.set_label_text("FWHM (pix)")
        self.fwhmLine = self.stripChartWdg.addLine(label="FWHM", subplotInd=spInd, color="green")
        self.stripChartWdg.addConstantLine(1.0, subplotInd=spInd, color="purple")
        self.stripChartWdg.showY(0, 1.2, subplotInd=spInd)
        spInd += 1
        
        self.guideModelDict = {} # guide camera name: guide model
        for guideModel in TUI.Guide.GuideModel.modelIter():
            gcamName = guideModel.gcamName
            if gcamName.endswith("focus"):
                continue
            self.guideModelDict[guideModel.gcamName] = guideModel
            guideModel.star.addCallback(self._updStar, callNow=False)
        
        # Brightness
        self.stripChartWdg.subplotArr[spInd].yaxis.set_label_text("Bright (ADU)")
        self.brightnessLine = self.stripChartWdg.addLine(label="Brightness", subplotInd=spInd, color="green")
        self.stripChartWdg.showY(0, 100, subplotInd=spInd)
        spInd += 1

        # Focus
        self.stripChartWdg.subplotArr[spInd].yaxis.set_label_text("Focus (um)")
        self.stripChartWdg.plotKeyVar(label="Sec Piston", subplotInd=spInd, keyVar=self.tccModel.secOrient, color="green")
        self.stripChartWdg.plotKeyVar(label="User Focus", subplotInd=spInd, keyVar=self.tccModel.secFocus, color="blue")
        self.stripChartWdg.showY(0, subplotInd=spInd)
        self.stripChartWdg.subplotArr[spInd].legend(loc=3, frameon=False)
        spInd += 1

        # Guide correction
        self.stripChartWdg.subplotArr[spInd].yaxis.set_label_text("Guide Off (\")")
        self.azOffLine = self.stripChartWdg.addLine(label="Az (on sky)", subplotInd=spInd, color="green")
        self.altOffLine = self.stripChartWdg.addLine(label="Alt", subplotInd=spInd, color="blue")
        self.stripChartWdg.showY(-3.0, 3.0, subplotInd=spInd)
        self.stripChartWdg.subplotArr[spInd].legend(loc=3, frameon=False)
        spInd += 1

        self.tccModel.guideOff.addCallback(self._updGuideOff, callNow=False)
    
    def _updGuideOff(self, *args, **kargs):
        """Updated actual guide offset in az, alt (")
        """
        if not self.tccModel.guideOff.isCurrent():
            return
        if not self.tccModel.guideOff.isGenuine():
            return

        guideOffPVTList = self.tccModel.guideOff.get()[0]
        if None in guideOffPVTList:
            return
        guideOffArcSecList = [pvt.getPos() * RO.PhysConst.ArcSecPerDeg for pvt in guideOffPVTList]
        currAlt = self.tccModel.axePos.getInd(1)[0]
        if currAlt is None:
            return
        azOffsetOnSky = guideOffArcSecList[0] * math.cos(currAlt * RO.PhysConst.RadPerDeg)
        
        self.azOffLine.addPoint(azOffsetOnSky)
        self.altOffLine.addPoint(guideOffArcSecList[1])
         
    def _updStar(self, valList, isCurrent=True, keyVar=None):
        """Updated star data

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
        if not isCurrent:
            return
        if valList[0] != "g":
            return
        self.fwhmLine.addPoint(valList[8])
        self.brightnessLine.addPoint(valList[12])


if __name__ == "__main__":
    from . import TestData

    addWindow(TestData.tuiModel.tlSet)
    TestData.tuiModel.tlSet.makeVisible(WindowName)
    
    TestData.runTest()
    
    TestData.tuiModel.tkRoot.mainloop()
