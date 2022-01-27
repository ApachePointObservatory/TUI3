#!/usr/bin/env python
"""An object that models the current state of ARCTIC.

History:
2015-07-31 CS       Created
2015-10-20 ROwen    Added filterState and switched to currFilter, cmdFilter.
2016-01-25 CS       Altered maxCoord to always return an even number (for 3x3 binning w/ quad)
2017-09-02 CS       Update for diffuser inclusion
"""
import RO.CnvUtil
import RO.Wdg
import RO.KeyVariable
import TUI.TUIModel

# reasonable time for fairly fast commands;
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
        self.actor = "arctic"
        self.dispatcher = tuiModel.dispatcher
        self.timelim = _TimeLim

        keyVarFact = RO.KeyVariable.KeyVarFactory(
            actor = self.actor,
            converters = str,
            nval = 1,
            dispatcher = self.dispatcher,
        )

        self.filterNames = keyVarFact(
            keyword="filterNames",
            nval = (1, None),
            description = "list of filter names",
        )

        self.filterID = keyVarFact(
            keyword = "filterID",
            converters = RO.CnvUtil.asInt,
            description = "filter wheel position",
        )

        self.currFilter = keyVarFact(
            keyword = "currFilter",
            converters = (RO.CnvUtil.asIntOrNone, str),
            nval = 2,
            description = "current filter ID (NaN if unknown) and name ('?' if unknown)",
        )

        self.cmdFilter = keyVarFact(
            keyword = "cmdFilter",
            converters = (RO.CnvUtil.asIntOrNone, str),
            nval = 2,
            description = "commanded filter ID (NaN if unknown) and name ('?' if unknown)",
        )

        self.filterState = keyVarFact(
            keyword = "filterState",
            converters = (str, RO.CnvUtil.asFloat, RO.CnvUtil.asFloat),
            nval = 3,
            description = """state of filter wheel:
            - state as a string
            - total estimated duration (sec) or 0 if unknown
            - estimated remaining time (sec), or 0 if unknown
            """,
        )

        self.ampNames = keyVarFact(
            keyword = "ampNames",
            nval = (1, None),
            description = "list of amp names",
        )

        self.ampName = keyVarFact(
            keyword = "ampName",
            description = "current amp",
        )

        self.readoutRateNames = keyVarFact(
            keyword = "readoutRateNames",
            nval = (1, None),
            description = "list of readoutRate names",
        )

        self.readoutRateName = keyVarFact(
            keyword = "readoutRateName",
            description = "current readoutRate",
        )

        self.diffuserPositions = keyVarFact(
            keyword = "diffuserPositions",
            nval = (1, None),
            description = "list of diffuser positions",
        )

        self.diffuserPosition = keyVarFact(
            keyword = "diffuserPosition",
            description = "current diffuser position",
        )

        self.diffuserRotations = keyVarFact(
            keyword = "rotateDiffuserChoices",
            nval = (1, None),
            description = "list of diffuser rotation toggles.",
        )

        self.diffuserRotation = keyVarFact(
            keyword = "rotateDiffuserChoice",
            description = "current diffuser rotation toggle.",
        )

        self.shutter = keyVarFact(
            keyword = "shutter",
            nval = 1,
            description = "Current shutter state",
        )

        keyVarFact.setKeysRefreshCmd()

        self.ccdState = keyVarFact(
            keyword = "ccdState",
            description = "ccd state",
        )

        self.ccdBin = keyVarFact(
            keyword = "ccdBin",
            nval = 2,
            converters = RO.CnvUtil.asIntOrNone,
            description = "ccd binning",
        )

        self.ccdWindow = keyVarFact(
            keyword = "loc_ccdWindow",
            nval = 4,
            converters = RO.CnvUtil.asIntOrNone,
            description = "ccd window, binned: minX, minY, maxX, maxY (inclusive)",
            isLocal = True,
        )

        self.ccdUBWindow = keyVarFact(
            keyword = "ccdUBWindow",
            nval = 4,
            converters = RO.CnvUtil.asIntOrNone,
            description = "ccd window, unbinned: minX, minY, maxX, maxY (inclusive)",
        )

        self.ccdOverscan = keyVarFact(
            keyword = "ccdOverscan",
            nval = 2,
            converters = RO.CnvUtil.asIntOrNone,
            description = "ccd overscan",
        )

        keyVarFact.setKeysRefreshCmd()

        # set up callbacks
        self.ccdBin.addCallback(self._updCCDWindow)
        self.ccdUBWindow.addCallback(self._updCCDWindow)


    def _updCCDWindow(self, *args, **kargs):
        """Updated ccdWindow.

        Called by two different keyVars, so ignores the argument data
        and reads the keyVars directly.
        """
        binFac, binCurrent = self.ccdBin.get()
        ubWindow, windowCurrent = self.ccdUBWindow.get()
        isCurrent = binCurrent and windowCurrent
        try:
            bWindow = self.bin(ubWindow, binFac)
        except TypeError:
            # occurs if None is present in list of values
            bWindow = [None] * 4
        self.ccdWindow.set(bWindow, isCurrent)

    def bin(self, unbinnedCoords, binFac):
        """Converts unbinned to binned coordinates.

        The output is constrained to be in range for the given bin factor
        (if a dimension does not divide evenly by the bin factor
        then some valid unbinned coords are out of range when binned).

        Inputs:
        - unbinnedCoords: 2 or 4 coords

        If any element of binnedCoords or binFac is None, all returned elements are None.
        """
        assert len(unbinnedCoords) in (2, 4), "unbinnedCoords must have 2 or 4 elements; unbinnedCoords = %r" % unbinnedCoords
        assert len(binFac) == 2, "binFac must have 2 elements; binFac = %r" % binFac

        if None in unbinnedCoords or None in binFac:
            return (None,)*len(unbinnedCoords)

        binXYXY = binFac * 2

        # compute value ignoring limits
        # Compute a binned width

        binnedCoords = [1 + ((unbinnedCoords[ind] - 1) // int(binXYXY[ind]))
            for ind in range(len(unbinnedCoords))]
        # apply limits

        minBinXYXY = self.minCoord(binFac)*2
        maxBinXYXY = self.maxCoord(binFac)*2
        binnedCoords = [min(max(binnedCoords[ind], minBinXYXY[ind]), maxBinXYXY[ind])
            for ind in range(len(binnedCoords))]
#       print "bin: converted %r bin %r to %r" % (unbinnedCoords, binFac, binnedCoords)
        return binnedCoords

    def unbin(self, binnedCoords, binFac):
        """Converts binned to unbinned coordinates.

        The output is constrained to be in range (but such constraint is only
        needed if the input was out of range).

        A binned coordinate can be be converted to multiple unbinned choices (if binFac > 1).
        The first two coords are converted to the smallest choice,
        the second two (if supplied) are converted to the largest choice.
        Thus 4 coordinates are treated as a window with LL, UR coordinates, inclusive.

        Inputs:
        - binnedCoords: 2 or 4 coords; see note above

        If any element of binnedCoords or binFac is None, all returned elements are None.
        """
        assert len(binnedCoords) in (2, 4), "binnedCoords must have 2 or 4 elements; binnedCoords = %r" % binnedCoords
        assert len(binFac) == 2, "binFac must have 2 elements; binFac = %r" % binFac

        if None in binnedCoords or None in binFac:
            return (None,)*len(binnedCoords)

        binXYXY = binFac * 2
        subadd = (1, 1, 0, 0)

        # compute value ignoring limits
        unbinnedCoords = [((binnedCoords[ind] - subadd[ind]) * binXYXY[ind]) + subadd[ind]
            for ind in range(len(binnedCoords))]

        # apply limits
        minUnbinXYXY = self.minCoord()*2
        maxUnbinXYXY = self.maxCoord()*2
        unbinnedCoords = [min(max(unbinnedCoords[ind], minUnbinXYXY[ind]), maxUnbinXYXY[ind])
            for ind in range(len(unbinnedCoords))]
#       print "unbin: converted %r bin %r to %r" % (binnedCoords, binFac, unbinnedCoords)
        return unbinnedCoords

    def maxCoord(self, binFac=(1,1)):
        """Returns the maximum binned CCD coordinate, given a bin factor.
        """
        # The value is even for both amplifiers, even if only using single readout,
        # just to keep the system more predictable. The result is that the full image size
        # is the same for 3x3 binning regardless of whether you read one amp or four,
        # and as a result you lose one row and one column when you read one amp.
        assert len(binFac) == 2, "binFac must have 2 elements; binFac = %r" % binFac
        return [(4096, 4096)[ind] // int(2 * binFac[ind]) * 2 for ind in range(2)]

    def minCoord(self, binFac=(1,1)):
        """Returns the minimum binned CCD coordinate, given a bin factor.
        """
        assert len(binFac) == 2, "binFac must have 2 elements; binFac = %r" % binFac
        return (1, 1)


if __name__ == "__main__":
    getModel()
