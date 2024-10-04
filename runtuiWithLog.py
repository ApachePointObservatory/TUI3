#!/usr/bin/env python3
"""Launch TUI, the APO 3.5m telescope user interface.

Location is everything:
This script's directory is automatically added to sys.path,
so having this script in the same directory as RO and TUI
makes those packages available without setting PYTHONPATH.

History:
2004-05-17 ROwen    Bug fix: automatic ftp hung due to import lock contention,
                    because execution was part of importing.
                    Fixed by first importing TUI.Main and then running the app.
2006-03-06 ROwen    Branch standard runtui.py; this version redirects stderr
                    to a log file in docs directory, if possible.
2007-01-23 ROwen    Changed #!/usr/local/bin/python to #!/usr/bin/env python
2008-01-29 ROwen    Modified to add ../tcllib to TCLLIBPATH on MacOS X;
                    this simplies the use of the built-in Tcl/Tk in the Mac package.
2009-02-24 ROwen    Modified to name log files by UTC date and to save 10 old log files.
2009-03-02 ROwen    Modified to redirect stdout to the error log (in addition to stderr).
2009-11-09 ROwen    Modified to generate the log name from TUI.Version.ApplicationName.
2014-04-25 ROwen    Modified to put the log files in a subdirectory
                    and to start the log with a timestamp and TUI version.
2014-11-13 ROwen    Modified log file name format to eliminate colons.
"""
import TUI.Main
TUI.Main.runTUIWithLog()

