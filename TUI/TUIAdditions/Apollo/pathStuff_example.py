def apolloWindowPaths():
  import sys
  # Point to hippodraw
  sys.path.append("C:\\Python25\\hippodraw") # no end backslashes!
  sys.path.append("C:\\Python25\\hippodraw\\examples")# no end backslashes!
  # point to location of Pmw folder
  sys.path.append("C:\\Python25")

def hippoWdgPaths(): # current ATUI code directory, substitute your user for "NPL"
  import sys
  path = "C:\\Documents and Settings\\NPL\\Application Data\\TUIAdditions\\APOLLO\\" # yes end backslashes!
  return path

def imagePath(): # image subfolder
  import sys
  path = "C:\\Documents and Settings\\NPL\\Application Data\\TUIAdditions\\APOLLO\\images\\" # yes end backslashes!
  return path

def dataDir(): # folder with archived APOLLO data to use for "replay"
    dataDir = "C:\\APOLLO\\data\\" # yes end backslashes!
    return dataDir

def moonPos():
  # This should point to your moon_pos.py executable
  return "/Users/jbattat/Library/Application\ Support/TUIAdditions/Apollo/ephem/moon_pos.py"
