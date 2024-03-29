#!/usr/bin/env python
"""Specialized version of RO.Wdg.LogWdg that adds nice filtering and text highlighting.

To do:
- Use automatic pink background for entry widgets to indicate if the value has been applied.

Known Issues:
- This log may hold more data than logSource (because it truncates excess data separately from logSource),
  but that extra data is fragile: you will lose it if you change the filter.
- Uses Python to check regular expressions for highlighting, even though tcl implements them;
  thus differences in Python and tcl's implementation of regular expression may result in subtle bugs.

History:
History:
2003-12-17 ROwen    Added addWindow and renamed to UsersWindow.py.
2004-05-18 ROwen    Stopped obtaining TUI model in addWindow; it was ignored.
2004-06-22 ROwen    Modified for RO.Keyvariable.KeyCommand->CmdVar
2004-07-22 ROwen    Play sound queue when user command finishes.
                    Warn (message and sound queue) if user command has no actor.
2004-08-25 ROwen    Do not leave command around if user command has no actor. It was confusing.
2004-09-14 ROwen    Minor change to make pychecker happier.
2005-08-02 ROwen    Modified for TUI.Sounds->TUI.PlaySound.
2006-03-10 ROwen    Modified to prepend UTC time to each logged message.
                    Modified to reject multi-line commands.
2006-03-16 ROwen    Modified to accept a command that ends with "\n".
2006-10-25 ROwen    Totally rewritten to use overhauled RO.Wdg.LogWdg.
2006-10-27 ROwen    Filtering and highlighting now show helpful messages in the status bar.
                    Changed the default severity from Warnings to Normal.
                    Regular expressions are checked and an error message shown if invalid.
                    Actors entries are checked and an error message shown if any don't match.
                    Fixed actor highlighting to remove old highlight.
2006-11-02 ROwen    Modified to filter by default.
2006-11-06 ROwen    Fixed filtering and highlighting to more reliably unfilter or unhighlight
                    for invalid inputs.
                    Fixed selections to show over highlighted text.
                    Added Prev and Next highlight buttons.
                    Clear "Removing highlight" message from status bar at instantiation.
2008-04-29 ROwen    Fixed reporting of exceptions that contain unicode arguments.
2009-07-22 ROwen    Bug fix: when an actor disappeared from the hub one could no longer filter on it.
2009-09-02 ROwen    Added support for sevCritical.
                    Modified to be resistant to additions to RO.Wdg.WdgPrefs SevPrefDict.
2010-03-10 ROwen    Added WindowName
2010-03-11 ROwen    Modified to use RO.Wdg.LogWdg 2010-11-11, which has severity support built in.
2010-05-04 ROwen    Restored None to the filter severity menu (it was lost in the 2010-03-11 changes).
2010-06-29 ROwen    Adopted multiple log support from STUI.
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
                    Added new filters: "Commands and Replies", "My Command and Replies" and "Custom"
                    (the latter of which uses python lambda expressions).
                    Removed filter "Commands".
                    Made the filter text widget wider.
                    Increased default maximum log length from 5000 to 20000.
                    Separated filter function into two separate components: severity filter and misc filter.
                    Filter description is now stored in function __doc__.
2011-06-17 ROwen    Modified filters "Commands and Replies" and "My Command and Replies" to hide debug messages.
2011-07-22 ROwen    Modified filter "Command and Replies" to ditch commands from MN01 (the site monitor)
                    and stopped filtering out apo.apo since the 3.5m apparently doesn't have an apo actor.
2011-07-25 ROwen    Changed default filter configuration from Normal to Warning + Commands and Replies.
2011-07-27 ROwen    Added "Commands" filter.
                    Upgraded filters to use new LogEntry fields cmdInfo and isKeys.
                    Bug fix: "Commands and Replies" did not show other user's commands.
                    Tweaked help text for "My Commands and Replies" to match STUI.
2011-07-28 ROwen    Bug fix: "Commands and Replies" filter was hiding CmdStarted and CmdDone messages.
2011-08-09 ROwen    Restored default filter to Normal.
2011-08-11 ROwen    Added a state tracker to track filter information.
2011-08-30 ROwen    Bug fix: Actor and Actors filters did not show commands sent to the actors.
2012-07-10 ROwen    Removed use of update_idletasks.
2012-11-13 ROwen    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
                    Cosmetic changes to make more similar to STUI's version (for easier diff).
2012-11-29 ROwen    Fix spelling of Run_Commands (the s was missing).
2015-11-05 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
"""
import bisect
import re
import tkinter
import RO.Alg
import RO.StringUtil
import RO.TkUtil
import RO.Wdg
import TUI.Models.HubModel
import TUI.TUIModel
import TUI.PlaySound
import TUI.Version
import collections.abc

HelpURL = "TUIMenu/LogWin.html"
WindowName = "%s.Log" % (TUI.Version.ApplicationName,)

def addWindow(tlSet):
    xBase = 496
    yBase = 534
    xDelta = 20
    yDelta = 20
    for i in range(TUI.TUIModel.MaxLogWindows):
        windowName = "%s %s" % (WindowName, i + 1)
        xPos = xBase + i * xDelta
        yPos = yBase + i * yDelta
        tlSet.createToplevel(
            name = windowName,
            defGeom = "736x411+%d+%d" % (xPos, yPos),
            resizable = True,
            visible = (i == 0),
            wdgFunc = TUILogWdg,
            doSaveState = True,
        )

FilterMenuPrefix = "+ "
HighlightLineColor = "#bdffe0"
HighlightColorScale = 0.92
HighlightTag = "highlighttag"
HighlightTextTag = "highlighttexttag"
ShowTag = "showtag"

ActorTagPrefix = "act_"
CmdrTagPrefix = "cmdr_"

class RegExpInfo(object):
    """Object holding a regular expression
    and associated tags.

    Checks the regular expression and raises RuntimeError if invalid.
    """
    def __init__(self, regExp, tag, lineTag):
        self.regExp = regExp
        self.tag = tag
        self.lineTag = lineTag
        try:
            re.compile(regExp)
        except re.error:
            raise RuntimeError("invalid regular expression %r" % (regExp,))

    def __str__(self):
        return "RegExpInfo(regExp=%r, tag=%r, lineTag=%r)" % \
            (self.regExp, self.tag, self.lineTag)

class TUILogWdg(tkinter.Frame):
    """A log widget that displays messages from the hub

    Filter Functions:
    Log messages are filtered using a pair of filter functions:
    - self.sevFilterFunc: filters out based on severity
    - self.miscFilterFunc: filters out based on other criteria
    Both filter functions take a single argument, a LogEntry,
    and return True if the entry is to be shown, False otherwise.
    The doc string may be None or a brief one-line description of the filter
    (long or multi-line doc strings will result in garbage in the status bar).
    """
    def __init__(self,
        master,
        maxCmds = 50,
        maxLines = 20000,
    **kargs):
        """
        Inputs:
        - master: master widget
        - maxCmds: maximun # of commands
        - maxLines: the max number of lines to display, ignoring wrapping
        - height: height of text area, in lines
        - width: width of text area, in characters
        - **kargs: additional keyword arguments for Frame
        """
        tkinter.Frame.__init__(self, master, **kargs)

        tuiModel = TUI.TUIModel.getModel()
        self.dispatcher = tuiModel.dispatcher
        self.logSource = tuiModel.logSource
        self.highlightRegExpInfo = None
        self.highlightTag = None
        self.isConnected = False
        self._stateTracker = RO.Wdg.StateTracker(logFunc = tuiModel.logFunc)

        # severity filter function: return True if severity filter criteria are met
        # for more information see the description of filter functions in class doc string
        self.sevFilterFunc = lambda x: False
        # miscellaneous filter function: return True if non-severity filter criteria are met
        self.miscFilterFunc = lambda x: False
        # highlightAllFunc(): clear existing highlighting and apply desired highlighting to all existing text
        self.highlightAllFunc = lambda: None
        # highlightLastFunc(): apply highlighting to last line of text and play sound if appropriate
        self.highlightLastFunc = lambda: None

        row = 0

        self.ctrlFrame1 = tkinter.Frame(self)
        ctrlCol1 = 0

        # Filter controls

        self.filterOnOffWdg = RO.Wdg.Checkbutton(
            self.ctrlFrame1,
            text = "Filter:",
            defValue = True,
            callFunc = self.doFilterOnOff,
            helpText = "enable or disable filtering",
            helpURL = HelpURL,
        )
        self.filterOnOffWdg.grid(row=0, column=ctrlCol1)
        ctrlCol1 += 1

        self.filterFrame = tkinter.Frame(self.ctrlFrame1)

        filtCol = 0

        self.severityMenu = RO.Wdg.OptionMenu(
            self.filterFrame,
            items = [val.title() for val in RO.Constants.NameSevDict.keys()] + ["None"],
            defValue = "Normal",
            callFunc = self.updateSeverity,
            helpText = "show replies with at least this severity",
            helpURL = HelpURL,
        )
        self._stateTracker.trackWdg("severity", self.severityMenu)
        self.severityMenu.grid(row=0, column=filtCol)
        filtCol += 1

        self.filterCats = ("Actor", "Actors", "Text", "Commands", "Commands and Replies", "My Commands and Replies", "Custom")
        filterItems = [""] + [FilterMenuPrefix + fc for fc in self.filterCats]
        self.filterMenu = RO.Wdg.OptionMenu(
            self.filterFrame,
            items = filterItems,
            defValue = "",
            callFunc = self.doFilter,
            helpText = "additional messages to show",
            helpURL = HelpURL,
        )
        self._stateTracker.trackWdg("filterMenu", self.filterMenu)
        self.filterMenu.grid(row=0, column=filtCol)
        filtCol += 1

        # grid all category-specific widgets in the same place
        # (but then show one at a time based on filterMenu)
        self.filterActorWdg = RO.Wdg.OptionMenu(
            self.filterFrame,
            items = ("",),
            defValue = "",
            callFunc = self.applyFilter,
            helpText = "show commands and replies for this actor",
            helpURL = HelpURL,
        )
        self._stateTracker.trackWdg("filterActor", self.filterActorWdg)
        self.filterActorWdg.grid(row=0, column=filtCol)

        self.filterActorsWdg = RO.Wdg.StrEntry(
            self.filterFrame,
            width = 20,
            doneFunc = self.applyFilter,
            helpText = "space-separated actors to show; . = any char; * = any chars",
            helpURL = HelpURL,
        )
        self._stateTracker.trackWdg("filterActors", self.filterActorsWdg)
        self.filterActorsWdg.grid(row=0, column=filtCol)

        self.filterTextWdg = RO.Wdg.StrEntry(
            self.filterFrame,
            width = 20,
            doneFunc = self.applyFilter,
            helpText = "text (regular expression) to show",
            helpURL = HelpURL,
        )
        self._stateTracker.trackWdg("filterText", self.filterTextWdg)
        self.filterTextWdg.grid(row=0, column=filtCol)

        self.filterCustomWdg = RO.Wdg.StrEntry(
            self.filterFrame,
            width = 40,
            doneFunc = self.applyFilter,
            helpText = "custom filter, a python lambda expression",
            helpURL = HelpURL,
        )
        self._stateTracker.trackWdg("filterCustom", self.filterCustomWdg)
        self.filterCustomWdg.set("lambda x: True")
        self.filterCustomWdg.grid(row=0, column=filtCol)

        # all filter controls that share a column have been gridded
        filtCol += 1

        self.filterFrame.grid(row=0, column=ctrlCol1)
        ctrlCol1 += 1

        # Find controls (and separator)

        # Note: controls are gridded instead of packed
        # so they can easily be hidden and shown
        # (there is no pack_remove command).

        #expandFrame = Tkinter.Frame(self).grid(row=0, column=ctrlCol1)
        self.ctrlFrame1.grid_columnconfigure(ctrlCol1, weight=1)
        ctrlCol1 += 1

        self.findButton = RO.Wdg.Button(
            master = self.ctrlFrame1,
            text = "Find:",
            command = self.doSearchBackwards,
            helpText = "press or type <return> to search backwards; type <ctrl-return> to search forwards",
            helpURL = HelpURL,
        )
        self.findButton.grid(row=0, column=ctrlCol1)
        ctrlCol1 += 1

        self.findEntry = RO.Wdg.StrEntry(
            master = self.ctrlFrame1,
            width = 15,
            helpText = "search regular expression; <return> to search backwards, <ctrl-return> forwards",
            helpURL = HelpURL,
        )
        self.findEntry.bind('<KeyPress-Return>', self.doSearchBackwards)
        self.findEntry.bind('<Control-Return>', self.doSearchForwards)
        self.findEntry.grid(row=0, column=ctrlCol1)

        self.ctrlFrame1.grid(row=row, column=0, sticky="ew")
        row += 1

        self.ctrlFrame2 = tkinter.Frame(self)
        ctrlCol2 = 0

        self.highlightOnOffWdg = RO.Wdg.Checkbutton(
            self.ctrlFrame2,
            text = "Highlight:",
            callFunc = self.doShowHideAdvanced,
            helpText = "enable or disable highlighting",
            helpURL = HelpURL,
        )
        self.highlightOnOffWdg.grid(row=0, column=ctrlCol2)
        ctrlCol2 += 1

        self.highlightFrame = tkinter.Frame(self.ctrlFrame2)
        highlightCol = 0

        self.highlightCats = ("Actor", "Actors", "Commands", "Text")

        self.highlightMenu = RO.Wdg.OptionMenu(
            self.highlightFrame,
            items = self.highlightCats,
            defValue = "Text",
            callFunc = self.doHighlight,
            helpText = "show actor or command",
            helpURL = HelpURL,
        )
        self.highlightMenu.grid(row=0, column=highlightCol)
        highlightCol += 1

        # grid all category-specific widgets in the same place
        # (but then show one at a time based on highlightMenu)
        self.highlightActorWdg = RO.Wdg.OptionMenu(
            self.highlightFrame,
            items = ("",),
            defValue = "",
            callFunc = self.doHighlightActor,
            helpText = "highlight commands and replies for this actor",
            helpURL = HelpURL,
        )
        self.highlightActorWdg.grid(row=0, column=highlightCol)

        self.highlightActorsWdg = RO.Wdg.StrEntry(
            self.highlightFrame,
            width = 20,
            doneFunc = self.doHighlightActors,
            helpText = "space-separated actors to highlight; . = any char; * = any chars",
            helpURL = HelpURL,
        )
        self.highlightActorsWdg.grid(row=0, column=highlightCol)

        self.highlightCommandsWdg = RO.Wdg.StrEntry(
            self.highlightFrame,
            width = 20,
            doneFunc = self.doHighlightCommands,
            helpText = "space-separated command numbers to highlight; . = any char; * = any chars",
            helpURL = HelpURL,
        )
        self.highlightCommandsWdg.grid(row=0, column=highlightCol)

        self.highlightTextWdg = RO.Wdg.StrEntry(
            self.highlightFrame,
            width = 20,
            doneFunc = self.doHighlightText,
            helpText = "text to highlight; regular expression",
            helpURL = HelpURL,
        )
        self.highlightTextWdg.grid(row=0, column=highlightCol)

        # all highlight widgets that share a column have been gridded
        highlightCol += 1

        self.highlightPlaySoundWdg = RO.Wdg.Checkbutton(
            self.highlightFrame,
            text = "Play Sound",
            helpText = "play a sound when new highlighted text is received?",
            helpURL = HelpURL,
        )
        self.highlightPlaySoundWdg.grid(row=0, column=highlightCol)
        highlightCol += 1

        self.prevHighlightWdg = RO.Wdg.Button(
            self.highlightFrame,
            text = "\N{BLACK UP-POINTING TRIANGLE}", # "Prev",
            callFunc = self.doShowPrevHighlight,
            helpText = "show previous highlighted text",
            helpURL = HelpURL,
        )
        self.prevHighlightWdg.grid(row=0, column=highlightCol)
        highlightCol += 1

        self.nextHighlightWdg = RO.Wdg.Button(
            self.highlightFrame,
            text = "\N{BLACK DOWN-POINTING TRIANGLE}", # "Next",
            callFunc = self.doShowNextHighlight,
            helpText = "show next highlighted text",
            helpURL = HelpURL,
        )
        self.nextHighlightWdg.grid(row=0, column=highlightCol)
        highlightCol += 1

        self.highlightFrame.grid(row=0, column=ctrlCol2, sticky="w")
        ctrlCol2 += 1

        self.ctrlFrame2.grid(row=row, column=0, sticky="w")
        row += 1

        self.logWdg = RO.Wdg.LogWdg(
            self,
            maxLines = maxLines,
            helpURL = HelpURL,
        )
        self.logWdg.grid(row=row, column=0, sticky="nwes")
        self.grid_rowconfigure(row, weight=1)
        self.grid_columnconfigure(0, weight=1)
        row += 1

        self.statusBar = RO.Wdg.StatusBar(self, helpURL=HelpURL)
        self.statusBar.grid(row=row, column=0, sticky="ew")
        row += 1

        cmdFrame = tkinter.Frame(self)

        RO.Wdg.StrLabel(
            cmdFrame,
            text = "Command:"
        ).pack(side="left")

        self.defActorWdg = RO.Wdg.OptionMenu(
            cmdFrame,
            items = ("", "hub", "tcc", "gcam"),
            defValue = "",
            callFunc = self.doDefActor,
            helpText = "default actor for new commands",
            helpURL = HelpURL,
        )
        self.defActorWdg.pack(side="left")

        self.cmdWdg = RO.Wdg.CmdWdg(
            cmdFrame,
            maxCmds = maxCmds,
            cmdFunc = self.doCmd,
            helpText = "command to send to hub; <return> to send",
            helpURL = HelpURL,
        )
        self.cmdWdg.pack(side="left", expand=True, fill="x")

        cmdFrame.grid(row=5, column=0, columnspan=5, sticky="ew")

        hubModel = TUI.Models.HubModel.getModel()
        hubModel.actors.addCallback(self._actorsCallback)

        # dictionary of actor name, tag name pairs:
        # <actor-in-lowercase>: act_<actor-in-lowercase>
        self.actorDict = {"tui": "act_tui"}

        # set up and configure other tags
        hcPref = tuiModel.prefs.getPrefVar("Highlight Background")
        if hcPref:
            hcPref.addCallback(self.updHighlightColor, callNow=True)
        else:
            self.updHighlightColor(HighlightLineColor)
        self.logWdg.text.tag_configure(ShowTag, elide=False)
        self.logWdg.text.tag_raise("sel")

        self.updateSeverity()
        self.doFilterOnOff()
        self.doShowHideAdvanced()
        self.logWdg.text.bind('<KeyPress-Return>', RO.TkUtil.EvtNoProp(self.doSearchBackwards))
        self.logWdg.text.bind('<Control-Return>', RO.TkUtil.EvtNoProp(self.doSearchForwards))

        # clear "Removing highlight" message from status bar
        self.statusBar.clear()

        self.bind("<Unmap>", self.mapOrUnmap)
        self.bind("<Map>", self.mapOrUnmap)

    def appendLogEntry(self, logEntry):
        outStr = logEntry.getStr()
        self.logWdg.addOutput(outStr, tags=logEntry.tags, severity=logEntry.severity)
        self.highlightLastFunc()

    def applyFilter(self, wdg=None):
        """Apply current filter settings.
        """
        if not self.isConnected:
            return
        try:
            miscFilterFunc = self.createMiscFilterFunc()
            fullFilterDescr = " or ".join(descr for descr in (self.sevFilterFunc.__doc__, miscFilterFunc.__doc__) if descr)
            self.statusBar.setMsg(
                fullFilterDescr,
                isTemp = True,
            )
        except Exception as e:
            miscFilterFunc = lambda x: False
            self.statusBar.setMsg(
                str(e),
                severity = RO.Constants.sevError,
                isTemp = True,
            )
            TUI.PlaySound.cmdFailed()
        self.miscFilterFunc = miscFilterFunc

        retainScrollPos = not self.logWdg.isScrolledToEnd()
        if retainScrollPos:
            # "linestart" helps a problem wereby if the text widget has not been selected
            # then the result is in the middle of a line; the resulting index when this problem occurs
            # may not be perfect but it appears to be good enough
            midLineIndex = self.logWdg.text.index("@0,%d linestart" % (self.logWdg.winfo_height() / 2))
            midLineDateStr = self.logWdg.text.get(midLineIndex, "%s + 8 chars" % midLineIndex)
#             print "retainScrollPos: midLineIndex=%s, midLineDateStr=%s" % (midLineIndex, midLineDateStr)

        self.logWdg.clearOutput()
        # this is inefficient; logWdg does a lot of processing that is unnecessary
        # when inserting a lot of lines at once; add an insertMany method to avoid this
        strTagsSevList = [(logEntry.getStr(), logEntry.tags, logEntry.severity)
            for logEntry in self.logSource.entryList
            if self.sevFilterFunc(logEntry) or self.miscFilterFunc(logEntry)]
        self.logWdg.addOutputList(strTagsSevList)

        if retainScrollPos:
            strList = [strTagsSev[0] for strTagsSev in strTagsSevList]
            ind = bisect.bisect(strList, midLineDateStr)
            # indicate result in "lines from the end" so the reference is valid
            # even if the data is truncated (as it often will be)
            linesFromEnd = len(strList) - ind
            self.logWdg.text.see("end - %d lines" % (linesFromEnd,))

        self.highlightAllFunc()

    def clearHighlight(self, showMsg=True):
        """Remove all highlighting"""
        if showMsg:
            self.statusBar.setMsg(
                "Removing highlight",
                isTemp = True,
            )
        self.logWdg.text.tag_remove(HighlightTag, "0.0", "end")
        self.logWdg.text.tag_remove(HighlightTextTag, "0.0", "end")

    def compileRegExp(self, regExp, flags):
        """Attempt to compile the regular expression.
        Show error in status bar and return None if it fails.
        """
        try:
            return re.compile(regExp, flags)
        except Exception:
            self.statusBar.setMsg(
                "%r is not a valid regular expression" % (regExp,),
                severity = RO.Constants.sevError,
                isTemp = True,
            )
        return None

    def createMiscFilterFunc(self):
        """Return a function that filters based on current filter settings other than severity

        A filter function accepts one argument: a logEntry.
        It returns True if the logEntry is to be displayed, False otherwise.

        The result of the filter function is ORed with the results of self.sevFilterFunc.

        Return:
        - filter function; the doc string is set to a brief description of what the filter does
        """
        filterEnabled = self.filterOnOffWdg.getBool()
        filterCat = self.filterMenu.getString()
        filterCat = filterCat[len(FilterMenuPrefix):] # strip prefix
        #print "applyFilter: filterEnabled=%r; filterCat=%r" % (filterEnabled, filterCat)

        def nullFunc(logEntry):
            return False

        if not filterEnabled:
            return nullFunc

        if not filterCat:
            return nullFunc

        elif filterCat == "Actor":
            actor = self.filterActorWdg.getString().lower()
            if not actor:
                return nullFunc
            def filterFunc(logEntry, actor=actor):
                return (logEntry.actor == actor) \
                    or (logEntry.cmdInfo and (logEntry.cmdInfo.actor == actor))
            filterFunc.__doc__ = "actor=%s" % (actor,)
            return filterFunc

        elif filterCat == "Actors":
            regExpList = self.filterActorsWdg.getString().split()
            if not regExpList:
                return nullFunc
            actorSet = set(self.getActors(regExpList))

            def filterFunc(logEntry, actorSet=actorSet):
                return (logEntry.actor in actorSet) \
                    or (logEntry.cmdInfo and (logEntry.cmdInfo.actor in actorSet))
            filterFunc.__doc__ = "actor in %s" % (actorSet,)
            return filterFunc

        elif filterCat == "Text":
            regExp = self.filterTextWdg.getString()
            if not regExp:
                return nullFunc

            try:
                compiledRegEx = re.compile(regExp, re.I)
            except Exception:
                raise RuntimeError("Invalid regular expression %r" % (regExp,))
            def filterFunc(logEntry, compiledRegEx=compiledRegEx):
                return compiledRegEx.search(logEntry.msgStr)
            filterFunc.__doc__ = "text contains %s" % (regExp)
            return filterFunc

        elif filterCat == "Commands":
            def filterFunc(logEntry):
                return (logEntry.cmdr and logEntry.cmdr[0] != ".") \
                    and not logEntry.cmdr.startswith("MN01") \
                    and logEntry.cmdInfo \
                    and not logEntry.isKeys
            filterFunc.__doc__ = "most commands"
            return filterFunc

        elif filterCat == "Commands and Replies":
            def filterFunc(logEntry):
                return (logEntry.cmdr and logEntry.cmdr[0] != ".") \
                    and not logEntry.cmdr.startswith("MN01") \
                    and (logEntry.severity > RO.Constants.sevDebug) \
                    and not logEntry.isKeys
            filterFunc.__doc__ = "most commands and replies"
            return filterFunc

        elif filterCat == "My Commands and Replies":
            cmdr = self.dispatcher.connection.getCmdr()

            def filterFunc(logEntry, cmdr=cmdr):
                return (logEntry.cmdr == cmdr) \
                    and (logEntry.severity > RO.Constants.sevDebug) \
                    and not logEntry.isKeys \
                    and ((logEntry.cmdInfo is None) or (logEntry.cmdInfo.isMine))
            filterFunc.__doc__ = "my commands and replies"
            return filterFunc

        elif filterCat == "Custom":
            funcStr = self.filterCustomWdg.getString()
            if not funcStr:
                return nullFunc
            filterFunc = eval(funcStr)
            if not isinstance(filterFunc, collections.abc.Callable):
                raise RuntimeError("not a function: %s" % (funcStr,))
            filterFunc.__doc__ = funcStr
            return filterFunc

        else:
            raise RuntimeError("Bug: unknown filter category %s" % (filterCat,))

    def dispatchCmd(self, actorCmdStr):
        """Executes a command (if a dispatcher was specified).

        Inputs:
        - actorCmdStr: a string containing the actor
            and command, separated by white space.

        On error, logs a message (does not raise an exception).

        Implementation note: the command is logged by the dispatcher
        when it is dispatched.
        """
        actor = "TUI"
        try:
            actorCmdStr = actorCmdStr.strip()

            if "\n" in actorCmdStr:
                raise RuntimeError("Cannot execute multiple lines; use Run_Commands script instead.")

            try:
                actor, cmdStr = actorCmdStr.split(None, 1)
            except ValueError:
                raise RuntimeError("Cannot execute %r; no command found." % (actorCmdStr,))

            # issue the command
            RO.KeyVariable.CmdVar (
                actor = actor,
                cmdStr = cmdStr,
                callFunc = self._cmdCallback,
                dispatcher = self.dispatcher,
            )
        except Exception as e:
            self.statusBar.setMsg(
                RO.StringUtil.strFromException(e),
                severity = RO.Constants.sevError,
                isTemp = True,
            )
            TUI.PlaySound.cmdFailed()

    def doCmd(self, cmdStr):
        """Handle commands typed into the command bar.
        Note that dispatching the command automatically logs it.
        """
        self.dispatchCmd(cmdStr)
        self.logWdg.text.see("end")

        defActor = self.defActorWdg.getString()
        if not defActor:
            return
        self.cmdWdg.set(defActor + " ")
        self.cmdWdg.icursor("end")

    def doDefActor(self, wdg=None):
        """Handle default actor menu."""
        defActor = self.defActorWdg.getString()
        if defActor:
            defActor += " "

        actorCmd = self.cmdWdg.get()
        if not actorCmd:
            self.cmdWdg.set(defActor)
        else:
            actorCmdList = actorCmd.split(None, 1)
            if len(actorCmdList) > 1:
                self.bell()
            else:
                self.cmdWdg.set(defActor)

        self.cmdWdg.icursor("end")
        self.cmdWdg.focus_set()

    def doFilter(self, wdg=None):
        """Show appropriate filter widgets and compute and apply the filter function
        """
        filterCat = self.filterMenu.getString()
        filterCat = filterCat[len(FilterMenuPrefix):] # strip prefix
        #print "doFilter; cat=%r" % (filterCat,)

        for cat in self.filterCats:
            wdg = getattr(self, "filter%sWdg" % (cat,), None)
            if not wdg:
                continue
            if cat == filterCat:
                wdg.grid()
            else:
                wdg.grid_remove()

        self.applyFilter()

    def doFilterOnOff(self, wdg=None):
        doFilter = self.filterOnOffWdg.getBool()
        if doFilter:
            self.filterFrame.grid()
        else:
            self.filterFrame.grid_remove()
        self.doFilter()

    def doHighlight(self, wdg=None):
        """Show appropriate highlight widgets and apply appropriate function
        """
        self.highlightAllFunc = lambda: None
        self.highlightLastFunc = lambda: None
        highlightCat = self.highlightMenu.getString()
        highlightEnabled = self.highlightOnOffWdg.getBool()
        #print "doHighlight; cat=%r; enabled=%r" % (highlightCat, highlightEnabled)

        for cat in self.highlightCats:
            wdg = getattr(self, "highlight%sWdg" % (cat,))
            if cat == highlightCat:
                wdg.grid()
            else:
                wdg.grid_remove()

        # apply highlighting
        if highlightEnabled and highlightCat:
            func = getattr(self, "doHighlight%s" % (highlightCat,))
            func()
        else:
            self.clearHighlight()

    def doHighlightActor(self, wdg=None):
        actor = self.highlightActorWdg.getString().lower()
        if not actor:
            return
        self.highlightActors([actor])

    def doHighlightActors(self, wdg=None):
        regExpList = self.highlightActorsWdg.getString().split()
        if not regExpList:
            return
        try:
            actors = self.getActors(regExpList)
        except RuntimeError as e:
            self.statusBar.setMsg(RO.StringUtil.strFromException(e), severity = RO.Constants.sevError, isTemp = True)
            TUI.PlaySound.cmdFailed()
            return
        if not actors:
            return
        self.highlightActors(actors)

    def doHighlightCommands(self, wdg=None):
        self.clearHighlight()
        cmds = self.highlightCommandsWdg.getString().split()
        if not cmds:
            return

        # create regular expression
        # it must include my username so only my commands are shown
        # it must show both outgoing commands: UTCDate username cmdNum
        # and replies: UTCDate cmdNum
        orCmds = "|".join(["(%s)" % (cmd,) for cmd in cmds])

        cmdr = self.dispatcher.connection.getCmdr()

        regExp = r"^\d\d:\d\d:\d\d( +%s)? +(%s) " % (cmdr, orCmds)
        try:
            regExpInfo = RegExpInfo(regExp, None, HighlightTag)
        except RuntimeError:
            self.statusBar.setMsg(
                "Invalid command list %s" % (" ".join(cmds)),
                severity = RO.Constants.sevError,
                isTemp = True,
            )
            TUI.PlaySound.cmdFailed()
            return

        if len(cmds) == 1:
            self.statusBar.setMsg(
                "Highlighting commands %s" % (cmds[0],),
                isTemp = True,
            )
        else:
            self.statusBar.setMsg(
                "Highlighting commands %s" % (" ".join(cmds),),
                isTemp = True,
            )

        self.highlightRegExp(regExpInfo)

    def doHighlightText(self, wdg=None):
        self.clearHighlight()
        regExp = self.highlightTextWdg.getString()
        if not regExp:
            return

        try:
            regExpInfo = RegExpInfo(regExp, HighlightTextTag, HighlightTag)
        except RuntimeError:
            self.statusBar.setMsg(
                "Invalid regular expression %r" % (regExp,),
                severity = RO.Constants.sevError,
                isTemp = True,
            )
            TUI.PlaySound.cmdFailed()
            return

        self.statusBar.setMsg(
            "Highlighting text %r" % (regExp,),
            isTemp = True,
        )
        self.highlightRegExp(regExpInfo)

    def doPlayHighlightSound(self):
        """Return True if the highlight sound is enabled and the window is visible"""
        return self.highlightPlaySoundWdg.getBool() and self.winfo_ismapped()

    def doSearchBackwards(self, evt=None):
        """Search backwards for search string"""
        searchStr = self.findEntry.get()
        self.logWdg.search(searchStr, backwards=True, noCase=True, regExp=True)

    def doSearchForwards(self, evt=None):
        """Search backwards for search string"""
        searchStr = self.findEntry.get()
        self.logWdg.search(searchStr, backwards=False, noCase=True, regExp=True)

    def doShowHideAdvanced(self, wdg=None):
        if self.highlightOnOffWdg.getBool():
            self.highlightFrame.grid()
            self.doHighlight()
        else:
            self.highlightFrame.grid_remove()
            self.doHighlight()

    def doShowNextHighlight(self, wdg=None):
        self.logWdg.findTag(HighlightTag, backwards=False, doWrap=False)

    def doShowPrevHighlight(self, wdg=None):
        self.logWdg.findTag(HighlightTag, backwards=True, doWrap=False)

    def findRegExp(self, regExpInfo, removeTags=True, elide=False, startInd="1.0"):
        """Find and tag all lines containing text that matches regExp.

        Returns the number of matches.

        This is just self.text.findAll with a particular set of options.
        """
        #print "findRegExp(regExpInfo=%r, removeTags=%r, elide=%r, startInd=%r)" % (regExpInfo, removeTags, elide, startInd)

        # Warning: you must modify this to call findAll from "after"
        # if this function is called from a variable trace (e.g. an Entry callFunc).
        # Otherwise the count variable is not updated
        # and the routine raises RuntimeError.
        return self.logWdg.findAll(
            searchStr = regExpInfo.regExp,
            tag = regExpInfo.tag,
            lineTag = regExpInfo.lineTag,
            removeTags = removeTags,
            noCase = True,
            regExp = True,
            startInd = startInd,
        )

    def getActors(self, regExpList):
        """Return a sorted list of actor based on a set of actor name regular expressions.

        Raise RuntimeError if any regular expression is invalid or has no match.
        """
        if not regExpList:
            return []

        actors = set()
        compRegExpList = []
        for regExp in regExpList:
            if not regExp.endswith("$"):
                termRegExp = regExp + "$"
            else:
                termRegExp = regExp
            compRegExp = self.compileRegExp(termRegExp, re.IGNORECASE)
            if not compRegExp:
                raise RuntimeError("Invalid regular expression %r" % (regExp,))
            compRegExpList.append((compRegExp, regExp))

        badEntries = []
        for (compRegExp, regExp) in compRegExpList:
            foundMatch = False
            for actor in self.actorDict.keys():
                if compRegExp.match(actor):
                    actors.add(actor)
                    foundMatch = True
            if not foundMatch:
                badEntries.append(regExp)
        if badEntries:
            raise RuntimeError("No actors match %s" % (badEntries,))

        #print "getActors(%r) returning %r" % (regExpList, actors)
        actors = list(actors)
        actors.sort()
        return actors

    def getFilterSeverityDescr(self, appendAnd=True):
        """Return a description of the currently selected filter severity

        Inputs:
        - appendAnd: append "and" if severity is not None
        """
        sevName = self.severityMenu.getString().lower()
        if sevName == "none":
            return ""
        elif appendAnd:
            return "severity >= %s and" % (sevName,)
        else:
            return "severity >= %s" % (sevName,)

    def getSeverityTags(self):
        """Return a list of severity tags that should be displayed
        based on the current setting of the severity menu.
        """
        sevName = self.severityMenu.getString().lower()
        if sevName == "none":
            return []
        else:
            return self.logWdg.getSeverityTags(RO.Constants.NameSevDict[sevName])

    def getStateTracker(self):
        """Return the state tracker"""
        return self._stateTracker

    def highlightActors(self, actors):
        """Create highlight functions to highlight the supplied actors
        and apply highlighting to all existing text.
        """
        if len(actors) == 1:
            self.statusBar.setMsg(
                "Highlighting actor %s" % (actors[0]),
                isTemp = True,
            )
        else:
            self.statusBar.setMsg(
                "Highlighting actors %s" % (" ".join(actors)),
                isTemp = True,
            )

        tags = [ActorTagPrefix + actor.lower() for actor in actors]

        def highlightAllFunc(tags=tags):
            self.clearHighlight()
            for tag in tags:
                tagRanges = self.logWdg.text.tag_ranges(tag)
                if len(tagRanges) > 1:
                    self.logWdg.text.tag_add(HighlightTag, *tagRanges)

        def highlightLastFunc(tags=tags):
            for tag in tags:
                tagRanges = self.logWdg.text.tag_prevrange(tag, "end")
                if tagRanges:
                    self.logWdg.text.tag_add(HighlightTag, *tagRanges)
                    if self.doPlayHighlightSound():
                        TUI.PlaySound.logHighlightedText()
                    return # no need to test more tags and must not play the sound again

        self.highlightAllFunc = highlightAllFunc
        self.highlightLastFunc = highlightLastFunc
        self.highlightAllFunc()

    def highlightRegExp(self, regExpInfo):
        """Create highlight functions based on a RegExpInfo object
        and apply highlighting to all existing text.
        """
        def highlightAllFunc(regExpInfo=regExpInfo):
            self.clearHighlight()
            self.findRegExp(regExpInfo, removeTags=False)

        def highlightLastFunc(regExpInfo=regExpInfo):
            nFound = self.findRegExp(regExpInfo, removeTags = False, startInd = "end - 2 lines")
            if nFound > 0 and self.doPlayHighlightSound():
                TUI.PlaySound.logHighlightedText()

        self.highlightAllFunc = highlightAllFunc
        self.highlightLastFunc = highlightLastFunc
        self.highlightAllFunc()

    def logSourceCallback(self, logSource):
        """Log a message from the log source

        Inputs:
        - logEntry: a TUI.Models.LogSource.LogEntry object
        """
        logEntry = logSource.lastEntry
        if not logEntry:
            return
        if self.sevFilterFunc(logEntry) or self.miscFilterFunc(logEntry):
            self.appendLogEntry(logEntry)

    def mapOrUnmap(self, evt=None):
        """Called when the window is mapped or unmapped

        If withdrawing instead of iconifying then disconnect
        """
        wantConnection = self.winfo_toplevel().wm_state() != "withdrawn"
#        print "mapOrUnmap: wantConnect=%s; isConnected=%s" % (wantConnection, self.isConnected)
        if self.isConnected and not wantConnection:
            self.logSource.removeCallback(self.logSourceCallback)
            self.isConnected=False
            self.logWdg.clearOutput()
        elif wantConnection and not self.isConnected:
            self.logSource.addCallback(self.logSourceCallback)
            self.isConnected=True
            self.applyFilter()

    def updHighlightColor(self, newColor, colorPrefVar=None):
        """Update highlight color and highlight line color"""

        newTextColor = RO.TkUtil.addColors((newColor, HighlightColorScale))
        self.logWdg.text.tag_configure(HighlightTag, background=newColor)
        self.logWdg.text.tag_configure(HighlightTextTag, background=newTextColor)

    def updateSeverity(self, dumWdg=None):
        """The severity menu was changed. Update self.sevFilterFunc and refilter entries.
        """
        sevName = self.severityMenu.getString().lower()
        if sevName == "none":
            def filterFunc(logEntry):
                return False
        else:
            minSeverity = RO.Constants.NameSevDict[sevName]
            def filterFunc(logEntry, minSeverity=minSeverity):
                return logEntry.severity >= minSeverity
            filterFunc.__doc__ = "severity >= %s" % (sevName,)
        self.sevFilterFunc = filterFunc
        self.applyFilter()

    def _actorsCallback(self, actors, isCurrent, keyVar=None):
        """Actor keyword callback.
        """
        if not actors:
            return

        newActors = set(actor.lower() for actor in actors)
        currActors = set(self.actorDict.keys())
        sortedActors = sorted(list(newActors | currActors))

        self.actorDict = dict((actor, "act_" + actor) for actor in sortedActors)
        blankAndActors = [""] + sortedActors
        self.defActorWdg.setItems(blankAndActors, isCurrent = isCurrent)
        self.filterActorWdg.setItems(blankAndActors, isCurrent = isCurrent)
        self.highlightActorWdg.setItems(blankAndActors, isCurrent = isCurrent)

    def _cmdCallback(self, msgType, msgDict, cmdVar):
        """Command callback; called when a command finishes.
        """
        if cmdVar.didFail():
            TUI.PlaySound.cmdFailed()
        elif cmdVar.isDone():
            TUI.PlaySound.cmdDone()

    def __del__ (self, *args):
        """Going away; remove myself as the dispatcher's logger.
        """
        self.logSource.removeCallback(self.logSourceCallback)


if __name__ == '__main__':
    import random
    root = RO.Wdg.PythonTk()
    root.geometry("600x350")
    tuiModel = TUI.TUIModel.getModel(testMode = True)

    testFrame = TUILogWdg (
        master=root,
        maxLines=50,
    )
    testFrame.grid(row=0, column=0, sticky="nsew")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    severities = list(RO.Constants.SevNameDict.keys())

    cmdrs = (".tcc", "TU01.me", "UW02.other")
    cmdIDs = (0, 0, 0, 1, 2, 1001, 1002)
    actors = ("ecam", "disExpose","dis", "keys")
    msgTypes = ("d", "i", "w", "f")

    hubModel = TUI.Models.HubModel.getModel()
    hubModel.actors.set(actors)

    for ii in range(100):
        cmdr = random.choice(cmdrs)
        cmdID = random.choice(cmdIDs)
        actor = random.choice(actors)
        msgType = random.choice(msgTypes)
        msgDict = tuiModel.dispatcher.makeMsgDict(
            dataStr = 'Text="sample entry %s from %s"' % (ii, actor),
            msgType = msgType,
            actor = actor,
            cmdr = cmdr,
            cmdID = cmdID,
        )
        tuiModel.dispatcher.logMsgDict(msgDict)

    root.mainloop()
