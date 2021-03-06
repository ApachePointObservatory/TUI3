#!/usr/bin/env python

"""Guiding support

To do:
- Set defRadMult from telescope model on first connection
  (and update when new values come in, if it makes sense to do so).
- Think about a fix for the various params when an image hasn't been
  downloaded yet -- what value to show during that process?

- Add a notation to non-guide images that are shown while guiding.
- Add snap points for dragging along slit -- a big job
- Work with Craig to handle "expired" images better.
  These are images that can no longer be used for guiding
  because the telescope has moved.


History:
2005-02-10 ROwen    alpha version; lots of work to do
2005-02-22 ROwen    Added drag to centroid. Modified for GryImageDispWdg 2005-02-22.
2005-02-23 ROwen    Added exposure time; first cut at setting exp time and thresh when a new image comes in.
2005-03-28 ROwen    Modified for improved files and star keywords.
2005-03-31 ROwen    Implemented hub commands. Added display of current image name.
2005-04-11 ROwen    Modified for GCamModel->GuideModel
2005-04-12 ROwen    Added display of data about selected star.
                    Improved to run in normal mode by default and local mode during tests.
2005-04-13 ROwen    Added Stop Guiding and Guide On Boresight.
                    Bug fix: mis-handled star data when multiple images used the same (cmdr,cmdID).
2005-04-15 ROwen    Modified to set exposure time and bin factor from the fits image header.
                    Modified to send exposure time and bin factor in commands that expose.
                    Bug fix: displayed new annotations on the wrong image while the new image was downloading.
2005-04-18 ROwen    Modified to only download guide images if this widget is visible.
                    Modified to delete images from disk when they fall off the history list
                    or when the application exits (but not in local test mode).
                    Initial default exposure time and bin factor are now set from the model.
                    Modified to use updated test code.
2005-04-21 ROwen    Added control-click to center on a point and removed the center Button.
                    Most errors now write to the status bar (imageRoot unknown is still an exception).
2005-04-26 ROwen    Added preliminary history navigation; it needs some cleanup.
                    Added attribute "deviceSpecificFrame" for device-specific controls.
2005-04-27 ROwen    Finished logic for history controls.
                    Finished error handling in BasicImObj.
2005-05-13 ROwen    Added preliminary support for manual guiding.
                    Re-added the Center button.
                    Added references to html help.
                    Mod. to pack the widgets instead of gridding them.
                    Added _DebugMem flag and commented out the remaining
                    non-flag-protected diagnostic print statement.
2005-05-20 ROwen    Bug fix: was not setting ImObj.defThresh on creation.
                    But fix: set ImObj.currThresh to None instead of default if curr thresh unknown.
                    Bug fix: layout was messed up by going to the packer so reverted to gridder.
                    (The space for multiple widgets with expand=True is always shared
                    even if some of them only grow in one direction. Truly hideous!)
                    Bug fix: the history controls were always disabled.
2005-05-23 ROwen    Mod. to overwrite image files if new ones come in with the same name;
                    this simplifies debugging and corrects bugs associated with the old way
                    (the new image's ImObj would replace the old one, so the old one
                    was never accessible and never deleted).
                    Bug fix: typo in code that handled displaying unavailable images.
2005-05-26 ROwen    Cleaned up button enable/disable.
                    Added doCmd method to centralize command execution.
2005-06-09 ROwen    Added more _DebugMem output.
                    Apparently fixed a bug that prevented file delete for too-old files.
2005-06-10 ROwen    Modified for noStarsFound->noGuideStar in guide model.
                    Also changed the no stars message to "Star Not Found".
2005-06-13 ROwen    Bug fix: one of the delete delete messages was mis-formatted.
                    Added more memory tracking code.
                    Modified test code to download images from APO.
2005-06-15 ROwen    Added Choose... button to open any fits file.
                    Modified so displayed image is always in history list;
                    also if there is a gap then the history buttons show it.
2005-06-16 ROwen    Changed to not use a command status bar for manual guiding.
                    Modified updGuideState to use new KeyVar getSeverity method.
                    Modified to only import GuideTest if in test mode.
                    Bug fix: isGuiding usually returned False even if true.
                    Bug fix: dragStar used as method name and attribute (found by pychecker).
2005-06-17 ROwen    Bug fix: mis-handled Cancel in Choose... dialog.
                    Bug fix: pyfits.open can return [] for certain kinds of invalid image files,
                    instead of raising an exception (presumably a bug in pyfits).
                    This case is now handled properly.
                    Manual centroid was sending radius instead of cradius.
2005-06-21 ROwen    Overhauled command buttons: improved layout and better names.
                    Removed the Center button (use control-click).
                    Changed appearance of the "Current" button to make it clearer.
                    Moved guiding status down to just above the status bar.
2005-06-22 ROwen    Moved guiding status back to the top.
                    Changed display of current image name to a read-only entry; this fixed
                    a resize problem and allows the user to scroll to see the whole name.
2005-06-23 ROwen    Added logic to disable the currently active command button.
                    Added a Cancel button to re-enable buttons when things get stuck.
                    Improved operation while guide window closed: image info
                    is now kept in the history as normal, but download is deferred
                    until the user displays the guide window and tries to look at an image.
                    Images that cannot be displayed now show the reason
                    in the middle of the image area, instead of in the status bar.
                    Tweaked definition of isGuiding to better match command enable;
                    now only "off" is not guiding; formerly "stopping" was also not guiding.
2005-06-24 ROwen    Modified to use new hub manual guider.
                    Added show/hide Image button.
                    Modified the way exposure parameters are updated: now they auto-track
                    the current value if they are already current. But as soon as you
                    change one, the change sticks. This is in preparation for
                    support of guiding tweaks.
                    Modified to not allow guiding on a star from a non-current image
                    (if the guider is ever smart enough to invalidate images
                    once the telescope has moved, this can be handled more flexibly).
                    Bug fix in test code; GuideTest not setting _LocalMode.
                    Bug fix: current image name not right-justified after shrinking window.
2005-06-27 ROwen    Removed image show/hide widget for now; I want to straighten out
                    the resize behavior and which other widgets to hide or disable
                    before re-enabling this feature.
                    Added workaround for bug in tkFileDialog.askopenfilename on MacOS X.
2005-07-08 ROwen    Modified for http download.
2005-07-14 ROwen    Removed _LocalMode and local test mode support.
2005-09-28 ROwen    The DS9 button shows an error in the status bar if it fails.
2005-11-09 ROwen    Fix PR 311: traceback in doDragContinue, unscriptable object;
                    presumably self.dragStar was None (though I don't know how).
                    Improved doDragContinue to null dragStar, dragRect on error.
2006-04-07 ROwen    In process of overhauling guider; some tests work
                    but more tests are wanted.
                    Removed tracking of mask files because the mask is now contained in guide images.
                    Bug fix: updGuideState was mis-called.
                    Re-added "noGuide" to centerOn commands to improve compatibility with old guide code.
2006-04-11 ROwen    Display boresight (if available).
                    Disable some controls when holding an image, and make it clear it's happening.
                    Bug fix: mode widget not getting correctly set when a new mode seen.
2006-04-13 ROwen    Added support for bad pixel and saturated pixel masks.
                    Changed centering commands from "guide on centerOn=x,y noGuide..."
                    to "guide centrOn=x,y...". Thanks for the simpler command, Craig!
2006-04-14 ROwen    Tweaked guide mode widget names and label.
                    Does not display a selected star in manual guide mode,
                    but maybe this stops a centroid from selecting itself in that mode?
                    Bug fix: the Apply button was not grayed out while operating.
2006-04-17 ROwen    Fix PR 393: ctrl-click guider offsets need to specify exposure time.
2006-04-21 ROwen    Bug fix: the Apply button's command called doCmd with isGuideOn=True.
2006-04-26 ROwen    Bug fix: two tests involving an image's defSelDataColor could fail
                    if there was no selection.
2006-04-27 ROwen    Bug fixes (thanks to pychecker):
                    - e missing from "except <exception>, e" in two error handlers.
                    - centerBtn -> self.centerBtn in doCenterOnSel.
                    - defGuideMode not set on new image objects.
2006-05-04 ROwen    Modified Cancel to clear self.doingCmd and call enableCmdButtons,
                    rather than relying on the command's abort method to do this.
                    This may make cancel a bit more reliable about enabling buttons.
                    Added _DebugBtnEnable to help diagnose button enable errors.
                    Clarified some code comments relating to self.doingCmd.
2006-05-19 ROwen    Overhauled the way commands are tied to images.
                    Added display of predicted guide star position.
                    Guide star(s) are now shown as distinct from other stars.
2006-05-19 ROwen    Modified to select the (first) guide star, thus displaying FWHM.
                    (If the guide star is missing, the first found star will be selected instead.)
                    Modified to always show centroid stars above guide stars above found stars.
                    Added support for color preferences.
                    Modified Current to restore selected star.
                    Bug fix: NA2 guider would not show Apply after selecting a star
                    (I'm not sure why any guider would, but I fixed it).
                    Bug fix: Current broken on NA2 guider due to method name conflict.
2006-05-24 ROwen    Changed non-slitviewer Star mode to Field Star for consistency.
2006-06-29 ROwen    Added imDisplayed method and modified code to use it;
                    this is more reliable than the old test of self.dispImObj not None.
                    This fixes a bug whereby DS9 is enabled but cannot send an image.
                    Started adding support for subframing, but much remains to be done;
                    meanwhile the new widgets are not yet displayed.
2006-08-03 ROwen    Moved ImObj class to its own file Image.py and renamed it to GuideImage.
2006-09-26 ROwen    Added subframe (CCD window) support.
2006-10-11 ROwen    Added explicit default for GuideMode.
2006-10-31 ROwen    Fixed incorrect units in one FWHM help text string.
2006-11-06 ROwen    Modified to use new definition of <x>cam window argument.
2007-01-11 ROwen    Bug fix: Thresh and Rad Mult limits not being tested
                    due to not using the doneFunc argument of RO.Wdg.Entry widgets.
                    Used the new label argument for RO.Wdg.Entry widgets.
2007-04-24 ROwen    Modified to use numpy instead of numarray.
2007-12-18 ROwen    Improved control-click offset: display an arrow showing the offset; the arrow
                    may be dragged to modify the offset or dragged off the image to cancel the offset.
2007-01-28 ROwen    Changed default range from 99.9% to 99.5%.
2008-02-11 ROwen    Changed name of cancel button from Cancel to X.
2008-03-28 ROwen    Fix PR 772: ctrl-click arrow stopped updating if ctrl key lifted.
2008-04-01 ROwen    Fix PR 780: ctrl-click fails; I was testing the truth value of an array.
                    Modified to cancel control-click if control key released.
2008-04-22 ROwen    Added display of exposure status.
2008-04-23 ROwen    Modified to accept expState durations of None as unknown.
2008-04-28 ROwen    Modified to only download one guide image at a time
                    when auto-downloading current images (if you go back in history
                    to view skipped images you can easily start multiple downloads).
2008-04-29 ROwen    Fixed reporting of exceptions that contain unicode arguments.
                    Bug fix: could download the same image twice.
2008-05-15 ROwen    Modified to use new doStretch argument for MaskInfo.
2010-03-02 ROwen    Added some doc strings.
                    Modified to expect gcamInfo.isSlitViewer instead of slitViewer.
2010-05-27 ROwen    Fixed ticket #1111: the guider might issue a new findStars command whenever a new
                    guide image was received, depending on how Thresh and RadMult were set.
                    Fixed by disabling callbacks from those controls while setting them programmatically.
2010-06-07 ROwen    Added setRadMult and setThreshWdg methods to simplify the code a bit.
2010-10-18 ROwen    Made drag-to-select and ctrl-drag-to-center modes more robust.
                    Display the Center button for slitviewers.
2010-10-18 ROwen    Further refined drag-to-select: if ctrl key is pressed the selection rectangle
                    is deleted and if there is no selection rectangle then mouse-release will not centroid.
2010-10-19 ROwen    Further refinements to event handling. Now the crosshair cursor is only shown
                    if the ctrl-click arrow is also shown. Thus the cursor now is a reliable indicator
                    that a center command will be sent if the mouse button is released.
2011-01-14 ROwen    Fix PR 1188: make the system more robust against unwanted ctrl-click by cancelling
                    drag and ctrl-click modes on canvas Activate, Deactivate and FocusOut events.
2011-06-08 ROwen    Modified Thresh and RadMult entry widgets as follows:
                    - Initial default is now based on fsDefThresh/RadMult; formerly it was hard-coded
                    - Subsequent defaults are based on fsActThresh/RadMult (but only if the values were
                      used to obtain the image or were changed by this user, as usual for this widget).
                    - Fixed several bugs that were incorrectly making their backgrounds pink.
                    Stop setting imObj.currGuideMode and defGuideMode since they were not being used.
2011-06-09 ROwen    Overhauled ctrl-click handling:
                    - Ctrl-click puts the selection at the cursor, allowing Center Sel to center on it.
                      Thus you must push a button to move the telescope, making unexpected motion unlikely.
                    - Normal drag vs. ctrl-click is now based on the initial ctrl key state, simplifying
                      the event handling.
                    - Normal drag or ctrl-click is temporarily disabled by dragging off the canvas;
                      thus you have a clear way to cancel either mode, good visual feedback.
                      The mode resumes if you drag back onto the canvas.
                    Bug fix: drag-to-centroid now works for any drag direction.
2011-06-16 ROwen    Refined ctrl-click to show an arrow when the user hovers over the Center Sel button
                    (if the button is enabled).
                    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2011-06-17 ROwen    Added "auto-guiding is on" to reasons why ctrl-click is disabled;
                    now Center Sel will be disabled when ctrl-click is allowed only if executing a cmd.
2011-06-28 ROwen    Changed Hold/Current and history behavior to reduce confusion between user-chosen
                    FITS files and images received from the guider:
                    - Current always shows an image from the guider, if one is available, else nothing.
                      Formerly if you used Choose... to view a FITS file and you had never received any images
                      from the guider, then the image you were viewing would stay up when you pressed Current.
                    - The image history is reserved for images received from the guider. Images viewed using
                      Choose... are not added to the image history.
                    Added initial default values for Thresh and RadMult because when the guide actors
                    are first started they don't report values for these parameters.
                    Changed ctrl-click annotation from a hollow X to a filled X.
                    Bug fix: star selection was much too picky.
2011-07-25 ROwen    Bug fix: enableCmdButtons was not being reliably called after ctrl-click.
                    Modified to disallow ctrl-click while executing a command.
                    Thus Center Sel should always be enabled after ctrl-click.
2012-07-10 ROwen    Modified to use RO.TkUtil.Timer.
                    Removed use of update_idletasks.
2012-08-29 ROwen    Removed use of deprecated dict.has_key method.
2012-11-13 ROwen    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
                    Modified to use generic timer.
                    Added an update_idletasks to work around a bug displaying holdWarnWdg on MacOS.
2015-09-18 ROwen    Add support for gzipped FITS files to the "Choose..." button, as per SDSS ticket 2430.
                    Note that tkFileDialog.askopenfilename does not support file types that contain
                    more than one dot, such as '.fits.gz' (at least on MacOS), so I had to use ".gz"
                    and permit any gzipped file.
                    If an image has no data in HDU 0 then display a warning in the guider window.
2015-11-02 ROwen    Correct computation of boreXY (was adding 0.5 instead of subtracting it).
                    Switch from numpy.alltrue to numpy.all.
                    Simplify some use of numpy and specify data types where ambiguous.
2015-11-05 ROwen    Fix a numpy warning when dealing with boresight.
"""
import atexit
import os
import sys
import weakref
import tkinter
import tkinter.filedialog
import numpy
if __name__ == "__main__":
    import RO.Comm.Generic
    RO.Comm.Generic.setFramework("tk")
import RO.Alg
import RO.Constants
import RO.DS9
import RO.KeyVariable
import RO.OS
import RO.Prefs
import RO.StringUtil
from RO.Comm.Generic import Timer
import RO.Wdg
import RO.Wdg.GrayImageDispWdg as GImDisp
import TUI.TUIModel
from . import GuideModel
from . import GuideImage
from . import SubFrame
from . import SubFrameWdg
try:
    set
except NameError:
    from sets import Set as set

_DebugCtrlClick = False

_HelpPrefix = "Guiding/index.html#"

_MaxDist = 25
_CentroidTag = "centroid"
_FindTag = "findStar"
_GuideTag = "guide"
_SelTag = "showSelection"
_CenterSelArrowTag = "centerSelArrow"
_BoreTag = "boresight"
_CtrlClickTag = "ctrlClick"

_SelRad = 18
_SelHoleRad = 9
_BoreRad = 6
_GuideRad = 18
_GuideHoleRad = 9
_GuidePredPosRad = 9

_HistLen = 100

_DebugMem = False # print a message when a file is deleted from disk?
_DebugBtnEnable = False # print messages that help debug button enable?

class CmdInfo(object):
    """Information about one image-related command"""
    Centroid = "c"
    Findstars = "f"
    def __init__(self,
        cmdr,
        cmdID,
        cmdChar,
        imObj,
        isNewImage,
    ):
        self.cmdr = cmdr
        self.cmdID = cmdID
        self.cmdChar = cmdChar.lower()
        self.imObj = imObj
        self.isNewImage = isNewImage

        self._sawStarData = set()

    def sawStarData(self, dataType):
        """Set sawStarData flag for the specified dataType and return old value of flag.
        dataType is a character from the star keyword; it is presently one of "c", "f" or "g".
        """
        dataType = dataType.lower()
        retVal = dataType in self._sawStarData
        self._sawStarData.add(dataType)
        return retVal

    def _clear(self):
        """Clear any data that might cause memory leaks"""
        self.imObj = None


class CurrCmds(object):
    """Information about all current image-related commands"""
    def __init__(self, timeLim=60):
        self.timeLim = timeLim
        self.currCmds = dict() # dict of (cmdr, cmdID): CmdInfo
        self._cmdTimer = Timer()

    def addCmd(self, cmdr, cmdID, cmdChar, imObj, isNewImage):
        cmdInfo = CmdInfo(
            cmdr = cmdr,
            cmdID = cmdID,
            cmdChar = cmdChar,
            imObj = imObj,
            isNewImage = isNewImage
        )
        self.currCmds[(cmdr, cmdID)] = cmdInfo
        self._cmdTimer.start(self.timeLim, self.delCmdInfo, cmdInfo.cmdr, cmdInfo.cmdID)

    def getCmdInfo(self, cmdr, cmdID):
        """Return cmdInfo, or None if no such command."""
        return self.currCmds.get((cmdr, cmdID), None)

    def getCmdInfoFromKeyVar(self, keyVar):
        """Return cmdInfo based on keyVar, or None if no such command."""
        cmdr, cmdID = keyVar.getCmdrCmdID()
        return self.getCmdInfo(cmdr, cmdID)

    def delCmdInfo(self, cmdr, cmdID):
        #print "deleting cmd (%s, %s)" % (cmdr, cmdID)
        cmdInfo = self.currCmds.pop((cmdr, cmdID), None)
        if cmdInfo:
            cmdInfo._clear()


class HistoryBtn(RO.Wdg.Button):
    """Arrow button to show the previous or next image in a list
    """
    _InfoDict = {
        (False, False): ("show previous image", "\N{BLACK LEFT-POINTING TRIANGLE}"),
        (False, True):  ("show previous OUT OF SEQUENCE image", "\N{WHITE LEFT-POINTING TRIANGLE}"),
        (True,  False): ("show next image", "\N{BLACK RIGHT-POINTING TRIANGLE}"),
        (True,  True):  ("show next OUT OF SEQUENCE image", "\N{WHITE RIGHT-POINTING TRIANGLE}"),
    }
    def __init__(self,
        master,
        isNext = True,
    **kargs):
        """Create an image history arrow button

        Inputs:
        - master: master widget
        - isNext: True for a "next image" button, False for a "previous image" button
        **kargs: keyword arguments for RO.Wdg.Button
        """
        self.isNext = bool(isNext)
        self.isGap = False
        if self.isNext:
            self.descr = "next"
        else:
            self.descr = "previous"
        RO.Wdg.Button.__init__(self, master, **kargs)
        self._redisplay()

    def setState(self, doEnable, isGap):
        self.setEnable(doEnable)
        if self.isGap == bool(isGap):
            return
        self.isGap = bool(isGap)
        self._redisplay()

    def _redisplay(self):
        self.helpText, btnText = self._InfoDict[(self.isNext, self.isGap)]
        self["text"] = btnText


class GuideWdg(tkinter.Frame):
    def __init__(self,
        master,
        actor,
    **kargs):
        tkinter.Frame.__init__(self, master, **kargs)

        self.actor = actor
        self.guideModel = GuideModel.getModel(actor)
        self.tuiModel = TUI.TUIModel.getModel()
        self.boreXY = None
        self.ctrlClickOK = False
        self.centerSelArrow = None
        self.dragStart = None
        self.dragRect = None
        self.exposing = None # True, False or None if unknown
        self.currDownload = None # image object being downloaded
        self.nextDownload = None # next image object to download

        # color prefs
        def getColorPref(prefName, defColor, isMask = False):
            """Get a color preference. If not found, make one."""
            pref = self.tuiModel.prefs.getPrefVar(prefName, None)
            if pref is None:
                pref = RO.Prefs.PrefVar.ColorPrefVar(
                    name = prefName,
                    defValue = "cyan",
                )
            if isMask:
                pref.addCallback(self.updMaskColor, callNow=False)
            else:
                pref.addCallback(self.redisplayImage, callNow=False)
            return pref

        self.typeTagColorPrefDict = {
            "c": (_CentroidTag, getColorPref("Centroid Color", "cyan")),
            "f": (_FindTag, getColorPref("Found Star Color", "green")),
            "g": (_GuideTag, getColorPref("Guide Star Color", "magenta")),
        }
        self.boreColorPref = getColorPref("Boresight Color", "cyan")
        self.maskColorPrefs = ( # for sat and bad pixel mask
            getColorPref("Saturated Pixel Color", "red", isMask = True),
            getColorPref("Masked Pixel Color", "green", isMask = True),
        )

        self.nToSave = _HistLen # eventually allow user to set?
        self.imObjDict = RO.Alg.ReverseOrderedDict()
        self._memDebugDict = {}
        self.dispImObj = None # object data for most recently taken image, or None
        self.ds9Win = None

        self.doingCmd = None # (cmdVar, cmdButton, isGuideOn) used for currently executing cmd
        self._btnsLaidOut = False

        self.currCmds = CurrCmds()

        totCols = 4

        row=0

        helpURL = _HelpPrefix + "GuidingStatus"

        guideStateFrame = tkinter.Frame(self)
        gsGridder = RO.Wdg.Gridder(guideStateFrame, sticky="w")

        self.guideStateWdg = RO.Wdg.StrLabel(
            master = guideStateFrame,
            formatFunc = str.capitalize,
            anchor = "w",
            helpText = "Current state of guiding",
            helpURL = helpURL,
        )
        gsGridder.gridWdg("Guiding", self.guideStateWdg, colSpan=2)

        self.expStateWdg = RO.Wdg.StrLabel(
            master = guideStateFrame,
            helpText = "Status of current exposure",
            helpURL = helpURL,
            anchor="w",
            width = 11
        )
        self.expTimer = RO.Wdg.TimeBar(
            master = guideStateFrame,
            valueFormat = "%3.1f sec",
            isHorizontal = True,
            autoStop = True,
            helpText = "Status of current exposure",
            helpURL = helpURL,
        )
        gsGridder.gridWdg("Exp Status", (self.expStateWdg, self.expTimer), sticky="ew")
        self.expTimer.grid_remove()

        guideStateFrame.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        guideStateFrame.columnconfigure(2, weight=1)
        row += 1

        helpURL = _HelpPrefix + "HistoryControls"

        histFrame = tkinter.Frame(self)

        self.showHideImageWdg = RO.Wdg.Checkbutton(
            histFrame,
            text = "Image",
            defValue = True,
            callFunc = self.doShowHideImage,
            helpText = "Show or hide image",
            helpURL = helpURL,
        )
        #self.showHideImageWdg.pack(side="left")

        self.prevImWdg = HistoryBtn(
            histFrame,
            isNext = False,
            callFunc = self.doPrevIm,
            helpURL = helpURL,
        )
        self.prevImWdg.pack(side="left")

        self.nextImWdg = HistoryBtn(
            histFrame,
            isNext = True,
            callFunc = self.doNextIm,
            helpURL = helpURL,
        )
        self.nextImWdg.pack(side="left")

        self.showCurrWdg = RO.Wdg.Checkbutton(
            histFrame,
            text = "Current",
            defValue = True,
            callFunc = self.doShowCurr,
            helpText = "Display new images as they come in?",
            helpURL = helpURL,
        )
        self.showCurrWdg.pack(side="left")

        self.chooseImWdg = RO.Wdg.Button(
            histFrame,
            text = "Choose...",
            callFunc = self.doChooseIm,
            helpText = "Choose a fits file to display",
            helpURL = helpURL,
        )
        self.chooseImWdg.pack(side="right")

        self.imNameWdg = RO.Wdg.StrEntry(
            master = histFrame,
            justify="right",
            readOnly = True,
            helpText = "Name of displayed image",
            helpURL = helpURL,
            )
        self.imNameWdg.pack(side="left", expand=True, fill="x", padx=4)

        def showRight(dumEvt=None):
            self.imNameWdg.xview("end")
        self.imNameWdg.bind("<Configure>", showRight)

        histFrame.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        row += 1

        maskInfo = (
            GImDisp.MaskInfo(
                bitInd = 1,
                name = "saturated pixels",
                btext = "Sat",
                color = self.maskColorPrefs[0].getValue(),
                intens = 255,
                doStretch = True,
            ),
            GImDisp.MaskInfo(
                bitInd = 0,
                name = "masked pixels",
                btext = "Mask",
                color = self.maskColorPrefs[1].getValue(),
                intens = 100,
                doStretch = False,
            ),
        )

        self.gim = GImDisp.GrayImageWdg(self,
            maskInfo = maskInfo,
            helpURL = _HelpPrefix + "Image",
            callFunc = self.enableSubFrameBtns,
            defRange = "99.5%",
        )
        self.gim.grid(row=row, column=0, columnspan=totCols, sticky="news")
        self.grid_rowconfigure(row, weight=1)
        self.grid_columnconfigure(totCols - 1, weight=1)
        row += 1

        self.defCnvCursor = self.gim.cnv["cursor"]

        helpURL = _HelpPrefix + "DataPane"

        starFrame = tkinter.Frame(self)

        RO.Wdg.StrLabel(
            starFrame,
            text = " Star ",
            bd = 0,
            padx = 0,
            helpText = "Information about the selected star",
            helpURL = helpURL,
        ).pack(side="left")

        RO.Wdg.StrLabel(
            starFrame,
            text = "Pos: ",
            bd = 0,
            padx = 0,
            helpText = "Centroid of the selected star (pix)",
            helpURL = helpURL,
        ).pack(side="left")
        self.starXPosWdg = RO.Wdg.FloatLabel(
            starFrame,
            width = 6,
            precision = 1,
            anchor="e",
            bd = 0,
            padx = 0,
            helpText = "X centroid of selected star (pix)",
            helpURL = helpURL,
        )
        self.starXPosWdg.pack(side="left")

        RO.Wdg.StrLabel(
            starFrame,
            text = ", ",
            bd = 0,
            padx = 0,
        ).pack(side="left")
        self.starYPosWdg = RO.Wdg.FloatLabel(
            starFrame,
            width = 6,
            precision = 1,
            anchor="e",
            bd = 0,
            padx = 0,
            helpText = "Y centroid of selected star (pix)",
            helpURL = helpURL,
        )
        self.starYPosWdg.pack(side="left")

        RO.Wdg.StrLabel(
            starFrame,
            text = "  FWHM: ",
            bd = 0,
            padx = 0,
            helpText = "FWHM of selected star (pix)",
            helpURL = helpURL,
        ).pack(side="left")
        self.starFWHMWdg = RO.Wdg.FloatLabel(
            starFrame,
            width = 4,
            precision = 1,
            anchor="e",
            bd = 0,
            padx = 0,
            helpText = "FWHM of selected star (pix)",
            helpURL = helpURL,
        )
        self.starFWHMWdg.pack(side="left")

        RO.Wdg.StrLabel(
            starFrame,
            text = "  Ampl: ",
            bd = 0,
            padx = 0,
            helpText = "Amplitude of selected star (ADUs)",
            helpURL = helpURL,
        ).pack(side="left")
        self.starAmplWdg = RO.Wdg.FloatLabel(
            starFrame,
            width = 7,
            precision = 1,
            anchor="e",
            bd = 0,
            padx = 0,
            helpText = "Amplitude of selected star (ADUs)",
            helpURL = helpURL,
        )
        self.starAmplWdg.pack(side="left")

        RO.Wdg.StrLabel(
            starFrame,
            text = "  Bkgnd: ",
            bd = 0,
            padx = 0,
            helpText = "Background level at selected star (ADUs)",
            helpURL = helpURL,
        ).pack(side="left")
        self.starBkgndWdg = RO.Wdg.FloatLabel(
            starFrame,
            width = 6,
            precision = 1,
            anchor="e",
            bd = 0,
            padx = 0,
            helpText = "Background level at selected star (ADUs)",
            helpURL = helpURL,
        )
        self.starBkgndWdg.pack(side="left")

        starFrame.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        row += 1

        helpURL = _HelpPrefix + "AcquisitionControls"

        subFrameFrame = tkinter.Frame(self)

        RO.Wdg.StrLabel(
            subFrameFrame,
            text = " Window",
            helpText = "CCD window",
            helpURL = helpURL,
        ).grid(row=0, rowspan=2, column=0)

        subFrame = SubFrame.SubFrame(
            fullSize = self.guideModel.gcamInfo.imSize,
            subBeg = (0, 0),
            subSize = self.guideModel.gcamInfo.imSize,
        )
        self.subFrameWdg = SubFrameWdg.SubFrameWdg(
            master = subFrameFrame,
            subFrame = subFrame,
            defSubFrame = subFrame,
            callFunc = self.enableSubFrameBtns,
            helpText = "CCD window",
            helpURL = helpURL,
            height = 5,
            borderwidth = 2,
            relief = "sunken",
        )
        self.subFrameWdg.grid(row=0, rowspan=2, column=1, sticky="ns")

        self.subFrameToFullBtn = RO.Wdg.Button(
            subFrameFrame,
            text = "Full",
            callFunc = self.doSubFrameToFull,
            helpText = "Set window to full frame",
            helpURL = _HelpPrefix + "AcquisitionControls",
        )
        self.subFrameToFullBtn.grid(row=0, column=2)

        self.subFrameToViewBtn = RO.Wdg.Button(
            subFrameFrame,
            text = "View",
            callFunc = self.doSubFrameToView,
            helpText = "Set window to current view",
            helpURL = _HelpPrefix + "AcquisitionControls",
        )
        self.subFrameToViewBtn.grid(row=1, column=2)

        subFrameFrame.grid(row=row, rowspan=2, column=1)

        inputFrame1 = tkinter.Frame(self)

        helpText = "exposure time"
        RO.Wdg.StrLabel(
            inputFrame1,
            text = "Exp Time",
            helpText = helpText,
            helpURL = helpURL,
        ).pack(side="left")

        self.expTimeWdg = RO.Wdg.FloatEntry(
            inputFrame1,
            label = "Exp Time",
            minValue = self.guideModel.gcamInfo.minExpTime,
            maxValue = self.guideModel.gcamInfo.maxExpTime,
            defValue = self.guideModel.gcamInfo.defExpTime,
            defFormat = "%.1f",
            defMenu = "Current",
            minMenu = "Minimum",
            autoIsCurrent = True,
            helpText = helpText,
            helpURL = helpURL,
        )
        self.expTimeWdg.pack(side="left")

        RO.Wdg.StrLabel(
            inputFrame1,
            text = "sec",
            width = 4,
            anchor = "w",
        ).pack(side="left")

        helpText = "binning factor"
        RO.Wdg.StrLabel(
            inputFrame1,
            text = "Bin",
            helpText = helpText,
            helpURL = helpURL,
        ).pack(side="left")

        self.binFacWdg = RO.Wdg.IntEntry(
            inputFrame1,
            label = "Bin",
            minValue = 1,
            maxValue = 99,
            defValue = self.guideModel.gcamInfo.defBinFac,
            defMenu = "Current",
            autoIsCurrent = True,
            callFunc = self.updBinFac,
            helpText = helpText,
        )
        self.binFacWdg.pack(side="left")

        inputFrame1.grid(row=row, column=0, sticky="ew")
        row += 1


        inputFrame2 = tkinter.Frame(self)

        helpText = "threshold for finding stars"
        RO.Wdg.StrLabel(
            inputFrame2,
            text = "Thresh",
            helpText = helpText,
            helpURL = helpURL,
        ).pack(side="left")

        self.threshWdg = RO.Wdg.FloatEntry(
            inputFrame2,
            label = "Thresh",
            minValue = 1.5,
            defValue = 2.5, # guider reports no value when it is first started, so just in case...
            defFormat = "%.1f",
            defMenu = "Current",
            doneFunc = self.doFindStars,
            autoIsCurrent = True,
            width = 5,
            helpText = helpText,
            helpURL = helpURL,
        )
        self.threshWdg.pack(side="left")

        RO.Wdg.StrLabel(
            inputFrame2,
            text = "\N{GREEK SMALL LETTER SIGMA} ",
        ).pack(side="left")

        helpText = "radius multipler for finding stars"
        RO.Wdg.StrLabel(
            inputFrame2,
            text = "Rad Mult",
            helpText = helpText,
            helpURL = helpURL,
        ).pack(side="left")

        self.radMultWdg = RO.Wdg.FloatEntry(
            inputFrame2,
            label = "Rad Mult",
            minValue = 0.5,
            defValue = 1.2,  # guider reports no value when it is first started, so just in case...
            defFormat = "%.1f",
            defMenu = "Current",
            autoIsCurrent = True,
            doneFunc = self.doFindStars,
            width = 5,
            helpText = helpText,
            helpURL = helpURL,
        )
        self.radMultWdg.pack(side="left")

        inputFrame2.grid(row=row, column=0, sticky="ew")
        row += 1

        guideModeFrame = tkinter.Frame(self)

        RO.Wdg.StrLabel(
            guideModeFrame,
            text = "Mode: "
        ).pack(side="left")

        if self.guideModel.gcamInfo.isSlitViewer:
            guideModes = ("Boresight", "Field Star", "Manual")
            valueList = ("boresight", "field", "manual")
            helpText = (
                "Guide on object in slit",
                "Guide on selected field star",
                "Expose repeatedly; center with ctrl-click or Nudger",
            )
            defValue = "boresight"
        else:
            guideModes = ("Field Star", "Manual")
            valueList = ("field", "manual")
            helpText = (
                "Guide on selected field star",
                "Expose repeatedly",
            )
            defValue = "field"

        self.guideModeWdg = RO.Wdg.RadiobuttonSet(
            guideModeFrame,
            textList = guideModes,
            valueList = valueList,
            defValue = defValue,
            autoIsCurrent = True,
            side = "left",
            helpText = helpText,
            helpURL = helpURL,
        )

        self.currentBtn = RO.Wdg.Button(
            guideModeFrame,
            text = "Current",
            command = self.doCurrent,
            helpText = "Show current guide parameters",
            helpURL = helpURL,
        )
        self.currentBtn.pack(side="right")

        guideModeFrame.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        row += 1

        self.guideParamWdgSet = [
            self.expTimeWdg,
            self.binFacWdg,
            self.threshWdg,
            self.radMultWdg,
            self.guideModeWdg,
            self.subFrameWdg,
        ]
        for wdg in self.guideParamWdgSet:
            wdg.addCallback(self.enableCmdButtons)

        self.devSpecificFrame = tkinter.Frame(self)
        self.devSpecificFrame.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        row += 1

        self.statusBar = RO.Wdg.StatusBar(
            master = self,
            dispatcher = self.tuiModel.dispatcher,
            prefs = self.tuiModel.prefs,
            playCmdSounds = True,
            helpURL = _HelpPrefix + "StatusBar",
        )
        self.statusBar.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        row += 1

        helpURL = _HelpPrefix + "GuidingControls"

        cmdButtonFrame = tkinter.Frame(self)
        self.exposeBtn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "Expose",
            callFunc = self.doExpose,
            helpText = "Take an exposure",
            helpURL = helpURL,
        )

        self.centerBtn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "Center Sel",
            callFunc = self.doCenterOnSel,
            helpText = "Put selected star on the boresight",
            helpURL = helpURL,
        )

        self.guideOnBtn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "Guide",
            callFunc = self.doGuideOn,
            helpText = "Start guiding",
            helpURL = helpURL,
        )

        self.applyBtn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "Apply",
            callFunc = self.doGuideTweak,
            helpText = "Apply new guide parameters",
            helpURL = helpURL,
        )

        self.guideOffBtn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "Stop Guiding",
            callFunc = self.doGuideOff,
            helpText = "Turn off guiding",
            helpURL = helpURL,
        )

        self.cancelBtn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "X",
            callFunc = self.cmdCancel,
            helpText = "Cancel executing command",
            helpURL = helpURL,
        )

        self.ds9Btn = RO.Wdg.Button(
            cmdButtonFrame,
            text = "DS9",
            callFunc = self.doDS9,
            helpText = "Display image in ds9",
            helpURL = helpURL,
        )

        self.holdWarnWdg = RO.Wdg.StrLabel(
            cmdButtonFrame,
            text = "Holding Image",
            severity = RO.Constants.sevWarning,
            anchor = "center",
            helpText = "Press Hold above to enable these controls",
        )

        # lay out command buttons
        col = 0
        self.exposeBtn.grid(row=0, column=col)
        self.holdWarnWdg.grid(row=0, column=col, columnspan=totCols, sticky="ew")
        self.holdWarnWdg.grid_remove()
        col += 1
        self.guideOnBtn.grid(row=0, column=col)
        col += 1
        if self.guideModel.gcamInfo.isSlitViewer:
            self.centerBtn.grid(row=0, column=col)
            col += 1
        self.applyBtn.grid(row=0, column=col)
        col += 1
        self.guideOffBtn.grid(row=0, column=col)
        col += 1
        self.cancelBtn.grid(row=0, column=col)
        col += 1
        self.ds9Btn.grid(row=0, column=col, sticky="e")
        cmdButtonFrame.grid_columnconfigure(col, weight=1)
        col += 1
        # leave room for the resize control
        tkinter.Label(cmdButtonFrame, text=" ").grid(row=0, column=col)
        col += 1

        # enable controls accordingly
        self.enableCmdButtons()
        self.enableHistButtons()

        cmdButtonFrame.grid(row=row, column=0, columnspan=totCols, sticky="ew")
        row += 1

        # event bindings
        self.gim.bind("<Map>", self.doMap)

        self.gim.cnv.bind("<ButtonPress-1>", self.doDragStart, add=True)
        self.gim.cnv.bind("<B1-Motion>", self.doDragContinue, add=True)
        self.gim.cnv.bind("<ButtonRelease-1>", self.doDragEnd, add=True)
        self.gim.cnv.bind("<Control-ButtonPress-1>", self.doCtrlClickBegin)

        self.gim.cnv.bind("<Activate>", self.doCancelDrag)
        self.gim.cnv.bind("<Deactivate>", self.doCancelDrag)
        self.gim.cnv.bind("<FocusOut>", self.doCancelDrag)

        self.centerBtn.bind("<Enter>", self.drawCenterSelArrow)
        self.centerBtn.bind("<Leave>", self.eraseCenterSelArrow)

        # keyword variable bindings
        self.guideModel.expState.addCallback(self.updExpState)
        self.guideModel.fsActRadMult.addIndexedCallback(self.updFSActRadMult)
        self.guideModel.fsActThresh.addIndexedCallback(self.updFSActThresh)
        self.guideModel.fsDefRadMult.addIndexedCallback(self.updFSDefRadMult)
        self.guideModel.fsDefThresh.addIndexedCallback(self.updFSDefThresh)
        self.guideModel.files.addCallback(self.updFiles)
        self.guideModel.star.addCallback(self.updStar)
        self.guideModel.guideState.addCallback(self.updGuideState)
        self.guideModel.guideMode.addCallback(self.setGuideState)
        self.guideModel.locGuideMode.addIndexedCallback(self.updLocGuideMode)

        # bindings to set the image cursor
        tl = self.winfo_toplevel()
        tl.bind("<Control-KeyPress>", self.eraseDragRect, add=True)
        tl.bind("<Control-KeyRelease>", self.ignoreEvt, add=True)

        # exit handler
        atexit.register(self._exitHandler)

        self.enableCmdButtons()
        self.enableHistButtons()

    def addImToHist(self, imObj, ind=None):
        imageName = imObj.imageName
        if ind is None:
            self.imObjDict[imageName] = imObj
        else:
            self.imObjDict.insert(ind, imageName, imObj)

    def areParamsModified(self):
        """Return True if any guiding parameter has been modified"""
        for wdg in self.guideParamWdgSet:
            if not wdg.getIsCurrent():
                return True

        if self.dispImObj and self.dispImObj.defSelDataColor and self.dispImObj.selDataColor \
            and (self.dispImObj.defSelDataColor[0] != self.dispImObj.selDataColor[0]):
            # star selection has changed
            return True

        return False

    def clearImage(self):
        """Clear image (if any), showing nothing.
        """
        self.boreXY = None
        self.dispImObj = None
        self.gim.clear()
        self.endCtrlClickMode()
        self.endDragMode()
        self.enableCmdButtons()

    def cmdCancel(self, wdg=None):
        """Cancel the current command.
        """
        if self.doingCmd is None:
            return
        cmdVar = self.doingCmd[0]
        self.doingCmd = None
        cmdVar.abort()
        self.enableCmdButtons()

    def cmdCallback(self, msgType, msgDict, cmdVar):
        """Use this callback when launching a command
        whose completion requires buttons to be re-enabled.

        DO NOT use as the sole means of re-enabling guide on button(s)
        because if guiding turns on successfully, the command is not reported
        as done until guiding is terminated.
        """
        if self.doingCmd is None:
            return
        if self.doingCmd[0] == cmdVar:
            cmdBtn = self.doingCmd[1]
            if cmdBtn is not None:
                cmdBtn.setEnable(True)
            self.doingCmd = None
        else:
            sys.stderr.write("GuideWdg warning: cmdCallback called for wrong cmd:\n- doing cmd: %s\n- called by cmd: %s\n" % (self.doingCmd[0], cmdVar))
        self.enableCmdButtons()

    def doCancelDrag(self, dumEvt=None):
        """Cancel drag and control-click modes
        """
#        print "doCancelDrag"
        self.endDragMode()
        self.endCtrlClickMode()
        self.eraseCenterSelArrow()

    def doCenterOnSel(self, evt):
        """Center up on the selected star.
        """
        try:
            if not self.imDisplayed():
                raise RuntimeError("No guide image")

            if not self.dispImObj.selDataColor:
                raise RuntimeError("No star selected")

            starArgs = self.getSelStarArgs(posKey="centerOn")
            expArgs = self.getExpArgStr() # inclThresh=False)
            cmdStr = "guide %s %s" % (starArgs, expArgs)
        except RuntimeError as e:
            self.statusBar.setMsg(RO.StringUtil.strFromException(e), severity = RO.Constants.sevError)
            self.statusBar.playCmdFailed()
            return

        self.doCmd(
            cmdStr = cmdStr,
            cmdBtn = self.centerBtn,
        )

    def doChooseIm(self, wdg=None):
        """Choose an image to display.
        """
        self.showCurrWdg.setBool(False)

        if self.dispImObj is not None:
            currPath = self.dispImObj.getLocalPath()
            startDir, startFile = os.path.split(currPath)
        else:
            # use user preference for image directory, if available
            startDir = self.tuiModel.prefs.getValue("Save To")
            startFile = None

        # work around a bug in Mac Aqua tkFileDialog.askopenfilename
        # for unix, invalid dir or file are politely ignored
        # but either will cause the dialog to fail on MacOS X
        kargs = {}
        if startDir is not None and os.path.isdir(startDir):
            kargs["initialdir"] = startDir
            if startFile is not None and os.path.isfile(os.path.join(startDir, startFile)):
                kargs["initialfile"] = startFile

        imPath = tkinter.filedialog.askopenfilename(
            filetypes = [("FITS", (".fit", ".fits", ".gz"))],
        **kargs)
        if not imPath:
            return

        self.showFITSFile(imPath)

    def doCtrlClickBegin(self, evt):
        """Start control-click: center up on the command-clicked image location.
        Display arrow showing the offset that will be applied.
        """
        self.endCtrlClickMode()
        self.endDragMode()

        reasonStr = self.whyNotCtrlClick()
        if reasonStr:
            errMsg = "Ctrl-click error: %s" % (reasonStr,)
            self.statusBar.setMsg(errMsg, severity = RO.Constants.sevError)
            self.statusBar.playCmdFailed()
            return

        self.ctrlClickOK = True
        self.drawCtrlClickSelection(evt)

    def doCtrlClickContinue(self, evt):
        """Drag control-click arrow around.
        """
        if self.dragRect:
            # in drag-to-centroid mode; delete the selection rectangle and ignore this event
            self.eraseDragRect()
            return

        self.drawCtrlClickSelection(evt)

    def doCtrlClickEnd(self, evt):
        """Make a new star at the cursor and select it
        """
        try:
            self.drawCtrlClickSelection(evt)
        finally:
            self.endCtrlClickMode()
            self.endDragMode()
            self.enableCmdButtons()

    def doCurrent(self, wdg=None):
        """Restore default value of all guide parameter widgets"""
        for wdg in self.guideParamWdgSet:
            wdg.restoreDefault()

        if self.dispImObj and self.dispImObj.defSelDataColor and self.dispImObj.selDataColor \
            and (self.dispImObj.defSelDataColor[0] != self.dispImObj.selDataColor[0]):
            # star selection has changed
            self.dispImObj.selDataColor = self.dispImObj.defSelDataColor
            self.showSelection()

    def doCmd(self,
        cmdStr,
        cmdBtn = None,
        isGuideOn = False,
        actor = None,
        abortCmdStr = None,
        cmdSummary = None,
    ):
        """Execute a command.

        Inputs:
        - cmdStr        the command to execute
        - cmdBtn        the button that triggered the command
        - isGuideOn     set True for commands that start guiding
        - actor         the actor to which to send the command;
                        defaults to the actor for the guide camera
        - abortCmdStr   abort command, if any
        - cmdSummary    command summary for the status bar

        Returns the cmdVar.
        """
        actor = actor or self.actor
        cmdVar = RO.KeyVariable.CmdVar(
            actor = actor,
            cmdStr = cmdStr,
            abortCmdStr = abortCmdStr,
        )
        if cmdBtn:
            self.doingCmd = (cmdVar, cmdBtn, isGuideOn)
            cmdVar.addCallback(
                self.cmdCallback,
                callTypes = RO.KeyVariable.DoneTypes,
            )
        else:
            self.doingCmd = None
        self.enableCmdButtons()
        print("about to do command")
        self.statusBar.doCmd(cmdVar, cmdSummary)
        print("cmdVar: " + str(cmdVar))
        return cmdVar

    def doExistingImage(self, imageName, cmdChar, cmdr, cmdID):
        """Data is about to arrive for an existing image.
        Decide whether we are interested in it,
        and if so, get ready to receive it.
        """
        #print "doExistingImage(imageName=%r, cmdChar=%r, cmdr=%r, cmdID=%r" % (imageName, cmdChar, cmdr, cmdID)
        # see if this data is of interest
        imObj = self.imObjDict.get(imageName)
        if not imObj:
            # I have no knowledge of this image, so ignore the data
            return
        isMe = (cmdr == self.tuiModel.getCmdr())
        if not isMe:
            # I didn't trigger this command, so ignore the data
            return

        self.currCmds.addCmd(
            cmdr = cmdr,
            cmdID = cmdID,
            cmdChar = cmdChar,
            imObj = imObj,
            isNewImage = False,
        )

    def doDragStart(self, evt):
        """Mouse down for current drag (whatever that might be).
        """
        self.endCtrlClickMode()
        self.endDragMode()
        if not self.gim.isNormalMode():
            return
        if not self.imDisplayed():
            return

        try:
            # this action starts drawing a box to centroid a star,
            # so use the centroid color for a frame
            colorPref = self.typeTagColorPrefDict["c"][1]
            color = colorPref.getValue()
            self.dragStart = self.gim.cnvPosFromEvt(evt)
            self.dragRect = self.gim.cnv.create_rectangle(
                self.dragStart[0], self.dragStart[1], self.dragStart[0], self.dragStart[1],
                outline = color,
            )
        except Exception:
            self.endDragMode()
            raise

    def doDragContinue(self, evt):
        # print "doDragContinue; dragStart=%s; dragRect=%s" % (self.dragStart, self.dragRect)
        if self.ctrlClickOK:
            self.doCtrlClickContinue(evt)

        try:
            if not self.gim.isNormalMode():
                return
            if not self.dragStart:
                return

            if not self.gim.evtOnCanvas(evt):
                self.eraseDragRect()
                return

            newPos = self.gim.cnvPosFromEvt(evt)
            if self.dragRect:
                self.gim.cnv.coords(self.dragRect, self.dragStart[0], self.dragStart[1], newPos[0], newPos[1])
            else:
                colorPref = self.typeTagColorPrefDict["c"][1]
                color = colorPref.getValue()
                self.dragRect = self.gim.cnv.create_rectangle(
                    self.dragStart[0], self.dragStart[1], newPos[0], newPos[1],
                    outline = color,
                )
        except Exception:
            self.endDragMode()
            raise

    def doDragEnd(self, evt):
        if self.ctrlClickOK:
            self.doCtrlClickEnd(evt)

        try:
            if not self.gim.isNormalMode():
                return
            if not self.imDisplayed():
                return
            if not self.dragStart:
                return
            if not self.dragRect:
                return

            if not self.gim.evtOnCanvas(evt):
                return

            endPos = self.gim.cnvPosFromEvt(evt)
            startPos = self.dragStart or endPos
            absDeltaPos = numpy.abs(numpy.subtract(endPos, startPos, dtype=float))
            if numpy.all(absDeltaPos > 1):
                # cursor has moved significantly; centroid the region
                rad = max(absDeltaPos) / (self.gim.zoomFac * 2.0)
                meanCnvPos = numpy.mean((startPos, endPos), axis=0, dtype=float)
                imPos = self.gim.imPosFromCnvPos(meanCnvPos)
                thresh = self.threshWdg.getNum()

                cmdStr = "centroid file=%r on=%.2f,%.2f cradius=%.1f thresh=%.2f" % \
                    (self.dispImObj.imageName, imPos[0], imPos[1], rad, thresh)
                self.doCmd(cmdStr)
            else:
                # cursor has barely moved; select the object
                self.doSelect(evt)
        finally:
            self.endDragMode()
            self.endCtrlClickMode()

    def doDS9(self, wdg=None):
        """Display the current image in ds9.
        """
        if not self.imDisplayed():
            self.statusBar.setMsg("No guide image", severity = RO.Constants.sevWarning)
            return

        # open ds9 window if necessary
        try:
            if self.ds9Win:
                # reopen window if necessary
                self.ds9Win.doOpen()
            else:
                self.ds9Win = RO.DS9.DS9Win(self.actor)
        except Exception as e:
            self.statusBar.setMsg(RO.StringUtil.strFromException(e), severity = RO.Constants.sevError)
            return

        localPath = self.dispImObj.getLocalPath()
        self.ds9Win.showFITSFile(localPath)

    def doExpose(self, wdg=None):
        """Take an exposure.
        """
        cmdStr = "findstars " + self.getExpArgStr(inclRadMult=True, inclImgFile=False)
        print("Command str: " + cmdStr)
        print("EXPOSING")
        self.doCmd(
            cmdStr = cmdStr,
            cmdBtn = self.exposeBtn,
            cmdSummary = "expose",
        )

    def doFindStars(self, *args):
        # check thresh and radMult values first
        # since they may be invalid
        try:
            thresh = self.threshWdg.getNum()
            radMult = self.radMultWdg.getNum()
        except ValueError:
            return

        if not self.imDisplayed():
            self.statusBar.setMsg("No guide image", severity = RO.Constants.sevWarning)
            return

        if (radMult == self.dispImObj.radMult) and (thresh == self.dispImObj.thresh):
                return

        # not strictly necessary since the hub will return this data;
        # still, it is safer to set it now and be sure it gets set
        self.dispImObj.thresh = thresh
        self.dispImObj.radMult = radMult

        # execute new command
        cmdStr = "findstars file=%r thresh=%.2f radMult=%.2f" % (self.dispImObj.imageName, thresh, radMult)
        self.doCmd(cmdStr)

    def doGuideOff(self, wdg=None):
        """Turn off guiding.
        """
        self.doCmd(
            cmdStr = "guide off",
            cmdBtn = self.guideOffBtn,
        )

    def doGuideOn(self, wdg=None):
        """Start guiding.
        """
        try:
            cmdStr = "guide on %s" % self.getGuideArgStr()
        except RuntimeError as e:
            self.statusBar.setMsg(RO.StringUtil.strFromException(e), severity = RO.Constants.sevError)
            self.statusBar.playCmdFailed()
            return

        self.doCmd(
            cmdStr = cmdStr,
            cmdBtn = self.guideOnBtn,
            abortCmdStr = "guide off",
            isGuideOn = True,
        )

    def doGuideTweak(self, wdg=None):
        """Change guiding parameters.
        """
        try:
            cmdStr = "guide tweak %s" % self.getGuideArgStr(modOnly=True)
        except RuntimeError as e:
            self.statusBar.setMsg(RO.StringUtil.strFromException(e), severity = RO.Constants.sevError)
            self.statusBar.playCmdFailed()
            return

        self.doCmd(
            cmdStr = cmdStr,
            cmdBtn = self.applyBtn,
        )

    def doMap(self, dumEvt=None):
        """Window has been mapped"""
        if self.dispImObj:
            # give the guide frame a chance to be redrawn so zoom can be set correctly.
            # formerly this was done using update_idletasks followed by calling showImage directly;
            # I'm not sure how to reproduce the problem so I'm not sure any workaround
            # is still needed and if this particular one does the job.
            Timer(0.001, self.showImage, self.dispImObj)

    def doNextIm(self, wdg=None):
        """Show next image from history list"""
        revHist, currInd = self.getHistInfo()
        if currInd is None:
            self.statusBar.setMsg("Position in history unknown", severity = RO.Constants.sevWarning)
            return

        try:
            nextImName = revHist[currInd-1]
        except IndexError:
            self.statusBar.setMsg("Showing newest image", severity = RO.Constants.sevWarning)
            return

        self.showImage(self.imObjDict[nextImName])

    def doPrevIm(self, wdg=None):
        """Show previous image from history list"""
        self.showCurrWdg.setBool(False)

        revHist, currInd = self.getHistInfo()
        if currInd is None:
            self.statusBar.setMsg("Position in history unknown", severity = RO.Constants.sevError)
            return

        try:
            prevImName = revHist[currInd+1]
        except IndexError:
            self.statusBar.setMsg("Showing oldest image", severity = RO.Constants.sevWarning)
            return

        self.showImage(self.imObjDict[prevImName])

    def doSelect(self, evt):
        """Select star nearest to mouse pointer.
        """
        if not self.gim.isNormalMode():
            return
        cnvPos = self.gim.cnvPosFromEvt(evt)
        imPos = self.gim.imPosFromCnvPos(cnvPos)

        try:
            # get current image object
            if not self.imDisplayed():
                return

            # erase data for now (helps for early return)
            self.dispImObj.selDataColor = None

            # look for nearby centroid to choose
            selStarData = None
            minDistSq = _MaxDist**2
            for typeChar, starDataList in self.dispImObj.starDataDict.items():
                #print "doSelect checking typeChar=%r, nstars=%r" % (typeChar, len(starDataList))
                tag, colorPref = self.typeTagColorPrefDict[typeChar]
                color = colorPref.getValue()
                for starData in starDataList:
                    if None in starData[2:4]:
                        continue
                    distSq = (starData[2] - imPos[0])**2 + (starData[3] - imPos[1])**2
                    if distSq < minDistSq:
                        minDistSq = distSq
                        selStarData = starData
                        selColor = color

            if selStarData:
                self.dispImObj.selDataColor = (selStarData, selColor)
        finally:
            # update display
            self.showSelection()

    def doShowCurr(self, wdg=None):
        """Handle show current image button"""
        doShowCurr = self.showCurrWdg.getBool()

        if doShowCurr:
            sev = RO.Constants.sevNormal
            self.holdWarnWdg.grid_remove()
#           self.statusBar.setMsg("",
#               severity=RO.Constants.sevNormal,
#           )
        else:
            sev = RO.Constants.sevWarning
            self.holdWarnWdg.grid()
            self.update_idletasks() # work around Tcl/Tk 8.5.11 bug that stops this widget from being shown
                # if the Current button is pushed several times in a row: the widget is always shown
                # the first time, but not after that on MacOS 10.8.2
#           self.statusBar.setMsg("Hold mode: guide controls disabled",
#               severity=RO.Constants.sevWarning,
#           )
        self.showCurrWdg.setSeverity(sev)

        self.enableCmdButtons()

        if not doShowCurr:
            return

        # show first fully downloaded image, if any, else most recent not-fully-downloaded image,
        # else show nothing
        revHist = list(self.imObjDict.values())
        if not revHist:
            self.clearImage()
            return

        for imObj in revHist:
            if imObj.isDone():
                break
        else:
            imObj = revHist[0]

        self.showImage(imObj, forceCurr=True)

    def doShowHideImage(self, wdg=None):
        """Handle show/hide image button
        """
        doShow = self.showHideImageWdg.getBool()
        if doShow:
            self.gim.grid()
        else:
            self.gim.grid_remove()

    def doSubFrameToFull(self, wdg=None):
        """Set subframe input controls to full frame"""
        self.subFrameWdg.subFrame.setFullFrame()
        self.subFrameWdg.update()

    def doSubFrameToView(self, wdg=None):
        """Set subframe input controls to match current view.
        """
        subFrame = self.getViewSubFrame()
        if not subFrame:
            self.statusBar.setMsg("Could not compute subframe", severity = RO.Constants.sevWarning)
            return

        self.subFrameWdg.setSubFrame(subFrame)

        self.subFrameToViewBtn.setEnable(False)

    def drawCenterSelArrow(self, dumEvt=None):
        """Draw or redraw the "center selection" arrow
        """
        if self.centerBtn["state"] != "normal":
            return

        selStarData = self.dispImObj.selDataColor[0]
        selCnvPos = self.gim.cnvPosFromImPos(selStarData[2:4])
        boreCnvPos = self.gim.cnvPosFromImPos(self.boreXY)
        self.centerSelArrow = self.gim.cnv.create_line(
            selCnvPos[0], selCnvPos[1], boreCnvPos[0], boreCnvPos[1],
            fill = self.boreColorPref.getValue(),
            tags = _CtrlClickTag,
            arrow = "last",
        )

    def drawCtrlClickSelection(self, evt):
        """Draw a ctrl-click selection at the cursor
        """
        if not self.ctrlClickOK or not self.gim.isNormalMode():
            return

        self.eraseSelection()

        if not self.gim.evtOnCanvas(evt):
            # mouse is off canvas; erase selection
            return

        cnvPos = self.gim.cnvPosFromEvt(evt)
        imPos = self.gim.imPosFromCnvPos(cnvPos)

        # get current image object
        if not self.imDisplayed():
            return

        # erase data for now (helps for early return)
        self.dispImObj.selDataColor = None

        # create new "star"
        tag, colorPref = self.typeTagColorPrefDict["c"]
        color = colorPref.getValue()

        starData = [None]*15
        starData[0] = "c" # type
        starData[1] = 0 # index; irrelevant
        starData[2:4] = imPos
        starData[6] = 5 # radius of centroid region
        self.dispImObj.selDataColor = (starData, color)

        self.gim.addAnnotation(
            GImDisp.ann_X,
            imPos = starData[2:4],
            isImSize = False,
            rad = _SelRad,
            tags = _SelTag,
            fill = self.dispImObj.selDataColor[1],
        )

    def enableCmdButtons(self, wdg=None):
        """Set enable of command buttons.
        """
        showCurrIm = self.showCurrWdg.getBool()
        isImage = self.imDisplayed()
        isCurrIm = isImage and not self.nextImWdg.getEnable()
        isSel = (self.dispImObj is not None) and (self.dispImObj.selDataColor is not None)
        isGuiding = self.isGuiding()
        isExec = (self.doingCmd is not None)
        isExecOrGuiding = isExec or isGuiding
        areParamsModified = self.areParamsModified()
        if _DebugBtnEnable:
            print("%s GuideWdg: showCurrIm=%s, isImage=%s, isCurrIm=%s, isSel=%s, isGuiding=%s, isExec=%s, isExecOrGuiding=%s, areParamsModified=%s" % \
            (self.actor, showCurrIm, isImage, isCurrIm, isSel, isGuiding, isExec, isExecOrGuiding, areParamsModified))
        try:
            self.getGuideArgStr()
            guideCmdOK = True
        except RuntimeError:
            guideCmdOK = False

        self.currentBtn.setEnable(areParamsModified)

        self.exposeBtn.setEnable(showCurrIm and not isExecOrGuiding)

        # most reasons for disabling centerBtn are given by whyNotCtrlClick
        reasonStr = self.whyNotCtrlClick()
        self.centerBtn.setEnable(isSel and not reasonStr)

        self.guideOnBtn.setEnable(showCurrIm and guideCmdOK and not isExecOrGuiding)

        self.applyBtn.setEnable(showCurrIm and isGuiding and isCurrIm and guideCmdOK and areParamsModified)

        guideState, guideStateCurr = self.guideModel.guideState.getInd(0)
        gsLower = guideState and guideState.lower()
        self.guideOffBtn.setEnable(gsLower in ("on", "starting"))

        self.cancelBtn.setEnable(isExec)
        self.ds9Btn.setEnable(isImage)
        if (self.doingCmd is not None) and (self.doingCmd[1] is not None):
            self.doingCmd[1].setEnable(False)

    def enableHistButtons(self):
        """Set enable of prev and next buttons"""
        revHist, currInd = self.getHistInfo()
        #print "currInd=%s, len(revHist)=%s, revHist=%s" % (currInd, len(revHist), revHist)
        enablePrev = enableNext = False
        prevGap = nextGap = False
        if (len(revHist) > 0) and (currInd is not None):
            prevInd = currInd + 1
            if prevInd < len(revHist):
                enablePrev = True
                if not self.dispImObj.isInSequence:
                    prevGap = True
                elif not (self.imObjDict[revHist[prevInd]]).isInSequence:
                    prevGap = True

            nextInd = currInd - 1
            if not self.showCurrWdg.getBool() and nextInd >= 0:
                enableNext = True
                if not self.dispImObj.isInSequence:
                    nextGap = True
                elif not (self.imObjDict[revHist[nextInd]]).isInSequence:
                    nextGap = True

        self.prevImWdg.setState(enablePrev, prevGap)
        self.nextImWdg.setState(enableNext, nextGap)

    def enableSubFrameBtns(self, sf=None):
        if not self.subFrameWdg.subFrame:
            self.subFrameToFullBtn.setEnable(False)
            self.subFrameToViewBtn.setEnable(False)
            return

        isFullFrame = self.subFrameWdg.isFullFrame()
        self.subFrameToFullBtn.setEnable(not isFullFrame)

        subFrame = self.getViewSubFrame()
        if not subFrame:
            sameView = False
        else:
            sameView = self.subFrameWdg.sameSubFrame(subFrame)

        self.subFrameToViewBtn.setEnable(not sameView)

    def endCtrlClickMode(self):
        """End control-click-drag-to-center mode
        """
        self.ctrlClickOK = False

    def endDragMode(self):
        """End drag-to-centroid-region mode
        """
        self.dragStart = None
        self.eraseDragRect()

    def eraseCenterSelArrow(self, dumEvt=None):
        """Erase the center selection arrow, if present
        """
        self.gim.cnv["cursor"] = self.defCnvCursor
        if self.centerSelArrow:
            try:
                self.gim.cnv.delete(self.centerSelArrow)
            finally:
                self.centerSelArrow = None

    def eraseDragRect(self, dumEvt=None):
        """Erase the drag rectangle, if present
        """
        if self.dragRect:
            try:
                self.gim.cnv.delete(self.dragRect)
            finally:
                self.dragRect = None

    def eraseSelection(self, dumEvt=None):
        """Erase current selection
        """
        # clear current selection
        self.gim.removeAnnotation(_SelTag)

        if not self.dispImObj:
            return
        self.dispImObj.selDataColor = None

    def fetchCallback(self, imObj):
        """Called when an image is finished downloading.
        """
        if self.dispImObj == imObj:
            # something has changed about the current object; update display
            self.showImage(imObj)
        elif self.showCurrWdg.getBool() and imObj.isDone():
            # a new image is ready; display it
            self.showImage(imObj)

        if self.currDownload and self.currDownload.isDone():
            # start downloading next image, if any
            if self.nextDownload:
                self.currDownload = self.nextDownload
                self.nextDownload = None
                if self.currDownload.state == imObj.Ready:
                    # download not already started, so start it already
                    self.currDownload.fetchFile()
            else:
                self.currDownload = None

    def getExpArgStr(self, inclThresh = True, inclRadMult = False, inclImgFile = True, modOnly = False):
        """Return exposure time, bin factor, etc.
        as a string suitable for a guide camera command.

        Inputs:
        - inclThresh: if True, the thresh argument is included
        - inclRadMult: if True, the radMult argument is included
        - inclImgFile: if True, the imgFile argument is included
        - modOnly: if True, only values that are not default are included

        The defaults are suitable for autoguiding.
        Set inclRadMult true for finding stars.
        Set inclRadMult false for manual guiding.

        Raise RuntimeError if imgFile wanted but no display image.
        """
        args = ArgList(modOnly)
        try:
            args.addKeyWdg("exptime", self.expTimeWdg)
        except Exception as e:
            # exptime is out of bounds
            self.statusBar.setMsg(RO.StringUtil.strFromException(e), severity = RO.Constants.sevWarning)
        else:
            # exptime is ok
            self.statusBar.setMsg("")

        args.addKeyWdg("bin", self.binFacWdg)

        if self.subFrameWdg.subFrame:
            binFac = self.binFacWdg.getNum() or 1
            subBeg, subSize = self.subFrameWdg.subFrame.getBinSubBegSize(binFac)
            #print "binFac=%s, subBeg=%s, subSize=%s, fullSize=%s" % \
            #   (binFac, subBeg, subSize, self.subFrameWdg.subFrame.fullSize)
            subEnd = subBeg + subSize - 1 # subEnd is included in the region
            print("vartype A: " + str(type(subEnd)))
            subBeg= subBeg.astype(numpy.int64)
            subEnd = subEnd.astype(numpy.int64)
            print("Vartype b: " + str(type(subBeg[0])))
            windowArg = "window=%s,%s,%s,%s" % (subBeg[0], subBeg[1], subEnd[0], subEnd[1]) #python3 must be ints here
            
            args.addArg(windowArg)

        if inclRadMult:
            args.addKeyWdg("radMult", self.radMultWdg)

        if inclThresh:
            args.addKeyWdg("thresh", self.threshWdg)

        if inclImgFile:
            if not self.imDisplayed():
                raise RuntimeError("No image")
            args.addArg("imgFile=%r" % (self.dispImObj.imageName,))

        return str(args)

    def getGuideArgStr(self, modOnly=False):
        """Return guide command arguments as a string.

        Inputs:
        - modOnly: if True, only include values the user has modified

        Note: guide mode is always included.

        Raise RuntimeError if guiding is not permitted.
        """
        guideMode = self.guideModeWdg.getString()
        if not guideMode:
            raise RuntimeError("Must select a guide mode")

        guideMode = guideMode.lower()
        argList = [guideMode]

        # error checking
        if guideMode != "manual" and not self.dispImObj:
            raise RuntimeError("No guide image")

        if guideMode == "field":
            selStarArg = self.getSelStarArgs("gstar", modOnly)
            if selStarArg:
                argList.append(selStarArg)

        expArgStr = self.getExpArgStr(
            inclThresh = True,
            inclRadMult = True,
            inclImgFile = True,
            modOnly = modOnly,
        )
        if expArgStr:
            argList.append(expArgStr)

        return " ".join(argList)

    def getHistInfo(self):
        """Return information about the location of the current image in history.
        Returns:
        - revHist: list of image names in history in reverse order (most recent first)
        - currImInd: index of displayed image in history
          or None if no image is displayed or displayed image not in history at all
        """
        revHist = list(self.imObjDict.keys())
        if self.dispImObj is None:
            currImInd = None
        else:
            try:
                currImInd = revHist.index(self.dispImObj.imageName)
            except ValueError:
                currImInd = None
        return (revHist, currImInd)

    def getSelStarArgs(self, posKey, modOnly=False):
        """Get guide command arguments appropriate for the selected star.

        Inputs:
        - posKey: name of star position keyword: one of gstar or centerOn
        - modOnly: if True, only return data if user has selected a different star
        """
        if not self.imDisplayed():
            raise RuntimeError("No image")

        if not self.dispImObj.selDataColor:
            raise RuntimeError("No star selected")

        if modOnly and self.dispImObj.defSelDataColor \
            and (self.dispImObj.defSelDataColor[0] == self.dispImObj.selDataColor[0]):
            return ""

        starData = self.dispImObj.selDataColor[0]
        pos = starData[2:4]
        rad = starData[6]
        return "%s=%.2f,%.2f cradius=%.1f" % (posKey, pos[0], pos[1], rad)

    def getViewSubFrame(self, reqFullSize=None):
        """Return subframe representing current view of image.

        Return None if cannot be computed.
        """
        if not self.imDisplayed():
            return None
        if not self.dispImObj.subFrame:
            return None
        if not self.dispImObj.binFac:
            return None
        if numpy.any(self.dispImObj.subFrame.fullSize != self.guideModel.gcamInfo.imSize):
            return None

        begImPos = self.gim.begIJ[::-1]
        endImPos = self.gim.endIJ[::-1]
        binSubBeg, binSubSize = self.dispImObj.subFrame.getBinSubBegSize(self.dispImObj.binFac)
        numpy.add(binSubBeg, begImPos, binSubBeg)
        numpy.subtract(endImPos, begImPos, binSubSize)
        return SubFrame.SubFrame.fromBinInfo(self.guideModel.gcamInfo.imSize, self.dispImObj.binFac, binSubBeg, binSubSize)

    def ignoreEvt(self, dumEvt=None):
        pass

    def imDisplayed(self):
        """Return True if an image is being displayed (with data).
        """
        return self.dispImObj and (self.gim.dataArr is not None)

    def imObjFromKeyVar(self, keyVar):
        """Return imObj that matches keyVar's cmdr and cmdID, or None if none"""
        cmdInfo = self.currCmds.getCmdInfoFromKeyVar(keyVar)
        if not cmdInfo:
            return None
        return cmdInfo.imObj

    def isDispObj(self, imObj):
        """Return True if imObj is being displayed, else False"""
        return self.dispImObj and (self.dispImObj.imageName == imObj.imageName)

    def isGuiding(self):
        """Return True if guiding"""
        guideState, guideStateCurr = self.guideModel.guideState.getInd(0)
        if guideState is None:
            return False

        return guideState.lower() != "off"

    def redisplayImage(self, *args, **kargs):
        """Redisplay current image"""
        if self.dispImObj:
            self.showImage(self.dispImObj)

    def setGuideState(self, *args, **kargs):
        """Set guideState widget based on guideState and guideMode"""
        guideState, isCurrent = self.guideModel.guideState.get()
        mainState = guideState[0] and guideState[0].lower()
        guideState = [item for item in guideState if item]
        if mainState and mainState != "off":
            guideMode, modeCurrent = self.guideModel.guideMode.getInd(0)
            if guideMode:
                guideState.insert(1, guideMode)
                isCurrent = isCurrent and modeCurrent
        stateStr = "-".join(guideState)
        self.guideStateWdg.set(stateStr, isCurrent=isCurrent)

    def setRadMultWdg(self, imObj, forceCurr=False):
        """Set radMultWdg from data in imObj

        Checks for equality to the nearest 0.1 because that is all the guider outputs.

        Inputs:
        - imObj: image data (reads field radMult)
        - forceCurr: if True then modifies the displayed value even if wdg value is not current;
            otherwise only updates the displayed value if wdg value is already current
        """
        if forceCurr or self.radMultWdg.getIsCurrent() \
            or (round(self.radMultWdg.getNum(), 1) == imObj.radMult):
            self.radMultWdg.set(imObj.radMult, isCurrent=True)
        self.radMultWdg.setDefault(imObj.radMult)

    def setThreshWdg(self, imObj, forceCurr=False):
        """Set threshWdg from data in imObj

        Checks for equality to the nearest 0.1 because that is all the guider outputs.

        Inputs:
        - imObj: image data (reads field thresh)
        - forceCurr: if True then modifies the displayed value even if wdg value is not current;
            otherwise only updates the displayed value if wdg value is already current
        """
        if forceCurr or self.threshWdg.getIsCurrent() \
            or (round(self.threshWdg.getNum(), 1) == imObj.thresh):
            self.threshWdg.set(imObj.thresh)
        self.threshWdg.setDefault(imObj.thresh)

    def showFITSFile(self, imPath):
        """Display a FITS file.
        """
        # try to split off user's base dir if possible
        localBaseDir = ""
        imageName = imPath
        startDir = self.tuiModel.prefs.getValue("Save To")
        if startDir is not None:
            startDir = RO.OS.expandPath(startDir)
            if startDir and not startDir.endswith(os.sep):
                startDir = startDir + os.sep
            imPath = RO.OS.expandPath(imPath)
            if imPath.startswith(startDir):
                localBaseDir = startDir
                imageName = imPath[len(startDir):]

        #print "localBaseDir=%r, imageName=%r" % (localBaseDir, imageName)
        imObj = GuideImage.GuideImage(
            localBaseDir = localBaseDir,
            imageName = imageName,
            isLocal = True,
        )
        self._trackMem(imObj, str(imObj))
        imObj.fetchFile()
        if self.dispImObj is not None:
            try:
                self.imObjDict.index(self.dispImObj.imageName)
            except KeyError:
                pass
        self.showImage(imObj)

    def showImage(self, imObj, forceCurr=None):
        """Display an image.

        Inputs:
        - imObj image to display
        - forceCurr force guide params to be set to current value?
            if None then automatically set based on the Current button
        """
        self.boreXY = None
        self.endCtrlClickMode()
        self.endDragMode()
        #print "showImage(imObj=%s)" % (imObj,)
        # expire current image if not in history (this should never happen)
        if (self.dispImObj is not None) and (self.dispImObj.imageName not in self.imObjDict):
            sys.stderr.write("GuideWdg warning: expiring display image that was not in history\n")
            self.dispImObj.expire()

        fitsIm = imObj.getFITSObj() # note: this sets various useful attributes of imObj such as binFac
        mask = None
        #print "fitsIm=%s, self.gim.ismapped=%s" % (fitsIm, self.gim.winfo_ismapped())
        if fitsIm:
            #self.statusBar.setMsg("", RO.Constants.sevNormal)
            imArr = fitsIm[0].data
            if imArr is None:
                self.gim.showMsg("Image %s has no data in plane 0" % (imObj.imageName,),
                    severity=RO.Constants.sevWarning)
                return
            imHdr = fitsIm[0].header

            if len(fitsIm) > 1 and \
                fitsIm[1].data.shape == imArr.shape and \
                fitsIm[1].data.dtype == numpy.uint8:
                mask = fitsIm[1].data

        else:
            if imObj.didFail():
                sev = RO.Constants.sevNormal
            else:
                if (imObj.state == imObj.Ready) and self.gim.winfo_ismapped():
                    # image not downloaded earlier because guide window was hidden at the time
                    # get it now
                    imObj.fetchFile()
                sev = RO.Constants.sevNormal
            self.gim.showMsg(imObj.getStateStr(), sev)
            imArr = None
            imHdr = None

        # check size of image subFrame; if it doesn't match, then don't use it
        if imObj.subFrame is not None and numpy.any(imObj.subFrame.fullSize != self.guideModel.gcamInfo.imSize):
            #print "image has wrong full size; subframe will not show current image"
            imObj.subFrame = None

        # display new data
        self.gim.showArr(imArr, mask = mask)
        self.dispImObj = imObj
        self.imNameWdg.set(imObj.imageName)
        self.imNameWdg.xview("end")

        # update guide params
        # if looking through the history then force current values to change
        # otherwise leave them alone unless they are already tracking the defaults
        if forceCurr is None:
            forceCurr = not self.showCurrWdg.getBool()

        if forceCurr or self.expTimeWdg.getIsCurrent():
            self.expTimeWdg.set(imObj.expTime)
        self.expTimeWdg.setDefault(imObj.expTime)

        if forceCurr or self.binFacWdg.getIsCurrent():
            self.binFacWdg.set(imObj.binFac)
        self.binFacWdg.setDefault(imObj.binFac)

        self.setThreshWdg(imObj, forceCurr=forceCurr)

        self.setRadMultWdg(imObj, forceCurr=forceCurr)

        if imObj.subFrame:
            if forceCurr or self.subFrameWdg.getIsCurrent():
                self.subFrameWdg.setSubFrame(imObj.subFrame)
            self.subFrameWdg.setDefSubFrame(imObj.subFrame)

        self.enableHistButtons()

        if imArr is not None:
            # add existing annotations, if any and show selection
            # (for now just display them,
            # but eventually have a control that can show/hide them,
            # and -- as the first step -- set the visibility of the tags appropriately)
            for typeChar in ("f", "g", "c"):
                starDataList = imObj.starDataDict.get(typeChar)
                if not starDataList:
                    continue
                for starData in starDataList:
                    self.showStar(starData)

            if self.guideModel.gcamInfo.isSlitViewer and imHdr:
                boreXYFITS = imHdr.get("CRPIX1"), imHdr.get("CRPIX2")
                if None not in boreXYFITS:
                    # boresight position known; display it
                    self.boreXY = numpy.subtract(boreXYFITS, 0.5, dtype=float)
                    boreColor = self.boreColorPref.getValue()
                    self.gim.addAnnotation(
                        GImDisp.ann_Plus,
                        imPos = self.boreXY,
                        rad = _BoreRad,
                        isImSize = False,
                        tags = _BoreTag,
                        fill = boreColor,
                    )

            self.showSelection()

    def showSelection(self):
        """Display the current selection.
        """
        # clear current selection
        self.gim.removeAnnotation(_SelTag)

        if not self.dispImObj or not self.dispImObj.selDataColor:
            # disable command buttons accordingly
            self.enableCmdButtons()

            # clear data display
            self.starXPosWdg.set(None)
            self.starYPosWdg.set(None)
            self.starFWHMWdg.set(None)
            self.starAmplWdg.set(None)
            self.starBkgndWdg.set(None)
            return

        starData, color = self.dispImObj.selDataColor

        # draw selection
        self.gim.addAnnotation(
            GImDisp.ann_X,
            imPos = starData[2:4],
            isImSize = False,
            rad = _SelRad,
            holeRad = _SelHoleRad,
            tags = _SelTag,
            fill = color,
        )

        # update data display
        self.starXPosWdg.set(starData[2])
        self.starYPosWdg.set(starData[3])
        if None in starData[8:10]:
            fwhm = None
        else:
            fwhm = (starData[8] + starData[9]) / 2.0
        self.starFWHMWdg.set(fwhm)
        self.starAmplWdg.set(starData[14])
        self.starBkgndWdg.set(starData[13])

        # enable command buttons accordingly
        self.enableCmdButtons()

    def showStar(self, starData):
        """Display data about a star on the current image."""
        typeChar = starData[0].lower()
        xyPos = starData[2:4]
        rad = starData[6]
        tag, colorPref = self.typeTagColorPrefDict[typeChar]
        color = colorPref.getValue()
        if (None not in xyPos) and (rad is not None):
            self.gim.addAnnotation(
                GImDisp.ann_Circle,
                imPos = xyPos,
                rad = rad,
                isImSize = True,
                tags = tag,
                outline = color,
            )
        if typeChar == "g":
            if (None not in xyPos):
                self.gim.addAnnotation(
                    GImDisp.ann_Plus,
                    imPos = starData[2:4],
                    rad = _GuideRad,
                    holeRad = _GuideHoleRad,
                    isImSize = False,
                    tags = tag,
                    fill = color,
                )
            xyPredPos = starData[15:17]
            if None not in xyPredPos:
                self.gim.addAnnotation(
                    GImDisp.ann_Plus,
                    imPos = xyPredPos,
                    rad = _GuidePredPosRad,
                    isImSize = False,
                    tags = tag,
                    fill = color,
                )

    def updBinFac(self, binFacWdg=None):
        """Handle updated bin factor.
        The displayed value is used by the subframe widget
        to determine if current subframe = default subframe
        at the current bin factor.
        """
        newBinFac = self.binFacWdg.getNum() or 1

        self.subFrameWdg.setBinFac(newBinFac)

    def updFiles(self, fileData, isCurrent, keyVar):
        """Handle files keyword
        """
        #print "%s updFiles(fileData=%r; isCurrent=%r)" % (self.actor, fileData, isCurrent)
        if not isCurrent:
            return

        cmdChar, isNew, imageDir, imageName = fileData[0:4]
        cmdr, cmdID = keyVar.getCmdrCmdID()
        imageName = imageDir + imageName

        if not isNew:
            # handle data for existing image
            self.doExistingImage(imageName, cmdChar, cmdr, cmdID)
            return

        # at this point we know we have a new image

        # create new object data
        localBaseDir = self.guideModel.ftpSaveToPref.getValue()
        imObj = GuideImage.GuideImage(
            localBaseDir = localBaseDir,
            imageName = imageName,
            downloadWdg = self.guideModel.downloadWdg,
            fetchCallFunc = self.fetchCallback,
        )
        self._trackMem(imObj, str(imObj))
        self.addImToHist(imObj)

        if self.gim.winfo_ismapped():
            if not self.currDownload:
                # nothing being downloaded, start downloading this image
                self.currDownload = imObj
                imObj.fetchFile()
                if (self.dispImObj is None or self.dispImObj.didFail()) and self.showCurrWdg.getBool():
                    # nothing already showing so display the "downloading" message for this image
                    self.showImage(imObj)
            else:
                # queue this up to be downloaded (replacing any image already there)
                self.nextDownload = imObj
        elif self.showCurrWdg.getBool():
            self.showImage(imObj)

        # create command info
        self.currCmds.addCmd(
            cmdr = cmdr,
            cmdID = cmdID,
            cmdChar = cmdChar,
            imObj = imObj,
            isNewImage = True,
        )

        # purge excess images
        if self.dispImObj:
            dispImName = self.dispImObj.imageName
        else:
            dispImName = ()
        isNewest = True
        if len(self.imObjDict) > self.nToSave:
            keys = list(self.imObjDict.keys())
            for imName in keys[self.nToSave:]:
                if imName == dispImName:
                    if not isNewest:
                        self.imObjDict[imName].isInSequence = False
                    continue
                if _DebugMem:
                    print("Purging %r from history" % (imName,))
                purgeImObj = self.imObjDict.pop(imName)
                purgeImObj.expire()
                isNewest = False
        self.enableHistButtons()

    def updLocGuideMode(self, guideMode, isCurrent, keyVar):
        """New locGuideMode data found.

        Unlike guideMode, the only possible values are "boresight", "field", "manual", None or ""
        and lowercase is guaranteed
        """
        #print "%s updLocGuideMode(guideMode=%r, isCurrent=%r)" % (self.actor, guideMode, isCurrent)
        if not guideMode or not isCurrent:
            return

        if self.showCurrWdg.getBool():
            if self.guideModeWdg.getIsCurrent():
                self.guideModeWdg.set(guideMode)
            self.guideModeWdg.setDefault(guideMode)

    def updExpState(self, expState, isCurrent, keyVar):
        """exposure state has changed. expState is:
        - user name
        - exposure state string (e.g. flushing, reading...)
        - start timestamp
        - remaining time for this state (sec; 0 or None if short or unknown)
        - total time for this state (sec; 0 or None if short or unknown)
        """
        if not isCurrent:
            self.expStateWdg.setNotCurrent()
            return

        expStateStr, startTime, remTime, netTime = expState
        lowState = expStateStr.lower()
        remTime = remTime or 0.0 # change None to 0.0
        netTime = netTime or 0.0 # change None to 0.0

        if lowState == "paused":
            errState = RO.Constants.sevWarning
        else:
            errState = RO.Constants.sevNormal
        self.expStateWdg.set(expStateStr, severity = errState)

        if not keyVar.isGenuine():
            # data is cached; don't mess with the countdown timer
            return

        exposing = lowState in ("integrating", "resume")

        if netTime > 0:
            # print "starting a timer; remTime = %r, netTime = %r" % (remTime, netTime)
            # handle a countdown timer
            # it should be stationary if expStateStr = paused,
            # else it should count down
            if lowState in ("integrating", "resume"):
                # count up exposure
                self.expTimer.start(
                    value = netTime - remTime,
                    newMax = netTime,
                    countUp = True,
                )
            elif lowState == "paused":
                # pause an exposure with the specified time remaining
                self.expTimer.pause(
                    value = netTime - remTime,
                )
            else:
                # count down anything else
                self.expTimer.start(
                    value = remTime,
                    newMax = netTime,
                    countUp = False,
                )
            self.expTimer.grid()
        else:
            # hide countdown timer
            self.expTimer.grid_remove()
            self.expTimer.clear()

#        if self.exposing in (True, False) \
#            and self.exposing != exposing \
#            and self.winfo_ismapped():
#            if exposing:
#                TUI.PlaySound.exposureBegins()
#            else:
#                TUI.PlaySound.exposureEnds()

        self.exposing = exposing


    def updGuideState(self, guideState, isCurrent, keyVar=None):
        """Guide state changed"""
        self.setGuideState()
        if not isCurrent:
            return

        # handle disable of guide on button when guiding starts
        # (unlike other commands, "guide on" doesn actually end
        # until guiding terminates!)
        if self.doingCmd and self.doingCmd[2]:
            gsLower = guideState[0] and guideState[0].lower()
            if gsLower != "off":
                self.doingCmd = None
        self.enableCmdButtons()

    def updMaskColor(self, *args, **kargs):
        """Handle new mask color preference"""
        for ind in range(len(self.maskColorPrefs)):
            self.gim.maskInfo[ind].setColor(self.maskColorPrefs[ind].getValue())
        self.redisplayImage()

    def updStar(self, starData, isCurrent, keyVar):
        """New star data found.

        Overwrite existing findStars data if:
        - No existing data and cmdr, cmdID match
        - I generated the command
        else ignore.

        Replace existing centroid data if I generated the command,
        else ignore.
        """
        #print "%s updStar(starData=%r, isCurrent=%r)" % (self.actor, starData, isCurrent)
        if not isCurrent:
            return

        # get data about current command
        cmdInfo = self.currCmds.getCmdInfoFromKeyVar(keyVar)
        if not cmdInfo:
            return

        imObj = cmdInfo.imObj
        isVisible = imObj.isDone() and self.isDispObj(imObj) and self.winfo_ismapped()

        typeChar = starData[0].lower()
        try:
            tag, colorPref = self.typeTagColorPrefDict[typeChar]
            color = colorPref.getValue()
        except KeyError:
            raise RuntimeError("Unknown type character %r for star data" % (typeChar,))

        sawStarData = cmdInfo.sawStarData(typeChar)

        doClear = False
        if cmdInfo.isNewImage:
            if (typeChar == "c") and (cmdInfo.cmdChar == "g"):
                # ignore "c" star data for guide images,
                # at least until the hub stops sending it as duplicates of "g" star data
                return
            if typeChar in imObj.starDataDict:
                imObj.starDataDict[typeChar].append(starData)
            else:
                imObj.starDataDict[typeChar] = [starData]
        else:
            if sawStarData:
                if typeChar in imObj.starDataDict:
                    imObj.starDataDict[typeChar].append(starData)
                else:
                    imObj.starDataDict[typeChar] = [starData]
            else:
                """Note: if we ever support multiple guide stars
                then it will be important to allow multiple current centroids;
                the trick then will be to delete any existing centroid that is "too close"
                to the new one.

                Meanwhile, it is much easier to clear out all existing data,
                regardless of where it came from.
                """
                imObj.starDataDict[typeChar] = [starData]
                doClear = True

        if not sawStarData:
            if None in starData[2:4]:
                imObj.defSelDataColor = None
            else:
                imObj.defSelDataColor = (starData, color)
            imObj.selDataColor = imObj.defSelDataColor
            if isVisible:
                self.showSelection()

        if not isVisible:
            # this image is not being displayed, so we're done
            return

        if doClear:
            # clear all stars of this type
            self.gim.removeAnnotation(tag)

        # add this star to the display
        self.showStar(starData)

    def updFSActRadMult(self, radMult, isCurrent, keyVar):
        """New radMult data found.
        """
#         print "%s updFSActRadMult(radMult=%r, isCurrent=%r)" % (self.actor, radMult, isCurrent)
        if not isCurrent:
            return

        imObj = self.imObjFromKeyVar(keyVar)
        if imObj is None:
            return

        imObj.radMult = radMult

        if self.isDispObj(imObj):
            self.setRadMultWdg(imObj)

    def updFSActThresh(self, thresh, isCurrent, keyVar):
        """New threshold data found.
        """
#         print "%s updFSActThresh(thresh=%r, isCurrent=%r)" % (self.actor, thresh, isCurrent)
        if not isCurrent:
            return

        imObj = self.imObjFromKeyVar(keyVar)
        if imObj is None:
            return

        imObj.thresh = thresh

        if self.isDispObj(imObj):
            self.setThreshWdg(imObj)

    def updFSDefRadMult(self, radMult, isCurrent, keyVar):
        """Saw fsDefRadMult

        Set the default for the RadMult widget, but only if it's not already set
        """
#         print "%s updFSDefRadMult(radMult=%r, isCurrent=%r)" % (self.actor, radMult, isCurrent)
        if not isCurrent:
            return

        if not self.radMultWdg.getDefault():
            self.radMultWdg.setDefault(radMult)

    def updFSDefThresh(self, thresh, isCurrent, keyVar):
        """Saw fsDefThresh

        Set the default for the Thresh widget, but only if it's not already set
        """
#         print "%s updFSDefThresh(thresh=%r, isCurrent=%r)" % (self.actor, thresh, isCurrent)
        if not isCurrent:
            return

        if not self.threshWdg.getDefault():
            self.threshWdg.setDefault(thresh)

    def whyNotCtrlClick(self, evt=None):
        """Is ctrl-click permitted (for centering up on the pointer position)?

        Return None if one can center, or a reason why not if not
        """
        if _DebugCtrlClick:
            print("WARNING: _DebugCtrlClick is True")
            return None

        if not self.guideModel.gcamInfo.isSlitViewer:
            return "not a slitviewer"

        if not self.imDisplayed():
            return "no image displayed"

        if not self.showCurrWdg.getBool():
            return "image Hold mode"

        if not self.gim.isNormalMode():
            return "not default mode (+ icon)"

        if self.boreXY is None:
            return "boresight unknown"

        if self.isGuiding():
            return "auto-guiding"

        if self.doingCmd is not None:
            return "executing a command"

        if evt and not self.gim.evtOnCanvas(evt):
           return "event not on canvas"

        return None

    def _exitHandler(self):
        """Delete all image files
        """
        for imObj in self.imObjDict.values():
            imObj.expire()

    def _trackMem(self, obj, objName):
        """Print a message when an object is deleted.
        """
        if not _DebugMem:
            return
        objID = id(obj)
        def refGone(ref=None, objID=objID, objName=objName):
            print("GuideWdg deleting %s" % (objName,))
            del(self._memDebugDict[objID])

        self._memDebugDict[objID] = weakref.ref(obj, refGone)
        del(obj)


class ArgList(object):
    def __init__(self, modOnly):
        self.argList = []
        self.modOnly = modOnly

    def addArg(self, arg):
        """Add argument: arg
        modOnly is ignored.
        """
        self.argList.append(arg)

    def addKeyWdg(self, key, wdg):
        """Add argument: key=wdg.getString()
        If modOnly=True then the item is omitted if default.
        """
        if self.modOnly and wdg.isDefault():
            return
        strVal = wdg.getString()
        if strVal:
            self.argList.append("=".join((key, wdg.getString())))

    def addWdg(self, wdg):
        """If modOnly=True then the item is omitted if default.
        """
        if not self.modOnly or not wdg.isDefault():
            self.argList.append(wdg.getString())

    def __str__(self):
        return " ".join(self.argList)

if __name__ == "__main__":
    #import GuideTest
    from . import TestData
    #import gc
    #gc.set_debug(gc.DEBUG_SAVEALL) # or gc.DEBUG_LEAK to print lots of messages

    root = TestData.tuiModel.tkRoot

    # GuideTest.init("dcam")

    testFrame = GuideWdg(root, "tcam")
    testFrame.pack(expand="yes", fill="both")
    testFrame.wait_visibility() # must be visible to download images
    #GuideTest.setParams(expTime=5, thresh=3, radMult=1, mode="field")

    TestData.start(actor="tcam")

#     GuideTest.runDownload(
#       basePath = "keep/guiding/tcam/UT131023/",
#       imPrefix = "proc-t",
#       startNum = 1214,
#       numImages = 2,
#       waitMs = 2500,
#     )
#    testFrame.doChooseIm()

    TestData.animate()

    root.mainloop()
