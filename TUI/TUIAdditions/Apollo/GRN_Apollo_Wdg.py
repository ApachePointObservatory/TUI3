#!/usr/local/bin/python
"""Display data from Apollo.
History:
2005-02-11 ROwen        a shell
2005-07-21 CDH much more than a shell, reads Houston!
2005-08-28 Erik Swanson - added code to read the 'Dark' record. This dark background is subtracted
                    from all 'stare' plots on the fly. In addition any APD channel that fires in > 90 percent
                    of the gates (ie. is stuck on) is added to a list and those channels are omitted from all plots
2005-11-10 CDH look at SVN repository for further update information - svn://svn.apo.nmsu.edu/Apollo/TUI/trunk/Main
2006-02-14 CDH this works with hippodraw 1.15.3 on Windows XP
2006-02-15 CDH changed to Pmw Notebook layout
2006-03-30 CDH update to TUI 1.2a and Hippodraw 1.16.3
2006-06-29 CDH requires TUI 1.2 and tested with hippodraw 1.17.3
2006-07-10 CDH use hippodraw 1.17.5 or later
2007-06-25 CDH tested OK with hippodraw 1.20.5 and TUI 1.3 (now must have LogWdg.py)
2014-09-22 CDH commented out stuff to start switch to matplotlib
2014-12-05 CDH functioning matplotlib interface on Windows 7 Machines
2015-02-05 CDH Had to edit registry commands for windows to make moonwdg work HKEY_CLASSES_ROOT\py_auto_file\shell\open\command
                    and HKEY_CLASSES_ROOT\Applications\python26.exe\shell\open\command both need additional %* at end of command
"""

import numpy as np
from scipy.optimize import leastsq

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure as mplFigure
import matplotlib.transforms as mplTransforms

import tkinter as Tk
import time
import string
import RO.Constants
import RO.Wdg
import TUI.TUIModel
import TUI.TCC.TCCModel
from . import ApolloModel
from . import pathStuff
from . import LogWdg
from .savgol_filter import savgol_filter

path = pathStuff.hippoWdgPaths()
imagePath = pathStuff.imagePath()
#
import Pmw
from . import moonWdg
from . import laserKeypad
from . import stv

import socket
import pickle
import sys
import errno

# globals
NChan = 17
gpsi = 0
testFlag = 0
labelFont = ('Times',10,'bold')

_HelpPrefix = "APOLLO graphics widget"

HOUSTON = 0
pickleSep = ':::::'

class NoteBook(Pmw.NoteBook):
        def __init__(self,master,**kargs):

    ## set up the notebook
                Pmw.NoteBook.__init__(self, master,**kargs)
                
                # get reference to the plot window ...
                #for child in master.master.children.values():
                #        print child
#                        if isinstance(child, RO.Wdg.Toplevel):
#                                for kid in child.children.values():
#                                        if isinstance(kid, ApolloPlotWindow.Plots):
#                                                self.ApolloPlot = kid
#                                                
                
                self.buttFrame = Tk.Frame(master, width=10)
                gr_butt = RO.Wdg.Gridder(self.buttFrame)
                self.buttFrame.pack(side='left',anchor='nw')
                self.buttFrame.pack_propagate(1)

                self.stateDict = {0:'EXIT',1:'IDLE',2:'WARMUP',3:'RUN',4:'COOLDOWN',5:'STARE',6:'FIDLUN',7:'STANDBY',
                                  8:'DARK',9:'FLAT',10:'LPOWER',11:'CALTDC',12:'LASERCAL'}
                self.numberOfStateName = {}  # assumes that all state names are unique and can serve as keys
                for key in list(self.stateDict.keys()):
                        val = self.stateDict[key]
                        self.numberOfStateName[val] = key

                # Order that state buttons appear in ATUI
                # ('None' gives a gap)
                # Tom's list
                self.stateButtonList = ['IDLE','WARMUP','STANDBY',None,'RUN',None,'FIDLUN','CALTDC','STARE',
                                        'DARK','FLAT','LPOWER','LASERCAL',None,'COOLDOWN']
                # Russet's list
                #self.stateButtonList = ['WARMUP','STARE','CALTDC','DARK','FLAT','FIDLUN','LPOWER','STANDBY','RUN','IDLE','LASERCAL','COOLDOWN']
                self.p1=self.add(' Main ')

                self.p2=self.add('Pointer')
                self.wdg2 = moonWdg.moonWdg(self.p2)
                self.wdg2.pack(side='top', anchor='nw')
 
                self.p3 = self.add('Plot Control')
                
                self.p4 = self.add('Alarms')

                self.p5 = self.add('Raster')
                
                self.p6 = self.add('STV')
                stvFrame = Tk.Frame(self.p6, width=640, height=640)
                stvFrame.pack(side='left',anchor='nw',fill='none',expand=0)
                
                self.p7 = self.add('Channels')
                
                self.p8 = self.add('Power')

                self.p9 = self.add('Laser Tuning')
                p9TopFrame = Tk.Frame(self.p9)
                p9TopFrame.pack(side='top', anchor='nw')
                p9MidFrame = Tk.Frame(self.p9)
                p9MidFrame.pack(side='top', anchor='nw')
                p9BotFrame = Tk.Frame(self.p9)
                p9BotFrame.pack(side='top', anchor='nw')
                laserFrame = Tk.Frame(p9TopFrame)
                laserFrame.pack(side='right',anchor='ne')
                self.p10 = self.add('ROOT')
                self.p11 = self.add('ACS')
                
# initialize stuff
    
                self.runStarted = 0    # logical true if run in progress
                self.shotsInSec = 0    # # of laser shots in the last second, as repoted by GPS
#
                self.shotBuffer = 10    # of shots to buffer before redrawing hippo plots
#
                self.state = 0
                self.nruns = 0
#
                self.cmdr = ''
                self.cmdrMID = 0
                self.cmdActor = ''
                self.cmdText = ''  # why is this needed as a global??? it's only used in newCmdText()
#                
                self.tccModel = TUI.TCC.TCCModel.getModel()
                self.apolloModel = ApolloModel.getModel()   # get models
                self.tuiModel = TUI.TUIModel.getModel()
#
                self.wdg2.tuiModel = self.tuiModel
                self.wdg2.tuiModel=self.tuiModel
#
                self.dispatcher = self.tuiModel.dispatcher               
#
                self.catList = (("Error","red"), ("Warning","blue2"), ("Information","black"))                
                self.AFSCImage =Tk.PhotoImage(file= imagePath + 'afspc100.gif') 
                self.wdgFlag = 0 # flag for space command widget color
#
#                # array buffers for displays
                self.hitGridReserve = 200
                self.intenReserve = 200
                self.histReserve = 200
                self.rateReserve = 200
                self.fidStripReserve = 2000
                self.lunStripReserve = 2000
                self.stareStripReserve = 10000
                self.trackReserve = 20000
#
                self.irasterGuide = 0
                self.irasterRxx = 0
                self.raster = 0
                self.rasterMag = 0.0
                self.rasterShots = 0
                self.rasterList = ['right','up','left','left','down','down','right','right','upLeft']
#                
#                # Adam's APD channel map (APD #), index is TDC channel
#                    # 0 in upper left ('top'), 15 in lower right
                self.chanMap = [6,15,2,11,3,10,1,7,8,14,5,12,4,13,0,9]
#                
#                # channel offset
                self.chanOffset = []
                chanOffRaw = [302.643,360.405,0.0,325.358,0.0,330.413,345.359,0.0,
                              350.086,337.171,324.468,278.374,312.305,290.245,0.0,329.595]
                nGood = 16-chanOffRaw.count(0.0) #number of good channels
                mn = np.add.reduce(chanOffRaw)/nGood # mean offset
                
                for i in range(16):
                    if chanOffRaw[i]:
                        self.chanOffset.append(int(round(chanOffRaw[i]-mn)))
                    else:
                        self.chanOffset.append(0)
                #old offsets
                #self.chanOffset = [-23,29,0,-5,0,12,16,0,28,15,3,-44,-10,-29,0,9] #channel offsets, index is TDC channel
                #self.chanOffset = [7, -16, 16, -33, 27, -10, 33, 18, 7, -12, 11, -26, -5, -13, 0, -8]
                self.chanOffset = [2, -21, 13, -37, 25, -14, 30, 16, 1, -16, 46, -31, -9, -19, 0, 16]  # March 30, 2017
                self.powerList = [] # list of power indices gotten from Power
                self.pwrWdgDict ={} # list of power checkbox widgets

                self.chanBackground = np.zeros(16)     # Background rate array
                self.chanFlat = np.zeros(16)           # Flat array
                self.chanFlatCorr = np.ones(16)
                self.omitTDCChan = []   # TDCs to be omitted
                self.sumDarkChans = 0   # sum of darks
                self.chanAPD = 0
                self.hitgridReg = True  # lunar hitgrid displays only registered photons if True
                
                self.totalFidNum = 0        # Total Photons and rates
                self.fidRegNum = 0          # total registered fiducials
                self.fidRate = 0.0          # fiducial photon rate
                self.fidRegRate =0.0        # registered fiducial rate
                self.tdc_target = 2000

                self.rxx = 0.               #optics x offset
                self.rxy = 0.               #optics y offset

                self.totalLunNum = 0        # total # of lunar photons
                self.lunRate = 0            # lunar rate

                self.totalLunRegNum = 0     # Registered Photons and rate
                self.lunRegRate = 0.0 # registered lunar rate
                self.yield_est = 0.0 # estimate of lunar yield
                self.gateWidth = 8 # lunar gatewidth setting
                self.runfidgw = 7 # fid gatewidth setting

                self.lunBackgroundNum = 0   # background Photons and rate
                self.lunBackgroundRate = 0.0
                self.missedFRC = 0
                
                self.regCenter=0             # center of registered region
                self.binForReg = 160         # full width in TDC bins for lunars to be "Registered"
                self.lower = self.regCenter-self.binForReg/2 # registered lower bound
                self.upper = self.regCenter+self.binForReg/2 # registered upper bound
                self.bg_after = (-6.5*self.binForReg, -1.5*self.binForReg)
                self.bg_before = (1.5 * self.binForReg, 2.5*self.binForReg)
                #self.bg_multiple = 6
                self.bg_multiple  = abs(self.bg_after[1]  - self.bg_after[0])
                self.bg_multiple += abs(self.bg_before[1] - self.bg_before[0])
                self.bg_multiple  /= self.binForReg
                self.bgLun = 0 

                
                self.regCenterFid=-444      # nominal center of fiducial spike
                self.binForRegFid = 160     # full width in TDC bins for fids to be "Registered"
                self.lowerFid = self.regCenterFid-self.binForRegFid/2
                self.upperFid = self.regCenterFid+self.binForRegFid/2
                self.tcorListFid=[]

                self.lunHeight = 1                
                self.changeState = 0.   #state change flag for adding delimiting lines to plots
                
                self.stareShot = 0          # # of stares taken

#            # tracking stuff
                self.offMag = 0.0           # magnitude of guide offset step for raster
                self.offx = 0.0             # guide offset in Az
                self.offy = 0.0             # guide g in Alt
                self.boreAz = 0.0           # boresight offset in Az
                self.boreEl = 0.0           # boresight offset in El
                self.offString = Tk.StringVar()
                self.rxxOffString = Tk.StringVar()
                self.offsetNum = 0          # Guide offset #
                self.offsetAz = 0.0         # Guide azimuth offset
                self.offsetEl = 0.0         # Guide elevation offset
                self.axisPos = (0.0,0.0)    # telscope axes (Az, Alt)
                self.altCor = 1.0           # 1/cos(alt)
                self.shotsHere = 0          # shots at this guide offset
                self.rateHere = 0.0         # rate at thie guide offset
                self.lunNumHere = 0         # total lunar # at this guide offset
                self.lunRegNum = 0          # total registered # of lunars
                self.lunRegNumHere = 0      # total registered # of lunars at this guide offset
                self.lunRateHere = 0        # lunar rate at this guide offset
                self.lunRegRateHere = 0     # lunar registered at this guide offset
                self.staresHere = 0         # of stares at this guide offset
                self.stareNumHere = 0
                self.stareRateHere = 0.0    #stare rate at this guide offset

                self.shotsRxx = 0           # shots at this rxx,rxy
                self.rateRxx = 0.0          # rate at thie rxx,rxy
                self.lunNumRxx = 0          # total lunar # at this rxx,rxy
                self.lunRegNumRxx = 0       # total registered # of lunars at this rxx,rxy
                self.lunRateRxx = 0         # lunar rate at this rxx,rxy
                self.lunRegRateRxx = 0      # lunar registered at this rxx,rxy

                self.shotNum = 0            # shot number as determined from fids
                self.shotNumLun = 0         # lunar shot number
                self.lpowerTime = 0         # length of laser power measurement
                self.laserPower = []
                self.lPowerNum = 0          # number of shots in power measurement
                self.lPowerNum_list = []    # list of numbers of samples [1,2,3,4,...]
                self.laserPowerAverage = [] # running average value of laser power
                self.lasernshots = 0        # test power
                # Indicate laser tuning adjustments on the Laser Power stripchart plot
                self.laserPowerOscVoltColor     = 'k' # black
                self.laserPowerSHGRotationColor = 'r' # green

                self.lockStatus = True      # houston commands enabled if False

                self.stateButtArray =[]     #array of houston state buttons
                self.predSkew = 0
                self.alarmState = False         # binary state of houston alarms
                self.ampDelInc = 10              # set default amp delay increment to 10
                
                self.lenFidBunch = self.shotBuffer        # number of fids to bundle
                self.lenLunBunch = self.shotBuffer        # number of luns to bundle
 
                self.chanTimesCorTot=[]
                #self.chanTimesCorHist=[]
                self.shotList=[]
                
                self.chanTimesCorTotLun=[]
                self.chanTimesCorHistLun=[]
                self.shotListLun=[] 
                
                self.lun_rate_strip_data=[]
                self.lunRegList=[]
                self.redrawFlag=False
                
                self.hitgridData=np.zeros([200,16])
                self.noConvergence = 0

                # ACS related, remember to put in resetCounters

                self.acsFakeDACScanN    = 0        # test DAC scanning
                self.acsFakePhaseSweepN = 0      # test Phase sweeps
                self.ACS_filter_on = False      # determines whether the program tries to find ACS-induced peak and identify photons that are potentially ACS
                self.ACS_filter_active = False  # whether the stats will be affected by the above. This is True when signal is clearly detected
                self.tws_mod_dict = {0:0, 2:200, 4:400, 6:100, 8:300}  # choose shift based on tws to align the arrival time in "ACS frame"


                #######new vars, need to add to reset#######
                
                #self.fidChanTimesTot = []
                #self.fidTWSPhasedTot = []
                self.fidTWSPhasedTransient = []

                #######new vars, need to add to reset#######
                #self.mod_list = [(self.ACS_peak + i) % self.ACS_period for i in range(-5, 6)]
                self.lunShotToCount = [0]
                self.lunRawTDCTot = []
                self.lunRawTDCHist = []
                self.ACSSubtracted = 0
                self.ACSTotNum = []
                self.ACSShotReserve = 100
                # shots
                #

                # track whether an ACS command is underway (BUSY) or finished (IDLE) or a command failed (ERROR)
                self.ACS_LSB_STATE_IDLE = 0
                self.ACS_LSB_STATE_BUSY = 1
                self.ACS_LSB_STATE_ERROR = 2
                self.acsLsbStateLEDColors = {self.ACS_LSB_STATE_BUSY:'yellow', 
                                             self.ACS_LSB_STATE_IDLE:'green', 
                                             self.ACS_LSB_STATE_ERROR:'red'}
                # Keep track of the current ACS LSB state
                self.acsLsbState = self.ACS_LSB_STATE_IDLE

                # Nominal FID and LUN delay values (fid0, fid1, lun0, lun1)
                self.acsNominalDelayValues = [0, 42, 85, 125]

                # Bias extremize values locally
                self.acsDACExtremizePostPPGRNVals = []
                self.acsDACExtremizeDACVals = []
                self.acsDACOptimumVal = 0 #3100 # nominal guess value  

                # log DAC sweep values locally
                self.acsDACSweepDACVals = []
                self.acsDACSweepPostPPIRVals = []
                self.acsDACSweepGreenVals = []
                #self.acsDACSweepDACOfMin = -1
                self.acsDACSweepIsStale = True

                # log Phase sweep values
                self.acsPhaseSweepPhaseVals    = []
                self.acsPhaseSweepPostPPIRVals = []
                self.acsPhaseSweepIsStale = True
                
                self.lunTWSPhasedTransient = []
                self.TWSPhasedBinWidth = 6
                self.TWSPhasedXlim = (1400, 3000)
                self.TWSPhasedBinEdges = np.arange(self.TWSPhasedXlim[0], self.TWSPhasedXlim[1], self.TWSPhasedBinWidth)
                self.ACSRadius = 20
                #self.TWSPhasedHistogram = np.histogram(self.lunTWSPhasedTransient, self.TWSPhasedBinEdges)
                self.TWSPhasedPeakLow = 9999 
                self.TWSPhasedPeakHigh = 9999
                self.TWSPeakWrapped = False    # combination that makes sure no photons get tagged before peak gets determined for the first time.
                self.fidTWSPhasedPeakLow = 9999 
                self.fidTWSPhasedPeakHigh = 9999
                self.fidTWSPeakWrapped = False

                
## set callbacks for keyword variables

                self.tccModel.guideOff.addCallback(self.newOffset)
                self.tccModel.boresight.addCallback(self.newBoresight)
                self.tccModel.axePos.addCallback(self.newAxePos)
                self.tccModel.secFocus.addCallback(self.newSecFocus)
                self.tccModel.objName.addCallback(self.newObjName)
                
                self.apolloModel.airTemp.addCallback(self.newAirTemp) # eventually change to tccModel
                self.apolloModel.pressure.addCallback(self.newPressure)
                self.apolloModel.humidity.addCallback(self.newHumidity)
    
#                self.apolloModel.oldfid.addCallback(self.newOldFid) # outdated?
#                
                self.apolloModel.fiducial.addCallback(self.newFiducial)
                self.apolloModel.lunar.addCallback(self.newLunar)
                self.apolloModel.stare.addCallback(self.newStare)
                self.apolloModel.gps.addCallback(self.newGPS)
                self.apolloModel.dark.addCallback(self.newDark)
                self.apolloModel.flat.addCallback(self.newFlat)
                self.apolloModel.state.addCallback(self.newState)
                self.apolloModel.polyname.addCallback(self.newPolyname)
                self.apolloModel.motrps.addCallback(self.newSpeed)
                self.apolloModel.mirrorphase.addCallback(self.newMirrPhase)
                self.apolloModel.nruns.addCallback(self.newNruns)
                self.apolloModel.gatewidth.addCallback(self.newGatewidth)
                self.apolloModel.tdc_target.addCallback(self.newTdc_target)
                self.apolloModel.runfidgw.addCallback(self.newRunfidgw)
                self.apolloModel.huntstart.addCallback(self.newHuntstart)
                self.apolloModel.huntdelta.addCallback(self.newHuntdelta)
                self.apolloModel.thunt.addCallback(self.newThunt)
                self.apolloModel.dskew.addCallback(self.newDskew)
                self.apolloModel.predskew.addCallback(self.newPredskew)
                self.apolloModel.starerate.addCallback(self.newStarerate)
                self.apolloModel.nstares.addCallback(self.newNstares)
                self.apolloModel.binning.addCallback(self.newBinning)
                self.apolloModel.ndarks.addCallback(self.newNdarks)
                self.apolloModel.flashrate.addCallback(self.newFlashrate)
                self.apolloModel.flashcum.addCallback(self.newFlashcum)
                self.apolloModel.vposx.addCallback(self.newVposx)
                self.apolloModel.vposy.addCallback(self.newVposy)
                self.apolloModel.vtargetx.addCallback(self.newVtargetx)
                self.apolloModel.vtargety.addCallback(self.newVtargety)
                self.apolloModel.fakertt.addCallback(self.newFakertt)
                self.apolloModel.blockremaining.addCallback(self.newBlockRemaining)
                self.apolloModel.releaseremaining.addCallback(self.newReleaseRemaining)
                self.apolloModel.apdtofpd.addCallback(self.newApdToFpd)
                self.apolloModel.dphase.addCallback(self.newDphase)
                self.apolloModel.dphase_target.addCallback(self.newDphase_target)
                self.apolloModel.bolopower.addCallback(self.newBolopower)
                self.apolloModel.bolopos.addCallback(self.newBolopos)
                self.apolloModel.powerstatus.addCallback(self.newPowerstatus)
                self.apolloModel.powerstate.addCallback(self.newPowerstate)
                self.apolloModel.statusline.addCallback(self.newStatusline)
                self.apolloModel.datafile.addCallback(self.newDatafile)
                self.apolloModel.logfile.addCallback(self.newLogfile)
                self.apolloModel.guideOff.addCallback(self.newGuideOff)
                self.apolloModel.boreOff.addCallback(self.newBoreOff)
                self.apolloModel.las_display.addCallback(self.newLas_display)
                self.apolloModel.stv_display.addCallback(self.newStv_display)
                self.apolloModel.text.addCallback(self.newText)
                self.apolloModel.g.addCallback(self.newG)
                self.apolloModel.i.addCallback(self.newI)
                self.apolloModel.h.addCallback(self.newH)
                self.apolloModel.alarms.addCallback(self.newAlarms)
                self.apolloModel.alarms_unack.addCallback(self.newAlarms_unack)
                self.apolloModel.cmdr.addCallback(self.newCmdr)
                self.apolloModel.cmdrMID.addCallback(self.newCmdrMID)
                self.apolloModel.cmdActor.addCallback(self.newCmdActor)
                self.apolloModel.cmdText.addCallback(self.newCmdText)
                self.apolloModel.oscVoltR.addCallback(self.newOscVoltR)
                self.apolloModel.ampdelay.addCallback(self.newAmpdelay)
                #self.apolloModel.shgRot.addCallback(self.newLaserShgRotation)
### ACS stuff
                self.apolloModel.pulseper.addCallback(self.newPulsePer)
                self.apolloModel.pulsegw.addCallback(self.newPulseGW)
                self.apolloModel.acsDACExtremize.addCallback(self.newACSDACExtremize)
                self.apolloModel.acsDACExtremizeStatus.addCallback(self.newACSDACExtremizeStatus)
                self.apolloModel.acsLaserLockState.addCallback(self.newACSLaserLockState)
                self.apolloModel.acsLaserDC.addCallback(self.newACSLaserDC)
                self.apolloModel.acsADC.addCallback(self.newACSADC)
                self.apolloModel.acsLunEn.addCallback(self.newACSLunEn)
                self.apolloModel.acsFidEn.addCallback(self.newACSFidEn)
                self.apolloModel.acsDacVal.addCallback(self.newACSDACVal)
                self.apolloModel.acsDelayVal.addCallback(self.newACSDelayVal)
                self.apolloModel.acsDACScanVal.addCallback(self.newACSDACScanVal)
                #self.apolloModel.acsDACScanDone.addCallback(self.newACSDACScanDone)
		self.apolloModel.acsDACSweepStatus.addCallback(self.newACSDACSweepStatus)
		self.apolloModel.acsPhaseSweepVal.addCallback(self.newACSPhaseSweepVal)
		self.apolloModel.acsPhaseSweepStatus.addCallback(self.newACSPhaseSweepStatus)
                #                                        
### Populate Tk Window with widgets
#
    # graphics control widgets 

                self.FuncCall = RO.Alg.GenericCallback


# some buttons to control ROOT window
                ROOTFrame = Tk.Frame(self.p10)
                ROOTFrame.pack(side = 'top', anchor = 'nw')
                self.connectButton = RO.Wdg.Button(
                        master = ROOTFrame,
                        text = 'Connect to ROOT',
                        command = self.socket_listen,
                        helpText = 'Creates socket that waits for connection fron a ROOT window.',
                        state = 'normal')
                self.connectButton.pack(side = 'top', padx = 5, pady = 5)
                self.connectButton.configure(foreground = 'purple')

                self.refreshButton = RO.Wdg.Button(
                        master = ROOTFrame,
                        text = 'Refresh',
                        command = self.ROOT_refresh,
                        helpText = 'Create fresh plot window. Exception: when ROOT window dies a horrible death, you will need to manually restart it, like using the Connect button.',
                        state = 'disabled')
                self.refreshButton.pack(side = 'top', padx =5, pady =5)


                self.ROOTidleButton = RO.Wdg.Button(
                        master = ROOTFrame,
                        text = 'Idle',
                        command = self.ROOT_idle,
                        helpText = 'ROOT window stops updating plots and process mouse events while staying connected.',
                        state = 'disabled')
                self.ROOTidleButton.pack(side = 'top', padx =5, pady =5)

                self.ROOTdisconnectButton = RO.Wdg.Button(
                        master = ROOTFrame,
                        text = 'Disconnect',
                        command = self.socket_destroy,
                        helpText = 'Closes connection to ROOT.',
                        state = 'disabled')
                self.ROOTdisconnectButton.pack(side = 'top', padx =5, pady =5)
                
                self.configFileLocEntry = RO.Wdg.StrEntry(
                        master = ROOTFrame,
                        defValue = '',
                        helpText ='Name of new configuration file. Leave blank to save to default location.',
                        width=20,
                        state = 'disabled'
                )
                self.configFileLocEntry.pack(side = 'left', pady = 5)

                
                self.ROOTsaveButton = RO.Wdg.Button(
                        master = ROOTFrame,
                        text = 'Save Configuration',
                        command = self.ROOT_save,
                        helpText = 'Save current ROOT window configuration. By default to pref.json.',
                        state = 'disabled')
                self.ROOTsaveButton.pack(side = 'top', padx = 5, pady = 5)

                #---------------------------------------------------------------------------
                # ACS Tab Start
                ACSFrame = Tk.Frame(self.p11)
                #ACSFrame.pack(side = 'top', anchor = 'nw', padx = 10)
                ACSFrame.grid(column=0, row=0, sticky='NS')

                ACS_PicoFYb_Frame = Tk.LabelFrame(ACSFrame, text = 'PicoFYb', font = labelFont)
                ACS_LSB_Frame     = Tk.LabelFrame(ACSFrame, text = 'LSB', font = labelFont)
                ACSRandomFrame    = Tk.LabelFrame(ACSFrame,text = 'Test',font = labelFont)
                #
                gr_PicoFYb = RO.Wdg.Gridder(ACS_PicoFYb_Frame, sticky= "nw")
                gr_LSB     = RO.Wdg.Gridder(ACS_LSB_Frame, sticky= "nw")
                gr_random  = RO.Wdg.Gridder(ACSRandomFrame, sticky="nw")

                self.acsPicoFYbDCPowerButton = RO.Wdg.Checkbutton(
                        master=ACS_PicoFYb_Frame,
                        text=None,
                        selectcolor = 'white',
                        defValue = False,
                        helpText = 'control power on/off of the PicoFYb laser',
                        command = self.acsPicoFYbDCPowerFxn,
                        padx=0
                )

                # For some reason the create_oval() function seems to require some extra padding...
                # or maybe there is some border/boundary in the Tk.Canvas that contains the oval (circle)?
                # Anyway, as a workaround, we add in some padding so that the circle is centered in the Canvas
                ledDiam = 15
                padding = 5
                canvasSize = ledDiam + padding
                xmin = canvasSize*0.5-ledDiam*0.5
                xmax = (canvasSize*0.5+ledDiam*0.5) - 1
                ymin = xmin
                ymax = xmax
                ledBorder = 0
                self.acsLaserPowerLED_ON    = 'green'
                self.acsLaserPowerLED_OFF   = 'black'
                self.acsLaserPowerLED_UNKNOWN = 'pink'
                self.acsLaserPowerLED_ERROR = 'red'
                self.acsLaserPowerLED_DEFAULT = self.acsLaserPowerLED_OFF
                self.acsLaserPowerLEDCanvas = Tk.Canvas(ACS_PicoFYb_Frame, width=canvasSize, height=canvasSize, bd=0)
                self.acsLaserDCPowerLED = self.acsLaserPowerLEDCanvas.create_oval(xmin, ymin, xmax, ymax, fill=self.acsLaserPowerLED_DEFAULT, outline='black', width=1)
                #self.acsLaserPowerLEDCanvas.pack()
                self.acsLaserPowerLEDCanvas.grid()



                self.acsPicoFYbLock = RO.Wdg.Checkbutton(
                        master=ACS_PicoFYb_Frame,
                        text=None,
                        selectcolor = 'white',
                        defValue = False,
                        helpText = 'control lock of PicoFYb',
                        command = self.acsLaserLockFxn,
                        padx=0
                )

                self.acsAttenuator = RO.Wdg.FloatEntry(ACS_PicoFYb_Frame,
                        defValue = None, minValue = 0., maxValue = 60., width = 5,
                        helpText ='Enter attenuator value (0-60dB)',
                        autoIsCurrent=False,
                        isCurrent=True,
                        defFormat = "%.1f",  # used when converting number to a string (not the format in the text box)
                        doneFunc=self.acsAttenuatorFxn,
                )
                self.acsAttenuator.setIsCurrent(False)

                
                # Gridding for the PicoFYb frame
                gr_PicoFYb.gridWdg('PicoFYb DC power', (self.acsPicoFYbDCPowerButton,self.acsLaserPowerLEDCanvas),col=0,sticky='w')
                gr_PicoFYb.gridWdg('PicoFYb Lock', self.acsPicoFYbLock, col=0, sticky='w')
                gr_PicoFYb.gridWdg('Attenuator [dB]', self.acsAttenuator, col=0,sticky='nw',colSpan=4)
                ACS_PicoFYb_Frame.pack(side='right', anchor='ne')


                # Make a specific Tab active/visible
                # Default Tab on launch of ATUI
                self.selectpage(self.index(' Main '))  # or 'ACS'
                #self.selectpage(self.index('Laser Tuning'))  # or 'ACS'
                #self.selectpage(self.index('ACS'))  # or 'ACS'


                # ACS Busy/Idle indicator
                ledDiam = 15   # pixels???
                padding = 5
                canvasSize = ledDiam + padding
                xmin = canvasSize*0.5-ledDiam*0.5
                xmax = (canvasSize*0.5+ledDiam*0.5) - 1
                ymin = xmin
                ymax = xmax
                ledBorder = 0
                self.acsLsbStateLEDCanvas = Tk.Canvas(ACS_LSB_Frame, width=canvasSize, height=canvasSize, bd=0)
                self.acsLsbStateLED = self.acsLsbStateLEDCanvas.create_oval(xmin, ymin, xmax, ymax, fill=self.acsLsbStateLEDColors[self.ACS_LSB_STATE_IDLE], outline='black', width=1)
                #self.acsLsbStateLEDCanvas.pack()
                self.acsLsbStateLEDCanvas.grid()
                
                # LUN enable
                self.acsLunEnable = RO.Wdg.Checkbutton(
                        master=ACS_LSB_Frame,
                        text=None,
                        selectcolor = 'white',
                        defValue = False,
                        helpText = '',
                        command = self.acsCheckLunEnable,
                        padx=0
                )
                self.acsLunEnable.setEnable(False)

                # FID enable
                self.acsFidEnable = RO.Wdg.Checkbutton(
                        master=ACS_LSB_Frame,
                        text=None,
                        selectcolor = 'white',
                        defValue = False,
                        helpText = '',
                        command = self.acsCheckFidEnable,
                        padx=0
                )
                self.acsFidEnable.setEnable(False)

                # Button to set the delay entries to their nominal values
                acsDelayVals = "%d %d %d %d" % tuple(self.acsNominalDelayValues)
                self.acsSetNominalDelays = RO.Wdg.Button(
                        master=ACS_LSB_Frame,
                        text="Set delays to nominal values",
                        helpText = 'Set fid and lun delays to nominal values: %s' % acsDelayVals, 
                        command  = self.acsSetNominalDelaysFxn,
                        padx=0
                )
                self.acsSetNominalDelays.configure(state = 'disabled')

                delayAutoIsCurrent = False
                self.acsLSBDelay_FID0 = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 255,
                        helpText = 'FID0',
                   autoIsCurrent = delayAutoIsCurrent,
                        isCurrent = False,
                )
                self.acsLSBDelay_FID1 = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 255,
                        helpText ='FID1',
                   autoIsCurrent = delayAutoIsCurrent,
                        isCurrent = False,
                )
                self.acsLSBDelay_LUN0 = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 255,
                        helpText ='LUN0',
                   autoIsCurrent = delayAutoIsCurrent,
                        isCurrent=False,
                )
                self.acsLSBDelay_LUN1 = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 255,
                        helpText ='LUN1',
                   autoIsCurrent = delayAutoIsCurrent,
                        isCurrent=False,
                )
                #self.apolloModel.acsDelayVal.addROWdg(self.acsLSBDelay_FID0, setDefault=True)
                #self.apolloModel.acsDelayVal.addROWdg(self.acsLSBDelay_FID1, setDefault=True)
                #self.apolloModel.acsDelayVal.addROWdg(self.acsLSBDelay_LUN0, setDefault=True)
                #self.apolloModel.acsDelayVal.addROWdg(self.acsLSBDelay_LUN1, setDefault=True)
                self.acsLSBDelays = [self.acsLSBDelay_FID0, self.acsLSBDelay_FID1,
                                     self.acsLSBDelay_LUN0, self.acsLSBDelay_LUN1]
                for wdg in self.acsLSBDelays:
                        #self.apolloModel.acsDelayVal.addROWdg(wdg, setDefault=True)
                        wdg.bind('<Return>',self.FuncCall(self.acsLSB_setDelay,None))
                        wdg.set(0, isCurrent=False)
                
                # Set the DAC
                # In volts
                self.acsModulatorBias = RO.Wdg.FloatEntry(ACS_LSB_Frame,
                        defValue = False,
                        minValue = 0.,
                        maxValue = 10.,
                        helpText ='Enter modulator bias voltage (0-10V)',
                        autoIsCurrent=False,
                        defFormat = "%.3f",
                )
                self.acsModulatorBias.set(0, isCurrent=False)
                self.apolloModel.acsDacVal.addROWdg(self.acsModulatorBias,setDefault=True)   ### I think this is for isCurrent to work
                self.acsModulatorBias.bind('<Return>',self.FuncCall(self.acsModulatorBiasSet, None))
                # In DAC value (0-4095)
                self.acsModulatorBiasDAC = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 4095,
                        helpText ='Enter modulator bias voltage (in DAC steps 0-4095)',
                    autoIsCurrent=True,
                )
                self.acsModulatorBiasDAC.set(0, isCurrent=False)
                self.apolloModel.acsDacVal.addROWdg(self.acsModulatorBiasDAC,setDefault=True)   ### I think this is for isCurrent to work
                self.acsModulatorBiasDAC.bind('<Return>',self.FuncCall(self.acsModulatorBiasSet, None))
                
                self.acsModulatorOpen = RO.Wdg.Button(
                        master=ACS_LSB_Frame,
                        text="Toggle Bias",
                        helpText = 'Jump between min and max modulator transmission',
                        command  = self.acsModulatorOpenFxn,
                        padx=0
                )
                self.acsModulatorOpen.configure(state = 'disabled')

                self.acsModulatorExtremTx = RO.Wdg.Button(
                        master=ACS_LSB_Frame,
                        text="Extremize bias",
                        helpText = 'Do a search for min/max modulator transmission',
                        command  = self.acsModulatorExtremTxFxn,
                        padx=0
                )
                self.acsModulatorExtremTx.configure(state = 'disabled')

                self.acsModulatorExtremTxStep = RO.Wdg.IntEntry(
                        master=ACS_LSB_Frame,
                        defValue = 200,
                        minValue = 1,
                        maxValue = 1000,
                        helpText = 'Step size for the modulator transmission search',
                )
                self.acsModulatorExtremTxStep.bind('<Return>', self.FuncCall(self.acsModulatorExtremTxStepFxn, None))
                self.acsModulatorExtremTxStep.setIsCurrent(True)

                self.acsModulatorSweep = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'DAC Sweep',
                        command = self.acsDACSweep,
                        helpText = 'Sweep through all DAC values',
                        state = 'normal'
                )
                self.acsModulatorSweep.configure(state = 'disabled')
                self.acsModulatorSweepDACMax = RO.Wdg.IntEntry(
                        master=ACS_LSB_Frame,
                        defValue = 4095,
                        minValue = 0,
                        maxValue = 4095,
                        helpText = 'MAX DAC value to sweep to (sweep starts at zero).  Really only used for debugging',
                )
                #self.acsModulatorSweepDACMax.bind('<Return>', self.FuncCall(self.acsModulatorSweepDACMaxFxn, None))

                self.acsClockPhaseSweep = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'Phase Sweep',
                        command = self.acsClockPhaseSweepFxn,
                        helpText = 'Sweep through all clock phase values',
                        state = 'normal')
                self.acsClockPhaseSweep.configure(state = 'disabled')
                self.acmPulsePer = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        minValue = 10,
                        maxValue = 250000000,
                        helpText = 'Pulse period parameter',
                        isCurrent = False,
                        autoIsCurrent = True,
                )
                self.acmPulsePer.bind('<Return>',self.FuncCall(self.setPar,var='pulseper'))
                self.apolloModel.pulseper.addROWdg(self.acmPulsePer,setDefault=True) 
                self.acmPulsePer.set(49, isCurrent=False)
                
                self.acmPulseGW = RO.Wdg.IntEntry(
                        master=ACS_LSB_Frame,
                        minValue = 1,
                        maxValue = 15,
                        helpText = 'Pulse gate width parameter',
                        isCurrent = False,
                        autoIsCurrent = True,
                )
                self.acmPulseGW.bind('<Return>',self.FuncCall(self.setPar,var='pulsegw'))
                self.apolloModel.pulsegw.addROWdg(self.acmPulseGW,setDefault=True) 
                self.acmPulseGW.set(1, isCurrent=False)

                # Allow manual phase adjustment
                #self.acsClockPhaseBump = RO.Wdg.Button(
                #        master = ACS_LSB_Frame,
                #        text = 'Phase Bump',
                #        command = self.acsClockPhaseBumpFxn,
                #        helpText = 'Bump clock phase',
                #        state = 'normal')
                #self.acsClockPhaseBump.configure(state = 'disabled')
                self.acsClockPhaseBumpAmt = RO.Wdg.IntEntry(ACS_LSB_Frame,
                        minValue = -5000,
                        maxValue = 5000,
                        helpText = 'Amount to bump phase (-N to +N)',
                        isCurrent = False,
                        autoIsCurrent = True,  #False?
                )
                self.acsClockPhaseBumpAmt.bind('<Return>',self.FuncCall(self.acsClockPhaseBumpAmtFxn, None))
                self.apolloModel.acsClockPhaseBumpAmt.addROWdg(self.acsClockPhaseBumpAmt,setDefault=True) 
                self.acsClockPhaseBumpAmt.set(-100, isCurrent=False)
                
                self.acsPhotodiodeADCRead = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'ADC Read',
                        command = self.acsADCRead,
                        helpText = 'Read the 4 ADC values',
                        state = 'normal')
                self.acsPhotodiodeADCRead.configure(state = 'disabled')
                self.acsADC0 = RO.Wdg.IntLabel(master=ACS_LSB_Frame, helpText = 'Upstream IR photodiode ADC')
                self.acsADC1 = RO.Wdg.IntLabel(master=ACS_LSB_Frame, helpText = 'Downstream IR photodiode ADC')
                self.acsADC2 = RO.Wdg.IntLabel(master=ACS_LSB_Frame, helpText = 'Modulator photodiode ADC')
                self.acsADC3 = RO.Wdg.IntLabel(master=ACS_LSB_Frame, helpText = 'Green photodiode ADC')
                self.acsADCs = [self.acsADC0, self.acsADC1, self.acsADC2, self.acsADC3]

                for intlabel in self.acsADCs:
                        intlabel.set(-1, isCurrent=False)
                
                self.acsLSBRecover = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'AD5592 Recover',
                        command = self.acsLSBRecoverFxn,
                        helpText = 'Recover from an AD5592 hang',
                        state = 'normal'
                )
                self.acsLSBRecover.configure(state = 'disabled')

                self.acsGetStatus = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'Get ACS Status',
                        command = self.acsGetStatusFxn,
                        helpText = 'Get the status of the ACS system',
                )
                self.acsFakeDACScan = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'Fake DAC scan',
                        command = self.acsFakeDACScanFxn,
                        helpText = 'Randomly generate some DAC scan data',
                )
                self.acsFakePhaseSweep = RO.Wdg.Button(
                        master = ACS_LSB_Frame,
                        text = 'Fake Phase sweep',
                        command = self.acsFakePhaseSweepFxn,
                        helpText = 'Randomly generate some Phase sweep data',
                )
                #self.acsPlotUpdate = RO.Wdg.Button(
                #        master = ACS_LSB_Frame,
                #        text = 'Update dummy plot',
                #        command = self.acsPlotUpdateFxn,
                #        helpText = 'test plot blitting/updating',
                #)

                # Set the layout for ACS stuff
                gr_LSB.gridWdg('LSB status:', self.acsLsbStateLEDCanvas,' (red=error, yellow=busy, green=idle)', col=0,sticky='w')
                gr_LSB.gridWdg('LUN_EN', self.acsLunEnable,col=0,sticky='nw')
                gr_LSB.gridWdg('FID_EN', self.acsFidEnable,col=0,sticky='nw')

                gr_LSB.gridWdg(False, self.acsSetNominalDelays, col=1, colSpan=3, sticky='nw')
                gr_LSB.gridWdg('Delay/Width (fid0, fid1, lun0, lun1)',
                               (self.acsLSBDelay_FID0,self.acsLSBDelay_FID1,
                                self.acsLSBDelay_LUN0,self.acsLSBDelay_LUN1),
                               col=0,sticky='ew')
                gr_LSB.gridWdg('Modulator DC Bias [V]', self.acsModulatorBias, col=0,sticky='nw', colSpan=4)
                gr_LSB.gridWdg('[DAC val]', self.acsModulatorBiasDAC, row=-1, col=3,sticky='nw', colSpan=2)
                gr_LSB.gridWdg(False, self.acsModulatorOpen, col=0,sticky='e')
                gr_LSB.gridWdg(False, self.acsModulatorExtremTx, col=0,sticky='e')
                gr_LSB.gridWdg("Step size", self.acsModulatorExtremTxStep, row=-1, col=2, sticky='w', colSpan=2)
                gr_LSB.gridWdg(False, (self.acsModulatorSweep,self.acsModulatorSweepDACMax),col=0,sticky='e')
                gr_LSB.gridWdg(False, self.acsClockPhaseSweep,col=0,sticky='e')
                gr_LSB.gridWdg('pulseper', self.acmPulsePer,row=-1, col=1,sticky='e')
                gr_LSB.gridWdg('pulsegw', self.acmPulseGW,row=-1, col=3,sticky='e')
                gr_LSB.gridWdg('Phase bump (+ moves data left):', self.acsClockPhaseBumpAmt, col=0, sticky='e')

                gr_LSB.gridWdg(False, (self.acsPhotodiodeADCRead, self.acsADC0, self.acsADC1,
                                            self.acsADC2, self.acsADC3),col=0,sticky='e')
                gr_LSB.gridWdg(False, self.acsLSBRecover, col=0,sticky='e')
                gr_LSB.gridWdg(False, self.acsGetStatus, col=0,sticky='e')
                gr_LSB.gridWdg(False, self.acsFakeDACScan, col=0,sticky='e')
                gr_LSB.gridWdg(False, self.acsFakePhaseSweep, col=0,sticky='e')
                #gr_LSB.gridWdg(False, self.acsPlotUpdate, col=0,sticky='e')

                ## add a plot to ACS tab that will host DAC scans, DAC optimize, (and phase scans?)
                self.acsSweepFig  = mplFigure(figsize=(3,3))
                self.acsSweepAxes = self.acsSweepFig.add_subplot(1,1,1)
                self.acsSweepAxes.plot([1,2,3],[1,4,9], 'b--')
                self.acsSweepCanvas = FigureCanvasTkAgg(self.acsSweepFig, master=ACSFrame)
                self.acsSweepCanvas.show()
                # FIXME:  should use grid() instead of pack()  (not supposed to mix grid and pack, right?)
                #self.acsSweepCanvas.get_tk_widget().grid(column=1) #FAIL
                self.acsSweepCanvas.get_tk_widget().pack(side=Tk.BOTTOM, fill=Tk.BOTH, expand=True)
                #gr_LSB.gridWdg(False, acsSweepCanvas.get_tk_widget(), col=0) ##FAIL


                
# PicoFYb Lock on/off (check box)

#### To do:
# button to jump from "min" to "max" transmission of Modulator (by adjusting bias voltage by Vpi)
# how to view plots of DAC sweep and phase sweep?
# phase bump (enter value in text box, then have a + button and a - button to bump phase)

##### Done (first pass) -- only one-way communication to houston
# From Tom's email 7/27/2016
#1) laser power checkbox; then status "LED" Wh = off; Grn = on; Red = error
#2) attenuator text box (0 to 60 dB)
#3) LUN enable checkbox; FID enable checkbox
#4) LUN delay (0-255) two textboxes for beg and end; FID delay (0-255) two text boxes
#5) DAC set (0-10 V) textbox float
#6) ADC read button with four values reported on line
#7) pulse picker open checkbox
#9) bias sweep button: report min and max ADC vals and assoc voltage
#10) phase delay sweep button: possibly text box for how many steps per sample


                
                ACS_LSB_Frame.pack(side = 'top', padx=10)
                
                self.ACSFilterButton = RO.Wdg.Button(
                        master = ACSRandomFrame,
                        text = 'ACS Lunar Filter Enable',
                        command = self.ACS_switch,
                        helpText = 'Turn on/off the ACS filter',
                        state = 'normal')
                gr_random.gridWdg(None, self.ACSFilterButton, row=0, col=0, sticky = "nw")


                ACSRandomFrame.pack(side= 'top',anchor='nw',padx=20, pady=20)
                
#graph

                
                graphFrame = Tk.LabelFrame(self.p3,text = 'Graphics Buffer Controls',font=labelFont,padx=5,pady=5)
                graphFrame.pack(anchor='nw')

                gr_graph = RO.Wdg.Gridder(graphFrame, sticky="w")

                self.regWidth = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.binForReg,
                        minValue = 1,
                        maxValue = 8200,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Full width in TDC bins for a return photon to be considered "registered"'
                )
                self.regWidth.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.regWidth))
                self.regWidth.bind('<Return>',self.FuncCall(self.chngRegBin,))
                gr_graph.gridWdg("'Registered' Full Width = ", self.regWidth," TDC Channels")

                self.regWidthFid = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.binForRegFid,
                        minValue = 1,
                        maxValue = 8200,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Full width in TDC bins for a fiducial return photon to be considered "registered"'
                )
                self.regWidthFid.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.regWidthFid))
                self.regWidthFid.bind('<Return>',self.FuncCall(self.chngRegBinFid,))
                gr_graph.gridWdg("Fiducial 'Registered' Full Width = ", self.regWidthFid," TDC Channels")

                self.regButton = RO.Wdg.Button(
                        master=graphFrame,
                        state='disabled',
                        text='Now: Reg',
                        command=self.reg,
                        helpText = 'All: all lunar returns displayed on lunar hitgrid. Reg: only display registered returns'
                )
                gr_graph.gridWdg("Lunar Hitgrid shows All or only 'Registered' ", self.regButton,colSpan = 3,sticky = 'ew')

                self.hitGridWindowLength = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.hitGridReserve,
                        minValue = 1,
                        maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for APD hitgrid displays (in # of return photons)'
                )
                self.hitGridWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.hitGridWindowLength))
##                self.hitGridWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.hitGridWindowLength,
##                                                                self.hitGridReserve,self.fid_hitgrid_all,
##                                                                self.fid_hitgrid,self.lun_hitgrid_all,self.lun_hitgrid)))
                self.hitGridWindowLength.bind('<Return>',self.FuncCall(self.chngHitgridBuffer,None))

                clearHgButton = RO.Wdg.Button(master = graphFrame,
                        text="Clear",
                        state='disabled',
##                        command = self.FuncCall(self.clear,varlist=(self.fid_hitgrid,self.lun_hitgrid)),
                        helpText = 'Clear the APD hitgrid displays'
                )
                gr_graph.gridWdg('',None)
                gr_graph.gridWdg("APD Hitgrids Time Window (Nhits)", self.hitGridWindowLength,clearHgButton)
#                
                self.intenWindowLength = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.intenReserve,
                        minValue = 1,
                        maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for intensity display (in # of shots)'
                )
                self.intenWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.intenWindowLength))
##                self.intenWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.intenWindowLength,
##                                                                    self.intenReserve,self.inten_all,self.inten,
##                                                                    self.dphase_all,self.dphase)))
                clearIntenButton = RO.Wdg.Button(
                        master=graphFrame,
                        text="Clear",
                        state='disabled',
##                        command = self.FuncCall(self.clear,varlist=(self.inten,)),
                        helpText = 'Clear the intensity display'
                )
                gr_graph.gridWdg("Intensity Histogram Time Window (# of shots)",self.intenWindowLength,clearIntenButton)
#
                self.histWindowLength = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.histReserve,
                        minValue = 1,
                        maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for return time histograms (in # of return photons)'
                )
                self.histWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.histWindowLength))
##                self.histWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.histWindowLength,self.histReserve,
##                                                                    self.cc_return_t_all,self.cc_return_t,
##                                                                    self.cc_return_raw_t_all,self.cc_return_raw_t,
##                                                                    self.fpd_all,self.fpd,
##                                                                    self.lun_return_t_all,self.lun_return_t,
##                                                                    self.lun_return_raw_t_all,self.lun_return_raw_t)))
                clearHistButton = RO.Wdg.Button(
                        master=graphFrame,
                        text="Clear",
                        state='disabled',
##                        command = self.FuncCall(self.clear,varlist=(self.cc_return_t,self.lun_return_t,
##                                                               self.cc_return_raw_t,self.lun_return_raw_t,
##                                                                self.fpd,)),
#                        helpText = 'Clear the return time histograms'
                )
                gr_graph.gridWdg("Return Time Histograms Time Window (Nhits)", self.histWindowLength,clearHistButton)

                self.rateWindowLength = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.rateReserve,
                        minValue = 1,
                        maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for rate histograms (in # of shots)'
                )
                self.rateWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.rateWindowLength))
##                self.rateWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.rateWindowLength,
##                                                                    self.rateReserve,
##                                                                    self.cc_rate_all,self.cc_rate,
##                                                                    self.fid_reg_all,self.fid_reg,
##                                                                    self.lun_rate_all,self.lun_rate,
##                                                                    self.lun_background_all,self.lun_background)))
                clearRateButton = RO.Wdg.Button(
                        master=graphFrame,
                        text="Clear",
                        state='disabled',
##                        command=self.FuncCall(self.clear,varlist=(self.cc_rate,self.lun_rate,self.lun_background)),
                        helpText = 'Clear the rate histograms'
                )
                gr_graph.gridWdg("Rate Histogram Time Window (# of shots)", self.rateWindowLength,clearRateButton)

                self.timeSeriesWindowLength = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.fidStripReserve,
                        minValue = 1,
                        maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for time series stripcharts (in # of return photons)'
                )
                self.timeSeriesWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.timeSeriesWindowLength))
#                self.timeSeriesWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.timeSeriesWindowLength,
##                                                            self.fidStripReserve,self.fidTimeSeries_all,self.fidTimeSeries,
##                                                            self.lunTimeSeries_all,self.lunTimeSeries,
##                                                            self.lunTimeSeriesReg_all,self.lunTimeSeriesReg,
##                                                            self.changes_all, self.changes,
##                                                            self.fidTimeSeries_raw_all,self.fidTimeSeries_raw,
##                                                            self.lunTimeSeries_raw_all,self.lunTimeSeries_raw
                #)))
            
                clearTimeSeriesButton = RO.Wdg.Button(
                        master=graphFrame,
                        text="Clear",
                        state='disabled',
##                        command=self.FuncCall(self.clear,varlist=(self.fidTimeSeries,self.lunTimeSeriesReg,self.lunTimeSeries,
##                                                             self.fidTimeSeries_raw,self.lunTimeSeries_raw,self.changes)),
                        helpText = 'Clear the time series stripcharts'
                )
                gr_graph.gridWdg("Stripchart Time Window (# of shots)", self.timeSeriesWindowLength,clearTimeSeriesButton)

                self.trackWindowLength = RO.Wdg.IntEntry(graphFrame,
                        defValue = self.trackReserve,
                        minValue = 1,
                        maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for tracking displays (in # of offsets)'
                )
                self.trackWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.trackWindowLength))
##               self.trackWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.trackWindowLength,
##                                                                self.trackReserve,self.rxxRate_all,self.rxxRate,
##                                                                self.track_ret_all,self.track_ret)))
                
                clearTrackButton = RO.Wdg.Button(
                        master=graphFrame,
                        text="Clear",
                        state='disabled',
##                        command=self.FuncCall(self.clear,varlist=(self.rxxRate,self.track_ret,self.track_ret_all)),
                        helpText = 'Clear the tracking displays'
                )
                gr_graph.gridWdg("Tracking Time Window (# of offsets)", self.trackWindowLength,clearTrackButton)
                gr_graph.gridWdg("",None)

                clearAllButton = RO.Wdg.Button(
                        master=graphFrame,
                        text='Clear All Plots',
                        command=self.FuncCall(self.ROOT_refresh),
                        helpText = 'Clear all plots)'
                )
                
                gr_graph.gridWdg(False,clearAllButton, sticky ='e')

## statistics label indicator widgets

                topFrame=Tk.Frame(self.p1)
                topFrame.pack(side='top',anchor='nw')

                self.statFrame = Tk.LabelFrame(topFrame,text = 'Run Statistics',font = labelFont)

                gr_stat = RO.Wdg.Gridder(self.statFrame, sticky="nw")

                self.totTime = RO.Wdg.IntLabel(master=self.statFrame, helpText = 'Shots per second')
                gr_stat.gridWdg("Shots per second", self.totTime)
                self.totTime.set(0)

                self.totalShots = RO.Wdg.IntLabel(master=self.statFrame, helpText = 'Total # of fiducial records since last reset')
                gr_stat.gridWdg("Fiducial Records", self.totalShots)
                self.totalShots.set(0)

                self.totalLunShots = RO.Wdg.IntLabel(master=self.statFrame,helpText = 'Total # of lunar return shots since last reset')
                gr_stat.gridWdg("Lunar Return Records", self.totalLunShots,"Per Shot")
                gr_stat.gridWdg("Current",row=-1,col=3)
                self.totalLunShots.set(0)
                
                self.totalFid = RO.Wdg.IntLabel(master=self.statFrame, helpText = 'Total # of fiducial returns')
                self.rateFid = RO.Wdg.FloatLabel(master=self.statFrame,helpText = 'Fiducial Rate')
                gr_stat.gridWdg("Total Fiducial Return Photons", self.totalFid,self.rateFid)
                self.totalFid.set(0)
                self.rateFid.set(0)

                self.fidRegWdg = RO.Wdg.IntLabel(master=self.statFrame, helpText = 'Total registered fiducial returns')
                self.fidRegRateWdg = RO.Wdg.FloatLabel(master=self.statFrame,
                                                       helpText = 'Registered Fiducial Rate')
                self.fidRegRateRecWdg = RO.Wdg.FloatLabel(master=self.statFrame,
                                                          helpText =
                                                          'Registered rate for'+
                                                          ' last %d shots - set in ' % self.rateReserve +
                                                          '\'Rate Histogram Time Window\' box')
                gr_stat.gridWdg("Registered Fiducial Photons", self.fidRegWdg,self.fidRegRateWdg)
                gr_stat.gridWdg(self.fidRegRateRecWdg,row=-1,col=3)
                self.fidRegWdg.set(0)
                self.fidRegRateWdg.set(0)
                self.fidRegRateRecWdg.set(0)

                self.totalLun = RO.Wdg.IntLabel(master=self.statFrame, helpText = 'Total # of lunar returns')
                self.rateLun = RO.Wdg.FloatLabel(master=self.statFrame, helpText = 'Lunar rate')
                gr_stat.gridWdg("Total Lunar Return Photons", self.totalLun,self.rateLun)
                self.totalLun.set(0)
                self.rateLun.set(0)

                self.regLun = RO.Wdg.IntLabel(master=self.statFrame, helpText = 'Registered lunar rate')
                self.regRateLun = RO.Wdg.FloatLabel(master=self.statFrame,
                                                    helpText = '"Registered" lunar rate')
                self.regRateRecLun = RO.Wdg.FloatLabel(master=self.statFrame,
                                                       helpText =
                                                          'Registered rate for'+
                                                          ' last %d shots - set in ' % self.rateReserve +
                                                          '\'Rate Histogram Time Window\' box')
                gr_stat.gridWdg("Registered Lunar Photons", self.regLun,self.regRateLun)
                gr_stat.gridWdg(self.regRateRecLun,row=-1,col=3)
                self.regLun.set(0)
                self.regRateLun.set(0)
                self.regRateRecLun.set(0)

                self.lunBackgroundWdg = RO.Wdg.IntLabel(master=self.statFrame,helpText =
                                                        'Estimate of Lunar yield')
 #               self.lunBackgroundRateWdg = RO.Wdg.FloatLabel(master=self.statFrame, helpText = 'Lunar background rate')
                gr_stat.gridWdg("Estimate of Lunar yield", self.lunBackgroundWdg)#,self.lunBackgroundRateWdg)
                self.lunBackgroundWdg.set(0)
 #               self.lunBackgroundRateWdg.set(0)
                
                
                
                resetCounterButton = RO.Wdg.Button(
                        master=self.statFrame,
                        text='Reset Everything for New Run',
                        command=self.resetCounters,
                        helpText = 'Reset all counters and plots - do this before each new run. Old data is lost.'
                )
                gr_stat.gridWdg(False,resetCounterButton,row= 9, sticky = 'ew')

                self.convWdg = RO.Wdg.IntLabel(master=self.statFrame,helpText =
                                            '# of total shots in which the Pulse Energy measurement did not converge')
                gr_stat.gridWdg("# of missed PE convergences", self.convWdg,row=10)
                self.convWdg.set(0)
                
                self.missedFRCWdg = RO.Wdg.IntLabel(master=self.statFrame,helpText =
                                                        '# of missed FRC')
                gr_stat.gridWdg("# of missed FRC", self.missedFRCWdg)#,self.lunBackgroundRateWdg)
                self.missedFRCWdg.set(0)

                self.totACSWdg = RO.Wdg.IntLabel(master = self.statFrame, helpText =
                                                 '# of ACS photons')
                self.rateACSWdg = RO.Wdg.FloatLabel(master=self.statFrame,
                                                    helpText = 'ACS strength')
                gr_stat.gridWdg("# of ACS photons", self.totACSWdg, self.rateACSWdg)

                self.totACSWdg.set(0)
                self.rateACSWdg.set(0)
# Control access

                lockFrame = Tk.Frame(topFrame,padx=5)
                lockFrame.pack(side='right',anchor='ne')

                gr_lock = RO.Wdg.Gridder(lockFrame)

                self.lockButton = RO.Wdg.Button(
                        master=lockFrame,
                        text="Take Control",
                        command=self.FuncCall(self.lock),
                        helpText = 'Get permission to execute all houston commands'
                )
                gr_lock.gridWdg(False, self.lockButton,sticky= 'ew')

##offset buttons and displays
                
                guideFrame = Tk.LabelFrame(topFrame,text = 'Offsets',font=labelFont,padx=5)
                guideFrame.pack(side='right',anchor='ne')
                self.statFrame.pack(side= 'right',anchor='ne',padx=20)

                
                gr_guide = RO.Wdg.Gridder(guideFrame)

                self.homeButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="Home",
                        command=self.FuncCall(self.offsetGuide,var='home'),
                        state = 'disabled',
                        helpText = 'Sete Guide offset to 0.,0.',pady=6
                )
                gr_guide.gridWdg(None, self.homeButton,row=1,col=1)

                self.upButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="^",
                        command=self.FuncCall(self.offsetGuide,var='up'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window'
                )
                gr_guide.gridWdg(None, self.upButton,row=0,col=1,sticky='ew')

                self.downButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="v",
                        command=self.FuncCall(self.offsetGuide,var='down'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window'
                )
                gr_guide.gridWdg(None, self.downButton,row=2,col=1,sticky='ew')

                self.leftButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="<",
                        command=self.FuncCall(self.offsetGuide,var='left'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window',padx=5
                )
                gr_guide.gridWdg(None, self.leftButton,row=1,col=0,sticky='ns')

                self.rightButton = RO.Wdg.Button(
                        master=guideFrame,
                        text=">",
                        command=self.FuncCall(self.offsetGuide,var='right'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window',padx=5
                )
                gr_guide.gridWdg(None, self.rightButton,row=1,col=2,sticky='ns')

                self.upLeftButt = RO.Wdg.Button(
                        master=guideFrame,
                        text="\\",
                        command=self.FuncCall(self.offsetGuide,var='upLeft'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window'
                )
                gr_guide.gridWdg(None, self.upLeftButt,row=0,col=0,sticky='ew')

                self.upRightButt = RO.Wdg.Button(
                        master=guideFrame,
                        text="/",
                        command=self.FuncCall(self.offsetGuide,var='upRight'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window'
                )
                gr_guide.gridWdg(None, self.upRightButt,row=0,col=2,sticky='ew')

                self.downLeftButt = RO.Wdg.Button(
                        master=guideFrame,
                        text="/",
                        command=self.FuncCall(self.offsetGuide,var='downLeft'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window'
                )
                gr_guide.gridWdg(None, self.downLeftButt,row=2,col=0,sticky='ew')

                self.downRightButt = RO.Wdg.Button(
                        master=guideFrame,
                        text="\\",
                        command=self.FuncCall(self.offsetGuide,var='downRight'),
                        state = 'disabled',
                        helpText = 'Offset Guiding by amount in guide increment window'
                )
                gr_guide.gridWdg(None, self.downRightButt,row=2,col=2,sticky='ew')

            ## checkbuttons

                self.scopeOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="Raster Scope",
                        selectcolor = 'white',
                        defValue = True,
                        helpText =
                        'Raster telescope pointing',
                        padx=5
                )
                self.scopeOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkRaster,None))
                gr_guide.gridWdg(None, self.scopeOn,row=0,col=3,sticky='ns')                

                self.opticsOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="Raster Optics",
                        selectcolor = 'white',
                        defValue = False,
                        #state='disabled',
                        helpText =
                        'Move optics (rxx and rxy) instead of telescope pointing,\"Home\" does nothing. NOT cumulative.',
                        padx=5
                )
                self.opticsOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkRaster,None))
                gr_guide.gridWdg(None, self.opticsOn,row=1,col=3,sticky='ns')

                self.beamOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="Raster Beam",
                        selectcolor = 'white',
                        defValue = False,
                        #state='disabled',
                        helpText =
                        'Raster Beam on lunar surface, corrects guide offset appropriately',
                        padx=5
                )
                self.beamOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkRaster,None))
                gr_guide.gridWdg(None, self.beamOn,row=2,col=3,sticky='ns')

                self.boreOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="Boresight Offset",
                        selectcolor = 'white',
                        defValue = False,
                        helpText =
                        'Raster or offset boresight',
                        padx=5
                )
                self.boreOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkRaster,None))
                gr_guide.gridWdg(False, self.boreOn,row=0,col=0,sticky='ns')

                self.offMagWdg = RO.Wdg.FloatEntry(guideFrame,
                        defValue = False,
                        minValue = 0.,
                        maxValue = 10.,
                        helpText ='Enter magnitude of guide offset increment in arcsec',
                        var=self.offString,
                        autoIsCurrent=False,
                        isCurrent=True,
                        defFormat = "%.4f",
                )
                self.offMagWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.offMagWdg))
                self.offMagWdg.bind('<Return>',self.FuncCall(self.setOff,None))
                gr_guide.gridWdg('Offset Increment [arcsec]',self.offMagWdg,row=4,colSpan=3,sticky = 'ew')

                self.offXWdg = RO.Wdg.FloatEntry(guideFrame,
                        defValue = False,
                        helpText ='Current Az guide offset [arcsec]',
                        readOnly = True,
                        defFormat = "%.4f",
                )
                gr_guide.gridWdg('Guide Az offset [arcsec]',self.offXWdg,row=5,colSpan=3,sticky='ew')

                self.offYWdg = RO.Wdg.FloatEntry(guideFrame,
                        defValue = False,
                        helpText ='Current El guide offset [arcsec]',
                        readOnly = True,
                        defFormat = "%.4f",
                )
                gr_guide.gridWdg('Guide El offset [arcsec]',self.offYWdg,row=6,colSpan=3,sticky='ew')

                self.boreXWdg = RO.Wdg.FloatEntry(guideFrame,
                        defValue = False,
                        helpText ='Current Az boresight offset [arcsec]',
                        readOnly = True,
                        defFormat = "%.4f",
                )
                gr_guide.gridWdg(False,self.boreXWdg,row=1,col=0,sticky='w')

                self.boreYWdg = RO.Wdg.FloatEntry(guideFrame,
                        defValue = False,
                        helpText ='Current El boresight offset [arcsec]',
                        readOnly = True,
                        defFormat = "%.4f",
                )
                gr_guide.gridWdg(False,self.boreYWdg,row=2,col=0,sticky='w')

            # choose coordinate frame
            
                self.nativeOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="Native",
                        selectcolor = 'white',
                        defValue = True,
                        helpText =
                        'Use native telescope coordinates for raster',
                        padx=5
                )
                self.nativeOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkCoords,None))
                gr_guide.gridWdg(None, self.nativeOn,row=0,col=4,sticky='ns')

                self.apdOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="APD",
                        selectcolor = 'white',
                        defValue = False,
                        helpText =
                        'Use APD coordinates for raster',
                        padx=5
                )
                self.apdOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkCoords,None))
                gr_guide.gridWdg(None, self.apdOn,row=1,col=4,sticky='ns')

                self.ccdOn = RO.Wdg.Checkbutton(
                        master=guideFrame,
                        text="CCD",
                        selectcolor = 'white',
                        defValue = False,
                        helpText =
                        'Use CCD coordinates for raster',
                        padx=5
                )
                self.ccdOn.bind('<ButtonRelease-1>',self.FuncCall(self.checkCoords,None))
                gr_guide.gridWdg(None, self.ccdOn,row=2,col=4,sticky='ns')

            # I like this boresight
                self.boreCommitButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="Boresight Good",
                        state = 'disabled',
                        command=self.FuncCall(self.boreConf),#,'rem boresight_confirm="%f %f"' % (self.boreAz, self.boreEl)),
                        helpText = 'Make note that boresight offset is good via boresight_confirm parameter'
                )
                gr_guide.gridWdg(False, self.boreCommitButton,row=3,col=0,sticky= 'ew')

            #Zero optics offsets
                self.commitRxxButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="Commit Rxx, Rxy",
                        state = 'disabled',
                        command=self.FuncCall(self.doCmd,'apollo','houston vcalibrate'),
                        helpText = 'Assign current rxx and rxy to target values'
                )
                gr_guide.gridWdg(False, self.commitRxxButton, row=6,col=4,sticky= 'ew')

            #Move mirror to target offset
                self.toTargetButton = RO.Wdg.Button(
                        master=guideFrame,
                        text="Go To Target",
                        state = 'disabled',
                        command=self.FuncCall(self.vMove,None),
                        helpText = 'Move rxx and rxy to target position'
                )
                gr_guide.gridWdg(False, self.toTargetButton, row=5,col=4,sticky= 'ew')

## Power status Page
                self.powerFrame = Tk.LabelFrame(self.p8,text = 'Power Status',font=labelFont,pady=5)
                self.powerFrame.pack(side='top',anchor='nw')

                self.gr_power = RO.Wdg.Gridder(self.powerFrame)

                self.powerButton = RO.Wdg.Button(
                        master=self.powerFrame,
                        text="Get Power Status",
                        command=self.FuncCall(self.doCmd,'apollo','houston power'),
                        helpText = 'get the current power status',
                )
                self.gr_power.gridWdg(False, self.powerButton)

# Pop Channels (dark) page

                self.darkFrame = Tk.LabelFrame(self.p7,text = 'Uncheck Channel to Remove',font=labelFont,pady=5)
                self.darkFrame.pack(side='top',anchor='nw')

                self.gr_dark = RO.Wdg.Gridder(self.darkFrame)

                self.darkWdgDict = {}

                for i in range(16):
                    j=i+1

                    self.darkWdgDict[i] = RO.Wdg.Checkbutton(
                        master=self.darkFrame,
                        defValue = True,
                        selectcolor='white',
                        helpText = 'Uncheck channel to remove, check to include'
                    )
                    self.darkWdgDict[i].bind('<ButtonRelease-1>',self.FuncCall(self.pop,var=i))
                    self.gr_dark.gridWdg(False,self.darkWdgDict[i],
                                         row=int(np.floor(np.true_divide(i,4))),col=np.remainder(i,4),sticky='ew')

                #corresponding TDC channel numbers 
                self.numFrame = Tk.LabelFrame(self.p7,text = 'TDC Channel #',font=labelFont,pady=5)
                self.numFrame.pack(side='top',anchor='nw',padx=23)

                self.gr_num = RO.Wdg.Gridder(self.numFrame)

                for i in range(16):
                    ind=self.chanMap.index(i)+1
                    txt='%d     ' % ind
                    self.gr_num.gridWdg(txt,False,
                                        row=int(np.floor(np.true_divide(i,4))),col=np.remainder(i,4),sticky='ew')

## Laser Tuning 

                tuneFrame = Tk.LabelFrame(p9TopFrame,text = 'Laser Power Measurement',font=labelFont,pady=5)
                tuneFrame.pack(side='left',anchor='nw',padx=5)
                # FIXME:
                #laserCmdFrame = Tk.LabelFrame(p9TopFrame,pady=5)
                #laserCmdFrame.pack(side='bottom',anchor='nw',padx=5)

                tunetop = Tk.Frame(tuneFrame)
                tunetop.pack(side='top',anchor='nw')

#            ###
                tunesub1 = Tk.Frame(tunetop)
                tunesub1.pack(side='left',anchor='nw')

                self.pwrupButton = RO.Wdg.Button(
                        master=tunesub1,
                        text="Laser \n Powerup",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser powerup'),
                        helpText = 'laser powerup',
                        state = 'disabled'
                )
                self.pwrupButton.pack(side='top',pady=2,padx = 5)

                self.warmupButton = RO.Wdg.Button(
                        master=tunesub1,
                        text="Laser \n Warmup ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser warmup'),
                        helpText = 'laser warmup',
                        state = 'disabled'
                )
                self.warmupButton.pack(side='top',pady=2,padx = 5)

                self.preprunButton = RO.Wdg.Button(
                        master=tunesub1,
                        text="Laser \n Preprun ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser preprun'),
                        helpText = 'laser preprun',
                        state = 'disabled'
                )
                self.preprunButton.pack(side='top',pady=2,padx = 5)

                self.measureButton = RO.Wdg.Button(
                        master=tunesub1,
                        text="Measure \n Power ",
                        command=self.FuncCall(self.measPower),
                        helpText = 'measure laser power',
                        state = 'disabled'
                )
                self.measureButton.pack(side='top',pady=2,padx = 5)


                tunesub1sub = Tk.Frame(tunesub1)
                tunesub1sub.pack()
                gr_tunesub1sub = RO.Wdg.Gridder(tunesub1sub)
                
                self.lpowerTimeWdg = RO.Wdg.IntEntry(tunesub1sub,
                        defValue = False,
                        minValue = 0,
                        maxValue = 180,
                        helpText ='laser power Measurement length (minutes)',
                        autoIsCurrent = False,
                        isCurrent=True,
                        #state = 'disabled'
                )

                self.cancelMeasButton = RO.Wdg.Button(
                        master=tunesub1,
                        text="   Stop   ",
                        command=self.FuncCall(self.doCmd,'apollo','houston standby'),
                        helpText = 'cancel laser power measurement',
                        state = 'disabled'
                )
                self.cancelMeasButton.pack(side='top',pady=3,padx = 5)

            ###
                
                self.lpowerTimeWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.lpowerTimeWdg))
                self.lpowerTimeWdg.bind('<Return>',self.FuncCall(self.setLength))
                gr_tunesub1sub.gridWdg(False, self.lpowerTimeWdg,'min')

            ###

                tunesub2 = Tk.Frame(tunetop,padx=30)
                tunesub2.pack(side='right',anchor='ne')

                gr_tune = RO.Wdg.Gridder(tunesub2)

                self.laser_powerWdg = RO.Wdg.FloatLabel(master=tunesub2,helpText = 'Current Bolometer reading',
                                                        font="Courier 18 bold")
                self.laser_powerWdg.configure(background='pink')
                gr_tune.gridWdg("Last Laser Power" , self.laser_powerWdg)
                self.laser_powerWdg.set(0.00)

                self.laser_powerAveWdg = RO.Wdg.FloatLabel(master=tunesub2,helpText = 'Average of last 20 bolometer measurements')
                gr_tune.gridWdg("20 point average ", self.laser_powerAveWdg)
                self.laser_powerAveWdg.set(0.00)

                self.loWdg = RO.Wdg.FloatLabel(master=tunesub2,helpText = 'Min power (last 20 measurements)')
                gr_tune.gridWdg("20 point min ", self.loWdg)
                self.loWdg.set(0.00)

                self.hiWdg = RO.Wdg.FloatLabel(master=tunesub2,helpText = 'Max power (last 20 measurements)')
                gr_tune.gridWdg("20 point max ", self.hiWdg)
                self.hiWdg.set(0.00)

                gr_tune.gridWdg(" ", None)

            ###
                tunesub2sub = Tk.Frame(tunesub2)
                gr_tune.gridWdg(False, tunesub2sub,colSpan=2)

                fakeLaserPowerButt = RO.Wdg.Button(
                        master=tunesub2sub,
                        text="Fake Laser Power",
                        command=self.fake_laser_power,
                        helpText = 'Randomly generate some laser power data.')
                fakeLaserPowerButt.pack(side = 'top')
                
                clearPowerButt = RO.Wdg.Button(
                        master=tunesub2sub,
                        text="Clear Stripchart",
                        command=self.FuncCall(self.laserPowerClear),
                        helpText = 'Clear Stripchart'
                )
                clearPowerButt.pack(side='top')

                self.loButton = RO.Wdg.Button(
                        master=tunesub2sub,
                        text="Low\n Power",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser power 0'),
                        helpText = 'Go to low laser power', padx=5,
                        state = 'disabled'
                )
                self.loButton.pack(side='left',padx=5,pady=5)

                self.hiButton = RO.Wdg.Button(
                        master=tunesub2sub,
                        text="High \n Power",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser power 1'),
                        helpText = 'Go to high laser power', padx=5,
                        state = 'disabled'
                )
                self.hiButton.pack(side='left',padx=5,pady=5)

                tunesub2subx = Tk.Frame(tunesub2)
                gr_tune.gridWdg(False, tunesub2subx,colSpan=2)

                self.pgm1Button = RO.Wdg.Button(
                        master=tunesub2subx,
                        text="Activate \n pgm 1",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser activate 1'),
                        helpText = 'Activate laser program 1',
                        state = 'disabled'
                )
                self.pgm1Button.pack(side='left',padx=5,pady=5)

                self.pgm2Button = RO.Wdg.Button(
                        master=tunesub2subx,
                        text="Activate \n pgm 2",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser activate 2'),
                        helpText = 'Activate laser program 2',
                        state = 'disabled'
                )
                self.pgm2Button.pack(side='bottom',padx=5,pady=5)

            ###
                tunesub2a = Tk.Frame(tuneFrame,height=20)
                tunesub2a.pack(side='top',anchor='n')
            ###
                tunesub2sub2 = Tk.Frame(tuneFrame)
                tunesub2sub2.pack(side='top',anchor='w')

                Twdg = Tk.Text(tunesub2sub2,height=1,width=20,relief='flat',pady=5)
                Twdg.insert('end',"Amplifier Delay ")
                Twdg.pack(side='left',anchor='e')

                self.ampdelWdg = RO.Wdg.IntLabel(master=tunesub2sub2,helpText = 'Amplifier Delay',relief='groove')
                self.ampdelWdg.pack(side='left',anchor='w',padx=5,pady=5)
                self.ampdelWdg.set(0)

                self.ampDelUpButton = RO.Wdg.Button(
                        master=tunesub2sub2,
                        text="    ^    ",
                        command=self.FuncCall(self.ampDelUp),
                        helpText = 'increase amplifier delay',
                        state = 'disabled'
                )
                self.ampDelUpButton.pack(side='left',padx=1,pady=8)

                self.ampDelDnButton = RO.Wdg.Button(
                        master=tunesub2sub2,
                        text="    v    ",
                        command=self.FuncCall(self.ampDelDown),
                        helpText = 'decrease amplifier delay',
                        state = 'disabled'
                )
                self.ampDelDnButton.pack(side='left',padx=1,pady=8)

                self.ampDelIncWdg = RO.Wdg.IntEntry(tunesub2sub2,
                        defValue = self.ampDelInc,
                        minValue = 0,
                        maxValue = 10000,
                        helpText ='number of increments for amplifier delay digipot change',
                        autoIsCurrent = False,
                        isCurrent=True,
                )
                self.ampDelIncWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.ampDelIncWdg))
                self.ampDelIncWdg.bind('<Return>',self.FuncCall(self.setAmpdelay))
                self.ampDelIncWdg.pack(side='left',padx=1,pady=8)
                

            ###
                tunesub3 = Tk.Frame(tuneFrame)
                tunesub3.pack(side='top',anchor='n')

                Twdg2 = Tk.Text(tunesub3,height=1,width=20,relief='flat',pady=5)
                Twdg2.insert('end',"Oscillator Voltage ")
                Twdg2.pack(side='left',anchor='w')

                self.oscVoltWdg = RO.Wdg.IntLabel(master=tunesub3,helpText = 'Oscillator Voltage',relief='groove')
                self.oscVoltWdg.pack(side='left',anchor='w',padx=5,pady=5)
                self.oscVoltWdg.set(0000)

                self.oscUpButton = RO.Wdg.Button(
                        master=tunesub3,
                        text="    ^    ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser oscvolt up'),
                        helpText = 'Increase Oscillator Voltage',
                        state = 'disabled'
                )
                self.oscUpButton.pack(side='left',padx=1,pady=8)

                self.oscDnButton = RO.Wdg.Button(
                        master=tunesub3,
                        text="    v    ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser oscvolt down'),
                        helpText = 'Decrease Oscillator Voltage',
                        state = 'disabled'
                )
                self.oscDnButton.pack(side='left',padx=1,pady=8)

                self.oscUp30Button = RO.Wdg.Button(
                        master=tunesub3,
                        text="    ^ 30 ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser oscvolt up30'),
                        helpText = 'Increase Oscillator Voltage by 30',
                        state = 'disabled'
                )
                self.oscUp30Button.pack(side='left',padx=1,pady=8)

                self.oscUp40Button = RO.Wdg.Button(
                        master=tunesub3,
                        text="    v 30 ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser oscvolt down 30'),
                        helpText = 'Decrease Oscillator Voltage by 30',
                        state = 'disabled'
                )
                self.oscUp40Button.pack(side='left',padx=1,pady=8)
            ###
                tunesub4 = Tk.Frame(tuneFrame)
                tunesub4.pack(side='top',anchor='w')

                Twdg3 = Tk.Text(tunesub4,height=1,width=20,relief='flat')
                Twdg3.insert('end',"Amplifier Voltage ")
                Twdg3.pack(side='left',anchor='e')

                self.ampVoltWdg = RO.Wdg.FloatLabel(master=tunesub4,helpText = 'Amplifier Voltage',relief='groove')
                self.ampVoltWdg.pack(side='left',anchor='w',padx=5,pady=5)
                self.ampVoltWdg.set(0.0000)

                self.ampUpButton = RO.Wdg.Button(
                        master=tunesub4,
                        text="    ^    ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser ampvolt up'),
                        helpText = 'Increase Amplifier voltage',
                        state = 'disabled'
                )
                self.ampUpButton.pack(side='left',padx=1,pady=8)

                self.ampDnButton = RO.Wdg.Button(
                        master=tunesub4,
                        text="    v    ",
                        command=self.FuncCall(self.doCmd,'apollo','houston laser ampvolt down'),
                        helpText = 'Decrease Amplifier voltage',
                        state = 'disabled'
                )
                self.ampDnButton.pack(side='left',padx=1,pady=8)
                
            # command/reply
                #command/reply frame **should be moved**

                cmdRepFrame = Tk.Frame(self.p1,padx=5)
                cmdRepFrame.pack(side='top',anchor='w')

                gr_cmdRep = RO.Wdg.Gridder(cmdRepFrame)
                
                self.cmdRepLog = LogWdg.LogWdg(cmdRepFrame,
                                            catSet = [("Replies:", self.catList)],
                                            maxLines = 200,
                                               helpText="cmdRepLog",
                                            padx=5,pady=5)
                self.cmdRepLog.text.configure(height=5)
                gr_cmdRep.gridWdg(False,self.cmdRepLog,sticky="ew") # row=15
                    
                self.cmdWdg = RO.Wdg.CmdWdg(cmdRepFrame,cmdFunc=self.FuncCall(self.doLineCmd),width=130)
                gr_cmdRep.gridWdg(False,self.cmdWdg,sticky="ew") # row=15
                
#                space = Tk.Frame(self.p9,height=20)
#                space.pack()
                
#                self.wdg9 = laserKeypad.MyApp(laserFrame,self.cmdRepLog,self.tuiModel)

#                cmdWdgTune = RO.Wdg.CmdWdg(self.p9,width=200,cmdFunc=self.FuncCall(self.doLineCmd))
#                cmdWdgTune.pack(side='top')

                # display this on the ACS tab too????
                #gr_random.gridWdg(None, self.cmdRepLog, sticky='e')  # first arg = None or False???



        # GUI version of the Laser Keypad
                self.wdg9 = laserKeypad.MyApp(laserFrame,self.cmdRepLog,self.tuiModel)

        # Command/Reply log window for Laser Tuning tab
                # FIXME: started on this, but dropped it for now....
                #laserCmdRepFrame = Tk.Frame(self.p9,padx=5)
                #laserCmdRepFrame.pack(side='top',anchor='w')
                #gr_laserCmdRep = RO.Wdg.Gridder(laserCmdRepFrame)
                
                #self.laserCmdRepLog = LogWdg.LogWdg(p9FrameTop,
                #                            catSet = [("Replies:", self.catList)],
                #                            maxLines = 200,
                #                               helpText="cmdRepLog",
                #                            padx=5,pady=5)
                #self.cmdRepLog.text.configure(height=5)
                #gr_cmdRep.gridWdg(False,self.cmdRepLog,sticky="ew") # row=15
                    
        # Command entry textbox
                cmdWdgTune = RO.Wdg.CmdWdg(p9MidFrame,width=200,cmdFunc=self.FuncCall(self.doLineCmd))
                cmdWdgTune.pack(side='top', anchor='nw', pady=7)


        # Laser Power Graph
                ## add a plot to Laser Monitor tab that will display the laser power measurements
                self.laserPowerFig  = mplFigure(figsize=(3,3))
                self.laserPowerAxes = self.laserPowerFig.add_subplot(1,1,1)
                #self.laserPowerAxes.plot([1,2,3],[1,4,9], 'b--')
                # coordinate transformation (x is in data units, y is in axis units)
                self.laserPowerTrans = mplTransforms.blended_transform_factory(self.laserPowerAxes.transData, self.laserPowerAxes.transAxes)  
                self.laserPowerCanvas = FigureCanvasTkAgg(self.laserPowerFig, master=p9BotFrame)
                self.laserPowerCanvas.show()
                # FIXME:  should use grid() instead of pack()  (not supposed to mix grid and pack, right?)
                # see discussion at ACS DAC scan plot creation...
                self.laserPowerCanvas.get_tk_widget().pack(side=Tk.LEFT, fill=Tk.BOTH, expand=False)


        # rxx/rxy offset

                #offFrame = Tk.LabelFrame(p9TopFrame,text = 'Offset rxx/rxy',font=labelFont,pady=5)
                offFrame = Tk.LabelFrame(p9BotFrame,text = 'Offset rxx/rxy',font=labelFont,pady=5)
                offFrame.pack(side='left',anchor='w',padx=5)

                gr_off = RO.Wdg.Gridder(offFrame)

                self.rxxButton = RO.Wdg.Button(
                        master=offFrame,
                        text="rxx/rxy",
                        helpText = 'Use buttons to adjust',pady=10,
                        state = 'disabled'
                )
                gr_off.gridWdg(False, self.rxxButton,row=1,col=2)

                self.rxxUpButton = RO.Wdg.Button(
                        master=offFrame,
                        text="^",
                        command=self.FuncCall(self.offsetRxx,var='up'),
                        helpText = 'Offset Guiding by amount in guide increment window',
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxUpButton,row=0,col=1,sticky='ew')

                self.rxxDownButton = RO.Wdg.Button(
                        master=offFrame,
                        text="v",
                        command=self.FuncCall(self.offsetRxx,var='down'),
                        helpText = 'Offset Guiding by amount in guide increment window',
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxDownButton,row=2,col=1,sticky='ew')

                self.rxxLeftButton = RO.Wdg.Button(
                        master=offFrame,
                        text="<",
                        command=self.FuncCall(self.offsetRxx,var='left'),
                        helpText = 'Offset Guiding by amount in guide increment window',padx=5,
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxLeftButton,row=1,col=0,sticky='ns')

                self.rxxRightButton = RO.Wdg.Button(
                        master=offFrame,
                        text=">",
                        command=self.FuncCall(self.offsetRxx,var='right'),
                        helpText = 'Offset Guiding by amount in guide increment window',padx=5,
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxRightButton,row=1,col=2,sticky='ns')

                self.rxxUpLeftButt = RO.Wdg.Button(
                        master=offFrame,
                        text="\\",
                        command=self.FuncCall(self.offsetRxx,var='upLeft'),
                        helpText = 'Offset Guiding by amount in guide increment window',
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxUpLeftButt,row=0,col=0,sticky='ew')

                self.rxxUpRightButt = RO.Wdg.Button(
                        master=offFrame,
                        text="/",
                        command=self.FuncCall(self.offsetRxx,var='upRight'),
                        helpText = 'Offset Guiding by amount in guide increment window',
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxUpRightButt,row=0,col=2,sticky='ew')

                self.rxxDownLeftButt = RO.Wdg.Button(
                        master=offFrame,
                        text="/",
                        command=self.FuncCall(self.offsetRxx,var='downLeft'),
                        helpText = 'Offset Guiding by amount in guide increment window',
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxDownLeftButt,row=2,col=0,sticky='ew')

                self.rxxDownRightButt = RO.Wdg.Button(
                        master=offFrame,
                        text="\\",
                        command=self.FuncCall(self.offsetRxx,var='downRight'),
                        helpText = 'Offset Guiding by amount in guide increment window',
                        state = 'disabled'
                )
                gr_off.gridWdg(None, self.rxxDownRightButt,row=2,col=2,sticky='ew')

                self.rxxOffMagWdg = RO.Wdg.FloatEntry(offFrame,
                        defValue = False,
                        minValue = 0.,
                        maxValue = 10.,
                        helpText ='Enter magnitude of guide offset increment in arcsec',
                        var=self.rxxOffString,
                        autoIsCurrent=False,
                        isCurrent=True,
                        defFormat = "%.4f",
                )
                self.rxxOffMagWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.rxxOffMagWdg))
                self.rxxOffMagWdg.bind('<Return>',self.FuncCall(self.rxxSetOff,None))
                gr_off.gridWdg('Increment [arcsec]',self.rxxOffMagWdg,row=0,col = 4,sticky = 'ew')

               #Zero optics offsets
                self.rxxCommitRxxButton = RO.Wdg.Button(
                        master=offFrame,
                        text="Commit",
                        state = 'disabled',
                        command=self.FuncCall(self.doCmd,'apollo','houston vcalibrate'),
                        helpText = 'Assign current rxx and rxy to target values'
                )
                gr_guide.gridWdg(False, self.rxxCommitRxxButton, row=0,col=8,sticky= 'ew')

               #Move mirror to target offset
                self.rxxToTargetButton = RO.Wdg.Button(
                        master=offFrame,
                        text="Go To Target",
                        state = 'disabled',
                        command=self.FuncCall(self.vMove,None),
                        helpText = 'Move rxx and rxy to target position'
                )
                gr_guide.gridWdg(False, self.rxxToTargetButton, row=1,col=8,sticky= 'ew')

                # set target to 0,0
                self.rxxZeroTargetButton = RO.Wdg.Button(
                        master=offFrame,
                        text="Zero Target",
                        state = 'disabled',
                        command=self.FuncCall(self.doCmd,'apollo','houston vtarget 0.0 0.0'),
                        helpText = 'Move rxx and rxy to target position'
                )
                gr_guide.gridWdg(False, self.rxxZeroTargetButton, row=2,col=8,sticky= 'ew')

            #copy of target graphic from moonWdg

                canvx = 100
                canvy = 70

                self.midx = canvx/2.0
                self.midy = canvy/2.0

                apd_size = 10
                self.orient_canv = Tk.Canvas(offFrame,width=canvx,height=canvy,bd=1)
                gr_off.gridWdg(False,self.orient_canv,row=3,col = 4,colSpan=4)

                orient_rect = self.orient_canv.create_rectangle(5,5,canvx-5,canvy-5)
                apd_ll = self.orient_canv.create_line(self.midx,self.midy-apd_size,self.midx-apd_size,self.midy)
                apd_ul = self.orient_canv.create_line(self.midx-apd_size,self.midy,self.midx,self.midy+apd_size)
                apd_ur = self.orient_canv.create_line(self.midx,self.midy+apd_size,self.midx+apd_size,self.midy)
                apd_lr = self.orient_canv.create_line(self.midx+apd_size,self.midy,self.midx,self.midy-apd_size)

                self.voff_mark = self.orient_canv.create_oval(self.midx-4,self.midy-4,self.midx+4,self.midy+4)
                
                


                
            #####
#                space = Tk.Frame(self.p9,height=20)
#               space.pack()
#                
#                self.wdg9 = laserKeypad.MyApp(self.p9,self.cmdRepLog,self.tuiModel)
#
#                cmdWdgTune = RO.Wdg.CmdWdg(self.p9,width=200,cmdFunc=self.FuncCall(self.doLineCmd))
#                cmdWdgTune.pack(side='top')

# Raster page
                rasterFrame = Tk.LabelFrame(self.p5,text = 'Auto Raster',font=labelFont,padx=5,pady=5)
                gr_raster = RO.Wdg.Gridder(rasterFrame)
                rasterFrame.pack(side='top',anchor='nw')

                self.rasterOnButton = RO.Wdg.Button(
                        master=rasterFrame,
                        text="Raster Off ",
                        command=self.FuncCall(self.rasterOn),
                        helpText = 'Click to change raster state. Text shows current state',pady=5
                )
                gr_raster.gridWdg(False,self.rasterOnButton,None)
                gr_raster.gridWdg('')

                self.rasterMagWdg = RO.Wdg.FloatEntry(rasterFrame,
                        defValue = False,
                        minValue = 0.,
                        maxValue = 10.,
                        helpText ='Enter magnitude of guide offset increment for raster in arcsec',
                        autoIsCurrent=False,
                        isCurrent=True,
                        defFormat = "%.4f",
                )
                self.rasterMagWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.rasterMagWdg))
                self.rasterMagWdg.bind('<Return>',self.FuncCall(self.rasterSetOff,None))
                gr_raster.gridWdg('Guide Offset Increment [arcsec]',self.rasterMagWdg,sticky = 'ew')

                self.rasterShotWdg = RO.Wdg.IntEntry(rasterFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 10000,
                        helpText ='Enter magnitude of guide offset increment for raster in arcsec',
                        autoIsCurrent=False,
                        isCurrent=True,
                )
                self.rasterShotWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.rasterShotWdg))
                self.rasterShotWdg.bind('<Return>',self.FuncCall(self.rasterSetShots,None))
                gr_raster.gridWdg('Shots per raster point',self.rasterShotWdg,sticky = 'ew')

##command/reply frame
#
#                cmdRepFrame = Tk.Frame(self.p1,padx=5)
#                cmdRepFrame.pack(side='top',anchor='w')
#
#                gr_cmdRep = RO.Wdg.Gridder(cmdRepFrame)

# Houston status and controls
                houstonFrame = Tk.Frame(self.p1,pady=5)
                houstonFrame.pack(side='top',anchor='nw')

                gr_houston = RO.Wdg.Gridder(houstonFrame)

    # state entry widget
                self.stateWdg = RO.Wdg.IntEntry(houstonFrame,
                        readOnly = True,
                        defValue = False,
                        minValue = 0,
                        maxValue = 50, # may change
                        helpText =
                        '0=EXIT, 1=IDLE, 2=WARMUP, 3=RUN, 4=COOLDOWN, 5=STARE, 6=FIDLUN, 7=STANDBY, 8=DARK, 9=FLAT, 10=LASER POWER, 11=CALTDC',
                        autoIsCurrent = True,
                        isCurrent = False
                        
                )
                self.stateWdg.bind('<Return>',self.FuncCall(self.setPar,var='state'))
                self.apolloModel.state.addROWdg(self.stateWdg,setDefault=True)
                gr_houston.gridWdg('Houston State ',self.stateWdg, sticky = 'ew')

    # polynomial name widget
                self.polynameWdg = RO.Wdg.StrEntry(houstonFrame,
                        readOnly = True,
                        defValue = 'None',
                        helpText =
                        'Polynomial name',
                        #autoIsCurrent = True,
                )
#                self.apolloModel.polyname.addROWdg(self.polynameWdg,setDefault=True)
                gr_houston.gridWdg('Polynomial Name ',self.polynameWdg,sticky = 'ew')

                moonButtFrame=Tk.Frame(self.p2)
                moonButtFrame.pack(side='top',anchor='nw')
                
                gr_moon= RO.Wdg.Gridder(moonButtFrame)

            ## copy on moon page
                self.polynameWdgMoon = RO.Wdg.StrEntry(moonButtFrame,
                        readOnly = True,
                        defValue = 'None',
                        helpText ='Polynomial name',
                        #autoIsCurrent = True,
                        width = 16
                )
                self.apolloModel.polyname.addROWdg(self.polynameWdgMoon,setDefault=True)
                gr_moon.gridWdg('',row=1,col=0)
                gr_moon.gridWdg('Polynomial Name ',self.polynameWdgMoon,row=2,col=0)

     # motor speed widget
                self.motrpsWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
                        defValue = False,
                        minValue = 0.,
                        maxValue = 25.,
                        helpText ='T/R motor setpoint [rps] ',
                        autoIsCurrent = True,
                )
                #self.motrpsWdg.bind('<Return>',self.FuncCall(self.setPar,var='motrps'))
                self.apolloModel.motrps.addROWdg(self.motrpsWdg,setDefault=True)
                gr_houston.gridWdg('T/R speed [rps] ',self.motrpsWdg,sticky = 'ew')

    # mirror phase widget

                self.mirrorphaseWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 2000,
                        helpText ='Mirror phase at laser fire',
                        autoIsCurrent = True,
                )
                self.mirrorphaseWdg.bind('<Return>',self.FuncCall(self.setPar,var='mirrorphase'))
                self.apolloModel.mirrorphase.addROWdg(self.mirrorphaseWdg,setDefault=True)
                gr_houston.gridWdg('Mirror phase at laser fire ',self.mirrorphaseWdg,sticky = 'ew')

    # target diffuser phase widget

                self.dphaseWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = -50000,
                        maxValue = 50000,
                        helpText ='Target Diffuser Phase',
                        autoIsCurrent = True,
                )
                self.dphaseWdg.bind('<Return>',self.FuncCall(self.setPar,var='dphase_target'))
                self.apolloModel.dphase_target.addROWdg(self.dphaseWdg,setDefault=True)
                gr_houston.gridWdg('Target Diffuser Phase ',self.dphaseWdg,sticky = 'ew')

    # nruns widget
                self.nrunsWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 100000,
                        helpText ='# of shots for RUN and FIDLUN',
                        autoIsCurrent = True,
                )
                self.nrunsWdg.bind('<Return>',self.FuncCall(self.setPar,var='nruns'))
                self.apolloModel.nruns.addROWdg(self.nrunsWdg,setDefault=True)   ### I think this is for isCurrent to work
                gr_houston.gridWdg('# of shots for RUN, FIDLUN ',self.nrunsWdg,sticky = 'ew')
                self.nrunsWdg.set(5000)

    # gatewidth widget
                self.gatewidthWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 400,
                        helpText ='LUN gate width (RUN, STARE, FIDLUN)',
                        autoIsCurrent = True,
                )
                self.gatewidthWdg.bind('<Return>',self.FuncCall(self.setPar,var='gatewidth'))
                self.apolloModel.gatewidth.addROWdg(self.gatewidthWdg,setDefault=True)
                gr_houston.gridWdg('LUN gate width ',self.gatewidthWdg,sticky = 'ew')

#    # gatewidth widget
                self.tdc_targetWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = -5000,
                        maxValue = 5000,
                        helpText ='desired average lunar TDC value',
                        autoIsCurrent = True,
                )
                self.tdc_targetWdg.bind('<Return>',self.FuncCall(self.setPar,var='tdc_target'))
                self.apolloModel.tdc_target.addROWdg(self.tdc_targetWdg,setDefault=True)
                gr_houston.gridWdg('TDC Target ',self.tdc_targetWdg,sticky = 'ew')
                
#
#    # fiducial gatewidth widget
                self.runfidgwWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 400,
                        helpText ='FID gate width',
                        autoIsCurrent = True,
                )
                self.runfidgwWdg.bind('<Return>',self.FuncCall(self.setPar,var='runfidgw'))
                self.apolloModel.runfidgw.addROWdg(self.runfidgwWdg,setDefault=True)
                gr_houston.gridWdg('FID gate width ',self.runfidgwWdg,sticky = 'ew')

#    # huntstart widget
                self.huntstartWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
                        defValue = False,
                        helpText ='Time-hunt start offset (ns)',
                        autoIsCurrent = True,
                )
                self.huntstartWdg.bind('<Return>',self.FuncCall(self.setPar,var='huntstart'))
                self.apolloModel.huntstart.addROWdg(self.huntstartWdg,setDefault=True)
#                
#    # huntdelta widget
                self.huntdeltaWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
                        defValue = False,
                        helpText ='Time-hunt increment (ns)',
                        autoIsCurrent = True,
                )
                self.huntdeltaWdg.bind('<Return>',self.FuncCall(self.setPar,var='huntdelta'))
                self.apolloModel.huntdelta.addROWdg(self.huntdeltaWdg,setDefault=True)
                
#    # thunt widget
                self.thuntWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
                        defValue = False,
                        helpText ='Time-hunt current offset (ns)',
                        autoIsCurrent = True,
                )
                self.thuntWdg.bind('<Return>',self.FuncCall(self.setPar,var='thunt'))
                self.apolloModel.thunt.addROWdg(self.thuntWdg,setDefault=True)
#                
#    # dskew gate slider
                self.dskewWdg = Tk.Scale(houstonFrame,
                                           orient = 'horizontal',
                                           from_ = -200.,
                                           to = 200.,
                                           length=160,
                                           tickinterval = 100.,
                                           resolution = 1.,
                                           label = 'Gate Offset (ns)',
                                           )
                self.dskewWdg.bind('<ButtonRelease-1>',self.FuncCall(self.setPar,var='dskew'))
                gr_houston.gridWdg(self.dskewWdg,sticky = 'ew',row=10,colSpan=2)
#
#    # predskew gate slider
                self.predskewSlider = Tk.Scale(houstonFrame,
                                           orient = 'horizontal',
                                           from_ = -400,
                                           to = 400,
                                           length=160,
                                           tickinterval = 200,
                                           resolution = 1,
                                           label = 'Pred. Skew (TDC Channels)',
                                           )
                self.predskewSlider.bind('<B1-Motion>',self.FuncCall(self.predSkew1))
                self.predskewSlider.bind('<ButtonRelease-1>',self.FuncCall(self.predSkew2))
                gr_houston.gridWdg(self.predskewSlider,sticky = 'ew',row = 10, col=3,colSpan=2)
                
    # fiducial slider (only affects graph)
                self.fidskewWdg = Tk.Scale(houstonFrame,
                                           orient = 'horizontal',
                                           from_ = -2000,
                                           to = 2000,
                                           length=160,
                                           tickinterval = 1000,
                                           resolution = 1,
                                           label = 'Fiducial Skew (TDC Channels)',
                                           )
                self.fidskewWdg.bind('<B1-Motion>',self.FuncCall(self.fidSkew))
                self.fidskewWdg.bind('<ButtonRelease-1>',self.FuncCall(self.fidSkew2))
                self.fidskewWdg.set(self.regCenterFid)
                gr_houston.gridWdg(self.fidskewWdg,sticky = 'ew',row=10,col=6,colSpan=2)

    # nstares widget
                self.nstaresWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 10000,
                        helpText ='# of stares to take',
                        autoIsCurrent = True,
                )
                self.nstaresWdg.bind('<Return>',self.FuncCall(self.setPar,var='nstares'))
                self.apolloModel.nstares.addROWdg(self.nstaresWdg,setDefault=True)
                gr_houston.gridWdg('  NStares ',self.nstaresWdg,row=0,col=3,sticky = 'ew')

    # starerate widget
                self.starerateWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 100000,
                        helpText ='Stare rate (gates/s)',
                        autoIsCurrent = True,
                )
                self.starerateWdg.bind('<Return>',self.FuncCall(self.setPar,var='starerate'))
                self.apolloModel.starerate.addROWdg(self.starerateWdg,setDefault=True)
                gr_houston.gridWdg('  Stare rate [Hz] ',self.starerateWdg,row=1,col=3,sticky = 'ew')

    # binning widget
                self.binningWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 100000,
                        helpText ='Stare Binning',
                        autoIsCurrent = True,
                )
                self.binningWdg.bind('<Return>',self.FuncCall(self.setPar,var='binning'))
                self.apolloModel.binning.addROWdg(self.binningWdg,setDefault=True)
                gr_houston.gridWdg('  Stare Binning ',self.binningWdg,row=2,col=3,sticky = 'ew')

    # ndarks widget
                self.ndarksWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 100000,
                        helpText ='# of DARKs',
                        autoIsCurrent = True,
                )
                self.ndarksWdg.bind('<Return>',self.FuncCall(self.setPar,var='ndarks'))
                self.apolloModel.ndarks.addROWdg(self.ndarksWdg,setDefault=True)
                gr_houston.gridWdg('  # of DARKs ',self.ndarksWdg,row=3,col=3,sticky = 'ew')

    # flashrate widget
                self.flashrateWdg = RO.Wdg.FloatEntry(houstonFrame,
                        defValue = False,
                        minValue = 0,
                        maxValue = 30,
                        helpText ='Flashrate',
                        autoIsCurrent = True,
                )
                self.flashrateWdg.bind('<Return>',self.FuncCall(self.setPar,var='flashrate'))
                self.apolloModel.flashrate.addROWdg(self.flashrateWdg,setDefault=True)
                gr_houston.gridWdg('  Flashrate ',self.flashrateWdg,row=5,col=3,sticky = 'ew')

    # flashcum widget (shoud be an integer!)
                #self.flashcumWdg = RO.Wdg.FloatEntry(houstonFrame,
                self.flashcumWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = False,
                        helpText ='Cumulative flash count',
                        autoIsCurrent = True,
                )
                self.flashcumWdg.bind('<Return>',self.FuncCall(self.setPar,var='flashcum'))
                self.apolloModel.flashcum.addROWdg(self.flashcumWdg,setDefault=True)
                gr_houston.gridWdg('  Flash count ',self.flashcumWdg,' Target values',row=6,col=3,sticky = 'ew')

    # current rxx widget
                self.rxxcumWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly=True,
                        defValue = False,
                        helpText ='Current Rxx',
                        autoIsCurrent = True,
                )
                self.rxxcumWdg.bind('<Return>',self.FuncCall(self.vMove2))
                self.apolloModel.vposx.addROWdg(self.rxxcumWdg,setDefault=True)
                gr_houston.gridWdg('  Current rxx ',self.rxxcumWdg,row=7,col=3,sticky = 'ew')
            ## copy to laser tuning
                self.rxxCumWdgTune = RO.Wdg.FloatEntry(offFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='Current Rxx',
                        autoIsCurrent = True,
                )
                self.apolloModel.vposx.addROWdg(self.rxxCumWdgTune,setDefault=True)
                gr_off.gridWdg('  Current rxx ',self.rxxCumWdgTune,row=1,col=4,sticky='ew')
                
    # target rxx widget
                self.rxxTargWdg = RO.Wdg.FloatEntry(houstonFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='target rxx',
                        autoIsCurrent = True,
                )
                self.apolloModel.vtargetx.addROWdg(self.rxxTargWdg,setDefault=True)
                gr_houston.gridWdg(None,self.rxxTargWdg,row=7,col=4,sticky = 'ew')
            ## copy to moon page
                self.rxxTargWdgMoon = RO.Wdg.FloatEntry(moonButtFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='target rxx',
                        autoIsCurrent = True,
                )
                self.apolloModel.vtargetx.addROWdg(self.rxxTargWdgMoon,setDefault=True)
                gr_moon.gridWdg('Target Vx ',self.rxxTargWdgMoon,row=3,col=0,sticky='ew')

            ## copy to laser tuning page
                self.rxxTargWdgTune = RO.Wdg.FloatEntry(offFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='target rxx',
                        autoIsCurrent = True,
                )
                self.apolloModel.vtargetx.addROWdg(self.rxxTargWdgTune,setDefault=True)
                gr_off.gridWdg('Target Vx ',self.rxxTargWdgTune,row=1,col=6,sticky='ew')

    # current rxy widget
                self.rxycumWdg = RO.Wdg.FloatEntry(houstonFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='Current rxy',
                        autoIsCurrent = True,
                )
                self.rxycumWdg.bind('<Return>',self.FuncCall(self.vMove2))
                self.apolloModel.vposy.addROWdg(self.rxycumWdg,setDefault=True)
                gr_houston.gridWdg('  Current rxy ',self.rxycumWdg,row=8,col=3,sticky = 'ew')

            ## copy to laser tuning
                self.rxyCumWdgTune = RO.Wdg.FloatEntry(offFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='Current Rxy',
                        autoIsCurrent = True,
                )
                self.apolloModel.vposy.addROWdg(self.rxyCumWdgTune,setDefault=True)
                gr_off.gridWdg('  Current rxy ',self.rxyCumWdgTune,row=2,col=4,sticky='ew')

    # target rxy widget
                self.rxyTargWdg = RO.Wdg.FloatEntry(houstonFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='target rxy',
                        autoIsCurrent = True,
                )
                self.apolloModel.vtargety.addROWdg(self.rxyTargWdg,setDefault=True)
                gr_houston.gridWdg(None,self.rxyTargWdg,row=8,col=4,sticky = 'ew')
            ## copy to moon page
                self.rxyTargWdgMoon = RO.Wdg.FloatEntry(moonButtFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='target rxy',
                        autoIsCurrent = True,
                )
                self.apolloModel.vtargety.addROWdg(self.rxyTargWdgMoon,setDefault=True)
                gr_moon.gridWdg('Target Vy ',self.rxyTargWdgMoon,row=4,col=0,sticky='ew')
            ## copy to laser tuning page
                self.rxyTargWdgTune = RO.Wdg.FloatEntry(offFrame,
                        defValue = False,
                        readOnly=True,
                        helpText ='target rxy',
                        autoIsCurrent = True,
                )
                self.apolloModel.vtargety.addROWdg(self.rxyTargWdgTune,setDefault=True)
                gr_off.gridWdg('Target Vy ',self.rxyTargWdgTune,row=2,col=6,sticky='ew')

    # fakertt widget
                self.fakerttWdg = RO.Wdg.FloatEntry(houstonFrame,
                        defValue = False,
                        helpText ='Forced roudtrip time',
                        autoIsCurrent = True,
                )
                self.fakerttWdg.bind('<Return>',self.FuncCall(self.setPar,var='fakertt'))
                self.apolloModel.fakertt.addROWdg(self.fakerttWdg,setDefault=True)
               
    # predskew entry
                self.predskewWdg = RO.Wdg.IntEntry(
                        master=houstonFrame,
                        defValue=False,
                        helpText = 'Set predskew parameter',
                        autoIsCurrent = True,
                )
                self.apolloModel.predskew.addROWdg(self.predskewWdg,setDefault=True)
                #self.predskewWdg.bind('<Return>',self.FuncCall(self.predZero))
                self.predskewWdg.bind('<Return>',self.FuncCall(self.setPar,var='predskew'))
                gr_houston.gridWdg("predskew = ", self.predskewWdg, row=9, col=0)

     # datafile widget
                self.datafileWdg = RO.Wdg.StrEntry(houstonFrame,
                        defValue = 'None',
                        helpText ='current data file',
                        autoIsCurrent = True,
                        readOnly = True,
                        width=20,
                )
                self.apolloModel.datafile.addROWdg(self.datafileWdg,setDefault=True)
                gr_houston.gridWdg('Current Data File ',self.datafileWdg,row=0,col=6,sticky = 'ew')

    # logfile widget
                self.logfileWdg = RO.Wdg.StrEntry(houstonFrame,
                        defValue = 'None',
                        helpText ='current log file',
                        autoIsCurrent = True,
                        readOnly = True,
                        width=20,
                )
                self.apolloModel.logfile.addROWdg(self.logfileWdg,setDefault=True)
                gr_houston.gridWdg('Current Log File ',self.logfileWdg,row=1,col=6,sticky = 'ew')

    # replay data file widget
                self.replayWdg = RO.Wdg.StrEntry(houstonFrame,
                        defValue = 'acs.run',
                        helpText ='replay data file (whole path may be necessary)',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=20,
                )
                self.replayWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.replayWdg))
                self.replayWdg.bind('<Return>',self.FuncCall(self.setCurrent,var=self.replayWdg))
                gr_houston.gridWdg('Replay data file: ',self.replayWdg,row=3,col=6,sticky = 'ew')

    # replay data start number
                self.replayStartWdg = RO.Wdg.StrEntry(houstonFrame,
                        defValue = 'None',
                        helpText ='Start from this shot in replay. Use None to replay entire run.',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=20,
                )
                self.replayStartWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.replayStartWdg))
                self.replayStartWdg.bind('<Return>',self.FuncCall(self.setCurrent,var=self.replayStartWdg))
                gr_houston.gridWdg('Replay starting shot # ',self.replayStartWdg,row=4,col=6,sticky = 'ew')

    # replay lines
                self.replayLengthWdg = RO.Wdg.IntEntry(houstonFrame,
                        defValue = 5000,
                        helpText ='Number of shots to replay ',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=20,
                )
                self.replayLengthWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.replayLengthWdg))
                self.replayLengthWdg.bind('<Return>',self.FuncCall(self.setCurrent,var=self.replayLengthWdg))
                gr_houston.gridWdg('# of shots to replay: ',self.replayLengthWdg,row=5,col=6,sticky = 'ew')

    # replay button
                replayButton = RO.Wdg.Button(
                        master=houstonFrame,
                        text="Replay Data File",
                        command=self.FuncCall(self.replay,None),padx=5,
                        helpText = 'Replay data file shown above',
                )
                gr_houston.gridWdg(False, replayButton, row=6,col=7,sticky= 'ew')

# Houston button controls

    # get status button
                statusButton = RO.Wdg.Button(
                        master=houstonFrame,
                        text="Get Status",
                        command=self.FuncCall(self.doCmd,'apollo','houston status'),padx=5,
                        helpText = 'Get current houston status report',
                )
                gr_houston.gridWdg(False, statusButton, row=3,col=5,sticky= 'ew')

    # startNubs
                self.nubsButton = RO.Wdg.Button(
                        master=houstonFrame,
                        text="StartNubs",
                        command=self.FuncCall(self.doCmd,'hub','startNubs apollo'),padx=5,
                        helpText = 'hub startNubs apollo',
                        state='disabled'
                )
                gr_houston.gridWdg(False, self.nubsButton, row=0,col=5,sticky= 'ew')

    # Listen
                listenButton = RO.Wdg.Button(
                        master=houstonFrame,
                        text="Listen",
                        command=self.FuncCall(self.doCmd,'hub','listen addActors apollo'),padx=5,
                        helpText = 'hub listen addActors apollo',
                )
                gr_houston.gridWdg(False, listenButton, row=1,col=5,sticky= 'ew')

    # ConnDev
                self.ConnDevButton = RO.Wdg.Button(
                        master=houstonFrame,
                        text="ConnDev",
                        command=self.FuncCall(self.doCmd,'apollo','ConnDev'),padx=5,
                        helpText = 'apollo ConnDev',
                        state='disabled'
                )
                gr_houston.gridWdg(False, self.ConnDevButton, row=2,col=5,sticky= 'ew')

    # disconnect
                self.disconnectButton = RO.Wdg.Button(
                        master=houstonFrame,
                        text="Disconnect",
                        command=self.FuncCall(self.doCmd,'apollo','disconnect'),padx=5,
                        helpText = 'apollo disconnect',
                        state = 'disabled'
                )
                gr_houston.gridWdg(False, self.disconnectButton, row=5,col=5,sticky= 'ew')
                
# Alarms Page

     # Exceptions log

                p4Frame = Tk.Frame(self.p4)
                p4Frame.pack(side='top',anchor='nw')
                self.excFrame = Tk.LabelFrame(p4Frame,text ='Houston Control Exceptions',font=labelFont,pady=5)
                self.excFrame.pack(side='top',anchor='nw')
#                
#                self.catList = (("Error","red"), ("Warning","blue2"), ("Information","black"))
                self.excLog = LogWdg.LogWdg(self.excFrame,
                                            catSet = [("Replies:", self.catList)],
                                            maxLines = 200,
                                            padx=5,pady=5)
                self.excLog.text.configure(height=20)
                self.excLog.pack()

                self.excsubFrame = Tk.LabelFrame(self.excFrame)
                self.excsubFrame.pack(side='top')
                gr_excsub = RO.Wdg.Gridder(self.excsubFrame)

                self.alarms_unackWdg = RO.Wdg.StrEntry(self.excsubFrame,
                        readOnly = False,
                        defValue = None,
                        helpText =
                        'reset individual alarm_unack bits',
                        text = 'alarms_unack',
                        autoIsCurrent = True,
                        isCurrent = False
                        
                )
                self.alarms_unackWdg.bind('<Return>',self.FuncCall(self.setPar,var='alarms_unack'))
                self.apolloModel.alarms_unack.addROWdg(self.alarms_unackWdg,setDefault=True)
                gr_excsub.gridWdg('alarms_unack', self.alarms_unackWdg)


                self.alarmsWdg = RO.Wdg.StrEntry(self.excsubFrame,
                        readOnly = True,
                        defValue = 'None',
                        helpText =
                        'alarm bit status',
                        text = 'alarms_unack',
                        autoIsCurrent = True,
                        isCurrent = False
                        
                )
                self.apolloModel.alarms.addROWdg(self.alarmsWdg,setDefault=True)
                gr_excsub.gridWdg('alarms', self.alarmsWdg)
                
                clearTabButton = RO.Wdg.Button(
                        master=self.excFrame,
                        text="Acknowledge Alarms",
                        command=self.FuncCall(self.clearTab),
                        helpText = 'Acknowledge Alarms (set alarms_unack=0)',
                )
                clearTabButton.pack()

    # Space Command alert
                self.spaceFrame = Tk.LabelFrame(p4Frame,text ='Space Command Status',font=labelFont,pady=5)
                self.spaceFrame.pack(side='top',anchor='nw')

                self.spaceAlertWdg = RO.Wdg.StrLabel(
                        master=self.spaceFrame,
                        text = 'No Blockage',
                        background = 'green',
                        helpText = 'Green if laser enabled, red if space command blockage'
                )
                self.spaceAlertWdg.pack()
                 
## General Tk widgets
              
            # status bar
                gr_graph.gridWdg('')
                self.statusbar = RO.Wdg.StatusBar(master,self.dispatcher,width = 130)#,relief='raised')
                self.statusbar.pack(side='bottom')
#
##            # command/reply
#                self.cmdRepLog = LogWdg.LogWdg(cmdRepFrame,
#                                            catSet = [("Replies:", self.catList)],
#                                            maxLines = 200,
#                                            padx=5,pady=5)
#                self.cmdRepLog.text.configure(height=5)
#                gr_cmdRep.gridWdg(False,self.cmdRepLog,sticky="ew") # row=15
#                    
#                self.cmdWdg = RO.Wdg.CmdWdg(cmdRepFrame,cmdFunc=self.FuncCall(self.doLineCmd),width=130)
#                gr_cmdRep.gridWdg(False,self.cmdWdg,sticky="ew") # row=15
#                
#                space = Tk.Frame(self.p9,height=20)
#                space.pack()
#                
#                self.wdg9 = laserKeypad.MyApp(self.p9,self.cmdRepLog,self.tuiModel)
#
#                cmdWdgTune = RO.Wdg.CmdWdg(self.p9,width=200,cmdFunc=self.FuncCall(self.doLineCmd))
#                cmdWdgTune.pack(side='top')

                self.wdg2.logWdg=self.cmdRepLog
    # state buttons
    # MARK
                gr_butt.gridWdg('')
                gr_butt.gridWdg('')
                # We used to build the button list from the states, ***in numerical order***
                #for i in range(len(self.stateDict)-1): # do not include EXIT (state = 0)
                #    stateButt = RO.Wdg.Button(
                #        master=self.buttFrame,
                #        text=string.lower(self.stateDict[i+1]),
                #        command=self.FuncCall(self.doCmd,'apollo','houston %s' % string.lower(self.stateDict[i+1])),
                #        helpText = 'Set houston state to %s' % self.stateDict[i+1],
                #        state = 'disabled',width=8
                #    )
                #    self.stateButtArray.append(stateButt)
                #    gr_butt.gridWdg(False,stateButt,sticky="ew")
                for stateName in self.stateButtonList:
                    if stateName == None:
                            gr_butt.gridWdg('')
                            continue
                    stateButt = RO.Wdg.Button(
                        master=self.buttFrame,
                        text=string.lower(stateName),
                        command=self.FuncCall(self.doCmd,'apollo','houston %s' % string.lower(stateName)),
                        helpText = 'Set houston state to %s' % stateName,
                        state = 'disabled',width=8
                    )
                    self.stateButtArray.append(stateButt)
                    gr_butt.gridWdg(False,stateButt,sticky="ew")
                #print 'self.stateButtArray = ', self.stateButtArray
# function buttons
                gr_butt.gridWdg('')
                self.funcButtArray=[]
                funclist=['tr sync','tr clear', 'tr dark',None,'readblock']
                for i in funclist:
                    if i == None:
                        gr_butt.gridWdg('')
                    else:
                        funcButt = RO.Wdg.Button(
                            master=self.buttFrame,
                            text=i,
                            command=self.FuncCall(self.doCmd,'apollo','houston %s' % i),
                            helpText = 'perform '+i,
                            state = 'disabled',
                            width=8
                        )
                        self.funcButtArray.append(funcButt)
                        gr_butt.gridWdg(False,funcButt,sticky="ew")
                        
# spotter buttons
    
                gr_butt.gridWdg('')
                for i in ['spotter 1','spotter 2']:
                    spotButt = RO.Wdg.Button(
                        master=self.buttFrame,
                        text=i,
                        command=self.FuncCall(self.spotterBlock,i),
                        helpText = 'record spotter block/enable',
                        state = 'disabled',width=8
                    )
                    self.funcButtArray.append(spotButt)
                    gr_butt.gridWdg(False,spotButt,sticky="ew") 

###### stv control page

                self.wdg6 = stv.StvFrontEnd(stvFrame,self.cmdRepLog,self.tuiModel)

###### laser control page

#                self.wdg9 = laserKeypad.MyApp(self.p9,self.cmdRepLog,self.tuiModel)
#                self.wdg9.pack(side='left')
                

                lbutFrame=Tk.Frame(laserFrame)
                lbutFrame.pack(side='top')
                self.boloInButton = RO.Wdg.Button(
                        master=lbutFrame,
                        text="Put Bolometer IN   ",
                        command=self.FuncCall(self.doCmd,'apollo','houston bolo 1'),
                        helpText = 'Enable bolometer',pady=5,
                        state = 'disabled'
                )
                self.boloInButton.pack(side='left',anchor='sw',padx=5,pady=5)

                self.boloOutButton = RO.Wdg.Button(
                        master=lbutFrame,
                        text="Take Bolometer OUT",
                        command=self.FuncCall(self.doCmd,'apollo','houston bolo 0'),
                        helpText = 'Disable Bolometer',pady=5,
                        state = 'disabled'
                )
                self.boloOutButton.pack(side='left',anchor='ne',padx=5,pady=5)

                #Control buttons and widgets
                self.buttList = [self.homeButton,
                                self.upButton,
                                self.downButton,
                                self.leftButton,
                                self.rightButton,
                                self.upLeftButt,
                                self.upRightButt,
                                self.downLeftButt,
                                self.downRightButt,
                                self.boreCommitButton,
                                self.commitRxxButton,
                                self.rxxCommitRxxButton,
                                self.toTargetButton,
                                self.rxxToTargetButton,
                                self.rxxZeroTargetButton,
                                self.pwrupButton,
                                self.warmupButton,
                                self.preprunButton,
                                self.measureButton,
                                self.cancelMeasButton, 
                                self.loButton,
                                self.hiButton,
                                self.pgm1Button,
                                self.pgm2Button,
                                self.ampDelUpButton,
                                self.ampDelDnButton,
                                self.oscUpButton,
                                self.oscDnButton,
                                self.oscUp30Button,
                                self.oscUp40Button,
                                self.ampUpButton,
                                self.ampDnButton,
                                self.rxxButton,
                                self.rxxUpButton,
                                self.rxxDownButton,
                                self.rxxLeftButton,
                                self.rxxRightButton,
                                self.rxxUpLeftButt,
                                self.rxxUpRightButt,
                                self.rxxDownLeftButt,
                                self.rxxDownRightButt,
                                self.nubsButton,
                                self.disconnectButton,
                                self.boloInButton,
                                self.boloOutButton,
                                self.ConnDevButton,
                                ] + self.stateButtArray+self.funcButtArray

                self.wdgList=[self.rxxOffMagWdg,
                                self.lpowerTimeWdg,
                                self.mirrorphaseWdg, 
                                self.dphaseWdg, 
                                self.nrunsWdg,
                                self.gatewidthWdg,
                                self.tdc_targetWdg,
                                self.runfidgwWdg,
                                self.nstaresWdg,
                                self.starerateWdg,
                                self.binningWdg,
                                self.ndarksWdg,
                                self.flashrateWdg,
                                self.flashcumWdg,
                                self.predskewWdg]
                                
                #self.plt = plt
                #self.createPlot()
                #self.socket_listen()


        def socket_listen(self):
                HOST = 'localhost'
                PORT = 32767
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                bindedFlag = False
                while bindedFlag == False:
                        PORT += 1
                        try:
                                self.server_sock.bind((HOST, PORT))
                        except:
                                pass
                        else:
                                bindedFlag = True
                                print("Binded to PORT", PORT)
                self.server_sock.listen(1)
                self.ROOT_sock, addr = self.server_sock.accept()

                self.connectButton.configure(state = 'disabled', text = 'CONNECTED')
                self.refreshButton.configure(state = 'normal')
                self.ROOTidleButton.configure(state = 'normal')
                self.ROOTdisconnectButton.configure(state = 'normal')
                self.ROOTsaveButton.configure(state = 'disabled')

                skews = pickle.dumps(('predskew', self.regCenter)) +\
                        pickleSep +\
                        pickle.dumps(('fidskew', self.regCenterFid)) +\
                        pickleSep
                self.try_sending_ROOT(skews)

                guideOff = pickle.dumps(('guideoff', (self.offsetAz, self.offsetEl))) + pickleSep
                self.try_sending_ROOT(guideOff)
                
                #fake stares
                #time.sleep(1)
                #staredata = [0, 1, 1, 2, 0, 1, 3, 0, 0, 0, 2, 1, 0, 0, 3, 0]
                #self.newStare(staredata, isCurrent = True)
                #time.sleep(1)
                #staredata = [0, 2, 0, 1, 3, 0, 0, 0, 2, 1, 0, 0, 3, 0, 1, 2]
                #self.newStare(staredata, isCurrent = True)
                #time.sleep(1)
                #staredata = [0, 0, 1, 0, 0, 1, 2, 0, 1, 0, 2, 0, 0, 0, 3, 0]
                #self.newStare(staredata, isCurrent = True)
                #time.sleep(1)
                #staredata = [0, -1, -1, -2, 0, -1, -3, 0, 0, 0, -2, -1, 0, 0, -3, 0]
                #self.newStare(staredata, isCurrent = True)
                #time.sleep(1)
                #staredata = [0, 1, 2, 0, 2, 0, 0, 1, 0, 0, 4, 0, 3, 0, 1, 0]
                #self.newStare(staredata, isCurrent = True)
                

        def socket_destroy(self):
                data = pickle.dumps(('disconnect', 0)) + pickleSep
                self.try_sending_ROOT(data)
                time.sleep(1)
                #self.ROOT_sock.close()
                self.server_sock.close()
                self.connectButton.configure(state = 'normal', text = 'Connect to ROOT')
                self.refreshButton.configure(state = 'disabled')
                self.ROOTidleButton.configure(state = 'disabled', text = "Idle")
                self.ROOTdisconnectButton.configure(state = 'disabled')
                self.ROOTsaveButton.configure(state = 'disabled')
                self.configFileLocEntry.configure(state = 'disabled')

        def ROOT_refresh(self):
                print('inside ROOT_refresh')
                data = pickle.dumps(('refresh', (self.regCenter, self.regCenterFid))) + pickleSep
                if self.try_sending_ROOT(data):
                        self.refreshButton.configure(state = 'normal')
                        self.ROOTidleButton.configure(state = 'normal', text = "Idle")
                        self.ROOTdisconnectButton.configure(state = 'normal')
                        self.ROOTsaveButton.configure(state = 'disabled')
                        self.configFileLocEntry.configure(state = 'disabled')


        def ROOT_idle(self):
                data = pickle.dumps(('idle', 0)) + pickleSep
                self.try_sending_ROOT(data)
                self.ROOTidleButton.configure(state = 'normal', text = "IDLING")
                self.ROOTsaveButton.configure(state = 'normal')
                self.configFileLocEntry.configure(state = 'normal')

        def ROOT_save(self):
                to_file = self.configFileLocEntry.get().strip()
                if to_file != '':
                        if to_file[:-5] != '.json':
                                to_file += '.json'
                        data = pickle.dumps(('save', to_file)) + pickleSep
                else:
                        data = pickle.dumps(('save', 0)) + pickleSep
                        
                self.try_sending_ROOT(data)

        def ACS_filter_set(self, active):
                """ active should be a boolean:  True or False
                """
                #active here has nothing to do with the self.ACS_filter_active parameter
                if self.ACS_filter_on == active:
                        return

                print("setting acs to active:", active)
                self.ACS_filter_on = active
                self.TWSPhasedPeakLow = 9999 
                self.TWSPhasedPeakHigh = 9999
                self.TWSPeakWrapped = False
                self.fidTWSPhasedPeakLow = 9999 
                self.fidTWSPhasedPeakHigh = 9999
                self.fidTWSPeakWrapped = False
                self.ACS_filter_active = False
                
                buttStateText = "Disable" if active else "Enable"
                self.ACSFilterButton.configure(text = "ACS Lunar Filter "+buttStateText)

                data = pickle.dumps(('ACS', (self.ACS_filter_on, self.ACS_filter_active))) + pickleSep
                self.try_sending_ROOT(data)

                
        def ACS_switch(self):
                if self.ACS_filter_on == True:
                        print('switching off')
                        self.ACS_filter_set(False)
                        # maybe also initialize some ACS structures here?  --> Yes!
                        
                elif self.ACS_filter_on == False:
                        print('switching on')
                        self.ACS_filter_set(True)
                #print "self.ACS_filter_on = ", self.ACS_filter_on

                
#        def find_best(self):
#                eventCount = self.lunShotToCount[-1] - self.lunShotToCount[-1 - self.ACSShotReserve]
#                if eventCount > self.ACSReserve:
#                        tot = self.lunRawTDCTot[-self.ACSShotReserve:]
#                        hist = [a for sublist in tot for a in sublist]
#                        print "no. of events = ", len(hist)
#                        # hist = flattened tot
#
#                else:
#                        hist = self.lunRawTDCHist[-self.ACSReserve:]
#                        print "no. of events = ", len(hist)
#
#                best = {'highest': 0, 'period': 100, 'peak': 0}
#                for t in range(100, 101):
#                        for a in [0, 50]:
#                                mod_hist = []
#                                for point in hist:
#                                        if point >= 1500 and point <= 3500:
#                                                mod_hist.append((point + a) % t)
#                                mod_hist = np.array(mod_hist)
#                                bin_content, bins = np.histogram(mod_hist, np.linspace(-0.5, t-0.5, t + 1))
#                                bin_content = savgol_filter(bin_content, 5, 1)
#                                guess = np.where(bin_content == bin_content.max())[0][0]
#                                highest = bin_content[guess]
#                                if highest > best['highest'] and guess >=2 and guess < t-2:
#                                        best['highest'] = highest
#                                        best['period'] = t
#                                        best['peak'] = (guess - a) % t
#
#                print best
#                return best
#

              
        #def acsPlotUpdateFxn(self):
        #        print "got here"
        #        can = self.acsSweepCanvas
        #        fig = self.acsSweepFig
        #        ax  = self.acsSweepAxes
        #
        #        xx = []
        #        yy = []
        #        for ii in range(10):
        #                xx.append(ii)
        #                yy.append(ii)
        #                ax.plot(xx, yy, 'k--')
        #                ax.set_xlabel("x-axis")
        #                ax.set_ylabel("y-axis")
        #                time.sleep(0.5)
        #                can.show()
                
        def acsFakeDACScanFxn(self):

                if self.acsFakeDACScanN == 0:
                        # clear the plot axes
                        # Local plot (ATUI tab)
                        self.acsDACSweepReset()
                        # ROOT plot
                        #self.acsClearSweepPlot(sweeptype='DAC')

                nmax = 100
                IRpre = 3500+int(np.random.rand()*500)
                IRpost = int(3500*(0.5+np.cos(2*np.pi*self.acsFakeDACScanN/float(nmax))))
                self.newACSDACScanVal([self.acsFakeDACScanN, IRpre, IRpost, 20, 2000+int(np.random.rand()*500)], isCurrent=True)
                print("self.acsFakeDACScanN = ", self.acsFakeDACScanN)
                if self.acsFakeDACScanN == nmax:
                        self.acsFakeDACScanN = 0
                        return
                # tuiModel.tkRoot returns the root (not ROOT) application window (a.k.a. Tkinter.TopLevel)
                # the after() method registers an alarm callback that is called after a given time
                # after(delay_milliseconds, callback)
                self.acsFakeDACScanN += 1

                #print 'got here'
                self.acsDACSweepReplot()
                #self.acsSweepAxes.clear()
                #self.acsSweepAxes.plot(self.acsFakeDACScanN, IRpre, 'ko')
                wait_ms = 50 # milliseconds to wait between calls
                self.tuiModel.tkRoot.after(wait_ms, self.acsFakeDACScanFxn)


        def acsFakePhaseSweepFxn(self):

                if self.acsFakePhaseSweepN == 0:
                        # clear the plot axes
                        # Local plot in ATUI tab
                        self.acsPhaseSweepReset()

                nmax = 250
                mean = 70.0
                sigma  = 10.0
                IRpost = 300*(1-np.exp(-(self.acsFakePhaseSweepN-mean)**2/(2*sigma**2))) + 100*np.random.rand()
                IRpre  = 500
                #IRpost = int(3500*(0.5+np.cos(2*np.pi*self.acsFakeDACScanN/float(nmax))))
                self.newACSPhaseSweepVal([self.acsFakePhaseSweepN, IRpre, IRpost, IRpre/IRpost], isCurrent=True)
                print("self.acsFakePhaseSweepN = ", self.acsFakePhaseSweepN)
                if self.acsFakePhaseSweepN == nmax:
                        self.acsFakePhaseSweepN = 0
                        return
                # tuiModel.tkRoot returns the root (not ROOT) application window (a.k.a. Tkinter.TopLevel)
                # the after() method registers an alarm callback that is called after a given time
                # after(delay_milliseconds, callback)
                self.acsFakePhaseSweepN += 1

                #print 'got here -- phase'
                self.acsPhaseSweepReplot()

                wait_ms = 50 # milliseconds of wait between iterations
                self.tuiModel.tkRoot.after(wait_ms, self.acsFakePhaseSweepFxn)

                
        def fake_laser_power(self):
                self.lasernshots += 1
                self.newBolopower([np.random.rand() * 3], isCurrent = True)
                if self.lasernshots == 20:
                        self.lasernshots = 0
                        return
                self.tuiModel.tkRoot.after(200, self.fake_laser_power)
                
                
        def try_sending_ROOT(self, pickled_data):
                if not hasattr(self, "server_sock"):
                        return
                elif self.server_sock._sock.__class__ == socket._closedsocket:
                        return
                else:
                        if hasattr(self, "ROOT_sock"):
                                try:
                                        self.ROOT_sock.sendall(pickled_data)
                                        return True
                                except socket.error as e:
                                        if isinstance(e.args, tuple):
                                                if e[0] == errno.EPIPE:
                                                        self.server_sock.close()
                                                        self.connectButton.configure(state = 'normal', text = 'Connect to ROOT')
                                                        self.refreshButton.configure(state = 'disabled')
                                                        self.ROOTidleButton.configure(state = 'disabled')
                                                        self.ROOTdisconnectButton.configure(state = 'disabled')
                                                        self.ROOTsaveButton.configure(state = 'disabled')
                                                        self.configFileLocEntry.configure(state = 'disabled')
                                                        # ROOT window disconnected
                                                        return False
                                                
                                                else:
                                                        raise Exception("Unexpected error:", e)
                                        else:
                                                raise Exception("Unexpected error:", e)
                                                        # remote
                                except:
                                        raise Exception("Unexpected error:", e)


        #-----------------------------------------------------
        # ACS-related call-back functions
        #-----------------------------------------------------
        def acsGetStatusFxn(self):
                #if self.lockStatus: return
                cmd = 'houston acs status'
                print(cmd)
                self.doCmd('apollo',cmd)

        ##########################################################################
        # DEFUNCT now that DAC and PHase sweep plots live in the ACS tab of TUI
        # and not in the ROOT plot window...
        #def acsClearSweepPlot(self, sweeptype=None):
        #        print "sweep type = ", sweeptype
        #        data = pickle.dumps(('clear', 'acssweep', sweeptype)) + pickleSep
        #        self.try_sending_ROOT(data)
        ###########################################################################
                
        def acsModulatorExtremTxStepFxn(self, junk1, junk2):
                if self.lockStatus: return
                print('junk1, junk2 = ', junk1, ", ", junk2)
                val_steps = int(self.acsModulatorExtremTxStep.get())  # DAC steps
                print('val_steps = ', val_steps)
                #cmd = 'houston acs bias %d' % val_steps
                #print cmd
                #self.doCmd('apollo',cmd)

        def acsModulatorExtremTxFxn(self):
                if self.lockStatus: return

                self.acsModulatorBias.setIsCurrent(False)
                self.acsModulatorBiasDAC.setIsCurrent(False)

                val_steps = int(self.acsModulatorExtremTxStep.get())  # DAC steps
                cmd = 'houston acs bias %d' % val_steps
                print(cmd)
                self.doCmd('apollo',cmd)
                
        def acsModulatorOpenFxn(self):
                if self.lockStatus: return
                print("not yet implemented")
                print("Will need to know what the right DAC setting is")
                print("Will need to send a DAC command to set the modulator to fully open")
                print("DON'T FORGET TO update the Modulator Bias voltage field as well")
                #self.acsModulatorBias.set(newvalue)

                #arg = "1" if self.acsModulatorOpen.getBool() else "0"
                #cmd = "houston acs lun "+arg
                #print cmd
                ####self.doCmd('apollo',cmd)
                        
        def acsAttenuatorFxn(self, junk):
                if self.lockStatus: return
                print("not implemented yet")
                val_dB = float(self.acsAttenuator.get())  # dB
                print('val_dB = ', val_dB)
                #cmd = 'houston acs atten %.3f' % val_dB
                cmd = 'houston acs atten %d' % val_dB
                print(cmd)
                self.doCmd('apollo',cmd)
                
        def acsLaserLockFxn(self):
                if self.lockStatus: return

                state = self.acsPicoFYbLock.getBool()
                print("PicoFYb Lock checkbox state = ", state)
                self.acsPicoFYbLock.setIsCurrent(False)

                arg = "1" if state else "0"
                cmd = 'houston acs lock '+arg
                print(cmd)
                self.doCmd('apollo', cmd)

        def acsPicoFYbDCPowerFxn(self):
                if self.lockStatus: return

                state = self.acsPicoFYbDCPowerButton.getBool()
                print("laser power checkbox state = ", state)
                self.acsPicoFYbDCPowerButton.setIsCurrent(False)
                
                arg = "1" if state else "0"
                cmd = 'houston acs DC '+arg
                print(cmd)
                self.doCmd('apollo', cmd)

                # set LED to pink until we get confirmation of the DC power state
                self.acsLaserPowerLEDCanvas.itemconfigure(self.acsLaserDCPowerLED, fill=self.acsLaserPowerLED_UNKNOWN)
                
                ## This is how you change the LED color
                #if state == True:
                #        self.acsLaserPowerLEDCanvas.itemconfigure(self.acsLaserPowerLED, fill='green')
                #elif state == False:
                #        self.acsLaserPowerLEDCanvas.itemconfigure(self.acsLaserPowerLED, fill='black')
                #
                ## This is how you check the LED color
                #currentColor = self.acsLaserPowerLEDCanvas.itemcget(self.acsLaserPowerLED, "fill")
                #print 'Current LED color = ', currentColor
                        
        def acsLSBRecoverFxn(self):
                if self.lockStatus: return
                cmd = 'houston acs recover'
                print(cmd)
                self.doCmd('apollo',cmd)

        def acsADCRead(self):
                if self.lockStatus: return


                # set adc readings to pink (stale)
                for intlabel in self.acsADCs:
                        intlabel.setIsCurrent(False)
                
                cmd = 'houston acs adc'
                print(cmd)
                self.doCmd('apollo',cmd)

        def acsClockPhaseSweepFxn(self):
                if self.lockStatus: return

                # set the pulseper and pulsegw parameters first
                print("setting pulseper -- FIXME: THIS MAY NOT WORK")
                self.FuncCall(self.setPar,var='pulseper')
                print("setting pulsegw  -- FIXME: THIS MAY NOT WORK")
                self.FuncCall(self.setPar,var='pulsegw')
                #pulseper = self.acmPulsePer.get() # returns a string
                #pulsegw  = self.acmPulseGW.get() # returns a string
                #cmd0 = 'houston set pulseper='+pulseper
                #cmd1 = 'houston set pulsegw='+pulsegw
                #print 'cmd0 = ', cmd0
                #print 'cmd1 = ', cmd1
                #self.doCmd('apollo',cmd0)
                #self.doCmd('apollo',cmd1)

                # then request a phase sweep
                cmd = 'houston acs phasesweep'
                print(cmd)
                self.doCmd('apollo',cmd)


        def acsClockPhaseBumpAmtFxn(self, var1, evt):
                # evt.widget holds ID of the widget that created the event
                #print "evt = ", evt
                #print "evt.widget = ", evt.widget
                if self.lockStatus: return

                # Get the bump amount (as integer)
                bumpInt = int(self.acsClockPhaseBumpAmt.get())  # converts int to string
                # then request a phase sweep, converting bump amount back to string because
                # lsb_cli phase command requires an explicit + or - in argument for incremental phase steps
                cmd = 'houston acs phase %+d' % bumpInt
                print(cmd)
                self.doCmd('apollo',cmd)
                
        def acsDACSweep(self):
                if self.lockStatus: return

                # LOCAL ONLY
                # clear the plot axes
                #self.acsClearSweepPlot(sweeptype='DAC')
                
                dacMax = self.acsModulatorSweepDACMax.get()  # returns a string
                cmd = 'houston acs dacsweep '+dacMax
                print(cmd)
                self.doCmd('apollo',cmd)

        def acsDACSweepReset(self):
                self.acsDACSweepPostPPIRVals = []
                self.acsDACSweepGreenVals = []
                self.acsDACSweepDACVals = []
                self.acsSweepAxes.cla()  # clear the plot axes
                
        def acsDACSweepReplot(self, force=False):
                nUpdate = 100  # number of points to acquire before plot update
                if force or (len(self.acsDACSweepDACVals) % nUpdate) == 0:
                        can = self.acsSweepCanvas
                        ax  = self.acsSweepAxes
                        ax.plot(self.acsDACSweepDACVals, self.acsDACSweepPostPPIRVals, 'r-')
                        ax.plot(self.acsDACSweepDACVals, self.acsDACSweepGreenVals, 'g-')
                        ax.set_xlabel("DAC Value")
                        ax.set_ylabel("PD ADC Values")
                        can.show()

        def acsPhaseSweepReset(self):
                self.acsPhaseSweepPhaseVals    = []
                self.acsPhaseSweepPostPPIRVals = []
                self.acsSweepAxes.cla()  # clear the plot axes

        def acsPhaseSweepReplot(self, force=False):
                # only plot every so often...
                nUpdate = 10  # number of points to acquire before plot update
                if force or (len(self.acsPhaseSweepPhaseVals) % nUpdate) == 0:
                        can = self.acsSweepCanvas
                        ax  = self.acsSweepAxes
                        ax.plot(self.acsPhaseSweepPhaseVals, self.acsPhaseSweepPostPPIRVals, 'r-')
                        ax.set_xlabel("Phase Value")
                        ax.set_ylabel("PD ADC Values")
                        can.show()

                
        def acsModulatorBiasSet(self, var1, evt):
                # evt.widget holds ID of the widget that created the event
                #print "evt = ", evt
                #print "evt.widget = ", evt.widget
                #print "self.acsModulatorBias    = ", self.acsModulatorBias
                #print "self.acsModulatorBiasDAC = ", self.acsModulatorBiasDAC
                if self.lockStatus: return

                self.acsModulatorBias.setIsCurrent(False)
                self.acsModulatorBiasDAC.setIsCurrent(False)

                wdgVolts, wdgDAC = "VOLTS", "DAC"
                if evt.widget == self.acsModulatorBias:
                        caller = wdgVolts
                elif evt.widget == self.acsModulatorBiasDAC:
                        caller = wdgDAC
                else:
                        print("How did you possible get here then?")
                        return
                
                if caller == wdgVolts:  # new input is in volts
                        val_volts = float(self.acsModulatorBias.get())  # Volts
                        val_dac   = int(val_volts*4095/10.0)        # Volts to DAC
                        # update estimated dac value (should still be pink)
                        self.acsModulatorBiasDAC.set(val_dac, isCurrent=False)
                else:  # new input is in DAC level
                        val_dac   = int(self.acsModulatorBiasDAC.get()) #DAC
                        val_volts = 10.0*val_dac/4095.
                        # update estimated volts value (should still be pink)
                        self.acsModulatorBias.set(val_volts, isCurrent=False)
                print('val_volts = ', val_volts)
                print('val_dac   = ', val_dac)

                # no matter the caller, by now, "val_dac" holds the desired DAC setting
                cmd = 'houston acs dac %d' % val_dac
                print(cmd)
                self.doCmd('apollo',cmd)
                
        def acsLSB_setDelay(self, var1, var2):
                if self.lockStatus: return
                #print "var1 = ", var1
                #print "var2 = ", var2
                vals = []
                for wdg in self.acsLSBDelays:
                        vals.append(wdg.get())
                        wdg.setIsCurrent(False)
                print("FID0 value = ", vals[0])
                print("FID1 value = ", vals[1])
                print("LUN0 value = ", vals[2])
                print("LUN1 value = ", vals[3])
                #cmd = "houston acs delay %s %s %s %s" % (fid0, fid1, lun0, lun1)
                cmd = "houston acs delay %s %s %s %s" % tuple(vals)
                print(cmd)
                self.doCmd('apollo',cmd)
                
        def acsCheckLunEnable(self):
                if self.lockStatus: return
                #print "LUN_EN checkbox status is: ", self.acsLunEnable.getBool()
                arg = "1" if self.acsLunEnable.getBool() else "0"
                self.acsLunEnable.setIsCurrent(False)

                cmd = "houston acs lun "+arg
                print(cmd)
                self.doCmd('apollo',cmd)

                
        def acsCheckFidEnable(self):
                if self.lockStatus: return
                #print "FID_EN checkbox status is: ", self.acsFidEnable.getBool()
                arg = "1" if self.acsFidEnable.getBool() else "0"
                self.acsFidEnable.setIsCurrent(False)
                cmd = "houston acs fid "+arg
                print(cmd)
                self.doCmd('apollo',cmd)

        def acsSetNominalDelaysFxn(self):
                if self.lockStatus: return

                isCurrent = True

                # Populate text fields with the nominal fid/lun delay values
                for ii in range(len(self.acsLSBDelays)):  # loop over the four delay fields
                        self.acsLSBDelays[ii].set(self.acsNominalDelayValues[ii], isCurrent=isCurrent)

                # Send those values to the LSB
                #print 'acsSetNominalDelaysFxn: calling self.acsLSB_setDelay()...'
                self.acsLSB_setDelay(None, None)
                #print 'acsSetNominalDelaysFxn: still alive???'
                #acsLSB_setDelay(self, var1, var2)


       #-----------------------------------------------------
       # end of ACS-related call-back functions
       #-----------------------------------------------------
 

                
        def newFiducial(self, fiducialData, isCurrent, keyVar=None):
                """Handle new fiducial datpa.
                """
                #print 'newFiducial():'
                #print '  fiducialData = ', fiducialData
                #print '  isCurrent    = ', isCurrent
                
                if not isCurrent:
                        return

                #print 'newFiducial()'
                #print '   fiducialData = ', fiducialData
                
                #send data through socket to plot window
                
                shotNum = fiducialData[0]

                #if shotNum < 0: return # perhaps redundant
                
                if not shotNum > -1: return # translated from original MPL_wdg code
                if self.runStarted == 1:
                        self.shotsInSec += 1                      
                self.shotNum += 1
                self.totalShots.set(shotNum)
                self.shotList.append(self.shotNum)
                self.chanTimesCorTot.append([])
                self.fidTWSPhasedTransient.append([])
                #self.fidChanTimesTot.append([])
                chanInten = fiducialData[2] # intensity
                photoD = fiducialData[4]    # photodiode time
                tws = fiducialData[6]
                tws_mod = self.tws_mod_dict[tws%10]
                chanDict = fiducialData[7]  # channel:time array
                #chanTimesCor = []

                # display if missed PE convergence
                if chanInten < 0:
                        self.noConvergence+=1
                        self.convWdg.set(self.noConvergence)
                                
                #if len(self.fidBunch) < self.lenFidBunch and shotNum < self.nruns:
                #    self.fidBunch.append(fiducialData)
                #    return
                #
                #else:
                #    if shotNum == self.nruns: 
                #        self.fidBunch.append(newfiducialData)
                #    for q in np.arange(len(self.fidBunch)):
                #        fiducialData = self.fidBunch[q]

                while len(self.fidTWSPhasedTransient) > self.ACSShotReserve:
                        self.fidTWSPhasedTransient.pop(0)
                                    
                # update diffuser phase histogram
                #self.dphase_all.addRow((dphase,))
                #self.dphase.addRow((dphase,))
                
                # remove any misbehaving APD channels (determined in 'Dark' callback)
                for j in self.omitTDCChan:
                        if j+1 in chanDict:
                                chanDict.pop(j+1)
                            
                
                
                if shotNum % self.lenFidBunch == 0:
                        rate = np.true_divide(self.totalFidNum,shotNum)
                        self.rateFid.set(rate)
                                
                #if len(chanNums): 
                #        chanArr[chanNums] = chanTimes        
                #        chanArr=[int(i) for i in chanArr]                                
                #        self.fidDat.append(chanArr)
                #        # self.doCmd('apollo','fidDat=%s' %self.fidDat)

                fidregnum = 0
                temp = {}
                chan_tagged = []
                for chan in chanDict:
                        # correct for channel offsets
                        time = temp[chan] = chanDict[chan] - self.chanOffset[chan -  1]
                        tagged = False
                        if time >= self.TWSPhasedXlim[0] and time <= self.TWSPhasedXlim[1]:
                                phased = temp[chan] + tws_mod
                                self.fidTWSPhasedTransient[-1].append(phased)
                                if self.TWSPeakWrapped:
                                        if phased % 500 <= self.TWSPhasedPeakHigh or phased % 500 >= self.TWSPhasedPeakLow:
                                                tagged = True
                                                chan_tagged.append(chan)

                                elif phased % 500 >= self.TWSPhasedPeakLow and phased % 500 <= self.TWSPhasedPeakHigh:
                                        tagged = True
                                        chan_tagged.append(chan)
                                
                                #self.chanTimesCorHist.append(tcor)
                                #chanTimesCor.append(tcor)
                                #self.tcorListFid.append(chanTimesCor)
                                #self.doCmd('apollo','fidDat=%s' %self.chanTimesCorTot)
                        if chan != 15:
                                if tagged == False or self.ACS_filter_active == False:
                                        tcor = photoD-temp[chan]
                                        self.chanTimesCorTot[-1].append(tcor)
                                        
                                        if tcor < self.upperFid and tcor > self.lowerFid:
                                                fidregnum = fidregnum+1
                                                self.fidRegNum = self.fidRegNum + 1


                fiducialData.append(chan_tagged)
                pickledFiducialData = pickle.dumps(('fiducial', fiducialData)) + pickleSep
                pickledFiducialData += pickle.dumps(('fid_tws_test', (shotNum, self.fidTWSPhasedTransient[-1]))) + pickleSep
                self.try_sending_ROOT(pickledFiducialData)
                


                self.fidRegRate = np.true_divide(self.fidRegNum,self.shotNum)
                self.fidRegWdg.set(self.fidRegNum)
                
                if shotNum % self.lenFidBunch == 0:
                        self.fidRegRateWdg.set(self.fidRegRate)


                if 15 in chanDict:
                        nhit = len(chanDict)-1          # number of hits (except for chan 15 - the photodiode)
                else:
                        nhit = len(chanDict)
    
                self.totalFidNum = self.totalFidNum + nhit
                if self.ACS_filter_active:
                        self.totalFidNum -= len(chan_tagged)
                self.totalFid.set(self.totalFidNum)

                if shotNum % 128 == 1:

                        TWSPhasedHistogram, _ = np.histogram([val for sublist in self.fidTWSPhasedTransient for val in sublist], self.TWSPhasedBinEdges)
                                
                        peakbin = np.where(TWSPhasedHistogram == TWSPhasedHistogram.max())[0][0]
                        peak = self.TWSPhasedBinEdges[peakbin] + self.TWSPhasedBinWidth / 2.0
                        pickledACSData = pickle.dumps(('ACS', peak)) + pickleSep
                        self.try_sending_ROOT(pickledACSData)  
                        peak %= 500
                        self.fidTWSPhasedPeakLow = (peak - self.ACSRadius )%500
                        self.fidTWSPhasedPeakHigh = (peak + self.ACSRadius )%500
                        if self.fidTWSPhasedPeakLow > self.fidTWSPhasedPeakHigh:
                                self.fidTWSPeakWrapped = True
                        else:
                                self.fidTWSPeakWrapped = False

                                
                # update registered fid rate indicator
                if shotNum > self.rateReserve and shotNum % self.lenFidBunch == 0:
                        recnum=0
                        for i in range(self.rateReserve):
                                dat = self.chanTimesCorTot[-i-1]
                                # counting backwards... the last 200 shots
                                for x in dat:
                                        if x < self.upperFid and x > self.lowerFid:
                                                recnum = recnum + 1

                        recRate = np.true_divide(recnum, self.rateReserve) 
                        self.fidRegRateRecWdg.set(recRate)
                        
        
                        
        def newLunar(self, lunarData, isCurrent, keyVar=None):
                """Handle new lunar data.
                """
                #print lunarData
                #print 'newLunar():'
                #print '  lunarData = ', lunarData
                #print '  isCurrent = ', isCurrent
                
                if not isCurrent:
                        return

                
                shotNum = lunarData[0]# lunar shot number

                
                if shotNum < 0: 
                    return
                    
                self.shotNumLun = self.shotNumLun + 1
                self.totalLunShots.set(shotNum)
                self.missedFRC = shotNum - self.shotNumLun

                # make sure shotNum = index in lunRawTDCTot + 1
                for i in range(len(self.lunRawTDCTot), shotNum):
                        self.lunRawTDCTot.append([])
                        self.chanTimesCorTotLun.append([]) # insert a dummy y value for scatter plot (in case no lunars)
                        self.lunTWSPhasedTransient.append([]) #filter need

                #if shotNum > -1:
                shotNum = lunarData[0]
                self.shotListLun.append(shotNum) # list of x values for lunar scatter plot
                chanDict = lunarData[6]             # channel:time dictionary 
                

                
                # get rid of bad channels as determined from Dark data
                #print self.omitTDCChan
                for j in self.omitTDCChan:
                        if j+1 in chanDict:
                                chanDict.pop(j+1)
                                    
                #secAcc = lunarData[1]           # accumulated seconds
                chanNums = list(chanDict.keys())      # channels hit
                nhit = lunarData[4]             # number of lunar hits
                #actually still includes chans in omitTDCChan?
                chanTimes = list(chanDict.values())   # time of hits
                #chanPred = lunarData[3]         # tpred
                #chanPred = lunarData[2]+self.predSkew # ppred+predSkew (should be the same as tpred)
                chanPred = lunarData[2] # ppred
                chanArr = np.zeros(NChan)


                #hitgrid calc not needed here
                #hitgrid_row=np.mod(shotNum-1,200)
                #if np.sum(self.hitgridData[hitgrid_row][:])>0:
                #        self.hitgridData[hitgrid_row][:]=np.zeros(16)
                #        #set to 0 if non-zero...
                #        
                #for i in chanNums:                
                #        self.hitgridData[hitgrid_row,i-1]=self.hitgridData[hitgrid_row,i-1]=+np.true_divide(1.0 - 0.0001*self.chanBackground[i-1],self.chanFlatCorr[i-1])

                # "..Here" refers to points at this guide offset for tracking plots
                self.shotsHere = self.shotsHere + 1
                self.shotsRxx = self.shotsRxx + 1
                
                # also includes counts from channels in omitTDCChan?
                self.lunNumHere = self.lunNumHere + len(chanNums)
                self.lunNumRxx = self.lunNumRxx + len(chanNums)
                self.lunRateHere = np.true_divide(self.lunNumHere,self.shotsHere)
                self.lunRateRxx = np.true_divide(self.lunNumRxx,self.shotsRxx)
               
                self.lunRegNum = 0

                #####ACS filter v0.2####
                
                
                temp = {}
                chan_tagged = []
                
                if chanDict: # if there are lunar returns...
            
                        chanArr[chanNums] = chanTimes 
                        self.lunShotToCount.append(self.lunShotToCount[-1] + len(chanTimes))
                        tws = lunarData[5]
                        tws_mod = self.tws_mod_dict[tws%10]

                        for chan in chanDict:
                                # correct for channel offsets
                                temp[chan] = chanDict[chan] - self.chanOffset[chan-1]
                                tagged = False

                                #tag photons that fall inside the peak in tws-phased space
                                if temp[chan] >= self.TWSPhasedXlim[0] and temp[chan] <= self.TWSPhasedXlim[1]:
                                        phased = temp[chan] + tws_mod
                                        self.lunTWSPhasedTransient[-1].append(phased)
                                        if self.TWSPeakWrapped:
                                                if phased % 500 <= self.TWSPhasedPeakHigh or phased % 500 >= self.TWSPhasedPeakLow:
                                                        tagged = True
                                                        chan_tagged.append(chan)

                                        elif phased % 500 >= self.TWSPhasedPeakLow and phased % 500 <= self.TWSPhasedPeakHigh:
                                                tagged = True
                                                chan_tagged.append(chan)
                                
                                
                                #self.lunRawTDCTot[-1].append(temp[chan])
                                #self.lunRawTDCHist.append(temp[chan])
                                chanDiff = temp[chan] - chanPred
                                if tagged == False or self.ACS_filter_active == False:
                                        self.chanTimesCorHistLun.append(chanDiff)
                                        self.chanTimesCorTotLun[-1].append(chanDiff)

                                        if chanDiff > self.lower and chanDiff < self.upper:
                                                self.lunRegNum = self.lunRegNum + 1
                                                self.lunRegNumHere = self.lunRegNumHere + 1
                                                self.lunRegNumRxx = self.lunRegNumRxx + 1
                                                self.lunRegRate = np.true_divide(self.lunRegNum,self.shotNumLun)
                                                self.lunRegRateHere = np.true_divide(self.lunRegNumHere,self.shotsHere)
                                                self.lunRegRateRxx = np.true_divide(self.lunRegNumRxx,self.shotsRxx)
                                                self.totalLunRegNum = self.totalLunRegNum + 1
                                        elif chanDiff >= self.regCenter+self.bg_before[0] and chanDiff <= self.regCenter+self.bg_before[1]:
                                                self.bgLun += 1
                                        elif chanDiff >= self.regCenter+self.bg_after[0] and chanDiff <= self.regCenter+self.bg_after[1]:
                                                self.bgLun += 1
                                                
                self.ACSTotNum.append(len(chan_tagged))
                if self.ACS_filter_active:
                        self.ACSSubtracted += self.ACSTotNum[-1]
                        self.totACSWdg.set(self.ACSSubtracted)

                self.rateACSWdg.set(np.true_divide(self.ACSSubtracted, shotNum))

                        
                self.totalLunNum = self.totalLunNum + len(chanDict) - len(chan_tagged)
                self.lunBackgroundNum = self.totalLunNum - self.totalLunRegNum 
                self.lunRegList.append(self.lunRegNum)

                

                lunarData.append(chan_tagged)
                pickledLunarData = pickle.dumps(('lunar', lunarData)) + pickleSep
                #pickledLunarData += pickle.dumps(('tws_test', (shotNum, self.lunTWSPhasedTransient[-1]))) + pickleSep # some TWS test data. Comment this line out when phased graph not needed
                self.try_sending_ROOT(pickledLunarData)

                #code to determine new peak
                while len(self.lunTWSPhasedTransient) > self.ACSShotReserve:
                        self.lunTWSPhasedTransient.pop(0)

                if self.ACS_filter_on == True:

                        #if np.random.rand() <= 0.02 and shotNum >= self.ACSShotReserve:
                        if shotNum % 64 == 1:
                                # update about once every 50 shots.
                                #recalculate (fid and lun combined) histogram based on the Transient arrays
                                TWSPhasedHistogram, _ = np.histogram([val for sublist in self.lunTWSPhasedTransient for val in sublist], self.TWSPhasedBinEdges)
                                
                                #determine peak (naively)
                                
                                peakbin = np.where(TWSPhasedHistogram == TWSPhasedHistogram.max())[0][0]
                                peak = (self.TWSPhasedBinEdges[peakbin] + self.TWSPhasedBinWidth / 2.0) % 500
                                #pickledACSData = pickle.dumps(('ACS', peak)) + pickleSep
                                #self.try_sending_ROOT(pickledACSData)  

                                self.TWSPhasedPeakLow = (peak - self.ACSRadius )%500
                                self.TWSPhasedPeakHigh = (peak + self.ACSRadius )%500
                                if self.TWSPhasedPeakLow > self.TWSPhasedPeakHigh:
                                        self.TWSPeakWrapped = True
                                else:
                                        self.TWSPeakWrapped = False

                                potential = 0
                                transient_flat = [t for l in self.lunTWSPhasedTransient for t in l]
                                for t in transient_flat:
                                        if self.TWSPeakWrapped:
                                                if t % 500 <= self.TWSPhasedPeakHigh or t % 500 >= self.TWSPhasedPeakLow:
                                                        potential += 1
                                        elif t % 500 >= self.TWSPhasedPeakLow and t % 500 <= self.TWSPhasedPeakHigh:
                                                potential += 1
                                if potential > 0.1 * self.ACSShotReserve * self.ACSRadius/15:
                                        self.ACS_filter_active = True
                                        #print "tagged lun:", potential
                                        #print "filter active:", self.ACS_filter_active
                                else:
                                        self.ACS_filter_active = False
                                        #print "tagged lun:", potential
                                        #print "filter active:", self.ACS_filter_active
                                data = pickle.dumps(('ACS', (self.ACS_filter_on, self.ACS_filter_active))) + pickleSep
                                self.try_sending_ROOT(data)

                
                # tracking stuff
                self.rateHere = self.lunRegRateHere
                #self.track_ret.addRow((self.offsetAz, self.offsetEl, self.rateHere))

                #if shotNum > 50:
                        #self.rateHere = self.lunRegRateHere
                        #self.track_ret.addRow((self.offsetAz, self.offsetEl, self.rateHere))
                        #if not len(self.track_ret_all.getColumn(2)): 
                        #        self.track_APD.setRange('z',0.,self.rateHere)
                        #elif len(self.track_ret_all.getColumn(2)) and self.rateHere > max(self.track_ret_all.getColumn(2)):
                        #        self.track_APD.setRange('z',0.,self.rateHere)
                        #elif len(self.track_ret_all.getColumn(2)) and self.rateHere < max(self.track_ret_all.getColumn(2)):
                        #        self.track_APD.setRange('z',0.,max(self.track_ret_all.getColumn(2)))
            
                        #self.rateRxx = self.lunRegRateRxx
                        #self.rxxRate.addRow((self.rxx, self.rxy, self.rateRxx))
                        #if not len(self.rxxRate_all.getColumn(2)):
                        #        self.rxxRate_disp.setRange('z',0.,self.rateRxx)
                        #elif len(self.rxxRate_all.getColumn(2)) and self.rateRxx > max(self.rxxRate_all.getColumn(2)):
                        #        self.rxxRate_disp.setRange('z',0.,self.rateRxx)
                        #elif len(self.rxxRate_all.getColumn(2)) and self.rateRxx < max(self.rxxRate_all.getColumn(2)):
                        #        self.rxxRate_disp.setRange('z',0.,max(self.rxxRate_all.getColumn(2)))
                                              

                #update current rate
                if shotNum > self.rateReserve and self.shotNumLun % self.lenLunBunch == 0:
                        recnum=0
                        for i in range(1, self.rateReserve+1):
                                dat = self.chanTimesCorTotLun[-i]
                                # counting backwards... the last 200 shots
                                for x in dat:
                                        if x < self.upper and x > self.lower:
                                                recnum = recnum + 1

                        recRate = np.true_divide(recnum, self.rateReserve) 
                        self.regRateRecLun.set(recRate)
                        


                #if self.shotNumLun > 1:
                #    self.changes_all.addRow((shotNum,0,(self.changeState-1.)*2000.))
                #    self.changes.addRow((shotNum,0,(self.changeState-1.)*2000.))
                #
                #if shotNum > self.rateReserve:
                #    self.lunseries.setRange('y',min(self.lunTimeSeriesReg.getColumn(1)),0.01+max(self.lunTimeSeriesReg.getColumn(1)))
                
                #if self.shotNumLun == 2:
                #    self.lunSeriesAll.setRange('y',-480,480)
                #    self.lun_return_hist.setRange('x',-2000,2000)
                #    self.cc_return_hist.setRange('x',-2500,2500)
                #    self.raw_hist.setRange('x',0,4000)
                #    self.rep_cc[0].setBinWidth('x',40)
                #    self.rep_lun[0].setBinWidth('x',40)
                #    self.rep_raw[0].setBinWidth('x',40)
                #    self.rep_raw[1].setBinWidth('x',40)
                #
                #        if self.rasterShots:
                #            rem = np.remainder(self.shotsHere,int(self.rasterShots))
                #
                #        if self.raster==1 and self.rasterShots>0 and self.shotsHere > 0 and rem==0:
                #            
                #            offMag=self.rasterMag
                #
                #            guideDict = {'up':(0.,1.),'down':(0.,-1.), 'left':(-self.altCor,0.),'right':(self.altCor,0.),
                #                         'upLeft':(-self.altCor,1.)} # corrected for Cos(Alt)
                #            offDir = guideDict.get(self.rasterList[self.irasterGuide])
                #            
                #            offx = offDir[0]*offMag
                #            offy = offDir[1]*offMag
                #
                #            if np.sqrt(offx**2 + offy**2) < np.true_divide(0.75,3600):
                #                self.doCmd('tcc','offset guide %f,%f' % (offx,offy))
                #            else:
                #                self.doCmd('tcc','offset guide %f,%f /computed' % (offx,offy))
                #            
                #            self.irasterGuide += 1                    
                #
                #            if self.irasterGuide == 9 and self.irasterRxx < 8 and self.offMag != 0.0:
                #                self.irasterGuide = 0
                #                self.offsetGuide(self.rasterList[self.irasterRxx])
                #                self.irasterRxx += 1
                #            elif self.irasterGuide == 9 and self.irasterRxx == 8 and self.offMag != 0.0:
                #                self.offsetGuide('up')
                #                self.offsetGuide('left')
                #                self.raster = 0
                #                self.irasterGuide = 0
                #                self.irasterRxx = 0 
                #                self.rasterOnButton.configure(text = 'Raster Ended')
                #            elif self.irasterGuide == 9 and self.offMag == 0.0:
                #                self.raster = 0
                #                self.irasterGuide = 0
                #                self.irasterRxx = 0 
                #                self.rasterOnButton.configure(text = 'Raster Ended
                    
                #if self.hitgridReg == True or self.hitgridReg==False:
                #    #whaaaatttt, meaning the function to display only registered hits on the hitgrid has yet to be implemented?
                #    a=np.sum(self.hitgridData,axis=0)
                #    
                #    if np.max(a)==0: 
                #        amax=1
                #    else:
                #        amax=np.max(a)
                #
                #    a[:] = [np.true_divide(i,amax) for i in a]
                #    
                #    for i in range(16):                                         
                #        self.chanAPD = self.chanMap[i]                           
                #        c = str(np.abs(a[i]-1.))                           
                #        self.lun_hitgrid_pix[self.chanAPD].set_color(c)
                #        self.lun_hitgrid_ax.draw_artist(self.lun_hitgrid_pix[self.chanAPD])
                #    self.mpl_fig.canvas.blit(self.lun_hitgrid_ax.bbox)                                                                          
                
                #scatter plot of lunar returns 
                
                #self.lun_strip_x_dat=self.shotListLun
                #self.lun_strip_y_dat=self.chanTimesCorHistLun
                
                ##xu,yu = self.lun_strip_upper.get_data()
                ##self.lun_strip_upper_old.set_data(xu,yu)
                ##self.lun_strip_ax.draw_artist(self.lun_strip_upper_old)
                ##xl,yl = self.lun_strip_lower.get_data()
                ##self.lun_strip_lower_old.set_data(xl,yl)
                ##self.lun_hist_ax.draw_artist(self.lun_strip_lower_old) 
                
                #self.lun_strip_lower_x_dat.append(shotNum)
                #self.lun_strip_upper_x_dat.append(shotNum)
                #self.lun_strip_lower_y_dat.append(self.lower)
                #self.lun_strip_upper_y_dat.append(self.upper)
                #                    
                #self.lun_strip_data_bundle=[self.lun_strip_x_dat,self.lun_strip_y_dat,self.lun_strip_lower_x_dat,self.lun_strip_lower_y_dat,\
                #    self.lun_strip_upper_x_dat,self.lun_strip_upper_y_dat]
                #
                #self.update_Axis(self.lun_strip_ax,self.lun_strip_line_bundle,self.lun_strip_data_bundle)
                #histogram                                        
                #xu,yu = self.lun_hist_upper.get_data()
                #self.lun_hist_upper_old.set_data(xu,yu)
                #self.lun_hist_ax.draw_artist(self.lun_hist_upper_old)
                #xl,yl = self.lun_hist_lower.get_data()
                #self.lun_hist_lower_old.set_data(xl,yl)
                #self.lun_hist_ax.draw_artist(self.lun_hist_lower_old) 
                #
                #self.lun_hist_upper.set_data([float(self.upper),float(self.upper)],[5,float(self.lun_hist_upper_lim)-5])
                #self.lun_hist_ax.draw_artist(self.lun_hist_upper)  
                #self.lun_hist_lower.set_data([float(self.lower),float(self.lower)],[5,float(self.lun_hist_upper_lim)-5])
                #self.lun_hist_ax.draw_artist(self.lun_hist_lower) 
                #
                #x,y=self.lun_hist.get_data()  # cover old data
                #self.lun_hist_old.set_data(x,y)
                #self.lun_hist_ax.draw_artist(self.lun_hist_old)
                #
                #data=np.array(self.chanTimesCorHistLun[-self.histReserve:])
                #binwidth=40
                #binnum=int(4000/binwidth)
                #y,binEdges=np.histogram(data,bins=binnum, range=(-2000,2000))
                #bincenters = 0.5*(binEdges[1:]+binEdges[:-1])
                #x=[]
                #z=[]
                #for i in range(len(bincenters)):
                #    x.append(bincenters[i]-0.5*binwidth)
                #    x.append(bincenters[i]+0.5*binwidth)
                #        
                #    z.append(y[i])
                #    z.append(y[i])
                #
                #self.lun_hist.set_data(np.array(x),np.array(z))
                #self.lun_hist_ax.draw_artist(self.lun_hist)  
                #
                #self.mpl_fig.canvas.blit(self.lun_hist_ax.bbox)
                #
                #
                #
                #
                ## rate stripchart                                                                  
                #self.lun_rate_strip_old_x_dat,self.lun_rate_strip_old_y_dat=self.lun_rate_strip.get_data()                 
                #
                #if shotNum > self.rateReserve:
                #    x=np.arange(self.shotNumLun-self.rateReserve)+self.rateReserve
                #    self.lun_rate_strip_x_dat=x
                #    y=np.zeros(len(x))
                #        
                #    for i in range(len(x)):                            
                #        y[i]=np.true_divide(np.sum(np.array(self.lunRegList[i:i+self.rateReserve])),self.rateReserve)
                #    self.lun_rate_strip_y_dat=y
                #    self.regRateRecLun.set(y[-1])
                #            
                #    self.lun_rate_strip_data_bundle=[self.lun_rate_strip_old_x_dat,self.lun_rate_strip_old_y_dat,self.lun_rate_strip_x_dat,self.lun_rate_strip_y_dat]
                #    self.update_Axis(self.lun_rate_strip_ax,self.lun_rate_strip_line_bundle,self.lun_rate_strip_data_bundle)

                        
                # update indicator widgets
                self.totalLun.set(self.totalLunNum)
                self.regLun.set(self.totalLunRegNum)

                if self.shotNumLun % self.lenLunBunch == 0:
                        # # of shots/# of return shots
                        self.rateLun.set(np.true_divide(self.totalLunNum,self.shotNumLun))
                        self.regRateLun.set(np.true_divide(self.totalLunRegNum,self.shotNumLun))
                        #self.yield_est = self.totalLunRegNum-self.binForReg*np.true_divide(self.totalLunNum-self.totalLunRegNum,3900.-self.binForReg)
                        self.yield_est = self.totalLunRegNum-np.true_divide(self.bgLun,self.bg_multiple)
                        self.lunBackgroundWdg.set(self.yield_est)
                        self.missedFRCWdg.set(self.missedFRC)
                    




                        
        def newStare(self, stareData, isCurrent, keyVar=None):
                """Handle new stare data.
                """
                if not isCurrent:
                        return
                
                pickledStareData = pickle.dumps(("stare", stareData)) + pickleSep
                self.try_sending_ROOT(pickledStareData)
                
                #print "Stare Data:", stareData
 #               self.omitTDCChan=[1,4]
                for j in self.omitTDCChan:   # omit channels determined from Dark data
                    stareData[j] = 0
                    
 #               if self.stareShot==0:
 #                   self.redraw()
                
                self.stareShot = self.stareShot+1

                self.staresHere = self.staresHere + 1 # stares taken at this guide offset
                self.stareNumHere = self.stareNumHere + np.add.reduce(stareData) - .05*self.sumDarkChans
                self.stareRateHere = np.true_divide(self.stareNumHere,self.staresHere)                
        
                #self.stare_rate_old_x_dat,self.stare_rate_old_y_dat=self.stare_rate.get_data()                 
                #self.stare_rate_x_dat=np.arange(self.stareShot)+1
                #self.stare_rate_y_dat.append(np.add.reduce(stareData)-.05*self.sumDarkChans) 
                ## MARK    
                #self.stare_rate_data_bundle=[self.stare_rate_old_x_dat,self.stare_rate_old_y_dat, self.stare_rate_x_dat,self.stare_rate_y_dat]   
                #self.update_Axis(self.stare_rate_ax,self.stare_rate_line_bundle,self.stare_rate_data_bundle)                                                     
                #
                #
                #for i in range(16):                                         
                #    self.chanAPD = self.chanMap[i]
                #    a=np.abs(np.true_divide(stareData[i],np.max(stareData) ) -1.0)                       
                #    c = str(a)
                #    self.lun_hitgrid_pix[self.chanAPD].set_color(c)
                #    self.lun_hitgrid_ax.draw_artist(self.lun_hitgrid_pix[self.chanAPD])
                #self.mpl_fig.canvas.blit(self.lun_hitgrid_ax.bbox) 

                
        def newDark(self, darkData, isCurrent, keyVar=None):
                """Handle new dark background data. values are for 10,000 gates
                """
                if not isCurrent:
                        return


                #self.omitTDCChan = [3, 6, 9, 12]
                #TO ADD to ROOT
                pickledDarkData = pickle.dumps(('dark', darkData)) + pickleSep
                self.try_sending_ROOT(pickledDarkData)
                
                #self.omitTDCChan = [] # This will be a list of TDC channels omitted from the plots
                #print "Dark Data:", darkData

                #darkData.pop(0)
                                       
                self.sumDarkChans = 0
                
                for i in range(len(darkData)):
                    chanAPD = self.chanMap[i] # not (i - 1) here because no channel # (starts at 0)
                    if darkData[i] > 3000 and i not in self.omitTDCChan:  # we want to omit this channel if it avalanches with nearly every gate
                        self.omitTDCChan.append(i)
                    else:
                        if darkData[i] != None:
                            self.sumDarkChans += darkData[i]

                    self.chanBackground[i] = darkData[i]    #put dark current data into chanBackground array
                     
                    # Then show the dark current data in the stare grid plot for verification                                    
                     
                for j in self.omitTDCChan:   # omit channels determined from Dark data
                    darkData[j] = 0                    
                     
                #for i in range(16):                                         
                #    self.chanAPD = self.chanMap[i]
                #    a=np.abs(np.true_divide(darkData[i],np.max(darkData) ) -1.0)                       
                #    c = str(a)
                #    #self.doCmd('apollo','%s' %c)
                #    self.lun_hitgrid_pix[self.chanAPD].set_color(c)
                #    self.lun_hitgrid_ax.draw_artist(self.lun_hitgrid_pix[self.chanAPD])
                #
                #self.mpl_fig.canvas.blit(self.lun_hitgrid_ax.bbox) 
                
                # uncheck boxes on Channels tab

                for j in self.omitTDCChan:
                    chanAPD = self.chanMap[j]
                    self.darkWdgDict[chanAPD].set(False)
                    
                #print self.omitTDCChan
                #print self.chanBackground
                #print self.sumDarkChans

        def newFlat(self, flatData, isCurrent, keyVar=None):
                """Handle newflat data. values are for 10,000 gates
                """
                if not isCurrent:
                        return

                #TO ADD to ROOT
                pickledFlatData = pickle.dumps(('flat', flatData)) + pickleSep
                self.try_sending_ROOT(pickledFlatData)
                
                
                #flatData.pop(0)
                print("flat:", flatData)

                nflat = 0
                flatsum = 0
                
                usable = list(np.zeros(16))
                self.chanFlatCorr= list(np.zeros(16))
                
                for i in range(len(flatData)):  
                    self.chanFlat[i] = flatData[i] - self.chanBackground[i]
                    usable[i] = self.chanFlat[i]
                
                for j in self.omitTDCChan:   # omit channels determined from Dark data
                    usable[j] = 24000       # put a bogus number in the omitted channel slots
                                            # total counts in a channel should never exceed 24000 
                for i in range(16):
                    if usable[i] < 24000:
                        flatsum += usable[i]

                ave = np.true_divide(flatsum,(16-usable.count(24000)))

                for i in range(len(self.chanFlat)):  
                    self.chanFlatCorr[i] = np.true_divide(self.chanFlat[i],ave)

                for j in self.omitTDCChan:   # set normalization for omitted channels to 1
                    self.chanFlatCorr[j] = 1.0

                for j in range(len(self.chanFlatCorr)):   # normallize to 1 if flat <= dark
                    if self.chanFlatCorr[j] <= 0.0:
                        self.chanFlatCorr[j] = 1.0

        def newOffset(self, offsetData, isCurrent, keyVar=None):
                """Handle new telescope guide offset.
                """
                if not isCurrent:
                        return
            
                #offsetAzNew = np.true_divide(offsetData[0].pos,self.altCor)*3600.0  #New Az offset position
                                                                                     #in arcsec, corected for cos(alt)
                offsetAzNew = offsetData[0].pos*3600.0  #New Az offset position
                offsetElNew = offsetData[1].pos*3600.0  #New Alt (El) offset in arcsec

                #print offsetAzNew,offsetElNew # print to CRT

##                self.trackHist.addRow((self.offsetNum,self.offsetAz,self.offsetEl,self.rateHere))

##                if  self.rateHere > 0.0:
##                    self.track_ret_all.addRow((self.offsetAz,self.offsetEl,self.rateHere))
##
##                if  self.stareRateHere > 0.0:
##                    self.stare_rate_all.addRow((self.offsetAz,self.offsetEl,self.stareRateHere))

#                self.shotsHere = 0
#                self.lunNumHere = 0
#                self.lunRateHere = 0
#                self.lunRegNumHere = 0
#                self.lunRegRateHere = 0
#                self.rateHere = 0.0
 #               self.track_ret.clear()

#                self.staresHere = 0
#                self.stareNumHere = 0
#                self.stareRateHere = 0.0
 #               self.stare_rate.clear()

                self.offsetNum = self.offsetNum + 1

                self.offsetAz = offsetAzNew
                self.offsetEl = offsetElNew

                self.offXWdg.set(offsetAzNew) 
                self.offYWdg.set(offsetElNew)

                # issue comment to Houston
                if not self.lockStatus:
                    self.doCmd('apollo','houston set guideOff="%.4f %.4f"' % (offsetAzNew,offsetElNew),write=False)

## for test mode
        def newGuideOff(self, guideOffData, isCurrent, keyVar=None):
                """Handle new telescope guide offset **in test mode**.
                """

                if not isCurrent:
                        return

                data=guideOffData[0].split()
                if len(data) == 0: return

                pickledGuideOffData = pickle.dumps(('guideoff', data)) + pickleSep
                self.try_sending_ROOT(pickledGuideOffData)
                
                offsetAzNew = float(data[0])  #New Az offset position in arcsec, corected for cos(alt)
                offsetElNew = float(data[1])  #New Alt (El) offset in arcsec

#                self.trackHist.addRow((self.offsetNum,self.offsetAz,self.offsetEl,self.rateHere))

##                if  self.rateHere > 0.0:
##                    self.track_ret_all.addRow((self.offsetAz,self.offsetEl,self.rateHere))
##
##                if  self.stareRateHere > 0.0:
##                    self.stare_rate_all.addRow((self.offsetAz,self.offsetEl,self.stareRateHere))

#                self.shotsHere = 0
#                self.lunNumHere = 0
#                self.lunRateHere = 0
#                self.lunRegNumHere = 0
#                self.lunRegRateHere = 0
#                self.rateHere = 0.0
 #               self.track_ret.clear()

#                self.staresHere = 0
#                self.stareNumHere = 0
#                self.stareRateHere = 0.0
#                self.stare_rate.clear()

                self.offsetNum = self.offsetNum + 1

                self.offsetAz = offsetAzNew
                self.offsetEl = offsetElNew

                self.offXWdg.set(offsetAzNew) 
                self.offYWdg.set(offsetElNew)

        def newBoresight(self, boresightData, isCurrent, keyVar=None):
                """Handle new telescope guide offset.
                """
                if not isCurrent:
                        return

                self.boreAz = boresightData[0].pos*3600.0
                self.boreEl = boresightData[1].pos*3600.0

                self.boreXWdg.set(self.boreAz)
                self.boreYWdg.set(self.boreEl)

                # issue comment to Houston
                if not self.lockStatus:
                    self.doCmd('apollo','houston set boreOff="%.4f %.4f"' % (self.boreAz,self.boreEl),write=False)
                    
# for test mode

        def newBoreOff(self, boreOffData, isCurrent, keyVar=None):
                """Handle new telescope guide offset. **Only in test mode!**
                """
                if not isCurrent:
                        return

                data = boreOffData[0].split()
                if len(data) == 0: return

                self.boreAz = float(data[0])
                self.boreEl = float(data[1])

                self.boreXWdg.set(self.boreAz)
                self.boreYWdg.set(self.boreEl)

        def newAxePos(self, axePosData, isCurrent, keyVar=None):
            
                if not isCurrent:
                        return
                newAxisPos = (axePosData[0],axePosData[1],axePosData[2])
                self.axisPos = newAxisPos
    
                if axePosData[1] != None:
                    self.altCor = np.true_divide(1.0,np.cos(np.pi*np.true_divide(self.axisPos[1],180.)))
                    #print axePosData[0], axePosData[1], self.altCor

                    if not self.lockStatus and None not in newAxisPos:
                        self.doCmd('apollo','houston set axePos="%.4f %.4f %.4f"' % (axePosData[0],axePosData[1],axePosData[2]),write=False)
                        
        def newObjName(self,objNameData,isCurrent,keyVar=None):
               if not isCurrent:
                        return
               newObjName = objNameData[0]
               
               title = 'Run Statistics %s' % newObjName
               
               self.statFrame.configure(text=title)
                

       
        def newSecFocus(self,secFocusData, isCurrent, keyVar=None):
            
                if not isCurrent:
                        return
                newSecFocus = secFocusData[0]
                
                #if newSecFocus != None:

                    #if not self.lockStatus:
                        #self.doCmd('apollo','houston set SecFocus="%.4f"' % newSecFocus,write=False)

        def newAirTemp(self, airTempData, isCurrent, keyVar=None):
                global path
                
                if not isCurrent:
                        return
                    
                if airTempData[0] != None and self.lockStatus==0: # airtemp is in deg. C
                    self.doCmd('apollo','houston set airtemp=%.2f' % airTempData[0],write=False)
                    
                else:
                    return
        def newPressure(self, pressureData, isCurrent, keyVar=None):
                global path
                
                if not isCurrent:
                        return
                    
                if pressureData[0] != None and self.lockStatus==0:
                    pressure = pressureData[0]*0.01 # convert to millibar
                    self.doCmd('apollo','houston set pressure=%.3f' % pressure,write=False)
                    
                else:
                    return

        def newHumidity(self, humidityData, isCurrent, keyVar=None):
                global path

                if humidityData[0] != None:
                    humidity = humidityData[0]*100. #convert to % relative humidity

                if humidityData[0] != None and self.lockStatus==0:

                    self.doCmd('apollo','houston set humidity=%.0f' % humidity,write=False)
                    
                else:
                    return

        def newGPS(self, GPSData, isCurrent, keyVar=None):
                """Handle new GPS  data.
                """
                global gpsi,HOUSTON
                
                if not isCurrent:
                    return

                HOUSTON = 1

                if gpsi == 0: # on first gpstrig, start recording run seconds, set run state                    
                    gpsi = 1
                    self.runStarted = 1
                    self.shotsInSec = 0
            
 #                   self.gauss.setParameters([self.histReserve, 6. ,1.])

                else:
                    self.totTime.set(self.shotsInSec) # for subsequent reads, update shot per second display

                    if self.shotsInSec < 19:
                        self.totTime.configure(background = 'red',foreground = 'white')
                    else:
                        self.totTime.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))    

                    self.shotsInSec = 0

#                    if self.shotNum > 0 :
#                        self.gauss.setParameters([self.intenReserve, 6. ,1.])
#                        self.gauss.fit()

        def newState(self, stateData, isCurrent, keyVar=None):
                """Handle new state data.
                """
                #print 'newState: start'
                if not isCurrent:
                        return
                #print 'newState: got here'
                #print 'newState: stateData = ', stateData

                state = stateData[0]
                #print 'newState: state = ', state
                stateName = self.stateDict[state]
                #print 'newState: stateName = ', stateName

                if state != 10:
                    self.laser_powerWdg.configure(background='pink')
                if state == 10:
                    self.laser_powerWdg.configure(background=Tk.Label().cget("background"))
                    
                self.state = state
                self.stateWdg.set(self.state)
        
                # reset all buttons to their nominal appearance
                for i in range(len(self.stateButtArray)):
                    text = self.stateButtArray[i].cget('text')
                    self.stateButtArray[i].configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"),text=string.lower(text))

                # Highlight the button of the current state
                # Warning, this assumes that the button order is the same as the state order...    
                #self.stateButtArray[self.state-1].configure(foreground='red', text=string.upper(self.stateDict[self.state]))
                # Get name of state from dictionary
                # remove None entries from list
                # get entry number of active state
                nameListNoNones = [tok for tok in self.stateButtonList if tok is not None]
                #print 'nameListNoNones = ', nameListNoNones
                buttonNumber = nameListNoNones.index(stateName)
                #print 'buttonNumber = ', buttonNumber
                self.stateButtArray[buttonNumber].configure(foreground='red', text=stateName.upper())

        def newPolyname(self, polynameData, isCurrent, keyVar=None):
                """Handle new polynomial name
                """
                if not isCurrent:
                        return

                if polynameData[0] == 'error':
                    self.polynameWdg.set(polynameData[0])
                    self.polynameWdgMoon.set(polynameData[0])
                    self.polynameWdg.configure(background='red',foreground='red')
                    self.polynameWdgMoon.configure(background='red',foreground='red')
                else:
                    self.polynameWdg.set(polynameData[0])
                    self.polynameWdgMoon.set(polynameData[0])
                    self.polynameWdg.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))
                    self.polynameWdgMoon.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))
            
        def newSpeed(self, motrpsData, isCurrent, keyVar=None):
                """Handle new motrps data.
                """
                if not isCurrent:
                        return

                self.motrpsWdg.set(motrpsData[0])

        def newMirrPhase(self, mirrorphaseData, isCurrent, keyVar=None):
                """Handle new mirrorphase data.
                """
                if not isCurrent:
                        return

                self.mirrorphaseWdg.set(mirrorphaseData[0])

        def newNruns(self, nrunsData, isCurrent, keyVar=None):
                """Handle new nruns data.
                """
                if not isCurrent:
                        return

                print("nrunsData = ", nrunsData)
                nruns=nrunsData[0]
                self.nrunsWdg.set(nruns)
                self.nruns=nruns
                
                if self.state==3 and self.shotNum and self.shotNum < nruns:
                    self.redraw()
                

        def newGatewidth(self, gatewidthData, isCurrent, keyVar=None):
                """Handle new gatewidth data.
                """
                if not isCurrent:
                        return

                if gatewidthData[0] & 0xf0 != self.runfidgw & 0xf0:
                        self.doCmd('apollo','houston set runfidgw=%d' % gatewidthData[0])
                        
                
                self.gateWidth = gatewidthData[0]
                self.gatewidthWdg.set(gatewidthData[0]) 

        def newTdc_target(self, tdc_targetData, isCurrent, keyVar=None):
                """Handle new gatewidth data.
                """
                if not isCurrent:
                        return
                tdc_target = tdc_targetData[0]
                self.tdc_target = tdc_target
                self.tdc_targetWdg.set(tdc_targetData[0])

 #               xlower = -tdc_target
 #               xupper = 4000 - tdc_target

#                self.lun_return_hist.setRange('x',xlower,xupper)

        def newRunfidgw(self, runfidgwData, isCurrent, keyVar=None):
                """Handle new gatewidth data.
                """
                if not isCurrent:
                        return

                if runfidgwData[0] & 0xf0 != self.gateWidth & 0xf0:
                        self.doCmd('apollo','houston set gatewidth=%d' % runfidgwData[0])

                self.runfidgwWdg.set(runfidgwData[0])
#                dat = runfidgwData[0]

                self.runfidgw = runfidgwData[0]

#                xlower = -8100+800*dat
#                xupper = -3100+800*dat

#                self.cc_return_hist.setRange('x',xlower,xupper)

        def newHuntstart(self, huntstartData, isCurrent, keyVar=None):
                """Handle new gatewidth data.
                """
                if not isCurrent:
                        return

                self.huntstartWdg.set(huntstartData[0])

        def newHuntdelta(self, huntdeltaData, isCurrent, keyVar=None):
                """Handle new gatewidth data.
                """
                if not isCurrent:
                        return

                self.huntdeltaWdg.set(huntdeltaData[0])

        def newThunt(self, thuntData, isCurrent, keyVar=None):
                """Handle new gatewidth data.
                """
                if not isCurrent:
                        return

                self.thuntWdg.set(thuntData[0])

        def newDskew(self, dskewData, isCurrent, keyVar=None):
                """Handle new dskew data.
                """
                if not isCurrent:
                        return
    
                self.dskewWdg.set(dskewData[0])

        def newPredskew(self, predskewData, isCurrent, keyVar=None):
                """Handle new dskew data.
                """
                if not isCurrent:
                        return

                if predskewData[0] != self.predSkew:
                        pickledPredskewData = pickle.dumps(('predskew', predskewData[0])) + pickleSep
                        self.try_sending_ROOT(pickledPredskewData)
                        self.predSkew = predskewData[0]
                        self.predskewWdg.set(predskewData[0])
                        if predskewData[0] != self.predskewSlider.get():
                                self.predskewSlider.set(predskewData[0])
                                self.predZero(None)

        def newStarerate(self, starerateData, isCurrent, keyVar=None):
                """Handle new starerate data.
                """
                if not isCurrent:
                        return
    
                self.starerateWdg.set(starerateData[0])

        def newNstares(self, nstaresData, isCurrent, keyVar=None):
                """Handle new nstares data.
                """
                if not isCurrent:
                        return
    
                self.nstaresWdg.set(nstaresData[0])

        def newBinning(self, binningData, isCurrent, keyVar=None):
                """Handle new binning data.
                """
                if not isCurrent:
                        return
    
                self.binningWdg.set(binningData[0])

        def newNdarks(self, ndarksData, isCurrent, keyVar=None):
                """Handle new ndarks data.
                """
                if not isCurrent:
                        return
    
                self.ndarksWdg.set(ndarksData[0])

        def newFlashrate(self, flashrateData, isCurrent, keyVar=None):
                """Handle new flashrate data.
                """
                if not isCurrent:
                        return
    
                self.flashrateWdg.set(flashrateData[0])

        def newFlashcum(self, flashcumData, isCurrent, keyVar=None):
                """Handle new flashcum data.
                """
                if not isCurrent:
                        return
    
                self.flashcumWdg.set(flashcumData[0])

        def newVposx(self, vposxData, isCurrent, keyVar=None):
                """Handle new vposx data.
                """
                if not isCurrent:
                        return

#                if  self.rateRxx > 0.0:
#                    self.rxxRate_all.addRow((self.rxx,self.rxy,self.rateRxx))

                self.rxx = vposxData[0]
                self.rxxcumWdg.set(self.rxx)
                self.rxxCumWdgTune.set(self.rxx)
                self.changeHappened()

#                if self.runStarted == 1:
#                    zmax = max(self.rxxRate_all.getColumn(2))
#                    self.rxxRate_disp.setRange('z',0.,zmax)

        def newVposy(self, vposyData, isCurrent, keyVar=None):
                """Handle new vposy data.
                """
                if not isCurrent:
                        return
                self.rxy = vposyData[0]
                self.rxycumWdg.set(self.rxy)
                self.rxyCumWdgTune.set(self.rxy)
                self.changeHappened()

                self.shotsRxx = 0
                self.lunNumRxx = 0
                self.lunRateRxx = 0
                self.lunRegNumRxx = 0
                self.lunRegRateRxx = 0
                self.rateRxx = 0.0
#                self.rxxRate.clear()

#                if self.runStarted == 1:
#                    zmax = max(self.rxxRate_all.getColumn(2))
#                    self.rxxRate_disp.setRange('z',0.,zmax)
                
        def newVtargetx(self, vtargetxData, isCurrent, keyVar=None):
                """Handle new vtagetx data.
                """
                if not isCurrent:
                        return

                self.rxxTarg = vtargetxData[0]
                self.rxxTargWdg.set(self.rxxTarg)
                self.rxxTargWdgMoon.set(self.rxxTarg)
                self.rxxTargWdgTune.set(self.rxxTarg)

        def newVtargety(self, vtargetyData, isCurrent, keyVar=None):
                """Handle new vtargety data.
                """
                if not isCurrent:
                        return
    
                self.rxyTarg = vtargetyData[0]
                self.rxyTargWdg.set(self.rxyTarg)
                self.rxyTargWdgMoon.set(self.rxyTarg)
                self.rxyTargWdgTune.set(self.rxyTarg)

            # update display on laser tuning panel
            
                dtr = np.pi/180.
                ccdx = np.cos(dtr*21.3)*self.rxxTarg + np.sin(dtr*21.3)*self.rxyTarg
                ccdy = -np.sin(dtr*21.3)*self.rxxTarg + np.cos(dtr*21.3)*self.rxyTarg
                oval_x = self.midx+ccdx*10.0
                oval_y = self.midy+ccdy*10.0
                self.orient_canv.coords(self.voff_mark,oval_x-4,oval_y-4,oval_x+4,oval_y+4)

        def newFakertt(self, fakerttData, isCurrent, keyVar=None):
                """Handle new fakertt data.
                """
                if not isCurrent:
                        return
    
                self.fakerttWdg.set(fakerttData[0])

        def newBlockRemaining(self, blockremainingData, isCurrent, keyVar=None):
                """Handle space command blockage data
                """

                if not isCurrent:
                        return
                
                if blockremainingData[0] >= 10:
                    if self.wdgFlag == 0:
                        self.wdgFlag = 1
                        self.afscWdg = Tk.Label(master=self.spaceFrame)
                        self.afscWdg.pack()
                        self.afscWdg.configure(image=self.AFSCImage)
                    self.spaceAlertWdg.configure(background = 'red')
                    self.spaceAlertWdg.configure(text='Time remaining in blockage: %d s' % blockremainingData[0])

                    a=self.component(' Main -tab')
                    a.configure(background='blue',foreground='white')

                if blockremainingData[0] < 10:
                    if self.wdgFlag == 0:
                        self.wdgFlag = 1
                        self.afscWdg = Tk.Label(master=self.spaceFrame)
                        self.afscWdg.pack()
                        self.afscWdg.configure(image=self.AFSCImage)
                    self.spaceAlertWdg.configure(background = 'yellow')
                    self.spaceAlertWdg.configure(text='Time remaining in blockage: %d s' % blockremainingData[0])

                    a=self.component(' Main -tab')
                    a.configure(background='blue',foreground='white')
                    
                if blockremainingData[0] < 3:
                    if self.wdgFlag == 1:
                        self.afscWdg.destroy()
                        self.wdgFlag = 0
                    self.spaceAlertWdg.configure(background = 'green')
                    self.spaceAlertWdg.configure(text='No Blockage')

                    a=self.component(' Main -tab')
                    a.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))

        def newReleaseRemaining(self, releaseremainingData, isCurrent, keyVar=None):
                """Handle space command release data
                """

                if not isCurrent:
                        return

                if self.wdgFlag == 0:
                        self.spaceAlertWdg.configure(text='Time remaining in release: %d s' % releaseremainingData[0])
        
        def newApdToFpd(self, apdtofpdData, isCurrent, keyVar=None):
                """ Handle new apdtofpd data
                """
                if not isCurrent:
                        print(isCurrent)
                        return
                
                self.chanOffset = []
                chanOffRaw = apdtofpdData
                nGood = 16-chanOffRaw.count(0.0)
                mn = np.add.reduce(chanOffRaw)/nGood

                for i in range(16):
                    if chanOffRaw[i]:
                        self.chanOffset.append(int(round(chanOffRaw[i]-mn)))
                    else:
                        self.chanOffset.append(0)

                pickledApdToFpd = pickle.dumps(('chanoffset',self.chanOffset)) + pickleSep
                self.try_sending_ROOT(pickledApdToFpd)

                print(self.chanOffset)

        def newDphase(self, dphaseData, isCurrent, keyVar=None):
                """ Handle new dphase data
                """
                if not isCurrent:
                        return
                dphase = dphaseData[0]
#                self.dphase_all.addRow((dphase,))
#                self.dphase.addRow((dphase,))
                
        def newDphase_target(self, dphase_targetData, isCurrent, keyVar=None):
                """ Handle new dphase_target data
                """

                if not isCurrent:
                        return

                self.dphase_target = dphase_targetData[0]
                self.dphaseWdg.set(self.dphase_target )

        def newBolopower(self, bolopowerData, isCurrent, keyVar=None):
                """ Handle new dphase_target data
                """

                if not isCurrent:
                        return

                # Update ROOT plot
                #pickledBolopowerData = pickle.dumps(('laser', bolopowerData)) + pickleSep
                #self.try_sending_ROOT(pickledBolopowerData)

                #print "Bolopower Data:", bolopowerData
                
                self.lPowerNum += 1
                self.lPowerNum_list.append(self.lPowerNum)
                
                laser_power = bolopowerData[0]
                self.laserPower.append(laser_power)
                self.laser_powerWdg.set(laser_power)

                ave = np.true_divide(sum(self.laserPower[-20:]), min(len(self.laserPower), 20.))
                self.laserPowerAverage.append(ave)
                self.laser_powerAveWdg.set(ave)

                self.hiWdg.set(max(self.laserPower[-20:]))
                self.loWdg.set(min(self.laserPower[-20:]))

                # Update plot on "Laser Tuning" tab
                self.laserPowerReplot()
###            # Could update the Laser Power graph title to show the average power reading
###            #subplots["laser_power"].mainGraph.SetTitle("Laser Power (20pt avg = %.2f)" % last20average)

 
        def newBolopos(self, boloposData, isCurrent, keyVar=None):
                """ Handle new dphase_target data
                """

                if not isCurrent:
                        return
                
                boloState = boloposData[0]

                if boloState == 1 and self.lockStatus == 0:
                    self.boloInButton.configure(state='disabled')
                    self.boloOutButton.configure(state='normal')
                elif boloState == 0 and self.lockStatus == 0:
                    self.boloOutButton.configure(state='disabled')
                    self.boloInButton.configure(state='normal')
                elif boloState == -1 and self.lockStatus == 0:
                    self.boloOutButton.configure(state='normal')
                    self.boloInButton.configure(state='normal')

        def newPowerstatus(self, powerstatusData, isCurrent, keyVar=None):
                """ Handle new powerstatus data
                """
        
                if not isCurrent:
                        return
                line = powerstatusData[0].split()
                index = int(line[0])

                if index not in self.powerList:

                    self.powerList.append(index)

                    if line[2] == '1':
                        dv=True
                        scolor = 'white'
                            
                    elif line[2] == '0':
                        dv=False
                        scolor = 'white'

                        if index == 13:
                            self.wdg9.updateDisplay('Laser OFF')

                        if index == 6:
                            self.wdg6.updateDisplay('STV OFF')
                            
                    else:
                        dv=False
                        scolor = 'pink'

                    self.nameOn = RO.Wdg.Checkbutton(self.powerFrame,
                        defValue = dv,
                        selectcolor = scolor,
                        )
                    self.pwrNum = RO.Wdg.IntLabel(self.powerFrame, helpText = 'Power code: 0=off;1=on;\
-1=not connected;2=should be off, but can\'t tell;3=should be on, but can\'t tell;4=forced off;\
5=forced on;6=forced off, but can\'t tell;7=forced on, but can\'t tell')
                    self.pwrNum.set(int(line[2]))
                    
                    self.pwrWdgDict[index] = [self.nameOn,self.pwrNum]
                    self.pwrWdgDict[index][0].bind('<ButtonRelease-1>',self.FuncCall(self.setPower,var=index))
                    self.apolloModel.powerstatus.addROWdg(self.pwrWdgDict[index][0],setDefault=True)
                    self.gr_power.gridWdg('%s %d' % (line[1],index),self.nameOn,self.pwrNum)

                if index in self.powerList:

                    if line[2] == '1':
                        dv=True
                            
                    elif line[2] == '0':
                        dv=False
                        
                        if index == 13:
                            self.wdg9.updateDisplay('Laser OFF')

                        if index == 6:
                            self.wdg6.updateDisplay('STV OFF')
                            
                    else:
                        dv=False

                    self.pwrWdgDict[index][0].set(dv)
                    self.pwrWdgDict[index][1].set(int(line[2]))

        def newPowerstate(self, powerstateData, isCurrent, keyVar=None):
                """ Handle new powerstatus data
                """

                if not isCurrent:
                        return

                for i in range(25):
                    
                    if i in self.powerList:

                        if powerstateData[i] == 0:
                            dv=False
                        elif powerstateData[i] == 1:
                            dv=True
                        else:
                            self.pwrWdgDict[i][0].configure(selectcolor='pink')

                        self.pwrWdgDict[i][0].set(dv)

                        self.pwrWdgDict[i][1].set(powerstateData[i])

                if powerstateData[13] == 0:
                    self.wdg9.updateDisplay('Laser OFF')

                if powerstateData[6] == 0:
                    self.wdg6.updateDisplay('STV OFF')

        def newStatusline(self, statuslineData, isCurrent, keyVar=None):
                """ Handle new statusline data
                """

                if not isCurrent: 
                        return

                self.statusbar.setMsg("Houston status: " + statuslineData[0],isTemp = False)

        def newDatafile(self, datafileData, isCurrent, keyVar=None):
                """ Handle new datafile data
                """

                if not isCurrent: 
                        return

                self.datafileWdg.set(datafileData[0])

        def newLogfile(self, logfileData, isCurrent, keyVar=None):
                """ Handle new logfile data
                """

                if not isCurrent: 
                        return

                self.logfileWdg.set(logfileData[0])

        def newLas_display(self, las_displayData, isCurrent, keyVar=None):
                """ Handle new laser display
                """

                if not isCurrent: 
                        return

                parts = las_displayData[0].split(':')
                self.wdg9.updateDisplay(parts[0]+'\n'+parts[1])
                
                LEDList = [self.wdg9.chargeLED,self.wdg9.eocLED,self.wdg9.shutterLED,self.wdg9.qswitchLED]
                for i in range(4):
                    if (parts[2][i]=='R') or (parts[2][i]=='G'):
                        # led is DC on
                        self.wdg9.cc.itemconfigure(LEDList[i], fill=self.wdg9.LED_ON[i])
                        # turn off border
                        self.wdg9.cc.itemconfigure(LEDList[i], width='1')
                        self.wdg9.cc.itemconfigure(LEDList[i], outline='black')
                    elif (parts[2][i]=='o') or (parts[2][i]=='r') or (parts[2][i]=='g'):
                        # led is flashing
                        self.wdg9.cc.itemconfigure(LEDList[i], fill=self.wdg9.LED_ON[i])
                        self.wdg9.cc.itemconfigure(LEDList[i], width='5')
                        self.wdg9.cc.itemconfigure(LEDList[i], outline='white')
                    elif (parts[2][i]=='-'):
                        # led is DC off
                        self.wdg9.cc.itemconfigure(LEDList[i], fill=self.wdg9.LED_OFF)
                        # turn off border
                        self.wdg9.cc.itemconfigure(LEDList[i], width='0')
                    else:
                        # we don't know the state (could be '.')
                        self.wdg9.cc.itemconfigure(LEDList[i], fill=self.wdg9.LED_OFF)
                        # turn off border
                        self.wdg9.cc.itemconfigure(LEDList[i], width='0')

        def newStv_display(self, stv_displayData, isCurrent, keyVar=None):
                """ Handle new laser display
                """

                if not isCurrent: 
                        return

                parts = str(stv_displayData[0]).split(':')

                if len(parts[0]) != 0:
                    self.wdg6.updateDisplay(parts[0]+'\n'+parts[1])
                else:
                    self.wdg6.updateDisplay(' ' +'\n'+' ')

        def newText(self, textData, isCurrent, keyVar=None):
                """ Handle new error text
                """
                    
                if not isCurrent: 
                        return

                timeStr = time.strftime("%H:%M:%S", time.gmtime())

                self.excLog.addOutput(timeStr + "     " + textData[0] + "\n",category="Error")
                self.cmdRepLog.addOutput(timeStr + "       " + textData[0] + "\n",category="Error")

        def newG(self, gData, isCurrent, keyVar=None):
                """ Handle new error text
                """
                    
                if not isCurrent: 
                        return

                timeStr = time.strftime("%H:%M:%S", time.gmtime())

                #self.excLog.addOutput(timeStr + "     " + gData[0] + "\n",category="Error")
                #self.cmdRepLog.addOutput(timeStr + "       " + gData[0] + "\n",category="Error")

        def newI(self, iData, isCurrent, keyVar=None):
                """ Handle new information text
                """
                    
                if not isCurrent: 
                        return

                infoStr = iData[0]

                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                self.cmdRepLog.addOutput(timeStr + "       " + infoStr + "\n")
                #self.cmdRepLog.addOutput(timeStr + "       " + iData[0] + "\n")

                oldAcsState = self.acsLsbState
                if infoStr == 'ACS command done':
                        self.acsLsbState = self.ACS_LSB_STATE_IDLE
                if infoStr == 'ACS command queued':
                        self.acsLsbState = self.ACS_LSB_STATE_BUSY
                if infoStr.find('ACS command failed') > -1:   # "ACS command failed for command %s. Error: %s\"\n"
                        self.acsLsbState = self.ACS_LSB_STATE_ERROR
                if self.acsLsbState != oldAcsState:
                        # update "LED" status on ACS tab.
                        self.acsLsbStateLEDCanvas.itemconfigure(self.acsLsbStateLED, fill=self.acsLsbStateLEDColors[self.acsLsbState])

        def newH(self, hData, isCurrent, keyVar=None):
                """ Handle new help text
                """
                    
                if not isCurrent: 
                        return

                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                self.cmdRepLog.addOutput(timeStr + "       " + hData[0] + "\n")

        def newOscVoltR(self, OscVoltRData, isCurrent, keyVar=None):
                """ Handle new oscvolt_r data
                """

                if not isCurrent:
                        return
                
                self.oscVoltWdg.set(OscVoltRData[0])
                # plotting handled in cmdText instead
                #self.laserPowerPlotNewOscVolt()

        #def newLaserShgRotation(self, SHGRotationData, isCurrent, keyVar=None):
        #        """ Handle new FIXME data
        #        """
        #        if not isCurrent:
        #                return
        #
        #        shgRotDirection = SHGRotationData[0]  # should be 'cw' or 'ccw'
        #        self.laserPowerPlotNewShgRotation(dir=shgRotDirection)

                
        def newAmpdelay(self, AmpdelayData, isCurrent, keyVar=None):
                """ Handle new ampdelay data
                """

                if not isCurrent:
                        return
                
                self.ampdelWdg.set(AmpdelayData[0])

        def newAlarms(self, alarmsData, isCurrent, keyVar=None):
                """ Handle new alarms text
                """
                    
                if not isCurrent: 
                        return

                timeStr = time.strftime("%H:%M:%S", time.gmtime())

                state = eval(alarmsData[0])

                self.alarmsWdg.set(alarmsData[0])

                if state != 0:
                    self.alarmState = True
                    a=self.component('Alarms-tab')
                    a.configure(background='pink',foreground='white')
                    #self.excLog.addOutput(timeStr + "     " + 'alarms = '+ alarmsData[0] + "\n",category="Error")
                    #self.cmdRepLog.addOutput(timeStr + "       " + 'alarms = '+ alarmsData[0] + "\n",category="Error")
                elif state == 0:
                    self.alarmState = False
                    a=self.component('Alarms-tab')
                    a.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))

        def newAlarms_unack(self, alarms_unackData, isCurrent, keyVar=None):
                """ Handle new alarms_unack text
                """
                    
                if not isCurrent: 
                        return

                timeStr = time.strftime("%H:%M:%S", time.gmtime())

                state = eval(alarms_unackData[0])

                self.alarms_unackWdg.set(alarms_unackData[0])

                if state != 0:
                    a=self.component('Alarms-tab')
                    a.configure(background='red',foreground='white')
                    #self.excLog.addOutput(timeStr + "     " + 'alarms_unack = ' + alarms_unackData[0] + "\n",category="Error")
                    #self.cmdRepLog.addOutput(timeStr + "       " + 'alarms_unack = ' + alarms_unackData[0] + "\n",category="Error")
                elif state == 0:
                    if self.alarmState:
                        a=self.component('Alarms-tab')
                        a.configure(background='pink',foreground='white')
                    else:
                        a=self.component('Alarms-tab')
                        a.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))
                        
        def newCmdr(self,cmdrData, isCurrent, keyVar=None):
                """ Handle new command data
                """
                    
                if not isCurrent: 
                        return

                self.cmdr = cmdrData[0]

        def newCmdrMID(self,cmdrMIDData, isCurrent, keyVar=None):
                """ Handle new command data
                """
                    
                if not isCurrent: 
                        return

                self.cmdrMID = str(cmdrMIDData[0])

        def newCmdActor(self,cmdActorData, isCurrent, keyVar=None):
                """ Handle new command data
                """
                    
                if not isCurrent: 
                        return

                self.cmdActor = cmdActorData[0]

        def newCmdText(self,cmdTextData, isCurrent, keyVar=None):
                """ Handle new command data
                """
                #print 'newCmdText()'
                
                if not isCurrent: 
                        return

                self.cmdText = cmdTextData[0]
                print('newCmdText():    cmdText = ', self.cmdText)
                
                checkID = self.cmdr[0:4]
                #print '    checkID = ', checkID
                #print '  self.cmdr = ', self.cmdr
                
                invalidForms = ['houston set axePos','houston set airtem','houston set pressu','houston set humidi',
                                'houston set guideO','houston set boreOf']
                if self.cmdText[0:18] in invalidForms:
                    return


                # check for Leopard Laser SHG rotation commands:
                #   cmdText =  houston laser ccw
                #   cmdText =  houston laser cw
                # and laser oscvolt changes:
                #   cmdText = houston laser oscvolt up 
                #   cmdText = houston laser oscvolt up30 
                #   cmdText = houston laser oscvolt down 
                #   cmdText = houston laser oscvolt down 30
                if self.cmdText == 'houston laser ccw':
                        self.laserPowerPlotNewShgRotation(rotationdir='ccw')
                if self.cmdText == 'houston laser cw':
                        self.laserPowerPlotNewShgRotation(rotationdir='cw')
                if self.cmdText.find('houston laser oscvolt up') > -1:
                        self.laserPowerPlotNewOscVolt(direction='up')
                if self.cmdText.find('houston laser oscvolt down') > -1:
                        self.laserPowerPlotNewOscVolt(direction='down')

                me = self.tuiModel.getCmdr()
                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                #print '    me = ', me

                # Reset plots and stats, no matter WHO issued the run/fidlun/fakerun command
                resetForms = ['houston run', 'houston fidlun', 'houston fakerun']
                # guessing state 13 = 'houston fakerun'
                if self.cmdText in resetForms:
                        #print '     will call resetCounters()'
                        self.resetCounters()

                # Filter out APOLLO-related commands to echo to the Main ATUI tab
                if checkID == 'ZA01' or self.cmdr[0:17].upper() == 'APO.RUSSET-LAPTOP': 
                        #print '    inside checkID'
                        if self.cmdr != me and self.cmdActor != 'keys':
                                self.cmdRepLog.addOutput('%s %s to %s %s %s \n' % (timeStr,self.cmdr,self.cmdActor.upper(),str(self.cmdrMID),self.cmdText))

        #-----------------------------------------------------------
        # Receiving ACS-related information from houston
        #-----------------------------------------------------------
        def newPulsePer(self, data, isCurrent, keyVar=None):
                """Called when the pulseper param is reported by housctl
                """
                #print 'newPulsePer():'
                #print '  data      = ', data
                #print '  isCurrent = ', isCurrent
                #print '  keyVar    = ', keyVar
                #print '\n'
                if not isCurrent:
                        return
                # Then act on the new info
                pulsepervalue = data[0]
                self.acmPulsePer.set(pulsepervalue, isCurrent=isCurrent)

        def newPulseGW(self, data, isCurrent, keyVar=None):
                """Called when the pulsegw param is reported by housctl
                """
                #print 'newPulseGW():'
                #print '  data      = ', data
                #print '  isCurrent = ', isCurrent
                #print '  keyVar    = ', keyVar
                #print '\n'
                if not isCurrent:
                        return
                # Then act on the new info
                pulsegwvalue = data[0]
                self.acmPulseGW.set(pulsegwvalue, isCurrent=isCurrent)

        def newACSDACExtremizeStatus(self, data, isCurrent, keyVar=None):
                """Called when a DAC extremize operation has begun (1) or ended (0)
                """
                #print 'newACSDAExtremizeStatus():'
                #print '  data      = ', data
                #print '  isCurrent = ', isCurrent
                #print '  keyVar    = ', keyVar
                #print '\n'
                if not isCurrent:
                        return
                if data[0] == 1:   # new sweep has started
                        # reset extremum values
                        print("DAC extremize started")
                        self.acsDACExtremizePostPPGRNVals = []
                        self.acsDACExtremizeDACVals = []
                        self.acsSweepAxes.cla()  # clear the plot axes
                elif data[0] == 0: # sweep has ended
                        print("DAC extremize ended")
                        # Fit parabola and plot the data in the Tkinter window
                        #
                        # fit a parabola
                        polyOrder = 2
                        print('acsDacExtremizePostPPGRNVals', self.acsDACExtremizePostPPGRNVals)
                        fit = np.poly1d(np.polyfit(self.acsDACExtremizeDACVals, self.acsDACExtremizePostPPGRNVals, polyOrder))
                        print('fit', fit)
                        bias_point = int(-fit[1]/(2*fit[2]))
                        xfit = np.linspace(min(self.acsDACExtremizeDACVals), max(self.acsDACExtremizeDACVals), num=50)
                        self.acsDACOptimumVal = bias_point
                        #
                        # Plot the data and fit parabola
                        can = self.acsSweepCanvas
                        ax  = self.acsSweepAxes
                        #fig = self.acsSweepFig
                        #
                        ax.plot(self.acsDACExtremizeDACVals, self.acsDACExtremizePostPPGRNVals, 'ko')
                        ax.plot(xfit, fit(xfit), 'k--')
                        ax.plot(bias_point, fit(bias_point), 'r*')  # FIXME: should be the ACTUAL DAC value chosen after the fit.
                        can.show()

                        # Do an ADC read after a DAC Extremize
                        self.acsADCRead()
                        
        def newACSDACExtremize(self, data, isCurrent, keyVar=None):
                """Handle new ACS DAC Extremize results (DAC, PD0, PD1, PD2, PD3)
                """
                #print 'newACSDAExtremize():'
                #print '  data      = ', data
                #print '  isCurrent = ', isCurrent
                #print '  keyVar    = ', keyVar
                #print '\n'
                if not isCurrent:
                        return
                # Then act on the new info
                dacVal = data[0]
                IRPost = data[2]
                grnVal = data[4]
                self.acsDACExtremizeDACVals.append(dacVal)
                #self.acsDACExtremizePostPPGRNVals.append(IRPost)
                self.acsDACExtremizePostPPGRNVals.append(grnVal)
                
        def newACSDACSweepStatus(self, data, isCurrent, keyVar=None):
                #print 'newACSDASweepStatus():'
                #print '  data      = ', data
                #print '  isCurrent = ', isCurrent
                #print '  keyVar    = ', keyVar
                #print '\n'
                if not isCurrent:
                        return
                if data[0] == 1:   # new sweep has started
                        # LOCAL ONLY
                        # Clear ACS Sweep plot (ROOT plot window)
                        #self.acsClearSweepPlot(sweeptype='DAC')

                        # Testing to plot sweep in ATUI tab...
                        print("DAC sweep started")
                        self.acsDACSweepReset()
                        self.acsDACSweepIsStale = False
                        
                elif data[0] == 0: # sweep has ended
                        # FIXME: for some reason, acsDACSweepFit() appears to be called
                        #        even if there is no new sweep.  To avoid the overplotting of stale sweep fit data
                        #        atop an (e.g.) extremize plot, and to avoid the DAC getting incorrectly set to
                        #        a stale sweep minimum value (overwriting the efforts of a more recent extremize run)
                        #        ensure that we don't run acsDACSweepFit() unless the sweep has really just ended.
                        #        UPDATE: this has been fixed... housctl was dumping the keyword that triggered this function to run
                        #                so the whole "sweepIsStale" paradigm (for both DAC and Phase) is unnecessary at this point.
                        if self.acsDACSweepIsStale:
                                return

                        # FIXME: should also replot the sweep data here,
                        #        in case there are fewer points that the update interval

                        # FIXME: add DAC sweep fitting code here
                        print("DAC sweep ended (local plot)")
                        self.acsDACSweepFit()
                        self.acsDACSweepIsStale = True
                        
                        
        def acsDACSweepFit(self):
                print("acsDACSweepFit()")
                print('(Green ADC channel)')
                #print "      self.acsDACSweepIsStale = ", self.acsDACSweepIsStale
                # Fitting function is:  A * {cos[(2*pi/T)*DAC + phi]}^2 + offset
                #      A = amplitude
                #      T = period [DAC counts]
                #    phi = phase
                # offset = DC offset
                guess_ampl   = 0.5*(np.max(self.acsDACSweepGreenVals)-np.min(self.acsDACSweepGreenVals))   #np.sqrt(2)*np.std(self.acsDACSweepGreenVals)
                guess_freq   = 4*1500.0  # DAC counts
                guess_phase  = 1750.0    # DAC value of peak (where cos is maximum)
                guess_offset = 5         # ADC counts
                guessParams = [guess_ampl, guess_freq, guess_phase, guess_offset]
                fit_func = lambda x, p: p[0]*np.power(np.cos((2*np.pi/p[1])*(x+p[2])),4) + p[3]
                residual_func = lambda p: fit_func(self.acsDACSweepDACVals, p) - self.acsDACSweepGreenVals
                fitParams = leastsq(residual_func, guessParams)[0]
                #fitAmpl, fitFreq, fitPhase, fitOffset = leastsq(residual_func, guessParams)[0]
                yFit = fit_func(self.acsDACSweepDACVals, fitParams)
                #print yFit
                # Compute the DAC values of the minima 
                dacOfMins = [0.25*fitParams[1]-fitParams[2], 0.75*fitParams[1]-fitParams[2]]

                # FIXME: Determine which minimum to use
                self.acsDACOptimumVal = int(dacOfMins[1])

                # log the fit results to housctl log
                self.doLineCmd('rem ACS_DACSWEEP_FIT_PARAMS: %6.1f,%6.1f,%6.1f,%4d' % (fitParams[0], fitParams[1], fitParams[2], fitParams[3]))
                self.doLineCmd('rem ACS_DACSWEEP_DAC_OF_MIN: %4d' % (self.acsDACOptimumVal))

                # Display the best-fit curve
                self.acsSweepAxes.plot(self.acsDACSweepDACVals, yFit, 'k--')
                # and identify the location of the minima using vertical lines
                for xx in dacOfMins:
                        self.acsSweepAxes.axvline(xx, linestyle=':')
                self.acsSweepCanvas.show()

                # Automatically set the DAC for minimum transfer
                dacPad = 400  # leave enough space to run an Extremize Bias,
                              # which takes 2 x 200step jumps on either end of nominal setting
                if (self.acsDACOptimumVal > (0+dacPad)) and (self.acsDACOptimumVal < (4095-dacPad)):
                        # no matter the caller, by now, "val_dac" holds the desired DAC setting
                        cmd = 'acs dac %d' % (self.acsDACOptimumVal)
                        print(cmd)
                        self.doLineCmd(cmd)

                # FIXME: could add a call to "EXTREMIZE" here as well...

                
        def newACSLaserLockState(self, data, isCurrent, keyVar=None):
                if not isCurrent:
                        return
                print('newACSLaserLockState():')
                print('  data      = ', data)
                print('  isCurrent = ', isCurrent)
                print('  keyVar    = ', keyVar)
                print('\n')

                # Update Laser Lock checkbox state
                self.acsPicoFYbLock.setBool(data[0], isCurrent=isCurrent)

        def newACSLaserDC(self, data, isCurrent, keyVar=None):
                if not isCurrent:
                        return
                print('newACSLaserDC():')
                print('  data      = ', data)
                print('  isCurrent = ', isCurrent)
                print('  keyVar    = ', keyVar)
                print('\n')

                # Update Laser Lock checkbox state
                self.acsPicoFYbDCPowerButton.setBool(data[0], isCurrent=isCurrent)
                # Update the "LED" indicator color
                if data[0] == 1:
                        LED_Color = self.acsLaserPowerLED_ON
                elif data[0] == 0:
                        LED_Color = self.acsLaserPowerLED_OFF
                else:
                        print("WARNING:  LED COLOR NOT SET because data[0] not recognized")
                        print("data[0] = ", data[0])
                        return
                print("setting LED color to: ", LED_Color)
                self.acsLaserPowerLEDCanvas.itemconfigure(self.acsLaserDCPowerLED, fill=LED_Color)

        def newACSPhaseSweepStatus(self, data, isCurrent, keyVar=None):
                if not isCurrent:
                        return
                print('newACSPhaseSweepStatus():')
                print('  data      = ', data)
                print('  isCurrent = ', isCurrent)
                print('  keyVar    = ', keyVar)
                print('\n')

                if data[0] == 1:   # new sweep has started
                        # Clear ACS Sweep plot
                        #self.acsClearSweepPlot(sweeptype='PHASE')
                        # Clear the plot in the ACS tab of TUI and reset arrays
                        self.acsPhaseSweepReset()
                        self.acsPhaseSweepIsStale = False
                elif data[0] == 0: # sweep has ended
                        if self.acsPhaseSweepIsStale:
                                return
                        self.acsPhaseSweepIsStale = True

        def newACSPhaseSweepVal(self, acsPhaseSweepValData, isCurrent, keyVar=None):
                """Handle new ACS phase scan results (phase, PD0, PD1, PD0/PD1)
                """
                if not isCurrent:
                        return
                print('newACSPhaseSweepVal():')
                print('  acsPhaseSweepValData = ', acsPhaseSweepValData)
                print('  isCurrent         = ', isCurrent)
                print('  keyVar            = ', keyVar)
                
                # Then act on the new info
                self.acsPhaseSweepPhaseVals.append(acsPhaseSweepValData[0])
                self.acsPhaseSweepPostPPIRVals.append(acsPhaseSweepValData[2])
                self.acsPhaseSweepReplot()
                
                # DEFUNCT:  Send to ROOT plots 
                #pickledData = pickle.dumps(('ACS_PHASE_SCAN', acsPhaseSweepValData[0],acsPhaseSweepValData[1],acsPhaseSweepValData[2],acsPhaseSweepValData[3])) + pickleSep
                #self.try_sending_ROOT(pickledData)

                
        def newACSDACScanVal(self, acsDACScanValData, isCurrent, keyVar=None):
                """Handle new ACS DAC scan results (DAC, PD0, PD1, PD2, PD3, PD0/PD1)
                """
                if not isCurrent:
                        return
                print('newACSDACScanVal():')
                print('  acsDACScanValData = ', acsDACScanValData)
                print('  isCurrent         = ', isCurrent)
                print('  keyVar            = ', keyVar)

                # update the "local" plot and values
                self.acsDACSweepPostPPIRVals.append(acsDACScanValData[2])
                self.acsDACSweepGreenVals.append(acsDACScanValData[4])
                self.acsDACSweepDACVals.append(acsDACScanValData[0])
                self.acsDACSweepReplot()

                # LOCAL ONLY
                # Also, send data to ROOT plots
                #pickledData = pickle.dumps(('ACS_DAC_SCAN', acsDACScanValData[0], acsDACScanValData[1], acsDACScanValData[2], acsDACScanValData[3], acsDACScanValData[4])) + pickleSep
                #self.try_sending_ROOT(pickledData)

        # this fxn seems to be redundant with newACSDACSweepStatus() (when status=0, the scan is done)
        #def newACSDACScanDone(self, acsDACScanDoneData, isCurrent, keyVar=None):
                ## send text to ROOT window
                #pickledDACScanDoneData = pickle.dumps(('dacsweepfit')) + pickleSep
                #self.try_sending_ROOT(pickledDACScanDoneData)
                

        def newACSDelayVal(self, acsDelayValData, isCurrent, keyVar=None):
                """Handle new ACS delay/width data (FID0, FID1, LUN0, LUN1)
                """
                if not isCurrent:
                        return
                print('newACSDelayVal():')
                print('  acsDelayValData = ', acsDelayValData)
                print('  isCurrent       = ', isCurrent)
                print('  keyVar          = ', keyVar)

                # Then act on the new info
                for ii in range(len(self.acsLSBDelays)):
                        self.acsLSBDelays[ii].set(acsDelayValData[ii], isCurrent=isCurrent)
                
        def newACSDACVal(self, acsDACValData, isCurrent, keyVar=None):
                """Handle new ACS DAC data (DC bias for the modulator).
                """
                if not isCurrent:
                        return

                print('newACSDACVal():')
                print('  acsDACValData = ', acsDACValData)
                print('  isCurrent     = ', isCurrent)
                print('  keyVar        = ', keyVar)

                # convert DAC value to volts
                val_volts = acsDACValData[0]*10.0/4095.
                print('  val_volts     = ', val_volts)
                
                # Then act on the new info
                self.acsModulatorBias.set(val_volts)  # isCurrent=True by default
                self.acsModulatorBiasDAC.set(acsDACValData[0])  # isCurrent=True by default


        def newACSADC(self, acsADCData, isCurrent, keyVar=None):
                """Handle new ACS ADC data (photodiode average power).
                """
                if not isCurrent:
                        return

                print('newACSADC():')
                print('  acsADCData = ', acsADCData)
                print('  isCurrent  = ', isCurrent)
                print('  keyVar     = ', keyVar)

                # Then act on the new info
                for ii in range(len(self.acsADCs)):
                        self.acsADCs[ii].set(acsADCData[ii])

        def newACSLunEn(self, acsLunEnData, isCurrent, keyVar=None):
                """Handle ACS LUN_EN status report from housctl
                """
                if not isCurrent:
                        return
                print('newACSLunEn():')
                print('  acsLunEnData = ', acsLunEnData)
                print('  isCurrent    = ', isCurrent)
                print('  keyVar       = ', keyVar)
                print('\n')
                # Update LUN_EN checkbox state based on acsLunEnData
                self.acsLunEnable.setBool(acsLunEnData[0], isCurrent=isCurrent)
                # Update the ACS filtering status
                print("self.ACS_filter_on = ", self.ACS_filter_on)
                newACSFilterState = True if acsLunEnData[0] else False
                #print "newACSFilterState = ", newACSFilterState
                self.ACS_filter_set(newACSFilterState)

                
        def newACSFidEn(self, acsFidEnData, isCurrent, keyVar=None):
                """Handle ACS FID_EN status report from housctl
                """
                if not isCurrent:
                        return
                print('newACSFidEn():')
                print('  acsFidEnData = ', acsFidEnData)
                print('  isCurrent    = ', isCurrent)
                print('  keyVar       = ', keyVar)
                print('\n')
                # Update FID_EN checkbox state based on value from housctl
                self.acsFidEnable.setBool(acsFidEnData[0], isCurrent=isCurrent)

                

        #-----------------------------------------------------------------------
                                
## Various Function definitions for buffer/clear controls and entry boxes, etc.

        def clearTab(self):
                self.doLineCmd('set alarms_unack=0')
                a=self.component('Alarms-tab')
                a.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))
                
        def doCmd(self,act,cmd,write=True):

                if write:
                    func=self.callBack
                else:
                    func=None

                cmdVar=RO.KeyVariable.CmdVar (
                        actor = act,
                        cmdStr = cmd,
                        dispatcher = self.dispatcher,
                        callFunc = func,
                        callTypes = RO.KeyVariable.AllTypes
                )

                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                me = self.tuiModel.getCmdr()
                
                if write:
                    self.cmdRepLog.addOutput('%s %s to %s %s %s \n' % (timeStr,me,act.upper(),str(cmdVar.cmdID),cmd))

        def callBack(self,msgType,msgDict,cmdVar):

                endStr = ' '
                
                if msgType in RO.KeyVariable.FailTypes:
                    cat="Error"
                elif msgType == 'w' or msgType == '>':
                    cat="Warning"
                else:
                    cat = "Information"

                if msgType == ':':
                    endStr = ' Finished '
                elif msgType == '>':
                    endStr = ' Queued '

                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                    
                self.cmdRepLog.addOutput(timeStr+endStr+msgDict.get('msgStr')+'\n',category=cat)
            
        def doLineCmd(self,cmd):

                if self.lockStatus:
                    return
                
                self.doCmd('apollo','houston ' + cmd)

        def spotterBlock(self,index):

                if index == 'spotter 1':
                    i = -2
                    s=1
                elif index == 'spotter 2':
                    i = -1
                    s=2

                bg = self.funcButtArray[i].cget('background')
                
                if bg == 'SystemButtonFace':
                    self.funcButtArray[i].configure(background='red',foreground = 'white')
                    self.doCmd('apollo','houston rem spotter %d blockage' %s)
                elif bg == 'red':
                    self.funcButtArray[i].configure(background = Tk.Label().cget('background'),foreground = Tk.Label().cget('foreground'))
                    self.doCmd('apollo','houston rem spotter %d blockage cleared' %s)


        def boreConf(self):

            self.doCmd('apollo','houston rem boresight_confirm="%f %f"' %(self.boreAz,self.boreEl))
        
        def fidSkew(self,evt):

            self.regCenterFid = self.fidskewWdg.get()
            self.lowerFid = self.regCenterFid-self.binForRegFid/2
            self.upperFid = self.regCenterFid+self.binForRegFid/2

            pickledFidskewData = pickle.dumps(('fidskew', self.regCenterFid)) + pickleSep
            self.try_sending_ROOT(pickledFidskewData)
            
#            ntup = self.rep_cc[0].createNTuple()
#            ntup.getColumn(1)
#            fidHeight = max(ntup.getColumn(1))                    
#
#            self.fidRegLower.addRow((self.lowerFid,0))
#            self.fidRegLower.addRow((self.lowerFid,fidHeight))
#                
#            self.fidRegUpper.addRow((self.upperFid,0))
#            self.fidRegUpper.addRow((self.upperFid,fidHeight))
            
        def setPar(self,evt,var):
                """ Set houston parameter"""
                if self.lockStatus: return
                
                wdgDict = {'state': self.stateWdg,'polyname': self.polynameWdg,
                           'motrps': self.motrpsWdg,'mirrorphase': self.mirrorphaseWdg,'nruns': self.nrunsWdg,
                           'gatewidth': self.gatewidthWdg,'tdc_target': self.tdc_targetWdg ,'runfidgw': self.runfidgwWdg,'huntstart': self.huntstartWdg,
                           'huntdelta': self.huntdeltaWdg,'thunt': self.thuntWdg,'dskew': self.dskewWdg,
                           'predskew': self.predskewWdg,'starerate': self.starerateWdg,'nstares': self.nstaresWdg,
                           'binning': self.binningWdg,'ndarks': self.ndarksWdg,'flashrate': self.flashrateWdg,
                           'flashcum': self.flashcumWdg,'fakertt': self.fakerttWdg,'dphase_target': self.dphaseWdg,
                           'alarms_unack': self.alarms_unackWdg, 'pulseper':self.acmPulsePer, 'pulsegw':self.acmPulseGW}

                wdg = wdgDict.get(var)
                val = str(wdg.get())

                self.doCmd('apollo','houston set %s=%s' % (var, val))
                
                self.changeHappened()
                    
        def predZero(self,evt):
                # resets histograms after predskew change in houston control
                #self.setPar(None,var='predskew')
                
                #self.regCenter=0
                #self.lower=-self.binForReg/2
                #self.upper=self.binForReg/2

                self.predSkew1(None)
                self.predSkew2(None)

#                ntup = self.rep_lun[0].createNTuple()
#                ntup.getColumn(1)
#                lunHeight = max(ntup.getColumn(1))                    
#
#                self.lunRegLower.addRow((self.lower,0))
#                self.lunRegLower.addRow((self.lower,lunHeight))
#                
#                self.lunRegUpper.addRow((self.upper,0))
#                self.lunRegUpper.addRow((self.upper,lunHeight))
#
#                xmin=min(self.lunTimeSeries.getColumn(0))
#
#                self.lunRegLowerSeries.addRow((xmin,self.lower))
#                self.lunRegLowerSeries.addRow((self.shotNumLun,self.lower))
#                
#                self.lunRegUpperSeries.addRow((xmin,self.upper))
#                self.lunRegUpperSeries.addRow((self.shotNumLun,self.upper))

        def predSkew1(self,evt):

                #if self.shotNumLun < 2: return
                self.regCenter=self.predskewSlider.get()
                self.lower=self.regCenter-self.binForReg/2
                self.upper=self.regCenter+self.binForReg/2

                pickledPredskewData = pickle.dumps(('predskew', self.regCenter)) + pickleSep
                self.try_sending_ROOT(pickledPredskewData)

                
#                ntup = self.rep_lun[0].createNTuple()
#                ntup.getColumn(1)
#                lunHeight = max(ntup.getColumn(1))
#
#                self.lunRegLower.addRow((self.lower,0))
#                self.lunRegLower.addRow((self.lower,lunHeight))
#                
#                self.lunRegUpper.addRow((self.upper,0))
#                self.lunRegUpper.addRow((self.upper,lunHeight))
#
#                if len(self.lunTimeSeries.getColumn(0)) >0:
#                    xmin=min(self.lunTimeSeries.getColumn(0))
#                else:
#                    xmin=0
#
#                self.lunRegLowerSeries.addRow((xmin,self.lower))
#                self.lunRegLowerSeries.addRow((self.shotNumLun,self.lower))
#                
#                self.lunRegUpperSeries.addRow((xmin,self.upper))
#                self.lunRegUpperSeries.addRow((self.shotNumLun,self.upper))

        def predSkew2(self,evt):
                self.regCenter=self.predskewSlider.get()
                self.lower=self.regCenter-self.binForReg/2
                self.upper=self.regCenter+self.binForReg/2


                pickledPredskewData = pickle.dumps(('predskew', self.regCenter)) + pickleSep
                self.try_sending_ROOT(pickledPredskewData)
                
                self.doLineCmd('set predskew=%d' % self.regCenter)

                #if not self.lockStatus:
                self.predskewSlider.configure(from_ = self.regCenter-400)
                self.predskewSlider.configure(to = self.regCenter+400)
#                self.lunSeriesAll.setRange('y',self.regCenter-480,self.regCenter+480)

#                if not self.lunTimeSeries_all.rows:
#                    shotNum=[1]
#                else:
#                    shotNum = list(self.lunTimeSeries_all.getColumn(0))
#                
#                all = list(self.lunTimeSeries_all.getColumn(1))

                regNum = 0
#                regRecNum = 0
                
 #               for i in range(len(all)):
 #                   if all[i] > self.lower and all[i] < self.upper:
 #                           regNum = regNum+1

 #               regRate = float(regNum)/shotNum[-1]

 #               self.totalLunRegNum = regNum
                
 #               tdcBins = min([self.gateWidth*800 - 2600,4096])
 #               self.yield_est = self.totalLunRegNum-self.binForReg*np.true_divide(self.totalLunNum-self.totalLunRegNum,3900-self.binForReg)

 #               self.lunBackgroundWdg.set(self.yield_est)
                
 #               self.regLun.set(self.totalLunRegNum)
 #               self.regRateLun.set(regRate)

#                self.lun_background_all.clear()
#                self.lun_background.clear()

                for x in self.chanTimesCorHistLun:
                        #                 regNum = 0
                    
                        if x > self.lower and x < self.upper:
                                regNum = regNum + 1
                        else:
                                regNum = regNum
                        
                self.totalLunRegNum = regNum
                        
                self.regRateLun.set(regNum)
                self.regLun.set(regNum)  
                
                rate = np.true_divide(regNum,self.shotNumLun) 
                self.regRateLun.set(rate)           
                
#                    self.lun_background_all.addRow((regNum,))
                     
#                for (var,var_all,var_len,res) in ((self.lun_background,self.lun_background_all,
#                                                   self.lun_background_all.rows,self.rateReserve),):#,

#                    if var_len - res < 0:
#                        var_start = 0
#                        itLen = var_len
#                    else:
#                        var_start = var_len - res
#                        itLen = res 

#                    for j in range(itLen):
#                        var.addRow(var_all.getRow(j + var_start))

#                recRateLun = self.rep_lun_rate[1].getMean('x') #rate for last n shots shown on rate histogram 
#                self.regRateRecLun.set(recRateLun)
                
                self.lunRegNumHere = 0
                self.lunRegRateHere = 0
                self.shotsHere = 0

                self.changeHappened()
                          
        def fidSkew2(self,evt):
                self.regCenterFid = self.fidskewWdg.get()
                self.lowerFid = self.regCenterFid-self.binForRegFid/2
                self.upperFid = self.regCenterFid+self.binForRegFid/2

                pickledFidskewData = pickle.dumps(('fidskew', self.regCenterFid)) + pickleSep
                self.try_sending_ROOT(pickledFidskewData)

#                if not self.fidTimeSeries_all.rows:
#                    shotNum=[1]
#                else:
#                    shotNum = list(self.fidTimeSeries_all.getColumn(0))
#                
#                all = list(self.fidTimeSeries_all.getColumn(1))

                regNum = 0
#                regRecNum = 0
                
                for i in range(len(self.chanTimesCorTot)):
                    for x in self.chanTimesCorTot[i][1:]:
                        if x > self.lowerFid and x < self.upperFid:
                            regNum = regNum+1

                regRate = np.true_divide(float(regNum),self.shotNum)

                self.fidRegNum = regNum
                self.fidRegWdg.set(regNum)
                self.fidRegRateWdg.set(regRate)

 #               for i in range(len(self.fidDat)):
 #                   regNum = 0
 #                   if self.fidDat[i][0] > -1:
 #                       times = self.fidDat[i][:-1]
 #                       for j in range(len(times)):
 #                           if times[j] > self.lowerFid and times[j] < self.upperFid:
 #                               regNum = regNum + 1
 #                   else:
 #                       regNum = 0
                        
#                    self.fid_reg_all.addRow((regNum,))
                     
#                for (var,var_all,var_len,res) in ((self.fid_reg,self.fid_reg_all,
#                                                   self.fid_reg_all.rows,self.rateReserve),):

#                    if var_len - res < 0:
#                        var_start = 0
#                        itLen = var_len
#                    else:
#                        var_start = var_len - res
#                        itLen = res
#
#                    for j in range(itLen):
#                        var.addRow(var_all.getRow(j + var_start))

#                recRate = self.rep_cc_rate[1].getMean('x') #rate for last n shots shown on rate histogram 
#                self.fidRegRateRecWdg.set(recRate)

        def setOff(self,evt,var):
            self.offString.set(float(self.offMagWdg.get())) # get offset magnitude from widget in arcsec
            self.offMag = np.true_divide(float(self.offMagWdg.get()),3600.) #offset increment magnitude in deg
            self.offMagWdg.setIsCurrent(True)

        def setLength(self,evt):
            """ laser power measurement length"""
            self.lpowerTime = self.lpowerTimeWdg.get()
            self.lpowerTimeWdg.setIsCurrent(True)

        def ampDelUp(self):
            """ ampdelay increment"""
            self.ampDelInc = int(self.ampDelIncWdg.get())
            if self.ampDelInc ==0:
                self.doCmd('apollo','houston laser ampdelay up')
            else:
                self.doCmd('apollo','houston laser ampdelay up %d' % self.ampDelInc)

        def setAmpdelay(self,evt):
            """ ampdelay increment"""
            self.ampDelInc = int(self.ampDelIncWdg.get())
            self.ampDelIncWdg.setIsCurrent(True)

        def ampDelDown(self):
            """ ampdelay increment"""
            self.ampDelInc = int(self.ampDelIncWdg.get())
            if self.ampDelInc ==0:
                self.doCmd('apollo','houston laser ampdelay down')
            else:
                self.doCmd('apollo','houston laser ampdelay down %d' % self.ampDelInc)

        def rxxSetOff(self,evt,var):
            self.rxxOffString.set(float(self.rxxOffMagWdg.get())) # get offset magnitude from rxx widget in arcsec
            self.rxxOffMag = np.true_divide(float(self.rxxOffMagWdg.get()),3600.) #rxx offset increment magnitude in deg
            self.rxxOffMagWdg.setIsCurrent(True)

        def rasterSetOff(self,evt,var):
            self.rasterMag = np.true_divide(float(self.rasterMagWdg.get()),3600.) #guide offset increment magnitude in deg
            self.rasterMagWdg.setIsCurrent(True)

        def rasterSetShots(self,evt,var):
            self.rasterShots = self.rasterShotWdg.get() #shots per raster point
            print(self.rasterShots)
            self.rasterShotWdg.setIsCurrent(True)

        def rasterOn(self):

            if self.raster == 1:
                self.raster = 0
                self.rasterOnButton.configure(text = 'Raster Off')
            elif self.raster == 0:
                self.raster = 1
                self.rasterOnButton.configure(text = 'Raster On')

        def checkRaster(self,evt,var):
            if not self.scopeOn.getBool():
                    self.opticsOn.setBool(False)
                    self.beamOn.setBool(False)
                    self.boreOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0
            if not self.opticsOn.getBool():
                    self.scopeOn.setBool(False)
                    self.beamOn.setBool(False)
                    self.boreOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0
            if not self.beamOn.getBool():
                    self.opticsOn.setBool(False)
                    self.scopeOn.setBool(False)
                    self.boreOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0
            if not self.boreOn.getBool():
                    self.opticsOn.setBool(False)
                    self.scopeOn.setBool(False)
                    self.beamOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0

        def checkCoords(self,evt,var):  # check coordinate system for raster
            if not self.nativeOn.getBool():
                    self.apdOn.setBool(False)
                    self.ccdOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0
            if not self.apdOn.getBool():
                    self.nativeOn.setBool(False)
                    self.ccdOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0
            if not self.ccdOn.getBool():
                    self.nativeOn.setBool(False)
                    self.apdOn.setBool(False)
                    self.offx = 0.0
                    self.offy = 0.0

        def setPower(self,evt,var):
            
            if self.lockStatus:
                self.doCmd('apollo','houston power')
                return
            index = var
            if self.pwrWdgDict[index][0].getBool():

                self.doCmd('apollo','houston power %d 0' % index)

            elif not self.pwrWdgDict[index][0].getBool():

                self.doCmd('apollo','houston power %d 1' % index)

        def measPower(self):
                val = int(self.lpowerTime)

                self.doCmd('apollo','houston lpower %d' % val)  

        def offsetGuide(self,var):
                opticsRaster = self.opticsOn.getBool()
                beamRaster = self.beamOn.getBool()
                boreRaster = self.boreOn.getBool()

                nativeCoords = self.nativeOn.getBool()
                apdCoords = self.apdOn.getBool()
                ccdCoords = self.ccdOn.getBool()

                dtr = np.pi/180.

                #coordinate rotation angles

                Y = 22.0*dtr		# fund. angle: RX rel to scope, CCD
                cY = np.cos(Y)
                sY = np.sin(Y)
                W = (90.0 - 53.0)*dtr - 2*Y	# 5 deg: APD rot is 53 
                cW = np.cos(W)
                sW = np.sin(W)
                X = Y - W		# 17 deg; optics moves in APD
                #X = 17.0*dtr
                cX = np.cos(X)
                sX = np.sin(X)
                Z = 2.0*Y		# scope moves in CCD
                cZ = np.cos(Z)
                sZ = np.sin(Z)
                
                if opticsRaster:
                    opticsDict = {'home':(0.,0.),'up':(0.,1.),'down':(0.,-1.),'left':(-1.,0.),'right':(1.,0.),
                                  'upLeft':(-1,1),'upRight':(1,1),'downLeft':(-1,-1),'downRight':(1,-1)} 

                    offDir = opticsDict.get(var)
                    x = offDir[0]*float(self.offMagWdg.get())
                    y = offDir[1]*float(self.offMagWdg.get())
                    
                    if var == 'home':
                        opticsOffx=0.0
                        opticsOffy=0.0
                    else:
                        if nativeCoords == True:
                            opticsOffx = x
                            opticsOffy = y

                        elif apdCoords == True:
                            opticsOffx = (-cX*x+sX*y)
                            opticsOffy = (sX*x+cX*y)

                        elif ccdCoords == True:
                            opticsOffx = (cY*x+sY*y)
                            opticsOffy = (sY*x-cY*y)

                    if opticsOffx != 0.0 or opticsOffy != 0.0:
                        self.doCmd('apollo','houston vnudge %f %f' % (opticsOffx, opticsOffy))

                elif beamRaster:
                    if var == 'home': return

                    opticsDict = {'up':(0.,1.),'down':(0.,-1.),'left':(-1.,0.),'right':(1.,0.),
                                  'upLeft':(-1,1),'upRight':(1,1),
                                  'downLeft':(-1,-1),'downRight':(1,-1)} # motion direction optics
                    

                    offDirOptics = opticsDict.get(var) # offset direction of rxx or rxy, from buttons

                    x = offDirOptics[0]*float(self.offMagWdg.get())
                    y = offDirOptics[1]*float(self.offMagWdg.get())

                    if nativeCoords == True:
                        opticsOffx = x
                        opticsOffy = y

                    elif apdCoords == True:
                        opticsOffx = (-cX*x+sX*y)
                        opticsOffy = (sX*x+cX*y)

                    elif ccdCoords == True:
                        opticsOffx = (cY*x+sY*y)
                        opticsOffy = (sY*x-cY*y)

                    #self.offx = self.altCor*(sY*opticsOffx+cY*opticsOffy)/3600.
                    self.offx = (sY*opticsOffx+cY*opticsOffy)/3600.0
                    self.offy = (-cY*opticsOffx+sY*opticsOffy)/3600.0

                    if opticsOffx != 0.0 or opticsOffy != 0.0:
                        self.doCmd('apollo','houston vnudge %f %f' % (opticsOffx, opticsOffy))

                    if self.offMag != 0.0:
                        if np.sqrt(self.offx**2+self.offy**2) < np.true_divide(0.75,3600):
                                self.doCmd('tcc','offset guide %f,%f' % (self.offx,self.offy))
                        else:
                                self.doCmd('tcc','offset guide %f,%f /computed' % (self.offx,self.offy))
                        #self.doCmd('tcc','offset guide %f,%f' % (self.offx,self.offy))

                elif boreRaster:
                    if var == 'home': return

                    boreDict = {'up':(0.,1.),'down':(0.,-1.),'left':(-1.,0.),'right':(1.,0.),
                                'upLeft':(-1,1),'upRight':(1,1),'downLeft':(-1,-1),'downRight':(1,-1)}
        
                    offDir = boreDict.get(var) # offset direction
                    x = offDir[0]
                    y = offDir[1]

                    if nativeCoords == True:
                        offx = x*self.offMag
                        offy = y*self.offMag

                    elif apdCoords == True:
                        offx = (-cW*x+sW*y)*self.offMag
                        offy = (sW*x+cW*y)*self.offMag

                    elif ccdCoords == True:
                        offx = (cZ*x+sZ*y)*self.offMag
                        offy = (sZ*x-cZ*y)*self.offMag

                    if self.offMag != 0.0:
                        if np.sqrt(offx**2 + offy**2) < np.true_divide(0.75,3600):
                                self.doCmd('tcc','offset boresight %f,%f' % (offx,offy))
                        else:
                                self.doCmd('tcc','offset boresight %f,%f /computed' % (offx,offy)) 
                        #self.doCmd('tcc','offset boresight %f,%f' % (offx,offy))

                else:
                    guideDict = {'home':(0.,0.),'up':(0.,1.),'down':(0.,-1.),'left':(-1,0.),'right':(1,0.),
                             'upLeft':(-1,1),'upRight':(1,1),'downLeft':(-1,-1),
                             'downRight':(1,-1)} 
                    offDir = guideDict.get(var)
                    x = offDir[0]
                    y = offDir[1]
                
                    if var == 'home':
                        if np.sqrt(self.offsetAz**2+self.offsetEl**2) < 0.75:
                                self.doCmd('tcc','offset guide %f,%f /PAbsolute' % (0.0,0.0))
                        else:
                                self.doCmd('tcc','offset guide %f,%f /PAbsolute /computed' % (0.0,0.0))
                        #self.offx=0.0
                        #self.offy=0.0
                        #self.doCmd('tcc','offset guide %f,%f /PAbsolute' % (self.offx,self.offy))
                    else:

                        if nativeCoords == True:
                            self.offx = x*self.offMag
                            self.offy = y*self.offMag

                        elif apdCoords == True:
                            self.offx = (-sW*x-cW*y)*self.offMag  
                            self.offy = (-cW*x+sW*y)*self.offMag
                            
                        elif ccdCoords == True:
                            self.offx = (-sZ*x+cZ*y)*self.offMag  
                            self.offy = (cZ*x+sZ*y)*self.offMag

                        #self.offx*=self.altCor # corrected for Cos(Alt)
                        
                        #self.doCmd('tcc','offset guide %f,%f /PAbsolute' % (self.offx,self.offy))
                        if np.sqrt(self.offx**2+self.offy**2) < np.true_divide(0.75,3600):
                                self.doCmd('tcc','offset guide %f,%f' % (self.offx,self.offy))
                        else:
                                self.doCmd('tcc','offset guide %f,%f /computed' % (self.offx,self.offy))
                                
                self.changeHappened()

        def offsetRxx(self,var):
            rxxOpticsDict = {'home':(0.,0.),'up':(0.,1.),'down':(0.,-1.),'left':(-1.,0.),'right':(1.,0.),
                                  'upLeft':(-1,1),'upRight':(1,1),'downLeft':(-1,-1),'downRight':(1,-1)} 

            rxxOffDir = rxxOpticsDict.get(var)
            
            if var == 'home':
                    rxxOpticsOffx=0.0
                    rxxOpticsOffy=0.0
            else:
                rxxOpticsOffx = rxxOffDir[0]*float(self.rxxOffMagWdg.get())
                rxxOpticsOffy = rxxOffDir[1]*float(self.rxxOffMagWdg.get())
            if rxxOpticsOffx != 0.0 or rxxOpticsOffy !=0:
                self.doCmd('apollo','houston vnudge %f %f' % (rxxOpticsOffx,rxxOpticsOffy))
                
        def chngRegBin(self,evt):
                self.binForReg = self.regWidth.getNum()
                self.lower=self.regCenter-self.binForReg/2
                self.upper=self.regCenter+self.binForReg/2
                self.predSkew2(None)
                self.regWidth.setIsCurrent(True)
                self.changeHappened()

        def chngRegBinFid(self,evt):
                self.binForRegFid = self.regWidthFid.getNum()
                self.regWidthFid.setIsCurrent(True)

        # added by J. Battat
        def chngHitgridBuffer(self, var, evt):
                """ change the length of the buffer for the hitgrid plot """
                print("chngHitgridBuffer()")
                print("  evt = ", evt)
                print("  var = ", var)
                # get the value entered into the textbox (as an integer)
                hitgridBufferLength = int(self.hitGridWindowLength.get())
                print("requested a buffer of ", hitgridBufferLength)
                newHitgridBuffer = pickle.dumps(('hitgrid_buffer', hitgridBufferLength)) + pickleSep
                self.try_sending_ROOT(newHitgridBuffer)
                return
        
        def chngBuffer(self,evt,varlist):
                """ change length of buffer for plots valist should be (label widget, reserve variable, var1_all, var1,
                var2_all, var2, etc.) """
                reserveNew = varlist[0].getNum()
                reserveVar = varlist[1]
                    
                varlist[0].setIsCurrent(True)
                    
                for i in range((len(varlist)-2)/2):

                    allVar = varlist[2*i+2] # e.g. 'self.fid'
                    var_len = allVar.rows

                    circ_var = varlist[2*i+3] 
                    circ_var.clear()
                    circ_var.reserve(reserveNew) 
                
                    if var_len - reserveNew <= 0:
                        var_start = 0
                        itLen = var_len
                    else:
                        var_start = var_len - reserveNew
                        itLen = reserveNew

                    if var_len > 0:
#                        for j in range(itLen):circ_var.addRow(allVar.getRow(j + var_start))
                        self.predSkew1(None)

                if reserveVar == self.rateReserve:
                    self.fidRegRateRecWdg.helpText = 'Registered rate for'+ \
                                                    ' last %d shots - set in ' % reserveNew + \
                                                    '\'Rate Histogram Time Window\' box'
                    self.regRateRecLun.helpText ='Registered rate for'+\
                                                    ' last %d shots - set in ' % reserveNew +\
                                                    '\'Rate Histogram Time Window\' box'

        def changeHappened(self):
            if self.changeState == 0.:
                self.changeState = 2.
            else:
                self.changeState = 0.

# #           self.changes_all.addRow((self.shotNumLun,0.5,(self.changeState-1.)*2000.))
# #           self.changes.addRow((self.shotNumLun,0.5,(self.changeState-1.)*2000.))

        def vMove(self,evt):
            vx = float(self.rxxTargWdg.get())
            vy = float(self.rxyTargWdg.get())
            cmd = 'houston vmove %f %f' % (vx,vy)
            self.doCmd('apollo',cmd)
#
        def vMove2(self,evt):
            vx = float(self.rxxcumWdg.get())
            vy = float(self.rxycumWdg.get())
            cmd = 'houston vmove %f %f' % (vx,vy)
            self.doCmd('apollo',cmd)

        def clear(self, varlist):
            for i in range(len(varlist)):
                varlist[i].clear()

        def laserPowerReplot(self, force=False):
                nUpdate = 1  # number of points to acquire before plot update
                if force or (len(self.lPowerNum_list) % nUpdate) == 0:
                        can = self.laserPowerCanvas
                        ax  = self.laserPowerAxes
                        ax.plot(self.lPowerNum_list, self.laserPower, 'g-')
                        ax.plot(self.lPowerNum_list, self.laserPowerAverage, 'b-')
                        plttitle = 'Avg. power [W] = %4.2f' % (self.laserPowerAverage[-1])
                        ax.set_title(plttitle)
                        ax.set_xlabel("Sample")
                        ax.set_ylabel("Laser Power [W]")
                        can.show()

        def plotArrowOnLaserAxes(self, direction, color):
                # direction = 'up' or 'down'
                #  up =  ^     down =  |
                #        |             |
                #        |             v
                #self.laserPowerAxes.axvline(self.lPowerNum_list[-1],linestyle='--',color=self.laserPowerSHGRotationColor)
                x_data_coord = self.lPowerNum_list[-1]
                dx_data_coord = 0
                if direction.upper() == 'UP':
                        y_axis_coord = 0
                        dy_axis_coord = 1
                else:
                        y_axis_coord = 1
                        dy_axis_coord = -1
                self.laserPowerAxes.arrow(x_data_coord, y_axis_coord, dx_data_coord, dy_axis_coord,
                                          transform=self.laserPowerTrans,
                                          head_width=1.5, length_includes_head=True, 
                                          head_length=0.2,  overhang=0.2,
                                          linestyle='dashed',  # for some reason '--' not a valid linestyle ????
                                          edgecolor=None,
                                          color=color)
                #lineWidth  = 5 # points
                #headWidth  = lineWidth*3 
                #headLength = headWidth*2
                #self.laserPowerAxes.annotate('', 
                #                             xytext=(x_data_coord,y_axis_coord),   # arrow tail
                #                             xy=(x_data_coord, y_axis_coord+dy_axis_coord),      # arrow head
                #                             arrowprops=dict(width=lineWidth, headwidth=headWidth,headlength=headLength,
                #                                             shrink=(0,0))
                #)

        def laserPowerPlotNewOscVolt(self, direction):
                # FIXME: indicate osc volt up/down direction by arrow???
                #self.laserPowerAxes.axvline(self.lPowerNum_list[-1],linestyle=':',color=self.laserPowerOscVoltColor)
                # Want to specify x-coordinate in data coordinates, but y-coordinate in axes coordinates
                # can do this with a "Blended Transformation" in matplotlib
                # see:  https://matplotlib.org/users/transforms_tutorial.html
                #self.laserPowerAxes.arrow(self.lPowerNum_list[-1],0,0,1,transform=mytrans,linestyle=':',color=self.laserPowerOscVoltColor)
                arrowDir = 'up' if direction.upper() == 'UP' else 'down'
                self.plotArrowOnLaserAxes(direction=arrowDir, color=self.laserPowerOscVoltColor)

        def laserPowerPlotNewShgRotation(self, rotationdir):
                # rotationdir is 'cw' or 'ccw'
                arrowDir = 'up' if rotationdir.upper() == 'CW' else 'down'
                self.plotArrowOnLaserAxes(direction=arrowDir, color=self.laserPowerSHGRotationColor)

        def laserPowerClear(self):
                print("laserPowerClear()")
                # Update ROOT-related plot stuff
                #data = pickle.dumps(('clear', 'laser')) + pickleSep
                #self.try_sending_ROOT(data)

                self.laserPowerAxes.cla()  # clear the local plot (on Laser Tuning tab)
                self.laserPowerCanvas.show()
                # FIXME: it doesn't actually clear the plot until the next data comes in
                #self.laserPowerAxes.cla()  # clear the local plot (on Laser Tuning tab)

                self.laserPower = []
                self.lPowerNum = 0
                self.lPowerNum_list = []
                self.laserPowerAverage = []

                self.laser_powerWdg.set(0.00)   # laser power stuff
                self.laser_powerAveWdg.set(0.00)
                self.loWdg.set(0.00)
                self.hiWdg.set(0.00)

#
        def setBackground(self, evt, var):
            var.setIsCurrent(False)

        def setCurrent(self, evt, var):
            var.setIsCurrent(True)
#
        def replay(self, evt):

                from . import TestData

                self.resetCounters()
                dataDir=pathStuff.dataDir()
                replayFile = self.replayWdg.get()
                replayStart = self.replayStartWdg.get()
                length = self.replayLengthWdg.get()
                if replayStart == 'None':
                    TestData.dispatchFile(dataDir+replayFile,None,length)
                else:
                    TestData.dispatchFile(dataDir+replayFile,replayStart,length)
#
        def pop(self, evt, var):
            switch=self.darkWdgDict[var].getBool()
            pos = self.chanMap.index(var)

            if switch and pos not in self.omitTDCChan:
                 self.omitTDCChan.append(pos)

            if not switch and pos in self.omitTDCChan:
                 self.omitTDCChan.remove(pos)

            print(self.omitTDCChan)
        
        def reg(self):
            if self.hitgridReg == False:
                self.hitgridReg = True
##                self.lun_hitgrid.clear()
##                self.lun_hitgrid_all.clear()
                self.regButton.configure(text = 'Now: Reg')
            elif self.hitgridReg == True:
                self.hitgridReg = False
##                self.lun_hitgrid.clear()
##                self.lun_hitgrid_all.clear()
                self.regButton.configure(text = 'Now: All')
#
        def lock(self):
                if self.lockStatus:
                    self.lockStatus = False
                    self.wdg6.state = 1
                    self.wdg9.state = 1
                    #self.wdg2.go_But.configure(state='normal') # no longer used
                    self.wdg2.new_go_But.configure(state='normal')
                    
                    self.wdg6.snapButt.configure(state='normal')
                    self.wdg6.saveButt.configure(state='normal')
                    self.wdg6.cursorButt.configure(state='normal')

                    self.wdg9.b2.configure(state='normal')
                    self.wdg9.b3.configure(state='normal')
                    self.wdg9.b4.configure(state='normal')

                    self.boloInButton.configure(state='normal')
                    self.boloOutButton.configure(state='normal')

                    a=self.component(' Main -tab')
                    a.configure(text='Active')
                    
                    self.lockButton.configure(text='Houston:\nActive Control',background='green')#,foreground='white')

                    for i in range(len(self.buttList)):
                        self.buttList[i].configure(state='normal')

                    # ACS-related
                    self.acsLunEnable.setEnable(True)
                    self.acsFidEnable.setEnable(True)
                    self.acsSetNominalDelays.configure(state = 'normal')
                    self.acsModulatorOpen.configure(state = 'normal')
                    self.acsModulatorExtremTx.configure(state = 'normal')
                    self.acsModulatorSweep.configure(state = 'normal')
                    self.acsPhotodiodeADCRead.configure(state = 'normal')
                    self.acsLSBRecover.configure(state = 'normal')
                    self.acsClockPhaseSweep.configure(state = 'normal')
                    
                elif not self.lockStatus:
                    self.lockStatus = True
                    self.wdg6.state = 0
                    self.wdg9.state = 0
                    #self.wdg2.go_But.configure(state='disabled') # no longer used
                    self.wdg2.new_go_But.configure(state='disabled')

                    self.wdg6.snapButt.configure(state='disabled')
                    self.wdg6.saveButt.configure(state='disabled')
                    self.wdg6.cursorButt.configure(state='disabled')

                    self.wdg9.b2.configure(state='disabled')
                    self.wdg9.b3.configure(state='disabled')
                    self.wdg9.b4.configure(state='disabled')

                    self.boloInButton.configure(state='disabled')
                    self.boloOutButton.configure(state='disabled')

                    a=self.component(' Main -tab')
                    a.configure(text=' Main ',foreground=Tk.Label().cget("foreground"))
                    
                    self.lockButton.configure(text='Take Control',background=Tk.Label().cget("background"),
                                              foreground=Tk.Label().cget("foreground"))

                    for i in range(len(self.buttList)):
                        self.buttList[i].configure(state='disabled')

                    # ACS-related
                    self.acsLunEnable.setEnable(False)
                    self.acsFidEnable.setEnable(False)
                    self.acsSetNominalDelays.configure(state = 'disabled')
                    self.acsModulatorOpen.configure(state = 'disabled')
                    self.acsModulatorExtremTx.configure(state = 'disabled')
                    self.acsModulatorSweep.configure(state = 'disabled')
                    self.acsPhotodiodeADCRead.configure(state = 'disabled')
                    self.acsLSBRecover.configure(state = 'disabled')
                    self.acsClockPhaseSweep.configure(state = 'disabled')


#                    
        def update_Axis(self, ax, lines, data):

#                background = self.mpl_fig.canvas.copy_from_bbox(ax.bbox.expanded(1.35, 1.2))
#                self.mpl_fig.canvas.restore_region(background)
                
                for i in range(len(lines)):
                    j=2*i
                    k=j+1

                    lines[i].set_data(np.array(data[j]),np.array(data[k]))

                    ax.relim()
                    ax.autoscale_view()
                    ax.draw_artist(lines[i])
                    
#                ax.draw(ax.get_renderer_cache())

                #for spine in ax.spines.values():
                #    ax.draw_artist(spine)
                #        
                #ax.draw_artist(ax.xaxis)
                #ax.draw_artist(ax.yaxis)

                #self.mpl_fig.canvas.draw()
                #to_update = ax.bbox.union([label.get_window_extent() for label in ax.get_xticklabels()]+[label.get_window_extent() for label in ax.get_yticklabels()]+[ax.bbox])
                
                self.mpl_fig.canvas.blit(ax.bbox)


                
        def resetCounters(self):
                        self.ROOT_refresh()

                        global gpsi
                        gpsi = 0
                        self.runStartTime = 0.
                        self.runStarted = 0
                        self.totTime.set(0)
                        self.totalShots.set(0)
                        self.totalLunShots.set(0)
                        self.totalFid.set(0)
                        self.rateFid.set(0)
                        self.fidRegWdg.set(0)
                        self.fidRegRateWdg.set(0)
                        self.fidRegRateRecWdg.set(0)
                        self.totalLun.set(0)
                        self.rateLun.set(0)
                        self.regLun.set(0)
                        self.regRateLun.set(0)
                        self.regRateRecLun.set(0)
                        self.lunBackgroundWdg.set(0)
 #                       self.lunBackgroundRateWdg.set(0)
                        self.missedFRCWdg.set(0)

                        self.noConvergence=0
                        self.convWdg.set(0)

                        self.chanAPD = 0

                        self.shotNum = 0
                        self.shotNumLun = 0

                        self.totalFidNum = 0        # Total Photons and rates
                        self.fidRegNum = 0          # total registered fiducials
                        self.fidRate = 0.0          # fiducial photon rate
                        self.fidRegRate =0.0        # registered fiducial rate
                        self.tcorListFid=[]
#
                        self.totalLunNum = 0
                        self.lunRate = 0
                        self.totalLunRegNum = 0     # Registered Photons and rates
                        self.lunRegRate = 0
                        self.lunRegNum = 0
                        self.yield_est = 0.0
                        self.lunBackgroundNum = 0   # background Photons and rates
                        self.lunBackgroundRate = 0
                        self.bgLun = 0

                        self.stareShot = 0
                        self.staresHere = 0
                        self.stareNumHere = 0
                        self.stareRateHere = 0.0
#
#                        # tracking stuff
                        self.offsetNum = 0      # Guide offset #
                        self.shotsHere = 0      # shots at this guide offset
                        self.rateHere = 0.0
                        self.lunNumHere = 0
                        self.lunRegNumHere = 0
                        self.lunRateHere = 0
                        self.lunRegRateHere = 0

                        self.irasterGuide = 0
                        self.irasterRxx = 0
#
                        self.shotsRxx = 0           # shots at this rxx,rxy
                        self.rateRxx = 0.0         # rate at thie rxx,rxy
                        self.lunNumRxx = 0         # total lunar # at this rxx,rxy
                        self.lunRegNumRxx = 0      # total registered # of lunars at this rxx,rxy
                        self.lunRateRxx = 0        # lunar rate at this rxx,rxy
                        self.lunRegRateRxx = 0     # lunar registered at this rxx,r#
                        
                        self.chanTimesCorTot=[]
                        #self.chanTimesCorHist=[]
                        self.shotList=[]
                        
                        self.chanTimesCorTotLun=[]
                        self.chanTimesCorHistLun=[]
                        self.shotListLun=[] 
                        
                        self.lunRegList=[]
            
                        self.laser_powerWdg.set(0.00)   # laser power stuff
                        self.laser_powerAveWdg.set(0.00)
                        self.loWdg.set(0.00)
                        self.hiWdg.set(0.00)
                        
                        self.hitgridData=np.zeros([200,16])
                        
                        self.totACSWdg.set(0)
                        self.rateACSWdg.set(0)
                        self.ACSSubtracted = 0
                        self.ACSTotNum = []
                        self.lunShotToCount = [0]
                        self.lunRawTDCTot = []
                        self.lunRawTDCHist = []
                        
                        self.lunTWSPhasedTransient = []
                        self.fidTWSPhasedTransient = []
                        #self.TWSPhasedHistogram = np.histogram(self.lunTWSPhasedTransient, self.TWSPhasedBinEdges)

                        self.TWSPhasedPeakLow = 9999 
                        self.TWSPhasedPeakHigh = 9999
                        self.TWSPeakWrapped = False

                        self.acsDACExtremizePostPPGRNVals = []
                        self.acsDACExtremizeDACVals = []

                        
def vp_start_gui():
    root = RO.Wdg.PythonTk()
    root.geometry("1200x900+200+50")
    w = NoteBook(root)
    root.mainloop()


if __name__ == '__main__':
    def vp_start_gui():
        root = RO.Wdg.PythonTk()
        root.geometry("1200x900+200+50")
        w = NoteBook(root)
        root.mainloop()
    vp_start_gui()

#  LocalWords:  usr
