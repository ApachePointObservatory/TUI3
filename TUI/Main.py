#!/usr/bin/env python
"""Telescope User Interface.
This is the main routine that calls everything else.

2003-02-27 ROwen    First version with history.
                    Modified to use the new Hub authorization
2003-03-20 ROwen    Added DIS
2003-03-25 ROwen    Moved TCC widgets into TCC subdirectory;
    modified to load TUI windows from TUIWindow.py
    and to auto-load windows from TCC, Inst and Misc directories
2003-04-04 ROwen    Fixed auto-load code to be platform-independent.
2003-04-22 ROwen    Modified to not auto-load window modules
                    whose file name begins with ".".
2003-06-09 ROwen    Modified to use TUIModel.
2003-06-18 ROwen    Modified to print a full traceback for unexpected errors;
                    modified to exclude SystemExit and KeyboardInterrupt
                    when testing for general exceptions.
2003-12-17 ROwen    Modified to auto load windows from all of the
                    TCC package (instead of specific sub-packages)
                    and also from TUISharedAdditions and TUIUserAdditions.
2004-01-23 ROwen    Modified to not rely on modules being loaded from the
                    same dir as this file. This simplifies generating a
                    Mac standalone app.
                    Modified to load *all* windows in TUI,
                    rather than searching specific directories.
                    Improved error handling of loadWindows:
                    - if TUI cannot be loaded, fail
                    - reject module names with "." in them
                    (both changes help debug problems with making
                    standalone apps).
2004-02-05 ROwen    Changed the algorithm for finding user additions.
2004-02-06 ROwen    Adapted to RO.OS.walkDirs->RO.OS.findFiles.
2004-02-17 ROwen    Changed to call buildMenus instead of buildAutoMenus
                    in the "None.Status" toplevel. .
2004-03-03 ROwen    Modified to print the version number during startup.
2004-03-09 ROwen    Bug fix: unix code was broken.
2004-05-17 ROwen    Modified to be runnable by an external script (e.g. runtui.py).
                    Modified to print version to log rather than stdout.
2004-07-09 ROwen    Modified to use TUI.TUIPaths
2004-10-06 ROwen    Modified to use TUI.MenuBar.
2005-06-16 ROwen    Modified to use improved KeyDispatcher.logMsg.
2005-07-22 ROwen    Modified to hide tk's console window if present.
2005-08-01 ROwen    Modified to use TUI.LoadStdModules, a step towards
                    allowing TUI code to be run from a zip file.
2005-08-08 ROwen    Moved loadWindows and findWindowsModules to WindowModuleUtil.py
2005-09-22 ROwen    Modified to use TUI.TUIPaths.getAddPaths instead of getTUIPaths.
2006-10-25 ROwen    Modified to not send dispatcher to BackgroundTasks.
2007-01-22 ROwen    Modified to make sure sys.executable is absolute,
                    as required for use with pyinstaller 1.3.
2007-12-20 ROwen    Import and configure matplotlib here and stop configuring it elsewhere. This works around
                    a problem in matplotlib 0.91.1: "use" can't be called after "import matplotlib.backends".
2009-04-17 ROwen    Updated for new Status window name: None.Status->TUI.Status.
2010-09-24 ROwen    Moved matplotlib.use call before any import of TUI code.
2012-07-18 ROwen    Modified to use RO 3.0 including the option to communicate using Twisted framework.
2012-11-13 ROwen    Add workaround for bug on Tcl/Tk 8.5.11 that shows OptionMenu too narrow on MacOS X.
2012-11-16 ROwen    Remove workaround for Tcl/Tk bug; I put a better solution in RO.Wdg.OptionMenu.
2012-11-29 ROwen    Set UseTwisted False; I don't know why it was True.
2013-07-19 ROwen    Modified to print some info to stdout (e.g. the log) on startup.
                    Modified to only show the version name, not version date, in the log at startup.
2014-02-12 ROwen    Added a call to reopen script windows.
"""
import glob
import os
import sys
import time
import traceback
import tkinter

## Initiate Tk toplevel before importing matplotlib
root = tkinter.Tk()

# make sure matplotlib is configured correctly (if it is available)
try:
    import matplotlib
    matplotlib.use("TkAgg")
    # controls the background of the axis label regions (which default to gray)
    matplotlib.rc("figure", facecolor="white")
    matplotlib.rc("axes", titlesize="medium") # default is large, which is too big
    matplotlib.rc("legend", fontsize="medium") # default is large, which is too big
except ImportError:
    pass

import RO.Comm.Generic

UseTwisted = True
if UseTwisted:
    RO.Comm.Generic.setFramework("twisted")
else:
    RO.Comm.Generic.setFramework("tk")

import TUI.BackgroundTasks
import TUI.LoadStdModules
import TUI.MenuBar
import TUI.TUIPaths
import TUI.TUIModel
import TUI.WindowModuleUtil
import TUI.Version

# hack for pyinstaller 1.3
sys.executable = os.path.abspath(sys.executable)

def runTUIWithLog():
   
    import glob
    import os
    import sys
    import time
    import traceback
    import TUI.Version

    LogPrefix = "%slog" % (TUI.Version.ApplicationName.lower(),)
    LogSuffix = ".txt"
    LogDirName = "%s_logs" % (TUI.Version.ApplicationName.lower(),)
    MaxOldLogs = 10
    
    if sys.platform == "darwin":
        tcllibDir = os.path.join(os.path.dirname(__file__), "tcllib")
        if os.path.isdir(tcllibDir):
            os.environ["TCLLIBPATH"] = tcllibDir
    
    # Open a new log file and purge excess old log files
    # If cannot open new log file then use default stderr.
    errLog = None
    try:
        import RO.OS
        docsDir = RO.OS.getDocsDir()
        if not docsDir:
            raise RuntimeError("Could not find your documents directory")
        logDir = os.path.join(docsDir, LogDirName)
        if not os.path.exists(logDir):
            os.mkdir(logDir)
        if not os.path.isdir(logDir):
            raise RuntimeError("Could not create log dir %r" % (logDir,))
    
        # create new log file        
        dateStr = time.strftime("%Y-%m-%dT%H_%M_%S", time.gmtime())
        logName = "%s%s%s" % (LogPrefix, dateStr, LogSuffix)
        logPath = os.path.join(logDir, logName)
        #errLog = file(logPath, "w", 1) # bufsize=1 means line buffered
        errLog = open(logPath, mode='w', buffering=1)
    
        # purge excess old log files
        oldLogGlobStr = os.path.join(docsDir, "%s????-??-??:??:??:??%s" % (LogPrefix, LogSuffix))
        oldLogPaths = glob.glob(oldLogGlobStr)
        if len(oldLogPaths) > MaxOldLogs:
            oldLogPaths = list(reversed(sorted(oldLogPaths)))
            for oldLogPath in oldLogPaths[MaxOldLogs:]:
                try:
                    os.remove(oldLogPath)
                except Exception as e:
                    errLog.write("Could not delete old log file %r: %s\n" % (oldLogPath, e))
    
    except OSError as e:
        sys.stderr.write("Warning: could not open log file so using stderr\nError=%s\n" % (e,))
    
    try:
        if errLog:
            sys.stderr = errLog
            sys.stdout = errLog
            import time
            import TUI.Version
            startTimeStr = time.strftime("%Y-%m-%dT%H:%M:%S")
            errLog.write("TUI %s started %s\n" % (TUI.Version.VersionStr, startTimeStr))
        
        runTUI()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
    
    if errLog:
        errLog.close()


def runTUI():
    """Run TUI.
    """
    # must do this before setting up preferences
    root.withdraw()
    # if console exists, hide it
    try:
        root.tk.call("console", "hide")
    except tkinter.TclError:
        pass

    if UseTwisted:
        ## This function gets around the twisted tksupport.install
        ## function using root.update() and uses dooneevent instead.
        def installTkRootIntoReactor(root, ms=10):
            import twisted.internet.task
            _tkTask = twisted.internet.task.LoopingCall(
                    root.dooneevent
                    )
            _tkTask.start(ms/1000.0, False)
        installTkRootIntoReactor(root, ms=1)
        import twisted.internet
        reactor = twisted.internet.reactor
    
    # create and obtain the TUI model
    tuiModel = TUI.TUIModel.getModel()
    
    if UseTwisted:
        tuiModel.reactor = reactor
    
    # set up background tasks
    backgroundHandler = TUI.BackgroundTasks.BackgroundKwds()

    # get locations to look for windows
    addPathList = TUI.TUIPaths.getAddPaths()
    
    # add additional paths to sys.path
    sys.path += addPathList
    
    TUI.LoadStdModules.loadAll()
    
    # load additional windows modules
    for winPath in addPathList:
        TUI.WindowModuleUtil.loadWindows(
            path = winPath,
            tlSet = tuiModel.tlSet,
            logFunc = tuiModel.logMsg,
        )

    # load scripts
    TUI.Base.ScriptLoader.reopenScriptWindows()
    
    # add the main menu
    TUI.MenuBar.MenuBar()
    
    tuiModel.logMsg(
        "TUI Version %s: ready to connect" % (TUI.Version.VersionName,)
    )
    startTimeStr = time.strftime("%Y-%m-%dT%H:%M:%S")
    platformStr = TUI.TUIModel.getPlatform()
    sys.stdout.write("TUI %s running on %s started %s\n" % (TUI.Version.VersionName, platformStr, startTimeStr))

    if UseTwisted:
        reactor.run()
    else:
        root.mainloop()

if __name__ == "__main__":
    runTUI()
