#!/usr/bin/env python
"""Model for guide cameras.

Warning: the config stuff will probably be modified.

2005-01-28 ROwen    preliminary; has all existing keywords, but there will be more
                    and "star" will probably change to include ellipticity.
2005-02-23 ROwen    added expTime and thresh.
2005-03-14 ROwen    overhauled for new keywords
2005-03-30 ROwen    overhauled again for new keywords files and star keywords.
2005-04-11 ROwen    Renamed to GuideModel from GCamModel (because an actor is named gcam).
2005-04-13 ROwen    Bug fix: was refreshing all keywords. Was refreshing nonexistent keyword time.
2005-04-20 ROwen    Removed expTime; get from FITS header instead.
                    Added default exposure time and bin factor to camInfo.
                    Tweaked description of fs...Thresh keywords, since they now
                    also apply to centroid.
2005-06-08 ROwen    Added noStarsFound and starQuality.
2005-06-10 ROwen    Added playing of sound cues.
                    Renamed noStarsFound to noGuideStar.
                    Modified starQuality to accept additional values.
2005-06-17 ROwen    Guide start/stop sounds only play if the state has changed.
                    Thus one can quietly ask for guide status.
2005-06-23 ROwen    Modified to not play NoGuideStar sound unless the keyword is "genuine".
                    This is mostly paranoia since it's not auto-refreshed anyway.
2005-06-27 ROwen    Changed default bin factor from 3 to 1 for the DIS and Echelle slitviewers.
2005-07-08 ROwen    Modified for http download:
                    - Changed ftpLogWdg to downloadWdg.
                    - Removed imageRoot.
2005-08-02 ROwen    Modified for TUI.Sounds->TUI.PlaySound.
2005-10-24 ROwen    Lowered default min exposure time to 0 sec.
2006-03-28 ROwen    Added "nfocus" actor.
                    Added guideMode keyword.
                    Bug fix: fsActRadMult was listening for fsDefRadMult.
2006-04-14 ROwen    Added locGuideMode.
                    Play a sound when locGuideMode changes while guiding.
2006-05-18 ROwen    Added measOffset and actOffset.
                    Added support for predicted position for star="g"...
                    Added support for NaN in star values.
2006-05-22 ROwen    Changed the default exposure time from 10 to 5 seconds
                    by request of the obs specs.
2006-03-03 ROwen    Added imSize to gcamInfo. This may be a temporary hack,
                    since it would be better to get the info from the hub.
2007-01-29 ROwen    Bug fix: guiding sound cues were not always played because
                    "starting" and perhaps "stopping" states were not always sent.
2007-06-05 ROwen    Added "sfocus" actor.
2008-02-04 ROwen    Added locGuideStateSummary.
2008-03-14 ROwen    Added tcam actor.
2008-03-17 ROwen    Bug fix: tcam was not listed as a slitviewer.
2008-03-25 ROwen    PR 744: changed default nfocus exposure time to 6 seconds.
2008-04-01 ROwen    Bug fix: _updLocGuideModeSummary mis-handled a mode of None.
2008-04-22 ROwen    Added expState.
2008-04-23 ROwen    Get expState from the cache (finally) but null out the times.
                    Modified expState so durations can be None or 0 for unknown (was just 0).
2008-07-24 ROwen    Fixed CR 851: changed tcam default bin factor to 2 (from 1).
2010-03-04 ROwen    Changed gcam info field slitViewer to isSlitViewer.
2010-03-18 ROwen    Added "afocus" actor.
2010-10-20 ROwen    Modified to not auto-refresh expState keyvar for focus actors; expState isn't
                    output by focus actors, but it's more consistent to leave it in with a null value.
2012-08-10 ROwen    Updated for RO.Comm 3.0.
2015-06-01 ROwen    Updated for new dcam, which has size 1024x1024 instead of 512x512.
2015-11-05 ROwen    Changed ==/!= True/False to is/is not True/False to modernize the code.
"""
__all__ = ['getModel']

import RO.CnvUtil
import RO.KeyVariable
import TUI.TUIModel
import TUI.PlaySound

class _GCamInfo:
    """Exposure information for a camera
    
    Inputs:
    - min/maxExpTime: minimum and maximum exposure time (sec)
    - isSlitViewer: True if a slit viewer
    """
    def __init__(self,
        imSize,
        minExpTime = 0.0,
        maxExpTime = 3600,
        defBinFac = 1,
        defExpTime = 5,
        isSlitViewer = False,
    ):
        self.imSize = imSize
        self.minExpTime = float(minExpTime)
        self.maxExpTime = float(maxExpTime)
        self.defBinFac = defBinFac
        self.defExpTime = defExpTime
        self.isSlitViewer = bool(isSlitViewer)

# dictionary of instrument information
# instrument names must be lowercase
_GCamInfoDict = {
    "kcam": _GCamInfo(
        imSize = (1024, 1024),
        minExpTime = 0.3,
        isSlitViewer = True,
    ),    
    "dcam": _GCamInfo(
        imSize = (1024, 1024),
        minExpTime = 0.3,
        isSlitViewer = True,
    ),
    "ecam": _GCamInfo(
        imSize = (512, 512),
        isSlitViewer = True,
    ),
    "gcam": _GCamInfo(
        imSize = (1024, 1024),
        defBinFac = 3,
    ),
    "tcam":_GCamInfo(
        imSize = (1024, 1024),
        isSlitViewer = True,
        defBinFac = 2,
    ),
    "afocus":_GCamInfo(
        imSize = (1024, 1024),
    ),
    "nfocus":_GCamInfo(
        imSize = (1024, 1024),
        defExpTime = 6,
    ),
    "sfocus":_GCamInfo(
        imSize = (2048, 2048),
    ),
}

# cache of guide camera models
# each entry is gcamName: model
_modelDict = {}

def getModel(gcamName):
    global _modelDict
    gcamNameLow = gcamName.lower()
    model = _modelDict.get(gcamNameLow)
    if model is None:
        model = Model(gcamName)
        _modelDict[gcamNameLow] = model
    return model

def modelIter():
    for gcamName in _GCamInfoDict.keys():
        yield getModel(gcamName)

class Model (object):
    def __init__(self, gcamName):
        self.gcamName = gcamName
        self.actor = gcamName.lower()
        self._isGuiding = None
        self._isFocusActor = self.actor.endswith("focus")

        self.gcamInfo = _GCamInfoDict[self.actor]
        
        self.tuiModel = TUI.TUIModel.getModel()
        
        keyVarFact = RO.KeyVariable.KeyVarFactory(
            actor = self.actor,
            dispatcher = self.tuiModel.dispatcher,
            converters = str,
            allowRefresh = True,
        )

        self.expState = keyVarFact(
            keyword = "expState",
            converters = (str, str, RO.CnvUtil.asFloatOrNone, RO.CnvUtil.asFloatOrNone),
            description = """current exposure info:
            - exposure state; one of: idle, flushing, integrating, paused,
                reading, processing, aborting, done or aborted.
            - start time (an ANSI-format UTC timestamp)
            - remaining time for this state (sec; 0 or None if short or unknown)
            - total time for this state (sec; 0 or None if short or unknown)

            Note: if the data is cached then remaining time and total time
            are changed to 0 to indicate that the values are unknown
            """,
            allowRefresh = not self._isFocusActor,
        )
        self.expState.addCallback(self._updExpState)
    
        # keywords for parameters
        self.fsActRadMult = keyVarFact(
            keyword="fsActRadMult",
            converters = RO.CnvUtil.asFloat,
            description="""Actual findStars radius multiplier""",
            allowRefresh = False,
        )
    
        self.fsActThresh = keyVarFact(
            keyword="fsActThresh",
            converters = RO.CnvUtil.asFloat,
            description="""Actual findStars and centroid threshold (sigma)""",
            allowRefresh = False,
        )

        self.fsDefRadMult = keyVarFact(
            keyword="fsDefRadMult",
            converters = RO.CnvUtil.asFloat,
            description="""Default findStars radius multiplier""",
        )
        
        self.fsDefThresh = keyVarFact(
            keyword="fsDefThresh",
            converters = RO.CnvUtil.asFloat,
            description="""Default findStars and centroid threshold (sigma)""",
        )
    
        self.files = keyVarFact(
            keyword="files",
            nval = (5, None),
            converters = (str, RO.CnvUtil.asBool, str),
            description="""Image used for command:
- command: one of: c (centroid), f (findStars) or g (guiding)
- isNew: 1 if a new file, 0 if an existing file
- baseDir: base directory for these files (relative to image root)
- finalFile: image file (with any processing)
- maskFile: mask file
other values may be added
""",
            allowRefresh = False,
        )

        self.guideState = keyVarFact(
            keyword="guideState",
            nval=(1,None),
            description="""State of guide actor. Fields are:
- mainState: one of: on, starting, stopping, off
any remaining fields are supplementary info
""",
        )
        self.guideState.addIndexedCallback(self._updGuideState)

        self.locGuideMode = keyVarFact(
            keyword="locGuideMode",
            description="""like guideMode, but restricted to one of:
field, boresight, manual, "" or None
and lowercase is guaranteed""",
            isLocal = True,
        )
        
        self.locGuideStateSummary = keyVarFact(
            keyword = "locGuideStateSummary",
            nval=1,
            description = """Summary of state of guide actor; one of: on, off, starting, stopping, manual
where manual means guide state = on and guide mode = manual
""",
            isLocal = True,
        )
        
        self.guideMode = keyVarFact(
            keyword="guideMode",
            description="one of: field, boresight or manual or some other values",
        )
        self.guideMode.addIndexedCallback(self._updGuideMode)

        self.star = keyVarFact(
            keyword="star",
            nval = (15,17),
            converters = (str, int, RO.CnvUtil.asFloatOrNone),
            description="""Data about a star.
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
""",
            allowRefresh = False,
        )
        
        self.measOffset = keyVarFact(
            keyword="measOffset",
            nval = 2,
            converters = float,
            description="""The measured offset of the guidestar from its predicted position, in az/alt arcseconds. See also actOffset.""",
            allowRefresh = False,
        )

        self.actOffset = keyVarFact(
            keyword="actOffset",
            nval = 2,
            converters = float,
            description="""The offset that willl be sent to the TCC, in az/alt arcseconds. This is measOffset adjusted as the hub guider sees fit.""",
            allowRefresh = False,
        )

        self.noGuideStar = keyVarFact(
            keyword="NoGuideStar",
            nval = 0,
            description="Guide loop found no stars.",
            allowRefresh = False,
        )
        self.noGuideStar.addCallback(self._updNoGuideStar)
        
        self.starQuality = keyVarFact(
            keyword="StarQuality",
            nval = (1, None),
            converters = RO.CnvUtil.asFloatOrNone,
            description="""Guide iteration centroid quality.
0   overall quality; a value between 0 and 1
additional fields may be used for components of star quality
""",
            allowRefresh = False,
        )
        
        keyVarFact.setKeysRefreshCmd()

        self.ftpSaveToPref = self.tuiModel.prefs.getPrefVar("Save To")
        downloadTL = self.tuiModel.tlSet.getToplevel("TUI.Downloads")
        self.downloadWdg = downloadTL and downloadTL.getWdg()
    
    def _updLocGuideModeSummary(self):
        """Compute new local guide mode summary"""
        guideState, gsCurr = self.guideState.getInd(0)
        if guideState is None:
            return
        if guideState.lower() != "on":
            self.locGuideStateSummary.set((guideState,), isCurrent = gsCurr)
            return
        
        guideMode, gmCurr = self.locGuideMode.getInd(0)
        if guideMode == "manual":
            self.locGuideStateSummary.set((guideMode,), isCurrent = gsCurr and gmCurr)
        else:
            self.locGuideStateSummary.set((guideState,), isCurrent = gsCurr)
    
    def _updGuideMode(self, guideMode, isCurrent, **kargs):
        """Handle new guideMode.
        
        Set locGuideMode and play "Guide Mode Changed"
        as appropriate.
        """
        if not guideMode:
            self.locGuideMode.set((None,), isCurrent = isCurrent)
            return
            
        gmLower = guideMode.lower()
        if gmLower not in ("boresight", "field", "manual", None):
            return

        if gmLower and isCurrent:
            guideState, gsIsCurrent = self.guideState.getInd(0)
            locGuideMode, lgmIsCurrent = self.locGuideMode.getInd(0)
            if guideState and gsIsCurrent and \
                locGuideMode and lgmIsCurrent and \
                (gmLower != locGuideMode) and \
                (guideState.lower() == "on"):
                TUI.PlaySound.guideModeChanges()

        self.locGuideMode.set((gmLower,), isCurrent)
    
        self._updLocGuideModeSummary()
        
    def _updExpState(self, expState, isCurrent, keyVar):
        """Set the durations to None (unknown) if data is from the cache"""
        if keyVar.isGenuine():
            return
        modValues = list(expState)
        modValues[2] = None
        modValues[3] = None
        keyVar._valueList = tuple(modValues)
    
    def _updGuideState(self, guideState, isCurrent, **kargs):
        if not isCurrent:
            if not self.tuiModel.dispatcher.connection.isConnected:
                self._isGuiding = None
            return
        
        gsLower = guideState.lower()

        if gsLower in ("starting", "on"):
            if self._isGuiding is not True:
                TUI.PlaySound.guidingBegins()
            self._isGuiding = True
        elif gsLower == "stopping":
            if self._isGuiding is not False:
                TUI.PlaySound.guidingEnds()
            self._isGuiding = False
    
        self._updLocGuideModeSummary()

    
    def _updNoGuideStar(self, noData, isCurrent, **kargs):
        if not isCurrent:
            return
        if not self.guideState.isGenuine():
            return
        
        guideState, gsCurr = self.guideState.getInd(0)
        if guideState.lower() not in ("on", "starting"):
            return
    
        TUI.PlaySound.noGuideStar()


if __name__ == "__main__":
#   getModel("dcam")
    getModel("ecam")
    getModel("gcam")
