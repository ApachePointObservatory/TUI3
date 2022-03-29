def apolloWindowPaths():
  import sys
  # Point to hippodraw
  #sys.path.append("C:\\Python25\\hippodraw") # no end backslashes!
  #sys.path.append("C:\\Python25\\hippodraw\\examples")# no end backslashes!
  # point to location of Pmw folder
  #sys.path.append("C:\\Python25")
  #sys.path.append("/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages")
  #sys.path.append("/usr/local/lib/python2.7/site-packages") 
  sys.path.append("/opt/pyenv/versions/observers39/lib/python3.9/site-packages")
def hippoWdgPaths(): # current ATUI code directory, substitute your user for "NPL"
  import sys
  path = "/Users/dev/Library/Application Support/TUIAdditions/Apollo/" # yes end backslashes!
  #path = "/Users/dev/Library/Application\ Support/TUIAdditions/Apollo/" # yes end backslashes!
  return path

def imagePath(): # image subfolder
  import sys
  #path = "/Users/Lou/Library/Application Support/TUIAdditions/Apollo/images/" # yes end backslashes!
  path = "/Users/dev/Library/Application Support/TUIAdditions/Apollo/images/" # yes end backslashes!
  return path

def dataDir(): # folder with archived APOLLO data to use for "replay"
    #dataDir = "/Users/Lou/Documents/Apollo/data/" # yes end backslashes!
    dataDir = "/Users/dev/Library/Application Support/TUIAdditions/Apollo/data/" # yes end backslashes!
    return dataDir

def moonPos():
    return "/Users/dev/Library/Application\ Support/TUIAdditions/Apollo/ephem/moon_pos.py

