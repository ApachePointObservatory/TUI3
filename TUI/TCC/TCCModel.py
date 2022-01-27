#!/usr/bin/env python
"""An object that models the current state of the TCC.

It contains instance variables that are KeyVariables
or sets of KeyVariables. Most of these are directly associated
with status keywords and a few are ones that I generate.

Thus it is relatively easy to get the current value of a parameter
and it is trivial to register callbacks for when values change
or register ROWdg widgets to automatically display updating values.

2003-03-26 ROwen
2003-04-02 ROwen    Added axis limits and iimScale.
2003-04-04 ROwen    Added all offsets and axis limits.
2003-04-07 ROwen    Bug fix: iimScale was not being dispatched.
2003-04-14 ROwen    Removed unused imports.
2003-04-29 ROwen    Bug fix: RotExists was int, not bool;
    this caused failure in Python 2.3b1.
2003-05-08 ROwen    Modified to use RO.CnvUtil.
2003-05-28 ROwen    Added slewDuration and slewEnd;
                    changed coordSys and rotType to expand the short names
                    used by the TCC to the longer names used internally in TUI.
2003-06-09 ROwen    Modified to get the dispatcher from TUI.TUIModel.
2003-06-11 ROwen    Renamed coordSys -> objSys;
                    modified objSys to use RO.CoordSys constants instead of names;
                    made keyword Inst uppercase.
2003-10-30 ROwen    Added tccPos.
2003-12-03 ROwen    Added guidePrep, guideStart
2004-01-06 ROwen    Modified to use KeyVarFactory.
2004-08-11 ROwen    Modified to allow NaN for the axis status word
                    in ctrlStatusSet (this shows up as "None" as isCurrent=True).
                    Bug fix: was not refreshing rotator status in ctrlStatusSet;
                    modified to optionally refresh it (since it may be missing)
                    using new refreshOptional argument in RO.KeyVariable.KeyVarFactory.
2005-06-03 ROwen    Improved indentation uniformity.
2006-02-21 ROwen    Modified to use new correctly spelled keyword SlewSuperseded.
2006-03-06 ROwen    Added axisCmdState (which supersedes tccStatus).
                    Modified to set rotExists from axisCmdState (instead of tccStatus)
                    and to only set it when the state (or isCurrent) changes.
2007-01-29 ROwen    Added instPos, gimCtr, gimLim, gimScale.
2007-07-25 ROwen    Added tai and utcMinusTAI.
2007-09-28 ROwen    Modified _cnvRotType to raise ValueError instead of KeyError for bad values
                    (because keyword conversion functions should always do that).
                    Modified _cnvObjSys to raise ValueError instead of returning None for bad values.
2008-02-01 ROwen    Fixed rotType; it was always set to None due to an error in _cnvRotType.
2008-03-25 ROwen    Removed obsolete gcFocus; get gmech focus from the gmech actor.
2010-03-04 ROwen    Added moveItems.
2010-06-28 ROwen    Removed unused _RotTypeDict (thanks to pychecker).
2010-09-24 ROwen    Added <mir> keywords.
2011-07-14 ROwen    Added ipConfig, gcFocus, gcFocusLim, gcNomFocus, instFocus, rotInstXYAng and rotOffsetScale;
                    all of these except ipConfig and gcFocus are new in TCC 2.15.0.
2014-04-23 ROwen    Added gProbeDict
2014-07-21 ROwen    Added <mir>DesEncMount and <mir>EncMount.
"""
from collections import OrderedDict

import RO.CnvUtil
import RO.CoordSys
import RO.KeyVariable
import TUI.TUIModel

_theModel = None

def getModel():
    global _theModel
    if _theModel ==  None:
        _theModel = _Model()
    return _theModel

def _cnvObjSys(tccName):
    """Converts a coordinate system name from the names used in the TCC keyword ObjSys
    to the RO.CoordSys constants used locally. Case-insensitive.

    Raise ValueError if tccName not a valid TCC ObjSys.
    """
    #print "_cnvObjSys(%r)" % tccName
    try:
        tuiName = dict(
            icrs = 'ICRS',
            fk5 = 'FK5',
            fk4 = 'FK4',
            gal = 'Galactic',
            geo = 'Geocentric',
            topo = 'Topocentric',
            obs = 'Observed',
            phys = 'Physical',
            mount = 'Mount',
            none = 'None',
        )[tccName.lower()]
    except KeyError:
        raise ValueError()
    return RO.CoordSys.getSysConst(tuiName)

def _cnvRotType(tccName):
    """Converts a rotation type name from the names used in the TCC keyword RotType
    to the (longer) names used locally. Case-insensitive.

    Raise ValueError if tccName not a valid TCC RotType.
    """
    #print "_cnvRotType(%r)" % (tccName,)
    try:
        return dict(
            obj = 'Object',
            horiz = 'Horizon',
            phys = 'Physical',
            mount = 'Mount',
            none ='None',
        )[tccName.lower()]
    except KeyError:
        raise ValueError()

class _Model (object):
    def __init__(self,
    **kargs):
        self.actor = "tcc"
        self.dispatcher = TUI.TUIModel.getModel().dispatcher
        keyVarFact = RO.KeyVariable.KeyVarFactory(
            actor = self.actor,
            converters = str,
            dispatcher = self.dispatcher,
        )
        pvtVarFact = RO.KeyVariable.KeyVarFactory(
            keyVarType = RO.KeyVariable.PVTKeyVar,
            actor = self.actor,
            naxes = 1,
            dispatcher = self.dispatcher,
        )

        self.axisNames = ("Az", "Alt", "Rot")

        # user-specified values

        self.objName = keyVarFact(
            keyword = "ObjName",
            nval = 1,
            converters = str,
            description = "name of current target",
        )

        self.objSys = keyVarFact(
            keyword = "ObjSys",
            converters = (_cnvObjSys, RO.CnvUtil.asFloatOrNone),
            description = "Coordinate system name, date",
            defValues = (RO.CoordSys.getSysConst(""), None),
        )

        self.netObjPos = pvtVarFact(
            keyword = "ObjNetPos",
            naxes = 2,
            description = "Net object position, including user and arc offsets",
        )

        self.objOff = pvtVarFact(
            keyword = "ObjOff",
            naxes = 2,
            description = "Object offset (user coords)",
        )

        self.objArcOff = pvtVarFact(
            keyword = "ObjArcOff",
            naxes = 2,
            description = "Object arc offset (user coords)",
        )

        self.rotType = keyVarFact(
            keyword = "RotType",
            converters = _cnvRotType,
            description = "Type of rotation",
        )

        self.rotPos = pvtVarFact(
            keyword = "RotPos",
            naxes = 1,
            description = "Rotation angle",
        )

        self.rotExists = keyVarFact(
            keyword = "RotExists",
            converters = RO.CnvUtil.asBool,
            description = "Type of rotation",
            isLocal = True,
        )

        self.boresight = pvtVarFact(
            keyword = "Boresight",
            naxes = 2,
            description = "Boresight position (inst x,y)",
        )

        self.calibOff = pvtVarFact(
            keyword = "CalibOff",
            naxes = 3,
            description = "Calibration offset (az, alt, rot)",
        )

        self.guideOff = pvtVarFact(
            keyword = "GuideOff",
            naxes = 3,
            description = "Guiding offset (az, alt, rot)",
        )

        # time

        self.tai = keyVarFact(
            keyword = "TAI",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            refreshCmd = "show time", # can't use archived data!
            description = "TAI time (MJD sec)",
        )

        self.utcMinusTAI = keyVarFact(
            keyword = "UTC_TAI",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "UTC time - TAI time (sec)",
        )

        # slew info; do not try to refresh these keywords

        self.moveItems = keyVarFact(
            keyword = "MoveItems",
            nval = 1,
            converters = str,
            description = """Indicates which user-set position attributes have been changed for a move.

This keyword always appears with Moved or SlewBeg, and never appears any other time.
The value is a string containing the following characters, each of which is either
"Y" (yes, this item changed) or "N" (no, this item did not change):
0   object name
1   any of object position, coordinate system, epoch, proper motion, etc., but NOT offset (see below)
2   object magnitude
3   object offset
4   arc offset (e.g. for drift-scanning)
5   boresight position
6   rotator angle or type of rotation
7   guide offset
8   calibration offset
""",
            allowRefresh = False,
        )

        self.slewDuration = keyVarFact(
            keyword="SlewDuration",
            converters=RO.CnvUtil.asFloatOrNone,
            description = "Duration of the slew that is beginning (sec)",
            allowRefresh = False,
        )

        self.slewEnd = keyVarFact(
            keyword = "SlewEnd",
            nval = 0,
            description = "Slew ended",
            allowRefresh = False,
        )

        self.slewSuperseded = keyVarFact(
            keyword = "SlewSuperseded",
            nval = 0,
            description = "Slew superseded",
            allowRefresh = False,
        )

        # computed information about the object

        self.objInstAng = pvtVarFact(
            keyword = "ObjInstAng",
            naxes = 1,
            description = "angle from inst x to obj user axis 1 (e.g. RA)",
        )

        self.spiderInstAng = pvtVarFact(
            keyword = "SpiderInstAng",
            naxes = 1,
            description = "angle from inst x to dir. of increasing az",
        )

        keyVarFact.setKeysRefreshCmd()

        # information about the axes

        self.tccStatus = keyVarFact(
            keyword = "TCCStatus",
            nval = 2,
            converters = str,
            description = "What the TCC thinks the axes are doing",
        )

        self.axisCmdState = keyVarFact(
            keyword = "AxisCmdState",
            nval = 3,
            converters = str,
            description = "What the TCC has told the azimuth, altitude and rotator to do",
        )

        self.axisErrCode = keyVarFact(
            keyword = "AxisErrCode",
            nval = 3,
            converters = RO.CnvUtil.StrCnv(subsDict = {"OK":""}),
            description = "Why the TCC is not moving azimuth, altitude and/or the rotator",
        )

        self.tccPos = keyVarFact(
            keyword = "TCCPos",
            nval = 3,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Target position of azimuth, altitude and rotator (limited accuracy)",
        )

        self.axePos = keyVarFact(
            keyword = "AxePos",
            nval = 3,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Actual position of azimuth, altitude and rotator (limited accuracy)",
        )

        self.azLim = keyVarFact(
            keyword = "AzLim",
            nval = 5,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Azimuth limits: min pos, max pos, vel, accel, jerk",
        )

        self.altLim = keyVarFact(
            keyword = "AltLim",
            nval = 5,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Altitude limits: min pos, max pos, vel, accel, jerk",
        )

        self.rotLim = keyVarFact(
            keyword = "RotLim",
            nval = 5,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Rotator limits: min pos, max pos, vel, accel, jerk",
        )

        self.rotOffsetScale = keyVarFact(
            keyword = "RotOffsetScale",
            nval = 2,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Rotator offset, scale: mount position = offset + (physical position * scale).",
        )

        # a set of controller status variables for each axis;
        # the entry for each axis consists of:
        # current position, velocity, time, status word
        #
        # the rotator does not have a refresh command because it may not exist
        self.ctrlStatusSet = [
            keyVarFact(
                keyword = "%sStat" % axisName,
                nval = 4,
                converters = (RO.CnvUtil.asFloatOrNone, RO.CnvUtil.asFloatOrNone,
                    RO.CnvUtil.asFloatOrNone, RO.CnvUtil.asIntOrNone),
                description = "%s controller status word" % axisName,
                refreshOptional = (axisName == self.axisNames[-1]),
            ) for axisName in self.axisNames
        ]

        # instrument data

        self.instName = keyVarFact(
            keyword = "Inst",
            converters = str,
            description = "Name of current instrument",
        )

        self.instPos = keyVarFact(
            keyword = "InstPos",
            converters = str,
            description = "Name of current instrument position",
        )

        self.ipConfig = keyVarFact(
            keyword = "IPConfig",
            converters = str,
            description = """Instrument-position configuration, e.g. is an instrument rotator available?

str contains the following elements, each of which is either "T" (true) or "N" (false):

instrument rotator is available
guide camera is available
guider mechanical controller is available
""",
        )
        self.ipConfig.addIndexedCallback(self._updRotExists)

        self.instFocus = keyVarFact(
            keyword = "InstFocus",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Secondary mirror focus offset due to instrument (um)",
        )

        self.iimCtr = keyVarFact(
            keyword = "IImCtr",
            nval = 2,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Center of current instrument (unbinned pixels)",
        )

        self.iimLim = keyVarFact(
            keyword = "IImLim",
            nval = 4,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Edges of current instrument (min x, min y, max x, max y) (unbinned pixels)",
        )

        self.iimScale = keyVarFact(
            keyword = "IImScale",
            nval = 2,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Scale of current instrument (unbinned pixels/deg)",
        )

        self.rotInstXYAng = keyVarFact(
            keyword = "RotInstXYAng",
            nval = 3,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Position of the center of the instrument rotator in instrument coordinate frame (x, y deg) " +
                "and angle of instrument rotator x axis in instrument coordinate frame (deg).",
        )

        # guider data

        self.gimCtr = keyVarFact(
            keyword = "GImCtr",
            nval = 2,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Center of current guider (unbinned pixels)",
        )

        self.gimLim = keyVarFact(
            keyword = "GImLim",
            nval = 4,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Edges of current guider (min x, min y, max x, max y) (unbinned pixels)",
        )

        self.gimScale = keyVarFact(
            keyword = "GImScale",
            nval = 2,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Scale of current guider (unbinned pixels/deg)",
        )

        self.gcFocus = keyVarFact(
            keyword = "GCFocus",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "User-specified focus offset for guide camera (um).",
        )

        self.gcFocusLim = keyVarFact(
            keyword = "GCFocusLim",
            nval = 2,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Limits of travel for guide camera focus actuator (um)",
        )

        self.gcNomFocus = keyVarFact(
            keyword = "GCNomFocus",
            nval = 1,
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Nominal position for guide camera focus actuator (um).",
        )

        self.ptErrProbe = keyVarFact(
            keyword = "PtErrProbe",
            nval = 1,
            converters = RO.CnvUtil.asIntOrNone,
            description = "Guide probe to use for pointing error data collection; 0 if none.",
        )

        self.gProbeInfo = keyVarFact(
            keyword = "GProbeInfo",
            converters = (
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asBool,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            description = """Information about one guide probe:
            - guide probe number (1...N)
            - exists?
            - x center (pixels)
            - y center (pixels)
            - min x (pixels)
            - min y (pixels)
            - max x (pixels)
            - max y (pixels)
            - x position of center of guide probe w.r.t. rotator (deg)
            - y position of center of guide probe w.r.t. rotator (deg)
            - angle from probe image x to rotator x (deg)
            """,
            allowRefresh = False,
        )
        self.gProbeDict = OrderedDict() # dict of guide probe number: GuideProbe object; based on GProbeInfo keyword
        self.gProbeInfo.addCallback(self._updGProbeDict)

        # miscellaneous

        self.ptCorr = keyVarFact(
            keyword = "PtCorr",
            converters = (
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            description = """Measured pointing error in a form suitable for guiding
            (thus, relative to current guide and calibration offsets).
            All values are in the pointing frame, which is the rotator frame rotated such that x = az
            - az pointing correction on the sky (deg)
            - alt pointing correction on the sky (deg)
            - x position in pointing frame (deg)
            - y position in pointing frame (deg)
            """,
            allowRefresh = False,
        )

        self.ptData = keyVarFact(
            keyword = "PtData",
            converters = (
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            description = """Measured pointing error in a form suitable for pointing model data
            - az desired physical position (deg)
            - alt desired physical position (deg)
            - az current mount position (deg)
            - alt current mount position (deg)
            - rot physical angle (deg)
            """,
            allowRefresh = False,
        )

        self.ptRefStar = keyVarFact(
            keyword = "PtRefStar",
            converters = (
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
                str,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            description = """Information about a pointing reference star:
            - equatorial position (deg)
            - polar position (deg)
            - parallax (arcsec)
            - equatorial proper motion (dEquatAng/dt as arcsec/year)
            - polar proper motion (arcsec/year)
            - radial velocity (km/sec, positive receding)
            - coordinate system name
            - coordinate system date
            - magnitude
            """,
            allowRefresh = False,
        )

        self.secFocus = keyVarFact(
            keyword = "SecFocus",
            converters = RO.CnvUtil.asFloatOrNone,
            description = "User-defined focus offset",
        )

        # mirrors

        self.secActMount = keyVarFact(
            keyword = "SecActMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Actual mount position",
        )

        self.secCmdMount = keyVarFact(
            keyword = "SecCmdMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Commanded mount position",
        )

        self.secDesOrient = keyVarFact(
            keyword = "SecDesOrient",
            nval = (5,6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Desired orientation (piston, x_tilt, y_tilt, x_trans, y_trans)",
        )

        self.secOrient = keyVarFact(
            keyword = "SecOrient",
            nval = (5,6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Actual orientation (piston, x_tilt, y_tilt, x_trans, y_trans)",
        )

        self.secOrientAge = keyVarFact(
            keyword = "SecOrientAge",
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Age of most recent computation of desired orientation, in sec."
        )

        self.secDesEncMount = keyVarFact(
            keyword = "SecDesEncMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Measured encoder length (actuator microsteps); " + \
                "for actuators without an encoder, this will be commanded mount",
        )

        self.secEncMount = keyVarFact(
            keyword = "SecEncMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Desired encoder length based on desired orientation (actuator microsteps); " + \
                "for actuators without an encoder, this will be commanded mount",
        )

        self.secState = keyVarFact(
            keyword = "SecState",
            converters = (
                str,
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            description = """Mirror controller state:
                - state string, such as: "Done", "Homing", "Moving" or "Failed",
                - iteration
                - max iterations
                - remaining duration (sec)
                - total duration (sec)
                """,
        )

        self.secStatus = keyVarFact(
            keyword = "SecStatus",
            nval = (1, 6),
            converters = RO.CnvUtil.asIntOrNone,
            description = "Status reported by each actuator."
        )


        self.tertActMount = keyVarFact(
            keyword = "TertActMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Actual mount position",
        )

        self.tertCmdMount = keyVarFact(
            keyword = "TertCmdMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Commanded mount position",
        )

        self.tertDesOrient = keyVarFact(
            keyword = "TertDesOrient",
            nval = (5,6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Desired orientation (piston, x_tilt, y_tilt, x_trans, y_trans)",
        )

        self.tertOrient = keyVarFact(
            keyword = "TertOrient",
            nval = (5, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Actual orientation (piston, x_tilt, y_tilt, x_trans, y_trans)",
        )

        self.tertOrientAge = keyVarFact(
            keyword = "TertOrientAge",
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Age of most recent computation of desired orientation, in sec."
        )

        self.tertDesEncMount = keyVarFact(
            keyword = "TertDesEncMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Desired encoder length based on desired orientation (actuator microsteps); " + \
                "for actuators without an encoder, this will be commanded mount",
        )

        self.tertEncMount = keyVarFact(
            keyword = "TertEncMount",
            nval = (1, 6),
            converters = RO.CnvUtil.asFloatOrNone,
            description = "Measured encoder length (actuator microsteps); " + \
                "for actuators without an encoder, this will be commanded mount",
        )

        self.tertState = keyVarFact(
            keyword = "TertState",
            converters = (
                str,
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asIntOrNone,
                RO.CnvUtil.asFloatOrNone,
                RO.CnvUtil.asFloatOrNone,
            ),
            description = """Mirror controller state:
                - state string, such as: "Done", "Homing", "Moving" or "Failed",
                - iteration
                - max iterations
                - remaining duration (sec)
                - total duration (sec)
                """,
        )

        self.tertStatus = keyVarFact(
            keyword = "TertStatus",
            nval = (1, 6),
            converters = RO.CnvUtil.asIntOrNone,
            description = "Status reported by each actuator."
        )

        # guiding state; do not try to refresh

        self.guidePrep = keyVarFact(
            keyword = "GuidePrep",
            nval = 0,
            description = "Guiding is preparing to start",
            allowRefresh = False,
        )

        self.guideStart = keyVarFact(
            keyword = "GuideStart",
            nval = 0,
            description = "Guiding begins",
            allowRefresh = False,
        )

        keyVarFact.setKeysRefreshCmd()
        pvtVarFact.setKeysRefreshCmd()

    def _updRotExists(self, ipConfig, isCurrent, **kargs):
        """Call when the TCC outputs ipConfig and use to set self.rotExists
        """
        if not ipConfig:
            return
        hasRotChar = ipConfig[0]
        rotExists = (hasRotChar.lower() == "t")
        if (rotExists, isCurrent) != self.rotExists.getInd(0):
            self.rotExists.set((rotExists,), isCurrent)
        #print "TCCModel._updRotExists: rotExists=%s, isCurrent=%s" % tuple(self.rotExists.getInd(0))

    def _updGProbeDict(self, valueList, isCurrent, **kargs):
        """Call when the TCC outputs gProbeInfo and use to update self.gProbeDict
        """
        if valueList[0] is None:
            return
        guideProbe = GuideProbe(valueList)
        if guideProbe.number == 1:
            self.gProbeDict = OrderedDict()
        self.gProbeDict[guideProbe.number] = guideProbe

class GuideProbe(object):
    """Information about one guide probe
    """
    def __init__(self, valueList):
        self.number = valueList[0]
        self.exists = valueList[1]
        self.ctrXY = (valueList[2], valueList[3])
        self.minXY = (valueList[4], valueList[5])
        self.maxXY = (valueList[6], valueList[7])
        self.gp_rot_xy = (valueList[8], valueList[9])
        self.rot_gim_ang = valueList[10]

if __name__ ==  "__main__":
    # confirm compilation
    model = getModel()
