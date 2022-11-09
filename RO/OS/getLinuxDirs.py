"""
Utilities for getting standard directories for Linux distributions.
"""

import os

def getAppDirs(inclNone = False):
    """
    Return's list of NoneTypes for Linux as PATH
    environment is used to locate apps.
    """
    if inclNone:
        return [None, None]
    else:
        return []

def getAppSuppDirs(inclNone = False):
    """
    Return User's preferences diectory. For Linux this
    is the home directory.
    """
    return getPrefsDirs(inclNone = inclNone)

def getDocsDir():
    """
    Return User's documents directory. For Linux this
    is the home directory.
    """
    return getHomeDir()

def getPrefsDirs(inclNone = False):
    """
    Return the preferences directory. For Linux, this
    is the home directory.
    """
    if inclNone:
        return [getHomeDir(), None]
    else:
        homeDir = getHomeDir()
        if homeDir is not None:
            return [homeDir]
    return []

def getHomeDir():
    """
    Return the path to the user's home directory.
    """
    return os.environ.get('HOME')

def getPrefsPrefix():
    """
    Return the prefix for the preferences file,
    '.' for Linux.
    """
    return '.'
