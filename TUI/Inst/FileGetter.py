"""Code to auto-download images.

Note: instantiate only one of these per instrument, regardless of how many copies
of ExposeStatusWdg there are, to avoid downloading duplicate images.

2009-05-05 ROwen    Extracted from ExposeModel.py and improved to support various modes
2009-05-06 ROwen    Modified to use getEvery download preference isntead of autoGet.
2009-07-09 ROwen    Removed unused import of Tkinter (found by pychecker).
                    Removed unusable test code (found by pychecker).
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2011-07-21 ROwen    Renamed instModel to exposeModel for improved clarity.
2011-07-27 ROwen    Updated for new location of HubModel.
2012-08-10 ROwen    Updated for RO.Comm 3.0.
2014-09-17 ROwen    Bug fix: __all__ was mis-set.
"""
__all__ = ['FileGetter']

import collections
import os
import sys
import RO.Alg
import RO.Astro.ImageWindow
import RO.CnvUtil
import RO.DS9
import RO.KeyVariable
import RO.SeqUtil
import RO.StringUtil
import TUI.TUIModel
import TUI.Models.HubModel

class FileGetter (object):
    def __init__(self, exposeModel):
        self.exposeModel = exposeModel
        self.instName = self.exposeModel.instName
        self.ds9WinDict = {}
        
        self.hubModel = TUI.Models.HubModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()
        
        # set of active downloads; each entry is an HTTPGet object
        self.activeDownloads = set()
        # queue of pending downloads; each entry is a list of keyword argument dictionaries
        # for the download widget's getFile method (one dict per camera, e.g. red and blue for DIS)
        self.pendingDownloadArgs = collections.deque()
        
        self.nSkipped = 0

        downloadTL = self.tuiModel.tlSet.getToplevel("TUI.Downloads")
        self.downloadWdg = downloadTL and downloadTL.getWdg()
        
        if self.downloadWdg:
            # set up automatic ftp; we have all the info we need
            self.exposeModel.files.addCallback(self._updFiles)

    def _downloadFinished(self, camName, httpGet):
        """Call when an image file has been downloaded"""
#         print "%s._downloadFinished(camName=%s, httpGet=%s)" % (self.__class__.__name__, camName, httpGet)
        try:
            self.activeDownloads.remove(httpGet)
        except Exception:
             sys.stderr.write("FileGetter internal error: could not remove completed httpGet from activeDownloads\n")

        # start next download if current set finished
        self._handlePendingDownloads()
        
        # display image if display wanted and camera name known and download succeeded
#         print "viewImageVarCont=%r" % (self.exposeModel.viewImageVarCont.get())
        if self.exposeModel.viewImageVarCont.get() and (camName is not None) and (httpGet.state == httpGet.Done):
            ds9Win = self.ds9WinDict.get(camName)
            try:
                if not ds9Win:
                    if camName not in self.exposeModel.instInfo.camNames:
                        raise RuntimeError("Unknown camera name %r for %s" % (camName, self.instName))
                    if camName:
                        ds9Name = "%s_%s" % (self.instName, camName)
                    else:
                        ds9Name = self.instName
                    ds9Win = RO.DS9.DS9Win(ds9Name, doOpen=True)
                    self.ds9WinDict[camName] = ds9Win
                elif not ds9Win.isOpen():
                    ds9Win.doOpen()
                ds9Win.showFITSFile(httpGet.toPath)
            except Exception as e:
                self.tuiModel.logMsg(
                    msgStr = RO.StringUtil.strFromException(e),
                    severity = RO.Constants.sevError,
                )
        
    def _updFiles(self, fileInfo, isCurrent, keyVar):
        """Call whenever a file is written
        to start an ftp download (if appropriate).
        
        fileInfo consists of:
        - cmdr (progID.username)
        - host
        - common root directory
        - program and date subdirectory
        - user subdirectory
        - file name(s) for most recent exposure
        """
        if not isCurrent:
            return
        if not keyVar.isGenuine():
            # cached; avoid redownloading
            return

#         print "_updFiles(%r, %r)" % (fileInfo, isCurrent)
        getEveryNum = self.exposeModel.getEveryVarCont.get()
        if getEveryNum == 0:
            # no downloads wanted
            self.pendingDownloadArgs.clear()
            return

        cmdr, dumHost, dumFromRootDir, progDir, userDir = fileInfo[0:5]
        progID, username = cmdr.split(".")
        fileNames = fileInfo[5:]
        
        host, fromRootDir = self.hubModel.httpRoot.get()[0]
        if None in (host, fromRootDir):
            errMsg = "Cannot download images; hub httpRoot keyword not available"
            self.tuiModel.logMsg(errMsg, RO.Constants.sevWarning)
            return
        
        if self.tuiModel.getProgID() not in (progID, "APO"):
            # files are for a different program; ignore them unless user is APO
            return
        if not self.exposeModel.getCollabPref.getValue() and username != self.tuiModel.getUsername():
            # files are for a collaborator and we don't want those
            return
        
        toRootDir = self.exposeModel.ftpSaveToPref.getValue()

        # save in userDir subdirectory of ftp directory
        argList = []
        for ii, fileName in enumerate(fileNames):
            if fileName == "None":
                continue

            dispStr = "".join((progDir, userDir, fileName))
            fromURL = "".join(("http://", host, fromRootDir, progDir, userDir, fileName))
            toPath = os.path.join(toRootDir, progDir, userDir, fileName)
            
            camName = RO.SeqUtil.get(self.exposeModel.instInfo.camNames, ii)
            doneFunc = RO.Alg.GenericCallback(self._downloadFinished, camName)
            if camName is None:
                self.tuiModel.logMsg(
                    "More files than known cameras for image %s" % fileName,
                    severity = RO.Constants.sevWarning,
                )
            
            argList.append(dict(
                fromURL = fromURL,
                toPath = toPath,
                isBinary = True,
                overwrite = False,
                createDir = True,
                dispStr = dispStr,
                doneFunc = doneFunc,
            ))

        self.pendingDownloadArgs.append(argList)
        self._handlePendingDownloads()

    def _handlePendingDownloads(self):
        """Examine pending downloads and start next download, if appropriate"""
#         print "%s._handlePendingDownloads(); there are %s active and %s pending downloads" % \
#             (self.__class__.__name__, len(self.activeDownloads), len(self.pendingDownloadArgs),)
        getEveryNum = self.exposeModel.getEveryVarCont.get()
        if getEveryNum == 0:
            # no downloads wanted
#             print "No downloads wanted; clearing pending downloads"
            self.pendingDownloadArgs.clear()
            return
        
        if self.activeDownloads:
            # make sure these are all truly active; this should never happen,
            # but the consequences are severe so be paranoid
            trulyActiveDownloads = [dl for dl in self.activeDownloads if not dl.isDone]
            if len(trulyActiveDownloads) != len(self.activeDownloads):
#                 print "warning: purging activeDownloads of %d completed downloads" % \
#                     (len(self.activeDownloads) - len(trulyActiveDownloads))
                self.activeDownloads = set(trulyActiveDownloads)
            if self.activeDownloads:
#                 print "There are %d active downloads; don't start a new one" % (len(self.activeDownloads),)
                return

        argList = []
        if getEveryNum > 0:
            # nToSkip = getEveryNum - 1
            nPending = len(self.pendingDownloadArgs)
            if nPending >= getEveryNum:
#                 print "Purge first %d entries from pendingDownloads and download the next" % (getEveryNum-1,)
                # deques don't handle slicing, unfortunately
                for x in range(getEveryNum-1):
                    del(self.pendingDownloadArgs[0])
                argList = self.pendingDownloadArgs.popleft()
#             else:
#                 print "There are not enough pending downloads yet; waiting"
        elif getEveryNum < 0:
            # start most recent images; ditch the rest
#             print "Download last image in pending downloads and clear the rest"
            if self.pendingDownloadArgs:
                argList = self.pendingDownloadArgs.pop()
                self.pendingDownloadArgs.clear()

        for argDict in argList:
            httpGet = self.downloadWdg.getFile(**argDict)
            if not httpGet.isDone:
                try:
                    self.activeDownloads.add(httpGet)
                except Exception:
#                     print "self.activeDownloads=%r" % (self.activeDownloads,)
                    raise
