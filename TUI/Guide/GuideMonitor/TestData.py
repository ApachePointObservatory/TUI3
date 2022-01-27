#!/usr/bin/env python
"""Supplies test data for the Seeing Monitor

History:
2010-09-24
2010-09-29 ROwen    modified to use RO.Alg.RandomWalk
2010-10-18 ROwen    Added guide offset information.
2012-07-09 ROwen    Modified to use RO.TkUtil.Timer.
"""
import math
import RO.Alg.RandomWalk
from RO.TkUtil import Timer
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher("tcc")
tuiModel = testDispatcher.tuiModel

Alt = 45.0

class GuideOffInfo(object):
    def __init__(self):
        azScale = 1.0 / math.cos(Alt * RO.PhysConst.RadPerDeg)
        lim = 10.0 / RO.PhysConst.ArcSecPerDeg
        mean = 0.0 / RO.PhysConst.ArcSecPerDeg
        sigma = 2.0 / RO.PhysConst.ArcSecPerDeg
        
        self.randomValueDict = dict(
            azOff = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(
                mean * azScale, sigma * azScale, -lim * azScale, lim * azScale),
            altOff = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(mean, sigma, -lim, lim),
            rotOff = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(mean, sigma, -lim, lim),
        )
    
    def update(self):
        """Randomly change values
        """
        for randomValue in self.randomValueDict.values():
            next(randomValue)
    
    def getValueDict(self):
        """Get a dictionary of value name: value
        """
        return dict((name, randomValue.value) for name, randomValue in self.randomValueDict.items())

    def getKeyVarStr(self):
        """Get the data as a keyword variable
        
        Fields are:
        az off, az vel, az time, alt off, alt vel, alt time, rot off, rot vel, rot time
        where offsets are in degrees
        the offsets are assumed constant so time is not interesting so I don't bother to set it realistically
        """
        return "GuideOff=%(azOff)0.5f, 0.0, 100.0, %(altOff)0.5f, 0.0, 100.0, %(rotOff)0.5f, 0.0, 100.0" % \
            self.getValueDict()

class StarInfo(object):
    def __init__(self):
        self.randomValueDict = dict(
            fwhm = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(0.5, 0.1, 0.3, 1.2),
            amplitude = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(10000, 100, 5000, 32000),
            xCenter = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(0, 10, -500, 500),
            yCenter = RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(0, 10, -500, 500),
        )
    
    def update(self):
        """Randomly change values
        """
        for randomValue in self.randomValueDict.values():
            next(randomValue)
    
    def getValueDict(self):
        """Get a dictionary of value name: value
        """
        valDict = dict((name, randomValue.value) for name, randomValue in self.randomValueDict.items())
        valDict["brightness"] = valDict["fwhm"] * valDict["amplitude"]
        valDict["background"] = 1200.0
        return valDict

    def getKeyVarStr(self):
        """Get the data as a keyword variable

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
        return "Star=c, 0, %(xCenter)0.1f, %(yCenter)0.1f, 10.0, -7.0, 5, 100.0, %(fwhm)0.2f, %(fwhm)0.2f, 0, 10, %(brightness)0.1f, %(background)0.1f, %(amplitude)0.1f" % \
            self.getValueDict()

def runTest():
    testDispatcher.dispatch("AxePos=0.0, %0.3f, 0" % (Alt,), actor="tcc")
    _nextGuideOffset(GuideOffInfo(), 2)
    _nextStar(StarInfo(), 5)
    _nextSecFocus(RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(0, 10, -500, 500), 6)
    _nextSecPiston(RO.Alg.RandomWalk.ConstrainedGaussianRandomWalk(100, 25, -2000, 2000), 3)

def _nextGuideOffset(guideOffInfo, delaySec):
    guideOffInfo.update()
    keyVarStr = guideOffInfo.getKeyVarStr()
    testDispatcher.dispatch(keyVarStr, actor="tcc")
    Timer(delaySec, _nextGuideOffset, guideOffInfo, delaySec)

def _nextStar(starInfo, delaySec):
    starInfo.update()
    keyVarStr = starInfo.getKeyVarStr()
    testDispatcher.dispatch(keyVarStr, actor="gcam")
    Timer(delaySec, _nextStar, starInfo, delaySec)

def _nextSecFocus(secFocus, delaySec):
    keyVarStr = "SecFocus=%0.1f" % (next(secFocus),)
    testDispatcher.dispatch(keyVarStr, actor="tcc")
    Timer(delaySec, _nextSecFocus, secFocus, delaySec)

def _nextSecPiston(secPiston, delaySec):
    keyVarStr = "SecOrient=%0.1f, 0, 0, 0, 0" % (next(secPiston),)
    testDispatcher.dispatch(keyVarStr, actor="tcc")
    Timer(delaySec, _nextSecPiston, secPiston, delaySec)
