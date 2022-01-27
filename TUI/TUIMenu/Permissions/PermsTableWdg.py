#!/usr/bin/env python
"""Specify what users from each program are allowed to do.

Note: the interface visible to the user uses the terms "add" and "delete"
because they are clear and succinct. However, the internal code use the
perms terminology "register" and "unregister" because they work
better in function calls when one might be toggling the state
and because the transition has to occur somewhere.

2003-12-19 ROwen    Preliminary version; html help is broken.
2003-12-29 ROwen    Implemented html help.
2004-07-22 ROwen    Updated for new RO.KeyVariable
2004-07-29 ROwen    Added read-only support.
2004-08-11 ROwen    Use modified RO.Wdg state constants with st_ prefix.
2004-09-03 ROwen    Modified for RO.Wdg.st_... -> RO.Constants.st_...
2004-11-16 ROwen    Modified for RO.Wdg.Label change.
2005-01-06 ROwen    Modified to use RO.Wdg.Label.setSeverity instead of setState.
                    Modified to use Checkbutton autoIsCurrent instead of
                    a separate changed indicator.
                    Fixed a bug in setReadOnly that prevented reliable toggling.
                    Fixed and improved test code.
2005-06-03 ROwen    Stopped setting checkbutton padx and pady (rely on new decent defaults).
                    Fixed irregular indentation (extra spaces).
2006-06-16 ROwen    Bug fix: helpSuffix arg was being ignored (caught by pychecker).
2006-04-10 ROwen    Fix PR 314: if a new actor was added, it was not properly displayed.
                    Modified so "sort" sorts actorList as well as programs.
2006-10-31 ROwen    Fix PR 511: program name widgets too narrow on unix.
2009-07-06 ROwen    Fix PR 940: permissions window does not handle new actorList properly.
                    Modified to always sort actorList; only programs may be out of order.
                    Modified for updated TestData.
2009-07-09 ROwen    Bug fix: bad class instance reference.
                    Modified test code to look more like tuisdss version.
2011-04-06 ROwen    Modified to order actors by category. To do: display separation between categories.
2011-04-08 ROwen    Renamed from PermsInputWdg to PermsTableWdg and made self-contained
                    (no need to create external frames for the header and scrolled table).
2011-07-27 ROwen    Modified to find PermsModel in TUI.Models.
2011-08-12 ROwen    Modified to highlight actor and program when the mouse is over a permission control.
2011-09-12 ROwen    Bug fix: resizing was somewhat messed up.
                    Improved alignment, especially on unix.
2011-09-28 ROwen    Bug fix: sorting and purging caused display errors
                    because _nameSpacerWdg was not reliably ungridded and regridded.
2011-10-12 ROwen    Bug fix: the row 2 permissions had a line across it after sorting (the width measuring frame).
2012-07-09 ROwen    Modified to use RO.TkUtil.Timer.
2012-08-10 ROwen    Updated for RO.Comm 3.0.
2012-11-13 ROwen    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
2012-11-19 ROwen    Fix PR 1396: program button sent the wrong command.
2013-10-11 ROwen    Removed an unused import (weakref) and an unused variable.
"""
import tkinter
import RO.Constants
import RO.Alg
if __name__ == "__main__":
    import RO.Comm.Generic
    RO.Comm.Generic.setFramework("tk")
from RO.Comm.Generic import Timer
import RO.KeyVariable
import RO.Wdg
import TUI.TUIModel
import TUI.Models.PermsModel

_HelpPrefix = "TUIMenu/PermissionsWin.html#"

_ProgramWidth = 10 # width of program control buttons: need room for "Lockout" and checkbuttons
_NewActorDelay = 1.0 # display disable delay (sec) while adding or removing actorList

class ActorList(object):
    """A list of actorList in category order

    Also keeps track of the title widgets, for highlighting the current one
    """
    def __init__(self, startCol=1):
        self._startCol = int(startCol)
        self._actorSet = set()
        self._colActorList = []
        self._titleWdgDict = {}
    
    def setActors(self, actors):
        """Set the actors
        
        Inputs:
        - actors: a collection of actors; order is ignored
        """
        self._actorSet = set(actors)
        # sort by category, then by actor name
        catActorList = sorted((self._getActorCategory(a), a) for a in actors)
        currCat = 1
        col = self._startCol
        self._colActorList = []
        for cat, actor in catActorList:
            if cat != currCat:
                self._colActorList.append((col, None))
                currCat = cat
                col += 1
            self._colActorList.append((col, actor))
            col += 1
    
    def getTitleWdg(self, actor):
        """Return the title widget for this actor, or None if not found
        """
        return self._titleWdgDict.get(actor)
    
    def setTitleWdg(self, actor, wdg):
        """Set the title widget for an actor
        """
        self._titleWdgDict[actor] = wdg
    
    def clearAllTitleWdg(self):
        """Clear all title widgets
        """
        self._titleWdgDict.clear()
    
    def getColActorList(self):
        """Return a list of (col, actor)
        """
        return self._colActorList
    
    def getActorSet(self):
        """Return the collection of actors as a set"""
        return self._actorSet
    
    def isSameActors(self, actors):
        """Return True if the set of actors is the same (ignoring order)
        """
        return self._actorSet == set(actors)
        
    def _getActorCategory(self, actor):
        """Return a category number for a given actor
        
        Returns one of:
        1: tcc, telmech and tlamps
        2: instruments
        3: guiders: dcam, ecam, gcam, tcam
        """
        return dict (
            gmech = 1,
            tcc = 1,
            telmech = 1,
            tlamps = 1,
            dcam = 3,
            ecam = 3,
            gcam = 3,
            tcam = 3,
        ).get(actor, 2)
    
    def __bool__(self):
        return len(self._actorSet) > 0


class PermsTableWdg(tkinter.Frame):
    """Inputs:
    - master        master widget
    - statusBar     status bar to handle commands.
    - readOnlyCallback  a function that is called when the readOnly state changes;
        the function receives one argument: isReadOnly: True for read only, False otherwise.
        Note that isReadOnly always starts out True.
    """
    def __init__(self,
        master,
        statusBar,
        readOnlyCallback = None,
    ):
        tkinter.Frame.__init__(self, master)
        self._statusBar = statusBar
        self._tuiModel = TUI.TUIModel.getModel()
        self._readOnlyCallback = readOnlyCallback

        self._actorList = ActorList(startCol=1)
        self._progDict = {} # prog name: prog perms

        self._titleWdgSet = []

        self._titleBorder = tkinter.Frame(self, borderwidth=2, relief="sunken")
        self._titleBorder.grid(row=0, column=0, sticky="ew")
        self._titleBorder.grid_columnconfigure(1, weight=1)
        
        self._titleFrame = tkinter.Frame(self._titleBorder, borderwidth=0)
        self._titleFrame.grid(row=0, column=0, sticky="w")
        
        self._scrollWdg = RO.Wdg.ScrolledWdg(
            master = self,
            hscroll = False,
            vscroll = True,
            borderwidth = 2,
            relief = "sunken",
        )
        self._scrollWdg.grid(row=1, column=0, sticky="nsew")
        self._tableFrame = tkinter.Frame(self._scrollWdg.getWdgParent(), borderwidth=0)
        self._vertMeasWdg = tkinter.Frame(self._tableFrame)
        self._vertMeasWdg.grid(row=0, column=0, sticky="wns")
        self._scrollWdg.setWdg(
            wdg = self._tableFrame,
            vincr = self._vertMeasWdg,
        )
        self.grid_rowconfigure(1, weight=1)
        
        self._nextRow = 0
        self._readOnly = True
        self._updActorTimer = Timer()
        
        self.permsModel = TUI.Models.PermsModel.getModel()
        
        self.permsModel.actors.addCallback(self._updActors)
        self.permsModel.authList.addCallback(self._updAuthList)
        self.permsModel.lockedActors.addCallback(self._updLockedActors)
        self.permsModel.programs.addCallback(self._updPrograms)
        
        self._lockoutRow = 3
        self._lockoutWdg = _LockoutPerms(
            master = self._titleFrame,
            actorList = self._actorList,
            readOnly = self._readOnly,
            row = self._lockoutRow,
            statusBar = self._statusBar,
        )

        statusBar.dispatcher.connection.addStateCallback(self.__connStateCallback)
    
    def purge(self):
        """Remove unregistered programs.
        """
        knownProgs = self.permsModel.programs.get()[0]

        # use items instead of iteritems so we can modify as we go
        for prog, progPerms in list(self._progDict.items()):
            if progPerms.isRegistered() or prog in knownProgs:
                continue
            progPerms.delete()
            del(self._progDict[prog])
    
    def sort(self):
        """Sort existing programs and redisplay all data.
        """
        self._actorList.clearAllTitleWdg()
        for wdg in self._titleWdgSet:
            wdg.destroy()
        for col, actor in self._actorList.getColActorList():
            if not actor:
                # insert dividor
                self._addTitle("  ", col)
            else:
                titleLabel = self._addTitle(actor, col)
                self._actorList.setTitleWdg(actor, titleLabel)
        
        self._lockoutWdg.display(row=self._lockoutRow)
        
        progNames = list(self._progDict.keys())
        progNames.sort()
        self._nextRow = 0
        for prog in progNames:
            progPerms = self._progDict[prog]
            progPerms.display(row=self._nextRow)
            self._nextRow += 1

    def _addProg(self, prog):
        """Create and display a new program.
        
        Called when the hub informs this widget of a new program
        (to add a program send the suitable command to the hub,
        don't just call this method).
        """
        prog = prog.upper()
        newProg = _ProgPerms(
            master = self._tableFrame,
            prog = prog,
            actorList = self._actorList,
            readOnly = self._readOnly,
            row = self._nextRow,
            statusBar = self._statusBar,
        )
        self._nextRow += 1
        self._progDict[prog] = newProg
    
    def _addTitle(self, text, col):
        """Create and grid a title label and two associated
        width measuring frames (one in the title frame, one in the main frame).
        
        Inputs:
        - text  text for title
        - col   column for title
        
        Returns the title label
        """
#         print "_addTitle(%r, %r)" % (text, col)
        strWdg = RO.Wdg.StrLabel(
            master = self._titleFrame,
            text = text,
        )
        strWdg.grid(row=0, column=col)
        titleSpacer = tkinter.Frame(self._titleFrame)
        titleSpacer.grid(row=1, column=col, sticky="new")
        mainSpacer = tkinter.Frame(self._tableFrame)
        mainSpacer.grid(row=0, column=col, sticky="new")
        self._titleWdgSet += [strWdg, titleSpacer, mainSpacer]
        
        def dotitle(evt):
#           print "dotitle: titlewidth = %r, mainwidth = %r" % (
#               titleSpacer.winfo_width(), mainSpacer.winfo_width(),
#           )
            if titleSpacer.winfo_width() > mainSpacer.winfo_width():
                mainSpacer["width"] = titleSpacer.winfo_width()  
        titleSpacer.bind("<Configure>", dotitle)
        
        def domain(evt):
#           print "domain: titlewidth = %r, mainwidth = %r" % (
#               titleSpacer.winfo_width(), mainSpacer.winfo_width(),
#           )
            if mainSpacer.winfo_width() > titleSpacer.winfo_width():
                titleSpacer["width"] = mainSpacer.winfo_width()     
        mainSpacer.bind("<Configure>", domain)
        return strWdg
    
    def __connStateCallback(self, conn):
        """If the connection closes, clear all programs from the list.
        """
        if self._progDict and not conn.isConnected:
            for prog, progPerms in list(self._progDict.items()):
                progPerms.delete()
                del(self._progDict[prog])

    def _updActors(self, actors, isCurrent=True, **kargs):
        """Perms list of actors updated.
        """
#         print "%s._updActors(%r)" % (self.__class__, actors,)
        if not isCurrent:
            return
        
        if self._actorList.isSameActors(actors):
            return
        
        if not self._readOnly and self._actorList:
            self._statusBar.setMsg("Updating actors", severity=RO.Constants.sevWarning, isTemp = True, duration=_NewActorDelay * 1000.0)
            self._setReadOnly(True)
            self._updActorTimer.start(_NewActorDelay, self._setReadOnly, False)

        self._actorList.setActors(actors)

        # Update lockout and each program
        self._lockoutWdg.updateActorList()
        for progPerms in self._progDict.values():
            progPerms.updateActorList()

        # display new header and everything
        self.sort()

    def _updPrograms(self, programs, isCurrent=True, **kargs):
        """Hub's list of registered programs updated.
        
        Delete old programs based on this info, but don't add new ones
        (instead, look for an authList entry for the new program,
        so we get auth info at the same time).
        """
        if not isCurrent:
            return
#       print "_updPrograms(%r)" % (programs,)

        # raise program names to uppercase
        programs = [prog.upper() for prog in programs]

        if self._tuiModel.getProgID().upper() not in programs:
#           print "my prog=%s is not in programs=%s; currReadOnly=%s" % (prog, programs, self._readOnly)
            self._setReadOnly(True)

        # mark unregistered programs
        anyUnreg = False
        for prog, progPerms in self._progDict.items():
            if prog not in programs:
                # mark progPerms as unregistered
                anyUnreg = True
                progPerms.setRegistered(False)
        
        # if read only, then automatically purge (if necessary) and sort
        if self._readOnly:
            if anyUnreg:
                self.purge()
            self.sort()
        
    def _setReadOnly(self, readOnly):
        """Set read only state.
        """
        readOnly = bool(readOnly)
        if self._readOnly != readOnly:
            self._readOnly = readOnly
#           print "toggling readOnly to", self._readOnly
            self._lockoutWdg.setReadOnly(self._readOnly)
            for progPerms in self._progDict.values():
                progPerms.setReadOnly(self._readOnly)
            if self._readOnlyCallback:
                self._readOnlyCallback(self._readOnly)
    
    def _updAuthList(self, progAuthList, isCurrent=True, **kargs):
        """New authList received.
        
        progAuthList is:
        - program name
        - 0 or more actorList
        """
        if not isCurrent:
            return
#         print "_updAuthList(%r)" % (progAuthList,)
        
        prog = progAuthList[0].upper()
        authActors = progAuthList[1:]
    
        if prog == self._tuiModel.getProgID().upper():
            # this is info about me (my program); check if I can set permissions
            readOnly = "perms" not in authActors
#             print "prog=%s is me; readOnly=%s, currReadOnly=%s, actorList=%s" % (prog, readOnly, self._readOnly, authActors)
            self._setReadOnly(readOnly)

        isNew = prog not in self._progDict
        if isNew:
#             print "program %s is not in program dict; adding" % (prog,)
            self._addProg(prog)

        progPerms = self._progDict[prog]
        progPerms.setRegistered(True)
        progPerms.setCurrActors(authActors)
    
    def _updLockedActors(self, lockedActors, isCurrent=True, **kargs):
        """Hub's locked actor list updated.
        """
        if not isCurrent:
            return
        
        self._lockoutWdg.setCurrActors(lockedActors)


class _BasePerms(object):
    """Basic set of permissions.
    
    Display current locked actorList as a set of checkbuttons.
    Handle read only, help and the action of clicking a button.
    
    Specialize to handle lockout or programs.
    
    Inputs:
    - master    master widget
    - actorList an ActorList
    - row       row at which to grid display widgets
    - statusBar object to handle commands (via doCmd)
    """
    def __init__(self,
        master,
        actorList,
        readOnly,
        row,
        statusBar,
        prog = "",
        helpSuffix = "",
    ):
#         print "_BasePerms(master=%s, actorList=%s, readOnly=%s, row=%s, prog=%s)" % (master, actorList, readOnly, row, prog)
        self._master = master
        self._actorList = actorList
        self._readOnly = readOnly
        self._row = row
        self._statusBar = statusBar
        self._prog = prog
        self._helpURL = _HelpPrefix + helpSuffix
        self._testWdg = tkinter.Label(self._master) # to determine current bg color

        self._nameSpacerWdg = tkinter.Label(
            master,
            text = "",
            width = _ProgramWidth,
        )
        self._nameSpacerWdg.grid(row=row, column=0)
        self._createNameWdg()

        # dictionary of actor: auth checkbutton entries
        self._actorWdgDict = {}
        self.updateActorList()

    def delete(self):
        """Cleanup
        """
        wdgSet = list(self._actorWdgDict.values()) # all widgets to destroy
        if self._nameSpacerWdg is not None:
            wdgSet.append(self._nameSpacerWdg)
        self._nameSpacerWdg = None
        if self._nameWdg is not None:
            wdgSet.append(self._nameWdg)
        self._nameWdg = None
        self._actorWdgDict = RO.Alg.OrderedDict()
        for wdg in wdgSet:
            wdg.grid_forget()
            wdg.destroy()
    
    def actorInfoIsConsistent(self):
        return self._actorList.getActorSet() == set(self._actorWdgDict.keys())
        
    def display(self, row):
        """Display widgets in the specified row.
        If widgets are already displayed, they are first withdrawn.
        
        Replaces the exisiting actor order.
        
        Raises ValueError if the set of actorList does not match.
        """
        # check actorList
#         print "%s.display(row=%s)" % (self, row)
        if not self.actorInfoIsConsistent():
            listActors = sorted(list(self._actorList.getActorSet()))
            dictActors = sorted(self._actorWdgDict.keys())
            raise ValueError("cannot display perms for %s; my actorList %r != %r" % \
                (self, listActors, dictActors))
        
        self._row = row
        self._nameSpacerWdg.grid_forget()
        self._nameWdg.grid_forget()
        self._nameSpacerWdg.grid(row=self._row, column=0, sticky="ew")
        self._nameWdg.grid(row=self._row, column=0, sticky="ew")
    
        for col, actor in self._actorList.getColActorList():
            if actor:
                wdg = self._actorWdgDict[actor]
                wdg.grid_forget()
                wdg.grid(row=self._row, column=col)
    
    def updateActorList(self):
        """The actorList has been updated
        """
        #print "%s.updateActorList()"
        currActorSet = set(self._actorWdgDict.keys())
        newActorSet = self._actorList.getActorSet()
        if currActorSet == newActorSet:
            return

        # ungrid and delete any deleted actorList
        for actor in currActorSet - newActorSet:
            self._actorWdgDict[actor].grid_forget()
            del(self._actorWdgDict[actor])

        # create any new actorList (they will be gridded later as part of display)
        for actor in newActorSet - currActorSet:
            if actor in self._actorWdgDict:
                raise ValueError("%r: actor %r already exists" % (self, actor))
            
            wdg = _ActorWdg (
                master = self._master,
                prog = self._prog,
                actor = actor,
                readOnly = self._readOnly,
                command = self._actorCommand,
                helpURL = self._helpURL,
            )
            self._actorWdgDict[actor] = wdg
            
            def hl(evt, actor=actor):
                self._doHighlight(evt, actor)
            
            def unHl(evt, actor=actor):
                self._unHighlight(evt, actor)
            
            wdg.bind("<Enter>", hl)
            wdg.bind("<Leave>", unHl)
        self.display(self._row)
    
    def _doHighlight(self, evt, actor):
        titleWdg = self._actorList.getTitleWdg(actor)
        if titleWdg:
            titleWdg["background"] = "yellow"
        self._nameWdg["background"] = "yellow"
        evt.widget["background"] = "yellow"
        
    def _unHighlight(self, evt, actor):
        titleWdg = self._actorList.getTitleWdg(actor)
        normalBackground = self._testWdg["background"]
        if titleWdg:
            titleWdg["background"] = normalBackground
        self._nameWdg["background"] = normalBackground
        evt.widget["background"] = normalBackground
    
    def setCurrActors(self, currActors):
        """Sets the list of actorList that should be checked (authorized).
        
        Inputs:
        - currActors: list of actorList that should be checked
        """
#       print "%s.setCurrActors(%r)" % (self.__class__, currActors)
        for actor, wdg in self._actorWdgDict.items():
            isAuth = actor in currActors
            wdg.setAll(isAuth)
    
    def setReadOnly(self, readOnly):
        """Update read only state.
        """
#       print "_BasePerms.setReadOnly(%r)" % (readOnly,)
        readOnly = bool(readOnly)
        if self._readOnly != readOnly:
            self._readOnly = readOnly
            try:
                self._nameWdg.setReadOnly(readOnly)
            except AttributeError:
                pass
            for wdg in self._actorWdgDict.values():
                wdg.setReadOnly(readOnly)

    def _actorCommand(self):
        """Called when an actor button is pressed by hand.
        """
#       print "%s._actorCommand()" % (self.__class__)
        
        actorList = [
            actor for actor, wdg in self._actorWdgDict.items()
            if wdg.getBool()
        ]
        actorList.sort()
        cmdStr = "%s %s" % (self._getCmdPrefix(), ' '.join(actorList),)
        self._doCmd(cmdStr)
        
    def _cmdFailed(self, *args, **kargs):
        """Called when a command fails; resets default state."""
        # handle name widget specially; it may not be an active control
        try:
            self._nameWdg.restoreDefault()
        except AttributeError:
            pass
        for wdg in self._actorWdgDict.values():
            wdg.restoreDefault()
    
    def _getCmdPrefix(self):
        """Return the command prefix"""
        raise NotImplementedError("_createNameWdg must be defined by the subclass")

    def _createNameWdg(self):
        """Create self._nameWdg.
        """
        raise NotImplementedError("_createNameWdg must be defined by the subclass")
    
    def _doCmd(self, cmdStr):
        """Execute a command.
        """
        cmd = RO.KeyVariable.CmdVar(
            actor = "perms",
            cmdStr = cmdStr,
            callFunc = self._cmdFailed,
            callTypes = RO.KeyVariable.FailTypes,
        )
        self._statusBar.doCmd(cmd)
    
    def __del__(self):
        self.delete()
    
    def __repr__(self):
        return "%s" % (self.__class__.__name__)


class _LockoutPerms(_BasePerms):
    """Lockout permissions
    
    This class keeps track of locked actorList,
    displays the info as a set of controls
    and responds to these controls by sending the appropriate commands.
    
    Inputs:
    - master    master widget
    - actorList    a list of the currently known actorList, in desired display order
    - row       row at which to grid display widgets
    - statusBar object to handle commands (via doCmd)
    """
    def __init__(self, master, actorList, readOnly, row, statusBar):
        _BasePerms.__init__(self,
            master = master,
            actorList = actorList,
            readOnly = readOnly,
            row = row,
            statusBar = statusBar,
            prog = "",
            helpSuffix = "Lockout",
        )

    def _getCmdPrefix(self):
        """Return the command prefix"""
        return "setLocked"

    def _createNameWdg(self):
        """Create self._nameWdg.
        """
        self._nameWdg = RO.Wdg.StrLabel (
            master = self._master,
            text = "Lockout",
            anchor = "center",
            helpText = "lock out non-APO users",
            helpURL = self._helpURL,
        )

    def setCurrActors(self, currActors):
#       print "_ProgPerms %s setCurrActors(%r)" % (self, currActors)
        _BasePerms.setCurrActors(self, currActors)
        someChecked = bool(currActors)
        if someChecked:
            self._nameWdg.setSeverity(RO.Constants.sevWarning)
        else:
            self._nameWdg.setSeverity(RO.Constants.sevNormal)

    def __str__(self):
        return "Lockout"


class _ProgPerms(_BasePerms):
    """Permissions for one program.
    
    This class keeps track of the permissions,
    displays the info as a set of controls
    and responds to these controls by sending the appropriate commands.
    
    Inputs:
    - master    master widget
    - prog      program name
    - actorList    a list of the currently known actorList, in desired display order
    - row       row at which to grid display widgets
    - statusBar object to handle commands (via doCmd)
    """
    def __init__(self, master, prog, actorList, readOnly, row, statusBar):
#         print "_ProgPerms(master=%s, prog=%s, actorList=%s, readOnly=%s, row=%s)" % (master, prog, actorList, readOnly, row)
        _BasePerms.__init__(self,
            master = master,
            actorList = actorList,
            readOnly = readOnly,
            row = row,
            statusBar = statusBar,
            prog = prog,
            helpSuffix = "ProgEntry",
        )
    
    def isRegistered(self):
        """Returns True if desired state is registered,
        False otherwise.
        """
        return self._nameWdg.getRegInfo()[1]
    
    def setCurrActors(self, currActors):
#       print "_ProgPerms %s setCurrActors(%r)" % (self, currActors)
        _BasePerms.setCurrActors(self, currActors)
        self._nameWdg.setCanUnreg("perms" not in currActors)

    def setRegistered(self, isReg):
        """Set registered or unregistered state.
        """
#       print "%s %s.setRegistered(%r)" % (self._prog, self.__class__, isReg)
        self._nameWdg.setRegistered(isReg)
        for wdg in self._actorWdgDict.values():
            wdg.setRegInfo(isReg, isReg)

    def _getCmdPrefix(self):
        return "set program=%s" % (self._prog,)

    def _createNameWdg(self):
        """Create the name widget; a checkbutton
        that, when checked, unregisters the program.
        """
        self._nameWdg = _ProgramWdg (
            master = self._master,
            prog = self._prog,
            command = self._progCommand,
            readOnly = self._readOnly,
            helpText = "Uncheck to delete program %r" % (self._prog),
            helpURL = self._helpURL,
        )
        self._nameWdg.addCallback(self._progCallFunc)
    
    def _progCommand(self):
        """Called when the program name button is pushed by hand.
        Sends the appropriate command(s) to the hub.
        See also _progCallFunc, which controls actor enabling.
        """     
#       print "%s._progCommand" % (self.__class__)
        doReg = self._nameWdg.getBool()
            
        # issue register or unregister command
        if doReg:
            cmdVerb = "register"
        else:
            cmdVerb = "unregister"
        cmdStr = '%s %s' % (cmdVerb, self._prog)
        self._doCmd(cmdStr)
    
        # if re-registering, restore permissions
        if doReg:
            self._actorCommand()

    def _progCallFunc(self, wdg=None):
        """Called when the program name button is toggled by any means.
        Sets enabled of actorList.
        See also progCommand, which sends commands to the hub.
        """
#       print "%s._progCallFunc" % (self.__class__)
        actReg, desReg = self._nameWdg.getRegInfo()
        
        # set enable of actor wdg
        for wdg in self._actorWdgDict.values():
            wdg.setRegInfo(actReg, desReg)
        
    def __str__(self):
        return self._prog
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self._prog)


class _SettingsWdg(RO.Wdg.Checkbutton):
    """Widget to toggle a setting (actor permission or delete program).
    """
    def __init__(self,
        master,
        prog,
        readOnly,
        helpURL = None,
    **kargs):
        self._prog = prog
        self._readOnly = readOnly
        
        RO.Wdg.Checkbutton.__init__ (self,
            master = master,
            helpURL = helpURL,
            autoIsCurrent = True,
            isCurrent = False,
        **kargs)
        self["disabledforeground"] = self["foreground"]
        
        self._saveActorInfo()
        self._setState()
    
    def _saveActorInfo(self):
        """Save actor settings that allow us to
        enable and disable the actor button appropriately.
        """
        pass

    def setAll(self, val):
        """Set the current and default value.
        """
        self.setDefault(val)
        self.set(val)
        self._setState()
    
    def _setState(self):
        pass
    
    def setReadOnly(self, readOnly):
        readOnly = bool(readOnly)
        if readOnly != self._readOnly:
            self._readOnly = readOnly
            self._setState()


class _ActorWdg(_SettingsWdg):
    """Minimal widget to display a checkbutton and a changed indicator.
    
    This widget has 3 states:
    - read only: user can view permissions but not change anything
    - registered: program is registered and user can change settings
    - not exists: program unregistered so settings disabled
    (read only and unregistered is irrelevant since read only users
    only see registered programs)
    """
    def __init__(self,
        master,
        actor,
        prog,
        readOnly,
        helpURL = None,
    **kargs):
        self._actor = actor
        self._actReg = True
        self._desReg = True
        _SettingsWdg.__init__(self,
            master = master,
            prog = prog,
            readOnly = readOnly,
            helpURL = helpURL,
        **kargs)
    
    def setReadOnly(self, readOnly):
        _SettingsWdg.setReadOnly(self, readOnly)
#       print "%s %s setReadOnly(%r)" % (self._prog, self._actor, readonly)
    
    def _setState(self):
        """State changed and not transitional; update widget appearance and help.
        """
        isChecked = self.getBool()
#       print "%s %s _ActorWdg._setState; readOnly=%s; isChecked=%s, actReg=%s; desReg=%s" % \
#           (self._prog, self._actor, self._readOnly, isChecked, self._actReg, self._desReg)

        if self._readOnly:
            self.setEnable(False)
            
            if self._prog:
                if isChecked:
                    self.helpText = "%s may use %s" % (self._prog, self._actor) 
                else:
                    self.helpText = "%s may not use %s" % (self._prog, self._actor) 
            else:
                if isChecked:
                    self.helpText = "%s is locked out" % (self._actor,)
                else:
                    self.helpText = "%s is available" % (self._actor,)
            return

        if self._actReg and self._desReg:
            self.setEnable(True)
            if self._prog:
                if isChecked:
                    self.helpText = "%s may use %s; uncheck to prohibit" % (self._prog, self._actor) 
                else:
                    self.helpText = "%s may not use %s; check to allow" % (self._prog, self._actor) 
            else:
                if isChecked:
                    self.helpText = "%s is locked out; uncheck to unlock" % (self._actor,)
                else:
                    self.helpText = "%s is unlocked; check to lock out" % (self._actor,)

        else:
            # program not registered or in transition, so user cannot change permissions
            self.setEnable(False)
            if not self._desReg:
                self.helpText = "Re-add %s to enable" % (self._prog)
            else:
                self.helpText = "%s being added; please wait" % (self._prog)

    def setRegInfo(self, actReg, desReg):
        actReg = bool(actReg)
        desReg = bool(desReg)
        if (self._desReg, self._actReg) != (desReg, actReg):
            self._actReg = actReg
            self._desReg = desReg
            self._setState()


class _ProgramWdg(_SettingsWdg):
    """Widget for showing program name.
    When disabled, shows up as a label and help is gone.
    When enabled, shows up as a checkbutton with the text as the button
    (rather than text next to a separate checkbox).
    """
    def __init__(self, *args, **kargs):
        # handle defaults and forced settings
        tuiModel = TUI.TUIModel.getModel()
        self._canUnreg = True # can program be unregistered? some are fixed
        prog = kargs.get("prog")
        currProg = tuiModel.getProgID()
        if currProg and currProg.lower() == prog.lower():
            dispText = "*" + prog
        else:
            dispText = prog
        kargs["text"] = dispText
        _SettingsWdg.__init__(self, *args, **kargs)
        
    def _saveActorInfo(self):
        """Save actor settings that allow us to
        enable and disable the actor button appropriately.
        """
        self._enabledPadX = int(str(self["padx"]))
        self._enabledPadY = int(str(self["pady"]))
        self._borderWidth = int(str(self["borderwidth"]))
        self._disabledPadX = self._enabledPadX + self._borderWidth
        self._disabledPadY = self._enabledPadY + self._borderWidth
        
    def setEnable(self, doEnable):
#       print "%s _ProgWdg.setEnable(%r)" % (self._prog, doEnable)
        _SettingsWdg.setEnable(self, doEnable)
        if doEnable:
            self.configure(
                padx = self._enabledPadX,
                pady = self._enabledPadY,
                borderwidth = self._borderWidth,
            )
        else:
            self.configure(
                padx = self._disabledPadX,
                pady = self._disabledPadY,
                borderwidth = 0,
            )
    
    def getRegInfo(self):
        """Returns actReg, desReg
        """
        return (self.getDefBool(), self.getBool())
    
    def _setState(self):
        """State changed; update widget appearance and help.
        """
#         print "%s _ProgWdg._setState; readOnly=%s; canUnreg=%s" % (self._prog, self._readOnly, self._canUnreg)
        if self._readOnly:
            self.setEnable(False)
            self.helpText = "Permissions for program %s" % (self._prog,)
            return
        
        if not self._canUnreg:
            self.setEnable(False)
            self.helpText = "%s may not be deleted" % (self._prog,)
            return
        
        self.setEnable(True)
        actReg, desReg = self.getRegInfo()
        if actReg:
            self.helpText = "%s added; uncheck to delete" % (self._prog,) 
        else:
            self.helpText = "%s deleted; check to re-add" % (self._prog,) 
    
    def setRegistered(self, isRegistered):
        self.setAll(isRegistered)

    def setReadOnly(self, readOnly):
#       print "%s _ProgWdg.setReadOnly(%s)" % (self._prog, readOnly,)
        _SettingsWdg.setReadOnly(self, readOnly)
    
    def setCanUnreg(self, canUnreg):
        """Indicate whether a program can be unregistered or is always registered.
        """
        canUnreg = bool(canUnreg)
        if canUnreg != self._canUnreg:
            self._canUnreg = canUnreg
            self._setState()


if __name__ == "__main__":
    from . import TestData
    root = TestData.tuiModel.tkRoot
    root.resizable(False, True)

    DefReadOnly = False
    
    statusBar = RO.Wdg.StatusBar(
        master = root,
        dispatcher = TestData.tuiModel.dispatcher
    )
    
    testFrame = PermsTableWdg(
        master = root,
        statusBar = statusBar,
    )
    testFrame.pack(side="top", expand=True, fill="y")
    testFrame._setReadOnly(DefReadOnly)
    
    statusBar.pack(side="top", fill="x")
    
    def doReadOnly(but):
        readOnly = but.getBool()
        testFrame._setReadOnly(readOnly)

    butFrame = tkinter.Frame(root)

    tkinter.Button(butFrame, text="Demo", command=TestData.animate).pack(side="left")
    
    RO.Wdg.Checkbutton(butFrame, text="Read Only", defValue=DefReadOnly, callFunc=doReadOnly).pack(side="left")
    
    butFrame.pack(side="top", anchor="w")

    TestData.start()

    root.mainloop()
