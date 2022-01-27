#!/usr/bin/env python
"""Users window (display a list of users).

To do:
- tweak tab stops
- test what happens during a failed login

2003-12-06 ROwen
2003-12-17 ROwen    Added addWindow and renamed to UsersWindow.py.
2004-05-18 ROwen    Stopped obtaining TUI model in addWindow; it was ignored.
2004-07-22 ROwen    Modified to use TUI.HubModel.
2004-08-11 ROwen    Modified for updated RO.Wdg.CtxMenu.
2004-08-25 ROwen    Modified to use new hubModel.users keyvar.
2004-09-14 ROwen    Stopped importing TUI.TUIModel since it wasn't being used.
2004-11-18 ROwen    Added code to silently handle usernames with no ".".
2005-01-06 ROwen    Modified to indicate the current user with an underline.
2010-03-05 ROwen    Modified to show client name and version.
                    Modified to not show monitor clients.
2010-03-10 ROwen    Modified to also show system info.
                    Removed unused import of RO.KeyVariable and RO.StringUtil.
                    Added WindowName.
2011-06-17 ROwen    Changed "type" to "msgType" in parsed message dictionaries (in test code only).
2011-07-27 ROwen    Updated for new location of HubModel.
2012-07-10 ROwen    Modified to use RO.TkUtil.Timer.
"""
import time
import tkinter
import RO.Wdg
from RO.TkUtil import Timer
import TUI.Models.HubModel
import TUI.TUIModel
import TUI.Version

WindowName = "%s.Users" % TUI.Version.ApplicationName

_HelpPage = "TUIMenu/UsersWin.html"

def addWindow(tlSet):
    tlSet.createToplevel(
        name = WindowName,
        defGeom = "300x125+0+722",
        visible = False,
        resizable = True,
        wdgFunc = UsersWdg,
    )

class User(object):
    """Information about a user
    
    cmdr: commander ID = program_name.user_name
    userInfo: data from hub user keyword (or None if unknown). If known, a list containing:
    - cmdrID (program.name)
    - client name (typically "TUI" or "monitor")
    - client version (sortable)
    - system info (e.g. platform.platform())
    - IP address (numeric)
    - fully qualified domain name (if supplied)
    """
    def __init__(self, cmdr, userInfo=None):
        self.cmdr = cmdr
        try:
            self.prog, self.user = self.cmdr.split(".", 1)
        except Exception:
            self.prog = self.cmdr
            self.user = "?"

        self._userInfo = userInfo
        self._disconnTime = None
    
    def setDisconnected(self):
        """Specify that this user has just disconnected.
        
        Warning: only call if the user is presently marked as connected
        
        Raise RuntimeError if user already marked as disconnected
        """
        if not self.isConnected:
            raise RuntimeError("%s already disconnected" % (self,))
        self._disconnTime = time.time()

    def setConnected(self):
        """Specify that this user is connected.
        
        Safe to call even if the user is already connected.
        """
        self._disconnTime = None

    def setUserInfo(self, userInfo):
        """Modify the user information list (value of user keyword)
        """
        self._userInfo = userInfo
        self._disconnTime = None

    @property
    def isConnected(self):
        """Return True if user is connected, False otherwise
        """
        return self._disconnTime is None
    
    @property
    def disconnTime(self):
        """Return time when user disconnected, or None if connected
        
        The returned time is the time returned by time.time()
        """
        return self._disconnTime
    
    @property
    def clientName(self):
        """Return the client name, e.g. "TUI" or "monitor", or "?" if unknown
        """
        if self._userInfo:
            return self._userInfo[1] or "?"
        else:
            return "?"

    @property
    def clientVersion(self):
        """Return the client version, or "?" if unknown
        """
        if self._userInfo:
            return self._userInfo[2] or "?"
        else:
            return "?"

    @property
    def systemInfo(self):
        """Return the client's system info, or "?" if unknown"""
        if self._userInfo:
            return self._userInfo[3] or "?"
        else:
            return "?"

    @property
    def userInfo(self):
        return self._userInfo

    def __str__(self):
        return "User(%s)" % (self.cmdr,)
    
    def __repr__(self):
        return "User(cmdr=%s; connected=%s; disconnTime=%s; userInfo=%s)" % \
            (self.cmdr, self.isConnected, self.disconnTime, self.userInfo)

class UsersWdg(tkinter.Frame):
    """Display the current users and those recently logged out.
    
    Inputs:
    - master    parent widget
    - retainSec time to retain information about logged out users (sec)
    - height    default height of text widget
    - width default width of text widget
    - other keyword arguments are used for the frame
    """
    def __init__ (self,
        master=None,
        retainSec=300,
        height = 10,
        width = 50,
    **kargs):
        tkinter.Frame.__init__(self, master, **kargs)
        
        hubModel = TUI.Models.HubModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()
        
        # entries are commanders (prog.user)
        self._cmdrList = []
        # entries are (cmdr, time deleted); time is from time.time()
        self._delCmdrTimeList = []
        # time to show deleted users
        self._retainSec = retainSec
        
        # dictionary of user name: User object
        self.userDict = dict()
        
        self._updateTimer = Timer()
                
        self.yscroll = tkinter.Scrollbar (
            master = self,
            orient = "vertical",
        )
        self.text = tkinter.Text (
            master = self,
            yscrollcommand = self.yscroll.set,
            wrap = "none",
            tabs = "1.6c 5.0c 6.7c 8.5c",
            height = height,
            width = width,
        )
        self.yscroll.configure(command=self.text.yview)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.yscroll.grid(row=0, column=1, sticky="ns")
        RO.Wdg.Bindings.makeReadOnly(self.text)
        RO.Wdg.addCtxMenu(
            wdg = self.text,
            helpURL = _HelpPage,
        )
        
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        self.text.tag_configure("del", overstrike=True)
        self.text.tag_configure("me", underline=True)

        hubModel.user.addCallback(self.updUser, callNow=False)
        hubModel.users.addCallback(self.updUsers)

    def scheduleUpdate(self, afterSec=1.0):
        """Schedule a new update
        """
        self._updateTimer.start(afterSec, self.updDisplay)

    def updDisplay(self):
        """Display current data.
        """
        self._updateTimer.cancel()
        
        myCmdr = self.tuiModel.getCmdr()
        maxDisplayTime = time.time() - self._retainSec

        self.text.delete("1.0", "end")
        doScheduleUpdate = False
        deleteCmdrList = []
        for cmdr in sorted(self.userDict.keys()):
            userObj = self.userDict[cmdr]
            if userObj.clientName == "monitor":
                continue
            if userObj.isConnected:
                tagList = ["curr"]
            elif userObj.disconnTime < maxDisplayTime:
                deleteCmdrList.append(cmdr)
                continue
            else:
                tagList = ["del"]
                doScheduleUpdate = True
            if cmdr == myCmdr:
                tagList.append("me")
            displayStr = "%s\t%s\t%s\t%s\t%s\n" % \
                (userObj.prog, userObj.user, userObj.clientName, userObj.clientVersion, userObj.systemInfo)
            self.text.insert("end", displayStr, " ".join(tagList))

        for cmdr in deleteCmdrList:
            del(self.userDict[cmdr])
        
        if doScheduleUpdate:
            self.scheduleUpdate()

    def updUser(self, userInfo, isCurrent, keyVar=None):
        """User keyword callback; add user data to self.userDict"""
        if (not isCurrent) or (userInfo is None):
            return

        cmdr = userInfo[0]
        oldUserObj = self.userDict.get(cmdr, None)
        if oldUserObj:
            oldUserObj.setUserInfo(userInfo)
        else:
            self.userDict[cmdr] = User(cmdr, userInfo)
        self.scheduleUpdate()

    def updUsers(self, newCmdrList, isCurrent=True, keyVar=None):
        """Users keyword callback. The value is a list of commander IDs.
        """
        if not isCurrent:
            # set background to notCurrent?
            return

        for cmdr in newCmdrList:
            userObj = self.userDict.get(cmdr, None)
            if userObj:
                if not userObj.isConnected:
                    userObj.setConnected()
            else:
                self.userDict[cmdr] = User(cmdr)

        # handle disconnected users (those in my userDict that aren't in newCmdrList)
        # handle timeout and final deletion in updDisplay, since it has to remove
        # stale entries even if the users keyword hasn't changed.
        disconnCmdrSet = set(self.userDict.keys()) - set(newCmdrList)
        for cmdr in disconnCmdrSet:
            userObj = self.userDict[cmdr]
            if userObj.isConnected:
                userObj.setDisconnected()

        self.updDisplay()


if __name__ == "__main__":
    root = RO.Wdg.PythonTk()

    kd = TUI.TUIModel.getModel(True).dispatcher

    testFrame = UsersWdg (root, retainSec = 5)
    testFrame.pack(expand=True, fill="both")
    
    dataDicts = (
        {"Users": ("CL01.CPL","TU01.me","TU01.ROwen")},
        {"Users": ("CL01.CPL","TU01.me")},
        {"Users": ("CL01.CPL","TU01.me","TU01.ROwen")},
        {"Users": ("CL01.CPL","TU01.me")},
    )

    dataIter = iter(dataDicts)
    def dispatchNext():
        try:
            newDataDict = next(dataIter)
        except StopIteration:
            return
        
        msgDict = {"cmdr":".hub", "cmdID":11, "actor":"hub", "msgType":"i", "data":newDataDict}
        kd.dispatch(msgDict)
        Timer(1.0, dispatchNext)
    dispatchNext() 

    root.mainloop()
