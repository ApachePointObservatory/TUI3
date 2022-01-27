#!/usr/bin/env python
"""An object that models the current state of Agile.

It contains instance variables that are KeyVariables
or sets of KeyVariables. Most of these are directly associated
with status keywords and a few are ones that I generate.

Thus it is relatively easy to get the current value of a parameter
and it is trivial to register callbacks for when values change
or register ROWdg widgets to automatically display updating values.

Note: expStatus is omitted because agileExpose outputs similar information
that is picked up by the exposure model.

History:
2008-11-10 ROwen    preliminary; does not include support for the filterwheel
2009-04-17 ROwen    Added many new keywords.
2009-06-24 ROwen    Added filter keywords.
"""
__all__ = ["getModel"]
import RO.CnvUtil
import RO.Wdg
import RO.KeyVariable
import TUI.TUIModel

# reasonable time for fairly fast commands
_TimeLim = 80

_theModel = None

def getModel():
    global _theModel
    if _theModel is None:
        _theModel = _Model()
    return _theModel
        
class _Model (object):
    def __init__(self,
    **kargs):
        tuiModel = TUI.TUIModel.getModel()
        self.actor = "agile"
        self.dispatcher = tuiModel.dispatcher
        self.timelim = _TimeLim
        self.arcsecPerPixel = 0.273

        keyVarFact = RO.KeyVariable.KeyVarFactory(
            actor = self.actor,
            converters = str,
            nval = 1,
            dispatcher = self.dispatcher,
        )
        
        # Filter wheel and filter slide
        # make sure fwNames comes before currFilter
        
        self.fwConnState = keyVarFact(
            keyword = "fwConnState",
            nval = 2,
            description = """Filter wheel connection state:
            - state: one of Connected, Disconnected, Connecting, Disconnecting
            - description: explanation for state (if any)
            """,
        )

        self.fwConfigPath  = keyVarFact(
            keyword = "fSlideConfig",
            converters = (str, RO.CnvUtil.asFloatOrNone),
            nval = 2,
            description = "Filter slide configuration: filter name, focus offset (um)",
        )
        
        self.fwConfigPath  = keyVarFact(
            keyword = "fwConfigPath",
            description = "Path of filter wheel config file",
        )
        
        self.fwNames = keyVarFact(
            keyword = "fwNames",
            nval = [1,None],
            description = "Name of filter in each filter wheel slot; name is ? if unknown",
        )

        self.fwMoveDuration  = keyVarFact(
            keyword = "fwMoveDuration",
            converters = RO.CnvUtil.asInt,
            description = "Expected time to completion of filter move (sec)",
            allowRefresh = False,
        )

        self.fwOffsets = keyVarFact(
            keyword = "fwOffsets",
            converters = RO.CnvUtil.asFloatOrNone,
            nval = [1,None],
            description = "Focus offset of filter in each filter wheel slot; offset is NaN if unknown",
        )

        self.fwSlotMinMax = keyVarFact(
            keyword = "fwSlotMinMax",
            converters = RO.CnvUtil.asIntOrNone,
            nval = 2,
            description = "Minimum and maximum filterwheel slot number",
        )
        
        self.fwStatus  = keyVarFact(
            keyword = "fwStatus",
            converters = (
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            nval = 4,
            description = """Filter wheel status:
* currSlot: current slot
* desSlot: desired slot
* statusWord: status word as hex constant (0x...)
* estRemTime: estimated remaining time for current command (sec)
""",
        )

        self.currFilter = keyVarFact(
            keyword = "currFilter",
            converters = (
                RO.CnvUtil.asIntOrNone,
                str,
                RO.CnvUtil.BoolOrNoneFromStr(trueStrs="In", falseStrs="Out", badStrs="?"),
                str,
                RO.CnvUtil.asFloatOrNone,
            ),
            nval=5,
            description = """Information about current filter:
* slotNum: filter wheel slot number
* slotName: name of filter in filterwheel slot
* slide position: one of In/Out/?
* slide name: name of filter in filter slide if slide is In, else ""
* focusOffset: focus offset in um
""",
        )

        # Detector
        
        self.detSizeConst = (1024, 1024)
        
        self.bin = keyVarFact(
            keyword="bin",
            nval = 1,
            converters=RO.CnvUtil.asIntOrNone,
            description="bin factor (x=y)",
        )
        
        self.extSync = keyVarFact(
            keyword="extSync",
            nval = 1,
            converters=RO.CnvUtil.asBoolOrNone,
            description="use external sync for accurate timing",
        )
        
        self.gain = keyVarFact(
            keyword="gain",
            nval = 1,
            description="amplifier gain; one of low, med or high",
        )

        self.overscan = keyVarFact(
            keyword="overscan",
            nval = 2,
            converters=RO.CnvUtil.asIntOrNone,
            description="overscan: x, y (binned pixels)",
        )
        
        self.readRate = keyVarFact(
            keyword="readRate",
            nval = 1,
            description="pixel readout rate; one of slow or fast",
        )
        
        self.window = keyVarFact(
            keyword="window",
            nval = 4,
            converters=RO.CnvUtil.asIntOrNone,
            description="window (subframe): minX, minY, maxX, maxY (binned pixels; inclusive)",
        )
        
        # Exposure Metadata
        
        self.numCircBufImages = keyVarFact(
            keyword = "numCircBufImages",
            nval = 2,
            converters = RO.CnvUtil.asIntOrNone,
            description = "Number of images in the circular buffer, maximum allowed",
        )
        
        self.readoutTime = keyVarFact(
            keyword = "readoutTime",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Time to read out an exposure (sec)",
        )
        
        # Environment
        
        self.cameraConnState = keyVarFact(
            keyword = "cameraConnState",
            nval = 2,
            description = """Camera connection state:
            - state: one of Connected, Disconnected, Connecting, Disconnecting
            - description: explanation for state (if any)
            """,
        )

        self.ccdTemp = keyVarFact(
            keyword = "ccdTemp",
            nval = 2,
            converters = (RO.CnvUtil.asFloatOrNone, str),
            description = "CCD temperature (C) and state summary",
        )
        
        self.ccdSetTemp = keyVarFact(
            keyword = "ccdSetTemp",
            nval = 2,
            converters = (RO.CnvUtil.asFloatOrNone, str),
            description = "CCD temperature setpoint (C) and state summary",
        )
        
        self.ccdTempLimits = keyVarFact(
            keyword = "ccdTempLimits",
            nval = 4,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "CCD temperature error limit: low, high, veryLow, veryHigh",
        )
        
        self.gpsSynced = keyVarFact(
            keyword = "gpsSynced",
            nval = 1,
            converters = RO.CnvUtil.asBoolOrNone,
            description = "Sync pulse clock card synced to GPS clock?",
        )
        
        self.ntpStatus = keyVarFact(
            keyword = "ntpStatus",
            nval = 3,
            converters = (RO.CnvUtil.asBoolOrNone, str, RO.CnvUtil.asIntOrNone),
            description = """State of NTP time synchronization:
            - ntp client running
            - ntp server name (abbreviated)
            - npt server stratum
            """,
        )
        
        # Parameters
        
        self.biasSecGap = keyVarFact(
            keyword = "biasSecGap",
            nval = 1,
            converters = RO.CnvUtil.asIntOrNone,
            description = "Unbinned pixels in overscan to skip before bias section",
        )
        
        self.defBin = keyVarFact(
            keyword = "defBin",
            nval = 1,
            converters = RO.CnvUtil.asIntOrNone,
            description = "Default bin factor",
        )
        
        self.defGain = keyVarFact(
            keyword = "defGain",
            nval = 1,
            description = "Default gain",
        )
        
        self.defReadRate = keyVarFact(
            keyword = "defReadRate",
            nval = 1,
            description = "Default read rate",
        )
        
        self.defExtSync = keyVarFact(
            keyword = "defExtSync",
            nval = 1,
            converters = RO.CnvUtil.asBoolOrNone,
            description = "Default for use external sync for accurate timing",
        )
        
        self.maxOverscan = keyVarFact(
            keyword = "maxOverscan",
            nval = 1,
            converters = RO.CnvUtil.asIntOrNone,
            description = "Maximum overscan (in unbinned pixels)",
        )
        
        self.minExpTime = keyVarFact(
            keyword = "minExpTime",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Minimum exposure time (sec)",
        )
        
        self.minExpOverheadTime = keyVarFact(
            keyword = "minExpOverheadTime",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Minimum time (sec) by which exposure time must exceed readout time",
        )
        
        keyVarFact.setKeysRefreshCmd()


if __name__ == "__main__":
    getModel()

