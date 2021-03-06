#!/usr/bin/env python
"""Creates the Script menu.

To Do:
- add html help; note that this will have to be fed to ScriptWdg,
  RO.ScriptWdg has no idea of TUI help

History:
2004-07-19 ROwen
2004-08-11 ROwen    Modified for updated RO.Wdg.Toplevel.
2004-08-23 ROwen    Added some diagnostic print statements (commented out).
2004-10-11 ROwen    Modified to reject files whose names begin with ".".
2004-10-28 ROwen    Bug fix: Open... was broken.
2005-09-22 ROwen    Fix PR 272: standard scripts not available on Mac;
                    this was broken by the packaging overhaul for TUI 1.0.1.
                    Fix PR 132: Script menu may not load at first on MacOS X;
                    this was fixed via a hideous hack.
                    Modified to check/rebuild the entire menu when the root
                    menu is shown, instead of using lazy check/rebuild;
                    this simplified the hack for PR 132.
                    Modified to prebuild the menu at startup.
                    Modified test code to show a standard pull-down menu.
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2012-07-18 ROwen    Removed use of update_idletasks and an ugly Mac workaround that is no longer required.
2014-02-12 ROwen    Moved some code to TUI.Base.ScriptLoader so other users could get to it more easily.
2015-03-18 ROwen    Removed _RootNode.isAqua because it was not being used.
"""
import os
import tkinter
import tkinter.filedialog
import RO.Alg
from TUI.Base.ScriptLoader import getScriptDirs, ScriptLoader

__all__ = ["getScriptMenu"]

def getScriptMenu(master):
    scriptDirs = getScriptDirs()
    
    rootNode = _RootNode(master=master, label="", pathList=scriptDirs)
    rootNode.checkMenu(recurse=True)
    
    return rootNode.menu

class _MenuNode:
    """Menu and related information about sub-menu of the Scripts menu

    Each node represents one level of hiearchy in the various scripts directories.
    The contents of a given subdir are dynamically tested, but the existence
    of a particular subdirectory is not. This sounds like a mistake to me;
    if a given subdir exists in any scripts dir, it should be checked every time
    in all scripts dirs.
    """
    def __init__(self, parentNode, label, pathList):
        """Construct a _MenuNode

        Inputs:
        - parentNode: parent menu node
        - label: label of this sub-menu
        - pathList: list of paths to this subdirectory in the script hierarchy
            (one entry for each of the following, but only if the subdir exists:
            built-in scripts dir, local TUIAddtions/Scripts and shared TUIAdditions/Scripts)
        """
#       print "_MenuNode(%r, %r, %r)" % (parentNode, label, pathList)
        self.parentNode = parentNode
        self.label = label
        self.pathList = pathList

        self.itemDict = {}
        self.subDict = RO.Alg.ListDict()
        self.subNodeList = []

        self._setMenu()
    
    def _setMenu(self):
        self.menu = tkinter.Menu(
            self.parentNode.menu,
            tearoff = False,
#           postcommand = self.checkMenu,
        )
        self.parentNode.menu.add_cascade(
            label = self.label,
            menu = self.menu,
        )
    
    def checkMenu(self, recurse=True):
        """Check contents of menu and rebuild if anything has changed.
        Return True if anything rebuilt.
        """
#       print "%s checkMenu" % (self,)
        newItemDict = {}
        newSubDict = RO.Alg.ListDict()
        didRebuild = False
        
        for path in self.pathList:
            for baseName in os.listdir(path):
                # reject files that would be invisible on unix
                if baseName.startswith("."):
                    continue
        
                baseBody, baseExt = os.path.splitext(baseName)
        
                fullPath = os.path.normpath(os.path.join(path, baseName))
                
                if os.path.isfile(fullPath) and baseExt.lower() == ".py":
#                   print "checkMenu newItem[%r] = %r" % (baseBody, fullPath)
                    newItemDict[baseBody] = fullPath
                
                elif os.path.isdir(fullPath) and baseExt.lower() != ".py":
#                   print "checkMenu newSubDir[%r] = %r" % (baseBody, fullPath)
                    newSubDict[baseName] = fullPath
                
#               else:
#                   print "checkMenu ignoring %r = %r" % (baseName, fullPath)
        
        if (self.itemDict != newItemDict) or (self.subDict != newSubDict):
            didRebuild = True
            # rebuild contents
#           print "checkMenu rebuild contents"
            self.itemDict = newItemDict
            self.subDict = newSubDict
            self.menu.delete(0, "end")
            self.subNodeList = []
            self._fillMenu()
#       else:
#           print "checkMenu do not rebuild contents"

        if recurse:
            for subNode in self.subNodeList:
                subRebuilt = subNode.checkMenu(recurse=True)
                didRebuild = didRebuild or subRebuilt

        return didRebuild
    
    def _fillMenu(self):
        """Fill the menu.
        """
#       print "%s _fillMenu"
        
        itemKeys = list(self.itemDict.keys())
        itemKeys.sort()
#       print "%s found items: %s" % (self, itemKeys)
        for label in itemKeys:
            subPathList = list(self.getLabels()) + [label]
            fullPath = self.itemDict[label]
#               print "adding script %r: %r" % (label, fullPath)
            self.menu.add_command(
                label = label,
                command = ScriptLoader(subPathList=subPathList, fullPath=fullPath),
            )
        
        subdirList = list(self.subDict.keys())
        subdirList.sort()
#       print "%s found subdirs: %s" % (self, subdirList)
        for subdir in subdirList:
            pathList = self.subDict[subdir]
#               print "adding submenu %r: %r" % (subdir, pathList)
            self.subNodeList.append(_MenuNode(self, subdir, pathList))
    
    def getLabels(self):
        """Return a list of labels all the way up to, but not including, the root node.
        """
        retVal = self.parentNode.getLabels()
        retVal.append(self.label)
        return retVal

    def __str__(self):
        return "%s %s" % (self.__class__.__name__, ":".join(self.getLabels()))
                


class _RootNode(_MenuNode):
    """The main scripts menu and related information
    """
    def __init__(self, master, label, pathList):
        """Construct the _RootNode

        Inputs:
        - parentNode: parent menu node
        - label: label of this sub-menu
        - pathList: list of paths to scripts, as returned by TUI.Base.ScriptLoader.getScriptDirs()
        """
        self.master = master
        _MenuNode.__init__(self, None, label, pathList)
        
    def _setMenu(self):
        self.menu = tkinter.Menu(
            self.master,
            tearoff = False,
            postcommand = self.checkMenu,
        )
    
    def _fillMenu(self):
        """Fill the menu.
        """
        self.menu.add_command(label="Open...", command=self.doOpen)
        _MenuNode._fillMenu(self)

    def doOpen(self):
        """Handle Open... menu item.
        """
        initialDir = os.path.expanduser("~")
        if initialDir == "~":
            initialDir = None
        fullPath = tkinter.filedialog.askopenfilename(
            master = self.master,
            initialdir = initialDir,
            title="TUI Script",
            filetypes = [("Python", "*.py")],
        )
        if not fullPath:
            return
        pathList = os.path.split(fullPath)
        ScriptLoader(subPathList=pathList, fullPath=fullPath)()

    def getLabels(self):
        """Return a list of labels all the way up to, but not including, the root node.
        """
        return []


if __name__ == "__main__":
    import RO.Wdg
    root = tkinter.Tk()
    
    menuBar = tkinter.Menu(root)
    root["menu"] = menuBar

    scriptMenu = getScriptMenu(menuBar)
    menuBar.add_cascade(label="Scripts", menu=scriptMenu)
    
    root.mainloop()
