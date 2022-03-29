#!/usr/bin/env python
"""Model for exposures (data from the expose command).
A different model is required for each instrument,
but there are only a few minor differences.

Notes:
- At this time, nextPath is the only keyword reliably returned by keys for <inst>Expose.
  Thus it is the only keyword with a refresh command.
  Fix this when the expose command is fixed.

2003-07-16 ROwen
2003-07-25 ROwen    Added expState, seqState, nFiles
2003-07-30 ROwen    Added inst-specific info and getModel
2003-10-01 ROwen    Modified to use new versions of seqState and expState (for new hub).
2003-10-06 ROwen    Modified to use new versions of files and nextPath (for new hub).
2003-10-10 ROwen    Modified actor to match change in hub expose.
2003-10-16 ROwen    Bug fix: some refresh commands had not been updated for the new hub.
2003-10-22 ROwen    Bug fix: GRIM min exposure time is >1.21, not >=1.21 sec,
                    so I set the lower limit to 1.22.
2003-12-17 ROwen    Modified to use KeyVariable.KeyVarFactory
                    and to take advantage of key variables now
                    auto-setting nval if a set of converters is supplied.
2004-01-06 ROwen    Modified to use KeyVarFactory.setKeysRefreshCmd.
2004-08-27 ROwen    Added new <inst>NewFiles keyword.
2004-09-10 ROwen    Moved auto ftp code here from ExposeInputWdg.
                    Added several ftp-related entries.
                    Added formatExpCmd (to make scripting easier).
                    Replaced model.dispatcher with model.tuiModel.
                    Added __all__ to improve "from ExposeModel import *".
2004-09-28 ROwen    Added comment entry.
2004-10-19 ROwen    Added nicfps to _InstInfoDict.
2004-11-16 ROwen    Modified to explicitly ask for binary ftp
                    (instead of relying on the ftp server to be smart).
2004-11-17 ROwen    Modified for changed RO.Comm.FTPLogWdg.
2004-11-29 ROwen    Changed nicfps minimum expose time to 0.
2004-12-20 ROwen    Listed the allowed states for expState and seqState.
2005-06-14 ROwen    Removed instrument info for grim.
                    Changed the test code to auto-select instrument names.
2005-07-08 ROwen    Modified for http download.
2005-07-13 ROwen    Bug fix: formatExpCmd rejected 0 as a missing exposure time.
2005-07-21 ROwen    Modified to fully quote the file name (meaningless now because special
                    characters aren't allowed, but in case that restriction is lifted...).
2005-09-15 ROwen    Replaced autoFTPPref -> autoFTPVar to allow user to toggle it
                    for this instrument w/out affecting other instruments.
                    Users logged into program APO are everyone's collaborators.
                    Added viewImageVar and added image view support. Warning:
                    it blocks events while the ds9 window is opened,
                    which can be a long time if there's an error.
2005-09-23 ROwen    Fix PR 269: Seq By File preference cannot be unset.
                    Fixed by alwys specifying seq (the <inst>Expose documentation
                    says the default is seqByDir, but it seems to be the last seq used).
                    View Image improvements:
                    - Use a separate ds9 window for each camera.
                    - Re-open a ds9 window if necessary.
2005-09-26 ROwen    Added canPauseExp, canStopExp, canAbortExp attributes to ExpInfo.
                    If RO.DS9 fails, complain to the log window.
2007-05-22 ROwen    Added SPIcam.
2007-07-27 ROwen    Set min exposure time for SPIcam to 0.76 seconds.
2008-03-14 ROwen    Added information for TripleSpec.
                    Added instName and actor arguments to _InstInfo class.
2008-03-25 ROwen    Split actor into instActor and exposeActor in _InstInfo class.
                    Changed instrument name TripleSpec to TSpec.
2008-04-23 ROwen    Get expState from the cache (finally) but null out the times.
                    Modified expState so durations can be None or 0 for unknown (was just 0).
2008-04-29 ROwen    Fixed reporting of exceptions that contain unicode arguments.
2008-10-24 ROwen    Added information for Agile.
2008-11-10 ROwen    Added imSize, bin, window and overscan data to instInfo.
                    Added bin, window and overscan-related arguments to formatExpCmd.
                    Includes support for one or two-component bin factor.
2008-12-15 ROwen    Reduce minimum exposure time for Agile to 0.3 seconds
2009-01-28 ROwen    Changed canOverscan to defOverscan in instInfo.
2009-02-24 ROwen    Added playExposureEnds to instInfo and set it False for Agile.
2009-04-15 ROwen    Increased default Agile x overscan from 9 to 27.
2009-05-04 ROwen    Added maxNumExp to instInfo and set it to 99999 for Agile.
2009-05-06 ROwen    Modified to use Get Every preference instead of Auto Get.
2009-07-09 ROwen    Removed unused import of os (found by pychecker).
2010-09-20 ROwen    Added canPauseSequece to _InstInfo.
                    Added Stop button to Agile.
2010-09-21 ROwen    Changed canPause to canPauseExposure similarly for canStop and canAbort.
                    Added canStopSeq and renamed canPauseSequence to canPauseSeq.
2010-10-06 ROwen    NICFPS: set canStopExp false (as it should have been).
2011-07-20 ROwen    Added Shack-Hartmann.
2011-07-21 ROwen    Bug fix: the exposure model was using instInfo.name instead of instInfo.instActor
                    as prefixes for keywords from the <instInfo.instActor>Expose actor.
2011-07-25 ROwen    Eliminated minimum exposure time for Shack-Hartmann. Let the actor deal with it.
2011-07-27 ROwen    Added modelIter.
                    Removed unneeded import of HubModel.
                    Changed all classes into modern style classes.
2013-07-10 ROwen    Removed Shack-Hartmann.
2015-08-11 CSayres  Added Arctic
2015-09-22 ROwen    Renamed Arctic to ARCTIC
2015-10-01 ROwen    Reduced ARCTIC min exposure time from 0.25 sec to 0.1 sec
2016-04-19 ROwen    Remove GIFS info
"""
__all__ = ['getModel', "GuiderActorNameDict"]

import tkinter
import RO.Alg
import RO.Astro.ImageWindow
import RO.CnvUtil
import RO.DS9
import RO.KeyVariable
import RO.SeqUtil
import RO.StringUtil
import TUI.TUIModel
from . import FileGetter

class _InstInfo(object):
    """Exposure information for a camera

    Inputs:
    - instName: the instrument name (in the preferred case)
    - imSize: the size of the image (e.g. CCD) in unbinned pixels; a pair of ints
    - instActor: the instrument's actor (defaults to instName.lower())
    - min/maxExpTime: minimum and maximum exposure time (sec)
    - camNames: name of each camera (if more than one)
    - expTypes: types of exposures supported
    - canPauseExp: instrument can pause an exposure
    - canPauseSeq: <inst>Exposure actor can pause an exposure sequence
    - canStopExp: instrument can stop an exposure
    - canStopSeq: <inst>Exposure actor can stop an exposure sequence
    - canAbortExp: instrument can abort an exposure
      (note: there is intentionally no canAbortSeq; if you wait to finish an exposure then read it out)
    - numBin: number of axes of bin the user can supply as part of expose command (0, 1 or 2)
    - defBin: default bin factor; a sequence of numBin elements;
            if numBin = 1 then you may specify an integer, which is converted to a list of 1 int
            if None then defaults to a list the right number of 1s.
    - canWindow: can specify window as part of expose command
    - defOverscan: default overscan in x, y; None if cannot set overscan; ignored if canWindow False
    - playExposureEnds: play ExposureEnds sound when appropriate;
        set False if time is short between ending one exposure and beginning the next
    - canImage: if True then can take imaging data
    - guiderActor: actor name of guider, or None if none
    - centroidActor: actor to centroid and find stars on an image (must be None if if canImage is False)

    Also sets fields:
    - exposeActor = <instActor>Expose
    """
    def __init__(self,
        instName,
        imSize,
        instActor = None,
        minExpTime = 0.1,
        maxExpTime = 12 * 3600,
        maxNumExp = 9999,
        camNames = None,
        expTypes = ("object", "flat", "dark", "bias"),
        canPauseExp = True,
        canPauseSeq = True,
        canStopExp = True,
        canStopSeq = True,
        canAbortExp = True,
        numBin = 0,
        defBin = None,
        canWindow = False,
        defOverscan = None,
        playExposureEnds = True,
        canImage = False,
        guiderActor = None,
        centroidActor = None,
    ):
        self.instName = str(instName)
        if len(imSize) != 2:
            raise RuntimeError("imSize=%s must contain two ints" % (imSize,))
        self.imSize = [int(val) for val in imSize]
        if instActor is not None:
            self.instActor = str(instActor)
        else:
            self.instActor = instName.lower()
        self.exposeActor = "%sExpose" % (self.instActor,)
        self.minExpTime = float(minExpTime)
        self.maxExpTime = float(maxExpTime)
        self.maxNumExp = int(maxNumExp)
        if camNames is None:
            camNames = ("",)
        self.camNames = camNames
        self.expTypes = expTypes
        self.canPauseExp = bool(canPauseExp)
        self.canPauseSeq = bool(canPauseSeq)
        self.canStopExp = bool(canStopExp)
        self.canStopSeq = bool(canStopSeq)
        self.canAbortExp = bool(canAbortExp)
        self.numBin = int(numBin)
        if not (0 <= self.numBin <= 2):
            raise RuntimeError("numBin=%s not in range [0,2]" % (self.numBin,))
        if defBin is None:
            defBinList = [1]*self.numBin
        else:
            defBinList = [int(val) for val in RO.SeqUtil.asList(defBin)]
            if len(defBinList) != self.numBin:
                raise RuntimeError("defBin=%s should have %d elements" % (defBin, self.numBin,))
        self.defBin = defBinList
        self.canWindow = bool(canWindow)
        self.defOverscan = defOverscan
        if defOverscan is not None:
            try:
                assert len(defOverscan) == 2
                self.defOverscan = [int(val) for val in defOverscan]
            except Exception:
                raise RuntimeError("defOverscan=%r; must be None or a pair of integers" % (defOverscan,))
        self.playExposureEnds = bool(playExposureEnds)
        self.canImage = bool(canImage)
        self.guiderActor = guiderActor
        if centroidActor is not None and not self.canImage:
            raise RuntimeError("centroidActor must be None if instrument canImage false")
        self.centroidActor = centroidActor

    def getNumCameras(self):
        return len(self.camNames)


def _makeInstInfoDict():
    """Generate instInfo dictionary and exposure model dictionary

    Returns:
    * instInfoDict: a dictionary if instName.lower(): _InstInfo
    """
    _InstInfoList = (
        _InstInfo(
            instName = "agile",
            imSize = (1024, 1024),
            minExpTime = 0.3,
            maxNumExp = 99999,
            canPauseExp = False,
            canPauseSeq = False,
            canStopExp = False,
            numBin = 1,
            canWindow = True,
            defOverscan = (27, 0),
            playExposureEnds = False,
            canImage = True,
            centroidActor = "afocus",
        ),
        _InstInfo(
            instName = "DIS",
            imSize = (2048, 1028),
            minExpTime = 1,
            camNames = ("blue", "red"),
            canImage = True,
            guiderActor = "dcam",
        ),
        _InstInfo(
            instName = "Echelle",
            imSize = (2048, 2048),
            guiderActor = "ecam",
        ),
        _InstInfo(
            instName = "NICFPS",
            imSize = (1024, 1024),
            minExpTime = 0,
            expTypes = ("object", "flat", "dark"),
            canPauseExp = False,
            canStopExp = False,
            canAbortExp = False,
            canImage = True,
            centroidActor = "nfocus",
            guiderActor = "gcam",
        ),
        _InstInfo(
            instName = "SPIcam",
            minExpTime = 0.76,
            imSize = (2048, 2048),
            canImage = True,
            centroidActor = "sfocus",
            guiderActor = "gcam",
        ),
        _InstInfo(
            instName = "ARCTIC",
            minExpTime = 0.1,
            imSize = (4096, 4096),
            canImage = True,
            centroidActor = "sfocus",
            guiderActor = "gcam",
        ),
        _InstInfo(
            instName = "Kosmos",
            minExpTime = 0.5,
            imSize = (2048, 4096),
            canImage = True,
            guiderActor = "kcam",
        ),        
        _InstInfo(
            instName = "TSpec",
            imSize = (2048, 1024),
            minExpTime = 0.75,
            expTypes = ("object", "flat", "dark"),
            canPauseExp = False,
            canStopExp = False,
            canImage = False,
            guiderActor = "tcam",
        ),
    )

    instInfoDict = {}
    for instInfo in _InstInfoList:
        instInfoDict[instInfo.instName.lower()] = instInfo
    return instInfoDict

# dictionary of instName.lower(): _InstInfo
_InstInfoDict = _makeInstInfoDict()

# cache of instName: model; filled as needed
_modelDict = {}

GuiderActorNameDict = {
    "gcam": "NA2 Guider",
    "dcam": "DIS Slitviewer",
    "tcam": "TSpec Slitviewer",
    "kcam": "Kosmos Slitviewer"

}

class _BoolPrefVarCont(object):
    """Class to set a Tkinter.BooleanVar from a RO.Pref boolean preference variable.
    If the preference value changes, the variable changes, but not visa versa.
    The contained var can be used as the var in a Checkbutton
    """
    def __init__(self, pref):
        self.var = tkinter.BooleanVar()
        pref.addCallback(self._prefCallback, callNow=True)
    def _prefCallback(self, prefVal, pref=None):
        self.var.set(prefVal)
    def get(self):
        """Return the current var value as a bool"""
        return self.var.get()


class _IntPrefVarCont(object):
    """Class to set a Tkinter StringVar from a RO.Pref int preference variable.
    If the preference value changes, the variable changes, but not visa versa.
    The contained var can be used as the var in an entry widget
    (I'd use a Tkinter.IntVar if I could, but it's not compatible with RO.Wdg.IntEntry).
    """
    def __init__(self, pref):
        self.var = tkinter.StringVar()
        pref.addCallback(self._prefCallback, callNow=True)
    def _prefCallback(self, prefVal, pref=None):
        self.var.set(str(prefVal))
    def get(self):
        """Return the current var value as an int"""
        return int(self.var.get())


def getModel(instName):
    global _modelDict
    instNameLow = instName.lower()
    model = _modelDict.get(instNameLow)
    if model is None:
        model = Model(instName)
        _modelDict[instNameLow] = model
    return model


def modelIter():
    global _InstInfoDict
    for instInfo in _InstInfoDict.values():
        yield getModel(instInfo.instName)


class Model(object):
    def __init__(self, instName):
        self.instName = instName
        self.instInfo = _InstInfoDict[instName.lower()]
        self.actor = self.instInfo.exposeActor
        instActor = self.instInfo.instActor

        self.tuiModel = TUI.TUIModel.getModel()

        keyVarFact = RO.KeyVariable.KeyVarFactory(
            actor = self.actor,
            dispatcher = self.tuiModel.dispatcher,
            converters = str,
            allowRefresh = False,
        )

        self.exposeTxt = keyVarFact(
            keyword="exposeTxt",
            description="progress report for current sequence",
            allowRefresh = False,
        )

        self.expState = keyVarFact(
            keyword = instActor + "ExpState",
            converters = (str, str, str, RO.CnvUtil.asFloatOrNone, RO.CnvUtil.asFloatOrNone),
            description = """current exposure info:
            - cmdr (progID.username)
            - exposure state; one of: idle, flushing, integrating, paused,
                reading, processing, aborting, failing, done, aborted or failed.
            - start time (an ANSI-format UTC timestamp)
            - remaining time for this state (sec; 0 or None if short or unknown)
            - total time for this state (sec; 0 or None if short or unknown)

            Note: if the data is cached then remaining time and total time
            are changed to 0 to indicate that the values are unknown
            """,
            allowRefresh = False, # do not use an archived value
        )
        self.expState.addCallback(self._updExpState)

        self.files = keyVarFact(
            keyword = instActor + "Files",
            nval = 5 + self.instInfo.getNumCameras(),
            description = """file(s) just saved:
            - cmdr (progID.username)
            - host
            - common root directory
            - program and date subdirectory
            - user subdirectory
            - file name(s)

            This keyword is only output when a file is saved.
            It is not output as a result of status.

            The full file path is the concatenation of common root, program subdir, user subdir and file name.
            If a file in a multi-file instrument is not saved,
            the missing file name is omitted (but the comma remains).
            """,
            allowRefresh = False,
        )

        self.newFiles = keyVarFact(
            keyword = instActor + "NewFiles",
            nval = 5 + self.instInfo.getNumCameras(),
            description = """file(s) that will be saved at the end of the current exposure:
            - cmdr (progID.username)
            - host
            - common root directory
            - program and date subdirectory
            - user subdirectory
            - file name(s)

            The full file path is the concatenation of common root, program subdir, user subdir and file name.
            If a file in a multi-file instrument is not saved,
            the missing file name is omitted (but the comma remains).
            """,
            allowRefresh = False, # change to True if/when <inst>Expose always outputs it with status
        )

        self.nextPath = keyVarFact(
            keyword = instActor + "NextPath",
            nval = 5,
            description = """default file settings (used for the next exposure):
            - cmdr (progID.username)
            - user subdirectory
            - file name prefix
            - sequence number (with leading zeros)
            - file name suffix
            """,
            allowRefresh = True,
        )

        self.seqState = keyVarFact(
            keyword = instActor + "SeqState",
            converters = (str, str, RO.CnvUtil.asFloatOrNone, RO.CnvUtil.asInt, RO.CnvUtil.asInt, str),
            description = """current sequence info:
            - cmdr (progID.username)
            - exposure type
            - exposure duration
            - exposure number
            - number of exposures requested
            - sequence state; one of: running, paused, aborted, stopped, done or failed
            """,
            allowRefresh = True,
        )

        self.comment = keyVarFact(
            keyword = "comment",
            converters = str,
            description = "comment string",
            allowRefresh = False, # change to True if/when <inst>Expose always outputs it with status
        )

        if self.instInfo.numBin > 0:
            self.bin = keyVarFact(
                keyword = "bin",
                nval = self.instInfo.numBin,
                converters = int,
                description = {1: "bin factor (x=y)", 2: "x, y bin factor"}[self.instInfo.numBin],
                allowRefresh = True,
            )

        if self.instInfo.canWindow:
            self.window = keyVarFact(
                keyword = "window",
                nval = 4,
                converters = int,
                description = "window: LL x, y; UR x, y (inclusive, binned pixels)",
                allowRefresh = True,
            )

        if self.instInfo.defOverscan:
            self.overscan = keyVarFact(
                keyword = "overscan",
                nval = 2,
                converters = int,
                description = "x, y overscan (binned pixels)",
                allowRefresh = True,
            )

        # utility to convert between binned and unbinned windows
        self.imageWindow = RO.Astro.ImageWindow.ImageWindow(
            imSize = self.instInfo.imSize,
        )

        keyVarFact.setKeysRefreshCmd(getAllKeys=True)

        # entries for file numbering and auto ftp, including:
        # variables for items the user may toggle
        # pointers to prefs for items the user can only set via prefs
        # a pointer to the download widget
        getEveryPref = self.tuiModel.prefs.getPrefVar("Get Every")
        self.getEveryVarCont = _IntPrefVarCont(getEveryPref)
        viewImagePref = self.tuiModel.prefs.getPrefVar("View Image")
        self.viewImageVarCont = _BoolPrefVarCont(viewImagePref)

        self.getCollabPref = self.tuiModel.prefs.getPrefVar("Get Collab")
        self.ftpSaveToPref = self.tuiModel.prefs.getPrefVar("Save To")
        self.seqByFilePref = self.tuiModel.prefs.getPrefVar("Seq By File")

        self._getFiles = FileGetter.FileGetter(self)

    def formatExpCmd(self,
        expType = "object",
        expTime = None,
        cameras = None,
        fileName = "",
        numExp = 1,
        startNum = None,
        totNum = None,
        comment = None,
        bin = None,
        window = None,
        overscan = None,
    ):
        """Format an exposure command.
        Raise ValueError or TypeError for invalid inputs.
        """
        outStrList = []

        expType = expType.lower()
        if expType not in self.instInfo.expTypes:
            raise ValueError("unknown exposure type %r" % (expType,))
        outStrList.append(expType)

        if expType.lower() != "bias":
            if expTime is None:
                raise ValueError("exposure time required")
            outStrList.append("time=%.2f" % (expTime))

        if cameras is not None:
            camList = RO.SeqUtil.asSequence(cameras)
            for cam in camList:
                cam = cam.lower()
                if cam not in self.instInfo.camNames:
                    raise ValueError("unknown camera %r" % (cam,))
                outStrList.append(cam)

        outStrList.append("n=%d" % (numExp,))

        if not fileName:
            raise ValueError("file name required")
        outStrList.append("name=%s" % (RO.StringUtil.quoteStr(fileName),))

        if self.seqByFilePref.getValue():
            outStrList.append("seq=nextByFile")
        else:
            outStrList.append("seq=nextByDir")

        if startNum is not None:
            outStrList.append("startNum=%d" % (startNum,))

        if totNum is not None:
            outStrList.append("totNum=%d" % (totNum,))

        if bin:
            if self.instInfo.numBin < 1:
                raise ValueError("Cannot specify bin in %s expose command" % (self.instInfo.instName,))
            outStrList.append(formatValList("bin", bin, "%d", self.instInfo.numBin))

        if window:
            if not self.instInfo.canWindow:
                raise ValueError("Cannot specify window in %s expose command" % (self.instInfo.instName,))
            outStrList.append(formatValList("window", window, "%d", 4))

        if overscan:
            if not self.instInfo.defOverscan:
                raise ValueError("Cannot specify overscan in %s expose command" % (self.instInfo.instName,))
            outStrList.append(formatValList("overscan", overscan, "%d", 2))

        if comment is not None:
            outStrList.append("comment=%s" % (RO.StringUtil.quoteStr(comment),))

        return " ".join(outStrList)

    def _updExpState(self, expState, isCurrent, keyVar):
        """Set the durations to None (unknown) if data is from the cache"""
        if keyVar.isGenuine():
            return
        modValues = list(expState)
        modValues[3] = None
        modValues[4] = None
        keyVar._valueList = tuple(modValues)


def formatValList(name, valList, valFmt, numElts=None):
    #print "formatValList(name=%r, valList=%s, valFmt=%r, numElts=%s)" % (name, valList, valFmt, numElts)
    if numElts is not None and len(valList) != numElts:
        raise ValueError("%s=%s; needed %s values" % (name, valList, numElts,))
    valStr = ",".join([valFmt % (val,) for val in valList])
    return "%s=%s" % (name, valStr)


if __name__ == "__main__":
    print("Contains exposure models for these instruments:")
    for model in modelIter():
        print(model.instName)
