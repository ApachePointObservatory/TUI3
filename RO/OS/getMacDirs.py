
"""Utilities for finding standard Mac directories.

History:
2004-02-04 ROwen
2004-02-12 ROwen    Modified to use fsref.as_pathname() instead of Carbon.File.pathname(fsref).
2005-07-11 ROwen    Modified getAppSuppDirs to return None for nonexistent directories.
                    Removed doCreate argument from getAppSuppDirs, getDocsDir and getPrefsDir.
                    Added getDocsDir.
2005-09-27 ROwen    Changed getPrefsDir to getPrefsDirs.
                    Added getAppDirs.
                    Refactored to use getMacUserDir and getMacUserSharedDirs.
2005-10-05 ROwen    Added inclNone argument to getXXXDirs functions.
                    Modified getStandardDir to return None if dirType is None.
                    Added getAppDirs and getPrefsDirs to the test code.
                    Removed obsolete getPrefsDir.
2015-09-24 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
"""
from Foundation import *


def getAppDirs(inclNone = False):
    """Return up to two paths: user's private and shared application directory.

    Inputs:
    - inclNone  if True, paths to missing folders are set to None;
                if False (the default) paths to missing folders are omitted
    """
    userPrivateAppDirs = NSSearchPathForDirectoriesInDomains(
            NSApplicationDirectory,
            NSUserDomainMask,
            True
            )
    userLocalAppDirs = NSSearchPathForDirectoriesInDomains(
            NSApplicationDirectory,
            NSLocalDomainMask,
            True
            )
    return [*userPrivateAppDirs, *userLocalAppDirs]

def getAppSuppDirs(inclNone = False):
    """Return up to two paths: the user's private and shared application support directory.
    
    Inputs:
    - inclNone  if True, paths to missing folders are set to None;
                if False (the default) paths to missing folders are omitted
    """
    userPrivateSuppDirs = NSSearchPathForDirectoriesInDomains(
            NSApplicationSupportDirectory,
            NSUserDomainMask,
            True
            )
    userLocalSuppDirs = NSSearchPathForDirectoriesInDomains(
            NSApplicationSupportDirectory,
            NSLocalDomainMask,
            True
            )
    return [*userPrivateSuppDirs, *userLocalSuppDirs] 

def getDocsDir():
    """Return the path to the user's documents directory.
    
    Return None if the directory does not exist.
    """
    userDocumentDir = NSSearchPathForDirectoriesInDomains(
            NSDocumentDirectory,
            NSUserDomainMask,
            True
            )
    return userDocumentDir[-1]

def getPrefsDirs(inclNone = False):
    """Return up to two paths: the user's local and shared preferences directory.
    
    Inputs:
    - inclNone  if True, paths to missing folders are set to None;
                if False (the default) paths to missing folders are omitted
    """
    userPrivatePrefPanesDir = NSSearchPathForDirectoriesInDomains(
            NSPreferencePanesDirectory,
            NSUserDomainMask,
            True
            )
    userLocalPrefPanesDir = NSSearchPathForDirectoriesInDomains(
            NSPreferencePanesDirectory,
            NSLocalDomainMask,
            True
            )
    return [*userPrivatePrefPanesDir, *userLocalPrefPanesDir]

