import os

"""
This hook script adds possible locations of other dependencies, such
as xpaget from xpa-tools. Add possible paths to the ADD_PATH
list object below.
"""
ADD_PATH=[
	'/opt/local/bin',
	'/opt/homebrew/bin',
	'/usr/local/Homebrew/bin',
	]
# Add only the existing path items to PATH.
for path in ADD_PATH:
	if os.path.exists(path):
		os.environ['PATH'] += os.pathsep + path
