#!/usr/local/bin/python
"""Display data from Apollo.
History:
2005-02-11 ROwen	a shell
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
"""

import tkinter as Tk
import numpy as num
import time
import string
import RO.Constants
import RO.Wdg
import TUI.TUIModel
import TUI.TCC.TCCModel
from . import ApolloModel
from . import pathStuff
from . import LogWdg

path = pathStuff.hippoWdgPaths()
imagePath  = pathStuff.imagePath()

import Image
from PIL import ImageTk
import sys
import Pmw
from . import moonWdg
from . import laserKeypad
from . import stv
from load_hippo import app, canvas
from hippo import *

# globals
NChan = 17
prf = PointRepFactory.instance()
reps = prf.names()
gpsi = 0
testFlag = 0
labelFont = ('Times',10,'bold')

_HelpPrefix = "APOLLO graphics widget"

HOUSTON = 0

class NoteBook(Pmw.NoteBook):
	def __init__(self,master,**kargs):

    ## set up the notebook
		Pmw.NoteBook.__init__(self, master,**kargs)

		self.buttFrame = Tk.Frame(master)
		gr_butt = RO.Wdg.Gridder(self.buttFrame)
		self.buttFrame.pack(side='left',anchor='nw')

		self.stateDict = {0:'EXIT',1:'IDLE',2:'WARMUP',3:'RUN',4:'COOLDOWN',5:'STARE',6:'FIDLUN',7:'STANDBY',
                                  8:'DARK',9:'FLAT',10:'LPOWER',11:'CALTDC',12:'LASERCAL'}

		self.nb = Pmw.NoteBook(master)
                self.nb.pack(fill = 'both', expand=1)

                self.p1=self.nb.add(' Main ')
                self.p1.pack(fill = 'both',padx=15,pady=15)

                self.p2=self.nb.add('Pointer')
                self.wdg2 = moonWdg.moonWdg(self.p2)
                self.wdg2.grid(row=0,column=0,sticky='n')

                self.p3 = self.nb.add('Hippo')
                
                self.p4 = self.nb.add('Alarms')

                self.p5 = self.nb.add('Raster')
                
                self.p6 = self.nb.add('STV')
                stvFrame = Tk.Frame(self.p6)
                #self.wdg6 = stv.StvFrontEnd(stvFrame)
                stvFrame.pack(side='top')
                
                self.p7 = self.nb.add('Channels')
                
                self.p8 = self.nb.add('Power')

                self.p9 = self.nb.add('Laser Tuning')
                laserFrame = Tk.Frame(self.p9)
                #self.wdg9 = laserKeypad.MyApp(laserFrame)
                laserFrame.pack(side='right',anchor='ne')

# initialize stuff
    
		self.runStarted = 0    # logical true if run in progress
                self.shotsInSec = 0    # # of laser shots in the last second, as repoted by GPS

                self.shotBuffer = 5    # of shots to buffer before redrawing hippo plots

                self.state = 0

                self.cmdr = ''
                self.cmdrMID = 0
                self.cmdActor = ''
                self.cmdText = ''
		
                self.tccModel = TUI.TCC.TCCModel.getModel()
		self.apolloModel = ApolloModel.getModel()   # get models
		self.tuiModel = TUI.TUIModel.getModel()

		self.wdg2.tuiModel = self.tuiModel

		self.dispatcher = self.tuiModel.dispatcher

		self.AFSCImage =Tk.PhotoImage(file= imagePath + 'afspc100.gif') 
                self.wdgFlag = 0 # flag for space command widget color

                # array buffers for displays
		self.hitGridReserve = 40
		self.intenReserve = 200
		self.histReserve = 200
		self.rateReserve = 200
		self.fidStripReserve = 2000
		self.lunStripReserve = 2000
		self.stareStripReserve = 10000
		self.trackReserve = 20000

		self.irasterGuide = 0
		self.irasterRxx = 0
		self.raster = 0
		self.rasterMag = 0.0
		self.rasterShots = 0
		self.rasterList = ['right','up','left','left','down','down','right','right','upLeft']
                
                # Adam's APD channel map (APD #), index is TDC channel
                    # 0 in upper left ('top'), 15 in lower right
                self.chanMap = [6,15,2,11,3,10,1,7,8,14,5,12,4,13,0,9]
                
                # channel offset
                self.chanOffset = []
                chanOffRaw = [302.643,360.405,0.0,325.358,0.0,330.413,345.359,0.0,
                              350.086,337.171,324.468,278.374,312.305,290.245,0.0,329.595]
                nGood = 16-chanOffRaw.count(0.0)
                mn = num.add.reduce(chanOffRaw)/nGood
                
                for i in range(16):
                    if chanOffRaw[i]:
                        self.chanOffset.append(int(round(chanOffRaw[i]-mn)))
                    else:
                        self.chanOffset.append(0)
                #old offsets
                #self.chanOffset = [-23,29,0,-5,0,12,16,0,28,15,3,-44,-10,-29,0,9] channel offsets, index is TDC channel

                self.powerList = [] # list of power indices gotten from Power
                self.pwrWdgDict ={} # list of power checkbox widgets

                self.chanBackground = num.zeros(16)     # Background rate array
                self.chanFlat = num.zeros(16)           # Flat array
                self.chanFlatCorr = num.ones(16)
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
                self.lunRegRate = 0.0
                self.yield_est = 0.0
                self.gateWidth = 8
                self.runfidgw = 7

                self.lunBackgroundNum = 0   # background Photons and rate
                self.lunBackgroundRate = 0.0
                
                self.regCenter=0             # center of registered region
                self.binForReg = 160         # full width in TDC bins for lunars to be "Registered"
                self.lower = self.regCenter-self.binForReg/2 # registered lower bound
                self.upper = self.regCenter+self.binForReg/2 # registered upper bound

                self.regCenterFid=-250      # nominal center of fiducial spike
                self.binForRegFid = 160     # full width in TDC bins for fids to be "Registered"
                self.lowerFid = self.regCenterFid-self.binForRegFid/2
                self.upperFid = self.regCenterFid+self.binForRegFid/2
                self.fidDat=[]

                self.lunHeight = 1
                self.lunDat =[]
                self.changeState = 0.
                
                self.stareShot = 0          # # of stares taken

            # tracking stuff
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

## Misc
                self.lpowerTime = 0         # length of laser power measurement
                self.lPowerNum = 0          # number of shots in power measurement

                self.lockStatus = True      # houston commands enabled if False

                self.stateButtArray =[]
                self.predSkew = 0
                self.alarmState = False         # binary state of houston alarms
                self.ampDelInc = 10              # set default amp delay increment to 10
                    
## Hippodraw data and plots

                canvas.setPlotMatrix(4,5)   # may need to be adjusted for different screens
                    
                # "All" fiducial data
                self.fid_data = NTuple(22)
                self.fid_data.setLabels(('shot #','sec','inten','nhit','Total Fid Returns','Fid rate','photodiode',
                                         'ch1','ch2','ch3','ch4','ch5','ch6','ch7','ch8','ch9','ch10','ch11',
                                         'ch12','ch13','ch14','ch15'))
                self.fid_data.setName('Fiducial Data')
                NTupleController.instance().registerNTuple(self.fid_data)

                # "All" lunar data
                self.lun_data = NTuple(30)
                self.lun_data.setLabels(('shot #','Offset Num','az','el','sec','ppred','tpred','nhit','Total Returns',
                                         'Registered Returns','Background Returns','Total Rate','Registered Rate',
                                         'Background Rate','ch0','ch1','ch2','ch3','ch4','ch5','ch6','ch7','ch8','ch9',
                                         'ch10','ch11','ch12','ch13','ch14','ch15'))
                self.lun_data.setName('Lunar Data')
                NTupleController.instance().registerNTuple(self.lun_data)
                
## Hippodraw Initialization

                # APD fiducial hitgrid
                self.fid_hitgrid_all = NTuple(3)
                self.fid_hitgrid = NTupleController.instance().createCircularBuffer(3)
                self.fid_hitgrid.setName('Fid Hitgrid')
                self.fid_hitgrid.reserve(self.hitGridReserve) # length of window (100 = 5 sec)
                self.fid_hitgrid.setLabels(('x_fid','y_fid','weight'))
                self.fid_APD = Display("Color Plot", self.fid_hitgrid,['x_fid', 'y_fid','weight'])
                self.fid_APD.setTitle("Corner Cube")
                self.fid_APD.setRange('x',0,4)
                self.fid_APD.setRange('y',0,4)
                self.fid_APD.setRange('z',0,20)
                self.fid_APD.setLabel('x','')
                self.fid_APD.setLabel('y','')
                self.fid_APD.setAspectRatio(1)
                self.fid_APD.setAutoRanging('z',True)
                self.fid_APD.setColorMap('Grey scale')
                self.fid_hitgrid.setIntervalCount(self.shotBuffer)
                self.fid_hitgrid.setIntervalEnabled(True)

                rep_fid_APD = self.fid_APD.getDataReps()
                rep_fid_APD[0].setBinWidth('x',1)
                rep_fid_APD[0].setBinWidth('y',1)

                canvas.addDisplay(self.fid_APD)

                # APD lunar hitgrid
                self.lun_hitgrid_all = NTuple(3)
                self.lun_hitgrid = NTupleController.instance().createCircularBuffer(3)
                self.lun_hitgrid.setName('Lun Hitgrid')
                self.lun_hitgrid.reserve(self.hitGridReserve) # length of window (100 = 5 sec)
                self.lun_hitgrid.setLabels(('x_lun','y_lun','weight'))
                self.lun_APD = Display("Color Plot", self.lun_hitgrid,['x_lun', 'y_lun','weight'])
                self.lun_APD.setTitle("Lunar")
                self.lun_APD.setRange('x',0,4)
                self.lun_APD.setRange('y',0,4)
                self.lun_APD.setRange('z',0,20)
                self.lun_APD.setLabel('x','')
                self.lun_APD.setLabel('y','')
                self.lun_APD.setAspectRatio(1)
                self.lun_APD.setAutoRanging('z',True)
                self.lun_APD.setColorMap('Grey scale')
                #self.lun_hitgrid.setIntervalCount(self.shotBuffer)
                #self.lun_hitgrid.setIntervalEnabled(True)

                rep_lun_APD = self.lun_APD.getDataReps()
                rep_lun_APD[0].setBinWidth('x',1)
                rep_lun_APD[0].setBinWidth('y',1)

                canvas.addDisplay(self.lun_APD)

                # tracking rate hitgrid
                self.track_ret_all = NTuple(3)

                self.trackHist = NTuple(4)
                NTupleController.instance().registerNTuple(self.trackHist)
                self.trackHist.setLabels(('Offset Number','Az','El','Lunar Rate'))
                self.trackHist.setName('Guide Offset History')

                self.track_ret = NTupleController.instance().createCircularBuffer(3)
                self.track_ret.setName('Lunar Rate at this Offset')
                self.track_ret.reserve(1)
                self.track_ret_all.setLabels(('az','el','rate'))
                self.track_ret.setLabels(('az','el','rate'))
                self.track_APD = Display("XYZ Plot", self.track_ret,['az', 'el','rate'])
                self.track_APD.setTitle("Tracking")
                self.track_APD.setRange('x',-2.5,2.5)
                self.track_APD.setRange('y',-2.5,2.5)
                #self.track_APD.setRange('z',0,0.2)
                self.track_APD.setAutoRanging('z',True)
                self.track_APD.setLabel('x','az')
                self.track_APD.setLabel('y','el')
                self.track_APD.setLabel('z','Lunar Rate')
                self.track_APD.setAspectRatio(1)

                self.track_APD.addDataRep("XYZ Plot", self.track_ret_all,['az', 'el','rate'])

                self.track_APD.setColorMap('Grey scale')

                rep_track_APD = self.track_APD.getDataReps()
                rep_track_APD[0].setSize(6)
                rep_track_APD[1].setSize(6)
                
                canvas.addDisplay(self.track_APD)

                # registered rate vs. optics offset rxx and rxy
                self.rxxRate_all = NTuple(3)
                self.rxxRate_all.setLabels(('rxx','rxy','registered rate'))
                self.rxxRate = NTupleController.instance().createCircularBuffer(3)
                self.rxxRate.setName('Registered Rate vs. rxx, rxy')
                self.rxxRate.reserve(self.trackReserve) # length of window (100 = 5 sec)
                self.rxxRate.setLabels(('rxx','rxy','registered rate'))
                self.rxxRate_disp = Display("XYZ Plot", self.rxxRate,['rxx','rxy','registered rate'])
                self.rxxRate_disp.setTitle("Reg. Rate vs. rxx, rxy")
                self.rxxRate_disp.setAutoRanging('x',True)
                self.rxxRate_disp.setAutoRanging('y',True)
                #self.rxxRate_disp.setRange('z',0.,0.05)
                self.rxxRate_disp.setAutoRanging('z',True)
                self.rxxRate_disp.setLabel('x','rxx')
                self.rxxRate_disp.setLabel('y','rxy')
                self.rxxRate_disp.setAspectRatio(1)

                self.rxxRate_disp.addDataRep("XYZ Plot", self.rxxRate_all,['rxx', 'rxy','registered rate'])
                self.rxxRate_disp.setColorMap('Grey scale')

                rep_rxxRate_disp = self.rxxRate_disp.getDataReps()
                rep_rxxRate_disp[0].setSize(6)
                rep_rxxRate_disp[1].setSize(6)

                canvas.addDisplay(self.rxxRate_disp)

                # Fiducial return histogram
                self.cc_return_t_all = NTuple(1)
                self.cc_return_t = NTupleController.instance().createCircularBuffer(1)
                self.cc_return_t.setName('Corrected Fiducial Return Time')
                self.cc_return_t.reserve(self.histReserve)   # length of window (100 = 5 sec)
                self.cc_return_t.setTitle('Fiducial Return Time (Cor)')
                self.cc_return_t.setLabels(('Return Time (Corrected TDC Units)',))
                self.cc_return_t.setIntervalCount(self.shotBuffer)
                self.cc_return_t.setIntervalEnabled(True)

                self.cc_return_raw_t_all = NTuple(1)
                self.cc_return_raw_t = NTupleController.instance().createCircularBuffer(1)
                self.cc_return_raw_t.setName('Raw Fiducial Return Time')
                self.cc_return_raw_t.reserve(self.histReserve)   # length of window (100 = 5 sec)
                self.cc_return_raw_t.setTitle('Fiducial Return Time (Uncor)')
                self.cc_return_raw_t.setLabels(('Return Time (Raw TDC Units)',))
                self.cc_return_raw_t.setIntervalCount(self.shotBuffer)
                self.cc_return_raw_t.setIntervalEnabled(True)

                self.fpd_all = NTuple(1)
                self.fpd = NTupleController.instance().createCircularBuffer(1)
                self.fpd.setName('FPD Values')
                self.fpd.reserve(self.histReserve)   # length of window (100 = 5 sec)
                self.fpd.setTitle('FPD Values (TDC Channel)')
                self.fpd.setLabels(('FPD (TDC Channel)',))
                self.fpd.setIntervalCount(self.shotBuffer)
                self.fpd.setIntervalEnabled(True)

                self.fidRegLower = NTupleController.instance().createCircularBuffer(2)
                self.fidRegLower.setLabels(('lower limit','height'))
                self.fidRegLower.reserve(2)

                self.fidRegUpper = NTupleController.instance().createCircularBuffer(2)
                self.fidRegUpper.setLabels(('upper limit','height'))
                self.fidRegUpper.reserve(2)

                self.cc_return_hist = Display("Histogram", self.cc_return_t,('Return Time (Corrected TDC Units)', ))

                self.cc_return_hist.setAspectRatio(1.5)

                self.cc_return_hist.addDataRep("XY Plot", self.fidRegLower,('lower limit','height' ))
                self.cc_return_hist.addDataRep("XY Plot", self.fidRegUpper,('upper limit','height' ))
                self.cc_return_hist.addDataRep("Histogram", self.fpd,('FPD (TDC Channel)',))
                
                self.rep_cc = self.cc_return_hist.getDataReps()
                self.rep_cc[1].setPointRep(prf.create(reps[6]))
                self.rep_cc[1].set(Line(2))
                self.rep_cc[2].setPointRep(prf.create(reps[6]))
                self.rep_cc[2].set(Line(2))
                self.rep_cc[0].setColor('red')
                self.rep_cc[1].setColor('black')
                self.rep_cc[2].setColor('black')
                self.rep_cc[3].setColor('blue')

                canvas.addDisplay(self.cc_return_hist)

                # Fiducial rate histogram
                self.cc_rate_all = NTuple(1)
                self.cc_rate = NTupleController.instance().createCircularBuffer(1)
                self.cc_rate.setName('Fiducial Rate')
                self.cc_rate.reserve(self.rateReserve)   # length of window (100 = 5 sec)
                self.cc_rate.setTitle('Fiducial Rate')
                self.cc_rate.setLabels(('Photons/Shot',))
                self.cc_rate.setIntervalCount(self.shotBuffer)
                self.cc_rate.setIntervalEnabled(True)


                self.fid_reg_all = NTuple(1)  # This is now 'registered' photons - ignore name for now
                self.fid_reg = NTupleController.instance().createCircularBuffer(1)
                self.fid_reg.setName('Registered Rate')
                self.fid_reg.reserve(self.rateReserve)   # length of window (100 = 5 sec)
                self.fid_reg.setTitle('Registered Rate')
                self.fid_reg.setLabels(('Photons/Shot',))
                self.fid_reg.setIntervalCount(self.shotBuffer)
                self.fid_reg.setIntervalEnabled(True)

                

                self.cc_rate_hist = Display("Histogram", self.cc_rate,('Photons/Shot', ))
                self.cc_rate_hist.setAspectRatio(1.5)
                self.cc_rate_hist.setRange('x',0,16)

                self.cc_rate_hist.addDataRep("Histogram", self.fid_reg,('Photons/Shot', ))

                self.rep_cc_rate = self.cc_rate_hist.getDataReps()
                self.rep_cc_rate[0].setColor('red')
                self.rep_cc_rate[0].setBinWidth('x',1)
                self.rep_cc_rate[1].setColor('green')
                self.rep_cc_rate[1].setBinWidth('x',1)

                canvas.addDisplay(self.cc_rate_hist)

                # time series plot of fiducial returns
                self.fidTimeSeries_all = NTuple(2)
                self.fidTimeSeries = NTupleController.instance().createCircularBuffer(2)
                self.fidTimeSeries.setName('Corrected Fiducial Return Time Series')
                self.fidTimeSeries.reserve(self.fidStripReserve) # length of window (100 = 5 sec)
                self.fidTimeSeries.setTitle('Corner Cube Photon Return Time')
                self.fidTimeSeries.setLabels(('Shot #','Return Time (Corrected TDC Units)'))
                self.fidseries = Display("XY Plot", self.fidTimeSeries,['Shot #', 'Return Time (Corrected TDC Units)'])
                #self.fidseries.setAspectRatio(1.5)

                self.fidTimeSeries_raw_all = NTuple(2)
                self.fidTimeSeries_raw = NTupleController.instance().createCircularBuffer(2)
                self.fidTimeSeries_raw.setName('Raw Fiducial Return Time Series')
                self.fidTimeSeries_raw.reserve(self.fidStripReserve) # length of window (100 = 5 sec)
                self.fidTimeSeries_raw.setTitle('Corner Cube Photon Return Time')
                self.fidTimeSeries_raw.setLabels(('Shot #','Return Time (Raw TDC Units)'))

                self.fidseries.addDataRep("XY Plot", self.fidTimeSeries_raw,['Shot #', 'Return Time (Raw TDC Units)'])

                rep_fidseries = self.fidseries.getDataReps()
                rep_fidseries[0].setColor('red')
                rep_fidseries[0].setSize(3)
                rep_fidseries[1].setColor('green')
                rep_fidseries[1].setSize(3)

                #canvas.addDisplay(self.fidseries)

                # Lunar return histogram
                self.lun_return_t_all = NTuple(1)
                self.lun_return_t = NTupleController.instance().createCircularBuffer(1)
                self.lun_return_t.setName('Corrected Lunar Return Time')
                self.lun_return_t.reserve(self.histReserve)   # length of window (100 = 5 sec)
                self.lun_return_t.setTitle('Lunar Return Time')
                self.lun_return_t.setLabels(('Return Time (Corrected TDC Units)',))
                self.lun_return_hist = Display("Histogram", self.lun_return_t,('Return Time (Corrected TDC Units)', ))
                self.lun_return_hist.setAspectRatio(1.5)
                self.lun_return_t.setIntervalCount(self.shotBuffer)
                self.lun_return_t.setIntervalEnabled(True)


                self.lun_return_raw_t_all = NTuple(1)
                self.lun_return_raw_t = NTupleController.instance().createCircularBuffer(1)
                self.lun_return_raw_t.setName('Raw Lunar Return Time')
                self.lun_return_raw_t.reserve(self.histReserve)   # length of window (100 = 5 sec)
                self.lun_return_raw_t.setTitle('Lunar Return Time')
                self.lun_return_raw_t.setLabels(('Return Time (Raw TDC Units)',))
                self.lun_return_raw_t.setIntervalCount(self.shotBuffer)
                self.lun_return_raw_t.setIntervalEnabled(True)
                
                self.lunRegLower = NTupleController.instance().createCircularBuffer(2)
                self.lunRegLower.setLabels(('lower limit','height'))
                self.lunRegLower.reserve(2)

                self.lunRegUpper = NTupleController.instance().createCircularBuffer(2)
                self.lunRegUpper.setLabels(('upper limit','height'))
                self.lunRegUpper.reserve(2)

                #self.lun_return_hist.addDataRep("Histogram", self.lun_return_raw_t,('Return Time (Raw TDC Units)', ))
                self.lun_return_hist.addDataRep("XY Plot", self.lunRegLower,('lower limit','height' ))
                self.lun_return_hist.addDataRep("XY Plot", self.lunRegUpper,('upper limit','height' ))

                self.rep_lun = self.lun_return_hist.getDataReps()
                self.rep_lun[1].setPointRep(prf.create(reps[6]))
                self.rep_lun[1].set(Line(2))
                self.rep_lun[2].setPointRep(prf.create(reps[6]))
                self.rep_lun[2].set(Line(2))
                self.rep_lun[0].setColor('blue')
                #self.rep_lun[1].setColor('green')
                self.rep_lun[1].setColor('black')
                self.rep_lun[2].setColor('black')

                canvas.addDisplay(self.lun_return_hist)

                # Lunar rate histogram
                self.lun_rate_all = NTuple(1)
                self.lun_rate = NTupleController.instance().createCircularBuffer(1)
                self.lun_rate.setName('Lunar Rate')
                self.lun_rate.reserve(self.rateReserve)   # length of window (100 = 5 sec)
                self.lun_rate.setTitle('Lunar Rate')
                self.lun_rate.setLabels(('Photons/Shot',))        
                self.lun_rate.setIntervalCount(self.shotBuffer)
                self.lun_rate.setIntervalEnabled(True)
                
                self.lun_background_all = NTuple(1)  # This is now 'registered' photons - ignore name for now
                self.lun_background = NTupleController.instance().createCircularBuffer(1)
                self.lun_background.setName('Registered Rate')
                self.lun_background.reserve(self.rateReserve)   # length of window (100 = 5 sec)
                self.lun_background.setTitle('Registered Rate')
                self.lun_background.setLabels(('Photons/Shot',))
                self.lun_background.setIntervalCount(self.shotBuffer)
                self.lun_background.setIntervalEnabled(True)

                self.lun_rate_hist = Display("Histogram", self.lun_rate,('Photons/Shot', ))
                self.lun_rate_hist.setAspectRatio(1.5)
                self.lun_rate_hist.setRange('x',0,16)

                self.lun_rate_hist.addDataRep("Histogram", self.lun_background,('Photons/Shot', ))
                
                self.rep_lun_rate = self.lun_rate_hist.getDataReps()
                self.rep_lun_rate[0].setColor('blue')
                self.rep_lun_rate[0].setBinWidth('x',1)
                self.rep_lun_rate[1].setColor('green')
                self.rep_lun_rate[1].setBinWidth('x',1)

                canvas.addDisplay(self.lun_rate_hist)
                
            # time series plot of registered lunar rate
                self.lunTimeSeriesReg_all = NTuple(2)
                self.lunTimeSeriesReg = NTupleController.instance().createCircularBuffer(2)
                self.lunTimeSeriesReg.setIntervalCount(self.shotBuffer)
                self.lunTimeSeriesReg.setIntervalEnabled(True)
                self.lunTimeSeriesReg.setTitle('"Current" Lunar Rate')
                self.lunTimeSeriesReg.setName('Reg. Lunar Rate Time Series')
                self.lunTimeSeriesReg.reserve(self.fidStripReserve) # length of window (100 = 5 sec)
                self.lunTimeSeriesReg.setLabels(('Shot #','Recent Rate'))
                self.lunseries = Display("XY Plot", self.lunTimeSeriesReg,['Shot #', 'Recent Rate'])
                self.lunseries.setAspectRatio(1.5)
                
                self.lunTimeSeries_raw_all = NTuple(2)
                self.lunTimeSeries_raw = NTupleController.instance().createCircularBuffer(2)
                self.lunTimeSeries_raw.setIntervalCount(self.shotBuffer)
                self.lunTimeSeries_raw.setIntervalEnabled(True)
                self.lunTimeSeries_raw.setName('Raw Lunar Return Time Series')
                self.lunTimeSeries_raw.reserve(self.fidStripReserve) # length of window (100 = 5 sec)
                self.lunTimeSeries_raw.setTitle('Raw Lunar Return Time')
                self.lunTimeSeries_raw.setLabels(('Shot #','Return Time (Raw TDC Units)'))

                self.changes_all = NTuple(3)
                self.changes = NTupleController.instance().createCircularBuffer(3)
                self.changes.setName('Track any changes')
                self.changes.reserve(self.fidStripReserve) # length of window (100 = 5 sec)
                self.changes.setLabels(('Shot #','y','y2'))
                self.changes.setIntervalCount(self.shotBuffer)
                self.changes.setIntervalEnabled(True)

                self.lunseries.addDataRep("XY Plot", self.changes,['Shot #', 'y'])

                self.rep_lunseries = self.lunseries.getDataReps()
                self.rep_lunseries[0].setSize(2)
                self.rep_lunseries[1].setPointRep(prf.create(reps[2]))
                self.rep_lunseries[1].setColor('blue')

                canvas.addDisplay(self.lunseries)

            # time series plot of all corrected lunar returns
                self.lunTimeSeries_all = NTuple(2)
                self.lunTimeSeries = NTupleController.instance().createCircularBuffer(2)
                self.lunTimeSeries.setName('Corrected Lunar Return Time Series')
                self.lunTimeSeries.reserve(self.fidStripReserve) # length of window (100 = 5 sec)
                self.lunTimeSeries.setTitle('Lunar Photon Return Time')
                self.lunTimeSeries.setLabels(('Shot #','Return Time (Corrected TDC Units)'))
                self.lunSeriesAll = Display("XY Plot", self.lunTimeSeries,['Shot #', 'Return Time (Corrected TDC Units)'])
                self.lunSeriesAll.setAspectRatio(1.5)
                self.lunTimeSeries.setIntervalCount(self.shotBuffer)
                self.lunTimeSeries.setIntervalEnabled(True)

                self.lunRegLowerSeries = NTupleController.instance().createCircularBuffer(2)
                self.lunRegLowerSeries.setLabels(('shot','lower'))
                self.lunRegLowerSeries.reserve(2)

                self.lunRegUpperSeries = NTupleController.instance().createCircularBuffer(2)
                self.lunRegUpperSeries.setLabels(('shot','upper'))
                self.lunRegUpperSeries.reserve(2)

                self.lunSeriesAll.addDataRep("XY Plot",self.lunRegLowerSeries,['shot','lower'])
                self.lunSeriesAll.addDataRep("XY Plot",self.lunRegUpperSeries,['shot','upper'])
                self.lunSeriesAll.addDataRep("XY Plot",self.changes,['Shot #','y2'])

                self.rep_lunSeriesAll = self.lunSeriesAll.getDataReps()
                self.rep_lunSeriesAll[0].setSize(1)
                self.rep_lunSeriesAll[0].setColor('blue')
                self.rep_lunSeriesAll[1].setPointRep(prf.create(reps[6]))
                self.rep_lunSeriesAll[2].setPointRep(prf.create(reps[6]))
                self.rep_lunSeriesAll[1].set(Line(2))
                self.rep_lunSeriesAll[2].set(Line(2))
                self.rep_lunSeriesAll[1].setColor('black')
                self.rep_lunSeriesAll[2].setColor('black')
                self.rep_lunSeriesAll[3].setPointRep(prf.create(reps[2]))
                self.rep_lunSeriesAll[3].setColor('red')

                canvas.addDisplay(self.lunSeriesAll)
                
                # time series plot of stare rate
                self.stareTimeSeries_all = NTuple(2)
                self.stareTimeSeries = NTupleController.instance().createCircularBuffer(2)
                self.stareTimeSeries.setName('Stare Rate Times Series')
                self.stareTimeSeries.reserve(self.stareStripReserve) # length of window (100 = 5 sec)
                self.stareTimeSeries.setTitle('Stare Rate')
                self.stareTimeSeries.setLabels(('Stare #','Rate (Photons/Stare)'))
                self.stareSeries = Display("XY Plot", self.stareTimeSeries,['Stare #', 'Rate (Photons/Stare)'])
                self.stareSeries.setAspectRatio(1.5)

                rep_stareSeries = self.stareSeries.getDataReps()
                rep_stareSeries[0].setPointRep(prf.create(reps[6]))
                rep_stareSeries[0].setColor('red')

                canvas.addDisplay(self.stareSeries)

                # Stare data hitgrid (dynamically updated, not accumulated)
                self.stare_all = NTuple(3)
                self.stare = NTupleController.instance().createCircularBuffer(1)
                self.stare.setName('Stare Data')
                self.stare.reserve(16) 
                self.stare.setLabels(('x','y','nhit'))
                self.stare_disp = Display("Color Plot", self.stare,['x', 'y','nhit'])
                self.stare_disp.setTitle("Stare Data")
                self.stare_disp.setRange('x',0,4)
                self.stare_disp.setRange('y',0,4)
                self.stare_disp.setLabel('x','')
                self.stare_disp.setLabel('y','')
                self.stare_disp.setAutoRanging('z',True)
                #self.stare_disp.setRange('z',0,500)
                self.stare_disp.setAspectRatio(1)
                self.stare_disp.setColorMap('Grey scale')

                rep_stare_disp = self.stare_disp.getDataReps()
                rep_stare_disp[0].setBinWidth('x',1)
                rep_stare_disp[0].setBinWidth('y',1)

                canvas.addDisplay(self.stare_disp)

                # Stare rate grid
                self.stare_rate_all = NTuple(3)
                self.stare_rate = NTupleController.instance().createCircularBuffer(3)
                self.stare_rate.setName('Stare Rate at this g')
                self.stare_rate.reserve(1)
                self.stare_rate_all.setLabels(('az','el','rate'))
                self.stare_rate.setLabels(('az','el','rate'))
                self.stareGrid = Display("XYZ Plot", self.stare_rate,['az', 'el','rate'])
                self.stareGrid.setTitle("Stare Rate")
                self.stareGrid.setRange('x',-5,5)
                self.stareGrid.setRange('y',-5,5)
                self.stareGrid.setAutoRanging('z',True)
                self.stareGrid.setLabel('x','az')
                self.stareGrid.setLabel('y','el')
                self.stareGrid.setLabel('z','Stare Rate')
                self.stareGrid.setAspectRatio(1)
                self.stareGrid.setColorMap('Grey scale')

                self.stareGrid.addDataRep("XYZ Plot", self.stare_rate_all,['az', 'el','rate'])

                rep_stareGrid = self.stareGrid.getDataReps()
                rep_stareGrid[0].setSize(6)
                
                canvas.addDisplay(self.stareGrid)

                # Raw return times

                self.raw_hist = Display("Histogram", self.cc_return_raw_t,('Return Time (Raw TDC Units)', ))
                self.raw_hist.setAspectRatio(1.5)
                self.raw_hist.addDataRep("Histogram", self.lun_return_raw_t,('Return Time (Raw TDC Units)', ))
                
                self.rep_raw = self.raw_hist.getDataReps()
                self.rep_raw[0].setColor('red')
                self.rep_raw[1].setColor('blue')

                canvas.addDisplay(self.raw_hist)

                # Intensity histogram 
                self.inten_all = NTuple(1)
                self.inten = NTupleController.instance().createCircularBuffer(1)
                self.inten.setName('Intensity')
                
                self.inten.reserve(self.intenReserve) # length of window (100 = 5 sec)
                self.inten.setTitle('Laser Shot Intensity')
                self.inten.setLabels(('Intensity (V)',))
                self.inten_hist = Display("Histogram", self.inten,('Intensity (V)', ))
                self.inten_hist.setAspectRatio(1.5)
                self.inten.setIntervalCount(self.shotBuffer)
                self.inten.setIntervalEnabled(True)

                self.rep_inten = self.inten_hist.getDataReps()
                self.rep_inten[0].setColor('green')
                
                canvas.addDisplay(self.inten_hist)
                #time.sleep(0.1)
                canvas.addTextRep(self.inten_hist,'averagex')

                self.gauss = Function ("Gaussian", self.rep_inten[0])
                self.gauss.addTo(self.inten_hist)

                self.noConvergence = 0

                # Diffuser phase histogram 
                self.dphase_all = NTuple(1)
                self.dphase = NTupleController.instance().createCircularBuffer(1)
                self.dphase.setName('Diffuser Phase')
                self.dphase.reserve(self.intenReserve) # length of window (100 = 5 sec)
                self.dphase.setTitle('Diffuser Phase')
                self.dphase.setLabels(('Phase',))
                self.dphase_hist = Display("Histogram", self.dphase,('Phase', ))
                self.dphase_hist.setAspectRatio(1.5)
                self.dphase.setIntervalCount(self.shotBuffer)
                self.dphase.setIntervalEnabled(True)

                rep_dphase = self.dphase_hist.getDataReps()
                rep_dphase[0].setColor('blue')

                canvas.addDisplay(self.dphase_hist)

                # time series plot of laser power
                self.lPowerTimeSeries = NTupleController.instance().createCircularBuffer(2)
                self.lPowerAveTimeSeries = NTupleController.instance().createCircularBuffer(2)
                self.lPowerTimeSeries20 = NTupleController.instance().createCircularBuffer(2)
                self.lPowerTimeSeries20.reserve(20)
                self.lPowerTimeSeries200 = NTupleController.instance().createCircularBuffer(2)
                self.lPowerTimeSeries200.reserve(20)
                self.lPowerTimeSeries.setName('Laser Power Times Series')
                self.lPowerAveTimeSeries.setName('Boxcar Average Laser Power Times Series')
                self.lPowerTimeSeries.reserve(20000) # length of window (100 = 5 sec)
                self.lPowerAveTimeSeries.reserve(20000) 
                self.lPowerTimeSeries.setTitle('Laser Power')
                self.lPowerTimeSeries.setLabels(('Measurement #','Bolometer Reading'))
                self.lPowerTimeSeries20.setLabels(('Measurement #','Bolometer Reading'))
                self.lPowerTimeSeries200.setLabels(('Measurement #','Bolometer Reading'))
                self.lPowerAveTimeSeries.setLabels(('Measurement #','Bolometer Reading'))
                self.lPowerSeries = Display("XY Plot", self.lPowerTimeSeries,['Measurement #','Bolometer Reading'])
                self.lPowerSeries.setAspectRatio(1.5)

                self.lPowerSeries.addDataRep("XY Plot",self.lPowerAveTimeSeries,['Measurement #','Bolometer Reading'])

                rep_lPowerSeries = self.lPowerSeries.getDataReps()
                rep_lPowerSeries[0].setPointRep(prf.create(reps[6]))
                rep_lPowerSeries[0].setColor('blue')

                rep_lPowerSeries[1].setPointRep(prf.create(reps[6]))
                rep_lPowerSeries[1].setColor('red')

                canvas.addDisplay(self.lPowerSeries)

## set callbacks for keyword variables
                
		self.tccModel.guideOff.addCallback(self.newOffset)
		self.tccModel.boresight.addCallback(self.newBoresight)
		self.tccModel.axePos.addCallback(self.newAxePos)
		self.tccModel.secFocus.addCallback(self.newSecFocus)
		
		self.apolloModel.airTemp.addCallback(self.newAirTemp) # eventually change to tccModel
		self.apolloModel.pressure.addCallback(self.newPressure)
		self.apolloModel.humidity.addCallback(self.newHumidity)

                self.apolloModel.oldfid.addCallback(self.newOldFid) # outdated?
                
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
		#self.apolloModel.huntstart.addCallback(self.newHuntstart)
		#self.apolloModel.huntdelta.addCallback(self.newHuntdelta)
		#self.apolloModel.thunt.addCallback(self.newThunt)
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
					
## Populate Tk Window with widgets

    # hippodraw graphics control widgets 

                gr = RO.Wdg.Gridder(self.p1, sticky="nw")
                self.FuncCall = RO.Alg.GenericCallback

                graphFrame = Tk.LabelFrame(self.p3,text = 'Hippodraw Graphics Controls',font=labelFont,padx=5,pady=5)
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
                self.hitGridWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.hitGridWindowLength,
                                                                self.hitGridReserve,self.fid_hitgrid_all,
                                                                self.fid_hitgrid,self.lun_hitgrid_all,self.lun_hitgrid)))

                clearHgButton = RO.Wdg.Button(master = graphFrame,
			text="Clear",
                        command = self.FuncCall(self.clear,varlist=(self.fid_hitgrid,self.lun_hitgrid)),
                        helpText = 'Clear the APD hitgrid displays'
		)
                gr_graph.gridWdg('',None)
                gr_graph.gridWdg("APD Hitgrids Time Window (Nhits)", self.hitGridWindowLength,clearHgButton)
                
                self.intenWindowLength = RO.Wdg.IntEntry(graphFrame,
			defValue = self.intenReserve,
			minValue = 1,
			maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for intensity display (in # of shots)'
                )
                self.intenWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.intenWindowLength))
                self.intenWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.intenWindowLength,
                                                                    self.intenReserve,self.inten_all,self.inten,
                                                                    self.dphase_all,self.dphase)))
                clearIntenButton = RO.Wdg.Button(
			master=graphFrame,
			text="Clear",
			command = self.FuncCall(self.clear,varlist=(self.inten,)),
                        helpText = 'Clear the intensity display'
		)
                gr_graph.gridWdg("Intensity Histogram Time Window (# of shots)",self.intenWindowLength,clearIntenButton)

                self.histWindowLength = RO.Wdg.IntEntry(graphFrame,
			defValue = self.histReserve,
			minValue = 1,
			maxValue = 500000,
                        autoIsCurrent = False,
                        isCurrent = True,
                        helpText = 'Buffer length for return time histograms (in # of return photons)'
                )
                self.histWindowLength.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.histWindowLength))
                self.histWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.histWindowLength,self.histReserve,
                                                                    self.cc_return_t_all,self.cc_return_t,
                                                                    self.cc_return_raw_t_all,self.cc_return_raw_t,
                                                                    self.fpd_all,self.fpd,
                                                                    self.lun_return_t_all,self.lun_return_t,
                                                                    self.lun_return_raw_t_all,self.lun_return_raw_t)))
                clearHistButton = RO.Wdg.Button(
			master=graphFrame,
			text="Clear",
			command = self.FuncCall(self.clear,varlist=(self.cc_return_t,self.lun_return_t,
                                                               self.cc_return_raw_t,self.lun_return_raw_t,
                                                                self.fpd,)),
                        helpText = 'Clear the return time histograms'
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
                self.rateWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.rateWindowLength,
                                                                    self.rateReserve,
                                                                    self.cc_rate_all,self.cc_rate,
                                                                    self.fid_reg_all,self.fid_reg,
                                                                    self.lun_rate_all,self.lun_rate,
                                                                    self.lun_background_all,self.lun_background)))
                clearRateButton = RO.Wdg.Button(
			master=graphFrame,
			text="Clear",
			command=self.FuncCall(self.clear,varlist=(self.cc_rate,self.lun_rate,self.lun_background)),
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
                self.timeSeriesWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.timeSeriesWindowLength,
                                                            self.fidStripReserve,self.fidTimeSeries_all,self.fidTimeSeries,
                                                            self.lunTimeSeries_all,self.lunTimeSeries,
                                                            self.lunTimeSeriesReg_all,self.lunTimeSeriesReg,
                                                            self.changes_all, self.changes,
                                                            self.fidTimeSeries_raw_all,self.fidTimeSeries_raw,
                                                            self.lunTimeSeries_raw_all,self.lunTimeSeries_raw
                                                            )))
                clearTimeSeriesButton = RO.Wdg.Button(
			master=graphFrame,
			text="Clear",
			command=self.FuncCall(self.clear,varlist=(self.fidTimeSeries,self.lunTimeSeriesReg,self.lunTimeSeries,
                                                             self.fidTimeSeries_raw,self.lunTimeSeries_raw,self.changes)),
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
                self.trackWindowLength.bind('<Return>',self.FuncCall(self.chngBuffer,varlist=(self.trackWindowLength,
                                                                self.trackReserve,self.rxxRate_all,self.rxxRate,
                                                                self.track_ret_all,self.track_ret)))
                clearTrackButton = RO.Wdg.Button(
			master=graphFrame,
			text="Clear",
			command=self.FuncCall(self.clear,varlist=(self.rxxRate,self.track_ret,self.track_ret_all)),
                        helpText = 'Clear the tracking displays'
		)
                gr_graph.gridWdg("Tracking Time Window (# of offsets)", self.trackWindowLength,clearTrackButton)
                gr_graph.gridWdg("",None)

                clearAllButton = RO.Wdg.Button(
			master=graphFrame,
			text='Clear All Plots',
			command=self.FuncCall(self.clear,
                                         varlist=(self.fid_hitgrid,self.lun_hitgrid,self.inten,self.inten_all,
                                                  self.dphase,self.dphase_all,
                                                  self.cc_return_t,self.lun_return_t,self.fpd,
                                                  self.cc_return_raw_t,self.lun_return_raw_t,self.cc_rate,
                                                  self.lun_rate,self.lun_background,self.fidTimeSeries,
                                                  self.lunTimeSeries,self.lunTimeSeriesReg,self.lunTimeSeriesReg_all,
                                                  self.fidTimeSeries_raw,self.lunTimeSeries_raw,
                                                  self.rxxRate,self.track_ret,self.stareTimeSeries,
                                                  self.stare,self.stare_rate,self.stareTimeSeries_all,
                                                  self.fid_reg_all,self.fid_reg, self.changes)),
                        helpText = 'Clear all plots)'
		)
                
                gr_graph.gridWdg(False,clearAllButton, sticky ='e')

                ## statistics label indicator widgets

                topFrame=Tk.Frame(self.p1)
                topFrame.pack(side='top',anchor='nw')

                statFrame = Tk.LabelFrame(topFrame,text = 'Run Statistics',font = labelFont)

                gr_stat = RO.Wdg.Gridder(statFrame, sticky="nw")

                self.totTime = RO.Wdg.IntLabel(master=statFrame, helpText = 'Shots per second')
                gr_stat.gridWdg("Shots per second", self.totTime)
                self.totTime.set(0)

                self.totalShots = RO.Wdg.IntLabel(master=statFrame, helpText = 'Total # of fiducial records since last reset')
                gr_stat.gridWdg("Fiducial Records", self.totalShots)
                self.totalShots.set(0)

                self.totalLunShots = RO.Wdg.IntLabel(master=statFrame,helpText = 'Total # of lunar return shots since last reset')
                gr_stat.gridWdg("Lunar Return Records", self.totalLunShots,"Per Shot")
                gr_stat.gridWdg("Current",row=-1,col=3)
                self.totalLunShots.set(0)
                
                self.totalFid = RO.Wdg.IntLabel(master=statFrame, helpText = 'Total # of fiducial returns')
                self.rateFid = RO.Wdg.FloatLabel(master=statFrame,helpText = 'Fiducial Rate')
                gr_stat.gridWdg("Total Fiducial Return Photons", self.totalFid,self.rateFid)
                self.totalFid.set(0)
                self.rateFid.set(0)

                self.fidRegWdg = RO.Wdg.IntLabel(master=statFrame, helpText = 'Total registered fiducial returns')
                self.fidRegRateWdg = RO.Wdg.FloatLabel(master=statFrame,
                                                       helpText = 'Registered Fiducial Rate')
                self.fidRegRateRecWdg = RO.Wdg.FloatLabel(master=statFrame,
                                                          helpText =
                                                          'Registered rate for'+
                                                          ' last %d shots - set in ' % self.rateReserve +
                                                          '\'Rate Histogram Time Window\' box')
                gr_stat.gridWdg("Registered Fiducial Photons", self.fidRegWdg,self.fidRegRateWdg)
                gr_stat.gridWdg(self.fidRegRateRecWdg,row=-1,col=3)
                self.fidRegWdg.set(0)
                self.fidRegRateWdg.set(0)
                self.fidRegRateRecWdg.set(0)

                self.totalLun = RO.Wdg.IntLabel(master=statFrame, helpText = 'Total # of lunar returns')
                self.rateLun = RO.Wdg.FloatLabel(master=statFrame, helpText = 'Lunar rate')
                gr_stat.gridWdg("Total Lunar Return Photons", self.totalLun,self.rateLun)
                self.totalLun.set(0)
                self.rateLun.set(0)

                self.regLun = RO.Wdg.IntLabel(master=statFrame, helpText = 'Registered lunar rate')
                self.regRateLun = RO.Wdg.FloatLabel(master=statFrame,
                                                    helpText = '"Registered" lunar rate')
                self.regRateRecLun = RO.Wdg.FloatLabel(master=statFrame,
                                                       helpText =
                                                          'Registered rate for'+
                                                          ' last %d shots - set in ' % self.rateReserve +
                                                          '\'Rate Histogram Time Window\' box')
                gr_stat.gridWdg("Registered Lunar Photons", self.regLun,self.regRateLun)
                gr_stat.gridWdg(self.regRateRecLun,row=-1,col=3)
                self.regLun.set(0)
                self.regRateLun.set(0)
                self.regRateRecLun.set(0)

                self.lunBackgroundWdg = RO.Wdg.IntLabel(master=statFrame,helpText =
                                                        'Estimate of Lunar yield')
                self.lunBackgroundRateWdg = RO.Wdg.FloatLabel(master=statFrame, helpText = 'Lunar background rate')
                gr_stat.gridWdg("Estimate of Lunar yield", self.lunBackgroundWdg)#,self.lunBackgroundRateWdg)
                self.lunBackgroundWdg.set(0)
                self.lunBackgroundRateWdg.set(0)

                resetCounterButton = RO.Wdg.Button(
			master=statFrame,
			text='Reset Everything for New Run',
			command=self.resetCounters,
                        helpText = 'Reset all counters and plots - do this before each new run. Old data is lost.'
		)
                gr_stat.gridWdg(False,resetCounterButton,row= 9, sticky = 'ew')

                self.convWdg = RO.Wdg.IntLabel(master=statFrame,helpText =
                                            '# of total shots in which the Pulse Energy measurement did not converge')
                gr_stat.gridWdg("# of missed PE convergences", self.convWdg,row=10)
                self.convWdg.set(0)

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
                statFrame.pack(side= 'right',anchor='ne',padx=20)

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

# Power status Page
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
                                         row=int(num.floor(num.true_divide(i,4))),col=num.remainder(i,4),sticky='ew')

                #corresponding TDC channel numbers 
                self.numFrame = Tk.LabelFrame(self.p7,text = 'TDC Channel #',font=labelFont,pady=5)
                self.numFrame.pack(side='top',anchor='nw',padx=23)

                self.gr_num = RO.Wdg.Gridder(self.numFrame)

                for i in range(16):
                    ind=self.chanMap.index(i)+1
                    txt='%d     ' % ind
                    self.gr_num.gridWdg(txt,False,
                                        row=int(num.floor(num.true_divide(i,4))),col=num.remainder(i,4),sticky='ew')

# Laser Tuning 

                tuneFrame = Tk.LabelFrame(self.p9,text = 'Laser Power Measurement',font=labelFont,pady=5)
                tuneFrame.pack(side='top',anchor='nw',padx=5)

                tunetop = Tk.Frame(tuneFrame)
                tunetop.pack(side='top',anchor='nw')

            ###
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

                clearPowerButt = RO.Wdg.Button(
			master=tunesub2sub,
			text="Clear Stripchart",
			command=self.FuncCall(self.clearPower),
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

        # rxx/rxy offset

                offFrame = Tk.LabelFrame(self.p9,text = 'Offset rxx/rxy',font=labelFont,pady=5)
                offFrame.pack(side='top',anchor='w',padx=5)

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
                space = Tk.Frame(self.p9,height=20)
                space.pack()

                cmdWdgTune = RO.Wdg.CmdWdg(self.p9,width=200,cmdFunc=self.FuncCall(self.doLineCmd))
                cmdWdgTune.pack(side='top')

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

#command/reply frame

                cmdRepFrame = Tk.LabelFrame(self.p1,text = 'Command/Reply',font=labelFont,padx=5)
                cmdRepFrame.pack(side='top',anchor='n')

                gr_cmdRep = RO.Wdg.Gridder(cmdRepFrame)

# Houston status and controls
                houstonFrame = Tk.LabelFrame(self.p1,text = 'Houston Mission Control',font=labelFont,pady=5)
                houstonFrame.pack(side='top',anchor='ne')

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
                self.apolloModel.polyname.addROWdg(self.polynameWdg,setDefault=True)
                gr_houston.gridWdg('Polynomial Name ',self.polynameWdg,sticky = 'ew')

                gr_moon= RO.Wdg.Gridder(self.p2)

            ## copy on moon page
                self.polynameWdgMoon = RO.Wdg.StrEntry(self.p2,
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
                gr_houston.gridWdg('Target Diffuse Phase ',self.dphaseWdg,sticky = 'ew')

    # nruns widget
                self.nrunsWdg = RO.Wdg.IntEntry(houstonFrame,
			defValue = False,
			minValue = 0,
			maxValue = 100000,
                        helpText ='# of shots for RUN and FIDLUN',
                        autoIsCurrent = True,
                )
                self.nrunsWdg.bind('<Return>',self.FuncCall(self.setPar,var='nruns'))
                self.apolloModel.nruns.addROWdg(self.nrunsWdg,setDefault=True)
                gr_houston.gridWdg('# of shots for RUN, FIDLUN ',self.nrunsWdg,sticky = 'ew')

    # gatewidth widget
                self.gatewidthWdg = RO.Wdg.IntEntry(houstonFrame,
			defValue = False,
			minValue = 0,
			maxValue = 400,
                        helpText ='RUN lunar, STARE, FIDLUN',
                        autoIsCurrent = True,
                )
                self.gatewidthWdg.bind('<Return>',self.FuncCall(self.setPar,var='gatewidth'))
                self.apolloModel.gatewidth.addROWdg(self.gatewidthWdg,setDefault=True)
                gr_houston.gridWdg('Gate width ',self.gatewidthWdg,sticky = 'ew')

    # gatewidth widget
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
                

    # fiducial gatewidth widget
                self.runfidgwWdg = RO.Wdg.IntEntry(houstonFrame,
			defValue = False,
			minValue = 0,
			maxValue = 400,
                        helpText ='RUN fiducial gate width',
                        autoIsCurrent = True,
                )
                self.runfidgwWdg.bind('<Return>',self.FuncCall(self.setPar,var='runfidgw'))
                self.apolloModel.runfidgw.addROWdg(self.runfidgwWdg,setDefault=True)
                gr_houston.gridWdg('RUN fiducial gate width ',self.runfidgwWdg,sticky = 'ew')

    # huntstart widget
                self.huntstartWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
			defValue = False,
                        helpText ='Time-hunt start offset (ns)',
                        autoIsCurrent = True,
                )
                self.huntstartWdg.bind('<Return>',self.FuncCall(self.setPar,var='huntstart'))
                self.apolloModel.huntstart.addROWdg(self.huntstartWdg,setDefault=True)
                
    # huntdelta widget
                self.huntdeltaWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
			defValue = False,
                        helpText ='Time-hunt increment (ns)',
                        autoIsCurrent = True,
                )
                self.huntdeltaWdg.bind('<Return>',self.FuncCall(self.setPar,var='huntdelta'))
                self.apolloModel.huntdelta.addROWdg(self.huntdeltaWdg,setDefault=True)
                
    # thunt widget
                self.thuntWdg = RO.Wdg.FloatEntry(houstonFrame,
                        readOnly = True,
			defValue = False,
                        helpText ='Time-hunt current offset (ns)',
                        autoIsCurrent = True,
                )
                self.thuntWdg.bind('<Return>',self.FuncCall(self.setPar,var='thunt'))
                self.apolloModel.thunt.addROWdg(self.thuntWdg,setDefault=True)
                
    # dskew gate slider
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

    # predskew gate slider
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

    # flashcum widget
                self.flashcumWdg = RO.Wdg.FloatEntry(houstonFrame,
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
                self.rxxTargWdgMoon = RO.Wdg.FloatEntry(self.p2,
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
                self.rxyTargWdgMoon = RO.Wdg.FloatEntry(self.p2,
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
			defValue = '2007\\070619\\070619-024307.run',
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
                
                self.catList = (("Error","red"), ("Warning","blue2"), ("Information","black"))
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
                self.statusbar.pack()

            # command/reply
                self.cmdRepLog = LogWdg.LogWdg(cmdRepFrame,
                                            catSet = [("Replies:", self.catList)],
                                            maxLines = 200,
                                            padx=5,pady=5)
                self.cmdRepLog.text.configure(height=5)
                gr_cmdRep.gridWdg(False,self.cmdRepLog,sticky="ew") # row=15
                    
                self.cmdWdg = RO.Wdg.CmdWdg(cmdRepFrame,cmdFunc=self.FuncCall(self.doLineCmd),width=130)
                gr_cmdRep.gridWdg(False,self.cmdWdg,sticky="ew") # row=15

                self.wdg2.logWdg=self.cmdRepLog
    # state butttons
                gr_butt.gridWdg('')
                gr_butt.gridWdg('')
                for i in range(len(self.stateDict)-1): # do not include EXIT (state = 0)
                    stateButt = RO.Wdg.Button(
			master=self.buttFrame,
			text=self.stateDict[i+1],
			command=self.FuncCall(self.doCmd,'apollo','houston %s' % string.lower(self.stateDict[i+1])),
                        helpText = 'Set houston state to %s' % self.stateDict[i+1],
                        state = 'disabled',width=8
                    )
                    self.stateButtArray.append(stateButt)
                    gr_butt.gridWdg(False,stateButt,sticky="ew")

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

###### laser control page

                self.wdg6 = stv.StvFrontEnd(stvFrame,self.cmdRepLog,self.tuiModel)

                self.wdg9 = laserKeypad.MyApp(laserFrame,self.cmdRepLog,self.tuiModel)

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
                
## Keyword Callback Functions

        def newOldFid(self, fiducialData, isCurrent, keyVar=None):
		"""Handle new fiducial data.
		"""
                if not isCurrent:
			return
		    
		shotNum = fiducialData[0]
		if shotNum < 0: return
		self.shotNum = self.shotNum + 1
                secAcc = fiducialData[1]    # accumulated seconds
                chanInten = fiducialData[2] # intensity
                photoD = fiducialData[3]    # photodiode time
		chanDict = fiducialData[5]  # channel:time array
		chanTimesCor = []

		if self.runStarted == 1:
                    self.shotsInSec += 1

		# remove any misbehaving APD channels (determined in 'Dark' callback)
                for j in self.omitTDCChan:
                    if j+1 in chanDict:
                        chanDict.pop(j+1)
                        
		chanNums = list(chanDict.keys())      # hit channels

                if 15 in chanNums:
                    nhit = len(chanDict)-1          # number of hits (except for chan 15 - the photodiode)
                else:
                    nhit = len(chanDict)
            
		if nhit < 0: return 

		chanTimes = list(chanDict.values())   # times of hit channels
		chanArr = num.zeros(NChan)      # array of 17 zeros to fill later

                self.totalFidNum = self.totalFidNum + nhit
                rate = num.true_divide(self.totalFidNum,self.shotNum)
                
        # set label widgets
                self.totalShots.set(self.shotNum)
                self.totalFid.set(self.totalFidNum)
                self.rateFid.set(rate)

		if len(chanNums): 
		   chanArr[chanNums] = chanTimes
				
                fidregnum = 0
                
                if chanTimes:
                   for i in range(len(chanTimes)):
                        if chanNums[i] != 15:
                # correct for channel offsets
                            chanTimes[i] = chanTimes[i] - self.chanOffset[chanNums[i]-1]

                            tcor = photoD-chanTimes[i]

                            chanTimesCor.append(tcor)
                            
                            if tcor < self.upperFid and tcor > self.lowerFid:
                                fidregnum = fidregnum+1
                                self.fidRegNum = self.fidRegNum + 1
                                self.fidRegRate = num.true_divide(self.fidRegNum,self.shotNum)       

            # update Fiducial return histogram
                             
                       
                            self.cc_return_t_all.addRow((tcor,))
                            self.cc_return_t.addRow((tcor,))

                            self.cc_return_raw_t_all.addRow((chanTimes[i],))
                            self.cc_return_raw_t.addRow((chanTimes[i],))

                            ntup = self.rep_cc[0].createNTuple()
                            ntup.getColumn(1)
                            fidHeight = max(ntup.getColumn(1))
				                         

                            self.fidRegLower.addRow((self.lowerFid,0))
                            self.fidRegLower.addRow((self.lowerFid,fidHeight))
                            
                            self.fidRegUpper.addRow((self.upperFid,0))
                            self.fidRegUpper.addRow((self.upperFid,fidHeight))
                            
            # Update APD hitgrid

                            self.chanAPD = self.chanMap[chanNums[i]-1]
                            weightfid = num.true_divide(1.0 - 0.0001*self.chanBackground[i],self.chanFlatCorr[i])

                            self.fid_hitgrid_all.addRow((num.remainder(self.chanAPD+4,4)+
                                                 0.5,3.5-num.floor((self.chanAPD+.5)/4),weightfid))

                            self.fid_hitgrid.addRow((num.remainder(self.chanAPD+4,4)+
                                                 0.5,3.5-num.floor((self.chanAPD+.5)/4),weightfid))

                        else:
                            self.fidRegRate = num.true_divide(self.fidRegNum,self.shotNum)

        # Update rate histogram
                self.cc_rate_all.addRow((nhit,))
                self.cc_rate.addRow((nhit,))

                self.fid_reg_all.addRow((fidregnum ,))
                self.fid_reg.addRow((fidregnum ,))

        # update registered indicators
                self.fidRegWdg.set(self.fidRegNum)
                self.fidRegRateWdg.set(self.fidRegRate)
                recRate = self.rep_cc_rate[1].getMean('x') # rate for last n shots shown on rate histogram
                self.fidRegRateRecWdg.set(recRate)
                    
    # Update Intensity histogram - not updating at present

                self.inten_all.addRow((chanInten,))
                self.inten.addRow((chanInten,))

                if shotNum > 0:
                    chanTimesCor.append(self.shotNum)
                    self.fidDat.append(chanTimesCor)
                else:
                    self.fidDat.append([-1,self.shotNum])

    # list of "all" data (accesible from hippodraw)

                """self.fid_data.addRow((self.shotNum,secAcc,chanInten,nhit,self.totalFidNum,
                                      rate,chanArr[14],
                                      chanArr[6],chanArr[2],chanArr[4],chanArr[12],chanArr[10],chanArr[0],chanArr[7],
                                      chanArr[8],chanArr[15],chanArr[5],chanArr[12],chanArr[4],chanArr[13],
                                      chanArr[9],chanArr[1]))"""

        

        def newFiducial(self, fiducialData, isCurrent, keyVar=None):
		"""Handle new fiducial data.
		"""
                if not isCurrent:
			return
		
		shotNum = fiducialData[0]
		if shotNum < 0: return
		self.shotNum = self.shotNum + 1
                secAcc = fiducialData[1]    # accumulated seconds
                chanInten = fiducialData[2] # intensity
                dphase = fiducialData[3]    # diffuser phase, new 03/07/06
                photoD = fiducialData[4]    # photodiode time
		chanDict = fiducialData[7]  # channel:time array
		chanTimesCor = []

            # update diffuser phase histogram
            
		self.dphase_all.addRow((dphase,))
                self.dphase.addRow((dphase,))

		if self.runStarted == 1:
                    self.shotsInSec += 1

		# remove any misbehaving APD channels (determined in 'Dark' callback)
                for j in self.omitTDCChan:
                    if j+1 in chanDict:
                        chanDict.pop(j+1)
                        
		chanNums = list(chanDict.keys())      # hit channels

                if 15 in chanNums:
                    nhit = len(chanDict)-1          # number of hits (except for chan 15 - the photodiode)
                else:
                    nhit = len(chanDict)
            
		if nhit < 0: return 

		chanTimes = list(chanDict.values())   # times of hit channels
		chanArr = num.zeros(NChan)      # array of 17 zeros to fill later

                self.totalFidNum = self.totalFidNum + nhit
                rate = num.true_divide(self.totalFidNum,self.shotNum)
                
        # set label widgets
                self.totalShots.set(self.shotNum)
                self.totalFid.set(self.totalFidNum)
                self.rateFid.set(rate)

		if len(chanNums): 
		   chanArr[chanNums] = chanTimes
				
                fidregnum = 0
                
                if chanTimes:
                   for i in range(len(chanTimes)):
                        if chanNums[i] != 15:
                # correct for channel offsets
                            chanTimes[i] = chanTimes[i] - self.chanOffset[chanNums[i]-1]

                            tcor = photoD-chanTimes[i]

                            chanTimesCor.append(tcor)
                            
                            if tcor < self.upperFid and tcor > self.lowerFid:
                                fidregnum = fidregnum+1
                                self.fidRegNum = self.fidRegNum + 1
                                self.fidRegRate = num.true_divide(self.fidRegNum,self.shotNum)       

                            self.fidTimeSeries_all.addRow((self.shotNum, tcor))
                            self.fidTimeSeries.addRow((self.shotNum,tcor))
                            self.fidTimeSeries_raw_all.addRow((self.shotNum, chanTimes[i]))
                            self.fidTimeSeries_raw.addRow((self.shotNum, chanTimes[i]))

            # update Fiducial return histogram
                             
                            self.cc_return_t_all.addRow((tcor,))
                            self.cc_return_t.addRow((tcor,))

                            self.cc_return_raw_t_all.addRow((chanTimes[i],))
                            self.cc_return_raw_t.addRow((chanTimes[i],))

                            self.fpd_all.addRow((photoD-self.tdc_target,))
                            self.fpd.addRow((photoD-self.tdc_target,))

                            ntup = self.rep_cc[0].createNTuple()
                            ntup.getColumn(1)
                            fidHeight = max(ntup.getColumn(1))

                            self.fidRegLower.addRow((self.lowerFid,0))
                            self.fidRegLower.addRow((self.lowerFid,fidHeight))
                            
                            self.fidRegUpper.addRow((self.upperFid,0))
                            self.fidRegUpper.addRow((self.upperFid,fidHeight))
                            
            # Update APD hitgrid

                            self.chanAPD = self.chanMap[chanNums[i]-1]
                            weightfid = num.true_divide(1.0 - 0.0001*self.chanBackground[i],self.chanFlatCorr[i])

                            self.fid_hitgrid_all.addRow((num.remainder(self.chanAPD+4,4)+
                                                 0.5,3.5-num.floor((self.chanAPD+.5)/4),weightfid))

                            self.fid_hitgrid.addRow((num.remainder(self.chanAPD+4,4)+
                                                 0.5,3.5-num.floor((self.chanAPD+.5)/4),weightfid))

                        else:
                            self.fidRegRate = num.true_divide(self.fidRegNum,self.shotNum)

        # Update rate histogram
                self.cc_rate_all.addRow((nhit,))
                self.cc_rate.addRow((nhit,))

                self.fid_reg_all.addRow((fidregnum ,))
                self.fid_reg.addRow((fidregnum ,))

        # update registered indicators
                self.fidRegWdg.set(self.fidRegNum)
                self.fidRegRateWdg.set(self.fidRegRate)
                recRate = self.rep_cc_rate[1].getMean('x') # rate for last n shots shown on rate histogram
                self.fidRegRateRecWdg.set(recRate)
                    
    # Update Intensity histogram - not updating at present

                if chanInten < 0:
                    self.noConvergence+=1
                    self.convWdg.set(self.noConvergence)
                    #canvas.addText(self.inten_hist,'No convergences = %d' % self.noConvergence)
                else:
                    self.inten_all.addRow((chanInten/1000.,))
                    self.inten.addRow((chanInten/1000.,))
                    

                if shotNum > 0:
                    chanTimesCor.append(self.shotNum)
                    self.fidDat.append(chanTimesCor)
                
                else:
                    self.fidDat.append([-1,self.shotNum])

    # list of "all" data (accesible from hippodraw)

                """self.fid_data.addRow((self.shotNum,secAcc,chanInten,nhit,self.totalFidNum,
                                      rate,chanArr[14],
                                      chanArr[6],chanArr[2],chanArr[4],chanArr[12],chanArr[10],chanArr[0],chanArr[7],
                                      chanArr[8],chanArr[15],chanArr[5],chanArr[12],chanArr[4],chanArr[13],
                                      chanArr[9],chanArr[1]))"""
                

        def newLunar(self, lunarData, isCurrent, keyVar=None):
		"""Handle new lunar data.
		"""
		if not isCurrent:
			return
		
		shotNum = lunarData[0]# lunar shot number
		if shotNum < 0: return
		self.shotNumLun = self.shotNumLun+1 # lunar shot number
		self.totalLunShots.set(self.shotNumLun)
		chanDict = lunarData[6]             # channel:time array

                # get rid of bad channels as determined from Dark data
		for j in self.omitTDCChan:
                    if j+1 in chanDict:
                        chanDict.pop(j+1)
                        
		secAcc = lunarData[1]           # accumulated seconds
		chanNums = list(chanDict.keys())      # channels hit
		nhit = lunarData[4]             # number of lunar hits
		chanTimes = list(chanDict.values())   # time of hits
		chanTimesCor =[]
		chanPred = lunarData[2]         # tpred
		chanArr = num.zeros(NChan)

        # "..Here" refers to points at this guiding offset for tracking plots

                self.shotsHere = self.shotsHere + 1
                self.shotsRxx = self.shotsRxx + 1
		self.totalLunNum = self.totalLunNum + len(chanNums)
		self.lunNumHere = self.lunNumHere + len(chanNums)
		self.lunNumRxx = self.lunNumRxx + len(chanNums)
		self.lunRateHere = num.true_divide(self.lunNumHere,self.shotsHere)
		self.lunRateRxx = num.true_divide(self.lunNumRxx,self.shotsRxx)

                self.lunRegNum = 0
                
                if chanTimes: # if there are lunar returns...

                    chanArr[chanNums] = chanTimes
                    
                    for i in range(len(chanTimes)):

                # correct for channel offsets
                        chanTimes[i] = chanTimes[i] - self.chanOffset[chanNums[i]-1]

                        if chanTimes[i] - chanPred < self.upper and chanTimes[i] - chanPred > self.lower:
                            self.lunRegNum = self.lunRegNum + 1
                            self.lunRegNumHere = self.lunRegNumHere + 1
                            self.lunRegNumRxx = self.lunRegNumRxx + 1
                            #self.lunRegRate = num.true_divide(self.lunRegNum,self.shotNumLun)
                            self.lunRegRateHere = num.true_divide(self.lunRegNumHere,self.shotsHere)
                            self.lunRegRateRxx = num.true_divide(self.lunRegNumRxx,self.shotsRxx)
                            self.totalLunRegNum = self.totalLunRegNum + 1
                            if self.hitgridReg == True:
                                self.chanAPD = self.chanMap[chanNums[i]-1]
                                weight = num.true_divide(1.0 - 0.0001*self.chanBackground[i],self.chanFlatCorr[i])
                                self.lun_hitgrid_all.addRow((num.remainder(self.chanAPD+4,4)+0.5,3.5-
                                                     num.floor((self.chanAPD+.5)/4),weight))
                                self.lun_hitgrid.addRow((num.remainder(self.chanAPD+4,4)+
                                                         0.5,3.5-num.floor((self.chanAPD+.5)/4),weight))

                    #self.lun_background_all.addRow((nhit-self.lunRegNum ,))
                    #self.lun_background.addRow((nhit-self.lunRegNum ,))

                    self.lunBackgroundNum = self.totalLunNum - self.totalLunRegNum

                # tracking stuff
                    #self.rateHere = self.lunRegRateHere
                    #self.track_ret.addRow((self.offsetAz, self.offsetEl, self.rateHere))

                    if shotNum > 50:
                        self.rateHere = self.lunRegRateHere
                        self.track_ret.addRow((self.offsetAz, self.offsetEl, self.rateHere))
                    if not len(self.track_ret_all.getColumn(2)): 
                        self.track_APD.setRange('z',0.,self.rateHere)
                    elif len(self.track_ret_all.getColumn(2)) and self.rateHere > max(self.track_ret_all.getColumn(2)):
                        self.track_APD.setRange('z',0.,self.rateHere)
                    elif len(self.track_ret_all.getColumn(2)) and self.rateHere < max(self.track_ret_all.getColumn(2)):
                        self.track_APD.setRange('z',0.,max(self.track_ret_all.getColumn(2)))

                    if shotNum > 50: 
                        self.rateRxx = self.lunRegRateRxx
                        self.rxxRate.addRow((self.rxx, self.rxy, self.rateRxx))
                    if not len(self.rxxRate_all.getColumn(2)):
                        self.rxxRate_disp.setRange('z',0.,self.rateRxx)
                    elif len(self.rxxRate_all.getColumn(2)) and self.rateRxx > max(self.rxxRate_all.getColumn(2)):
                        self.rxxRate_disp.setRange('z',0.,self.rateRxx)
                    elif len(self.rxxRate_all.getColumn(2)) and self.rateRxx < max(self.rxxRate_all.getColumn(2)):
                        self.rxxRate_disp.setRange('z',0.,max(self.rxxRate_all.getColumn(2)))
                
                # set tk panel indicators
                    self.totalLun.set(self.totalLunNum)
                    self.rateLun.set(num.true_divide(self.totalLunNum,self.shotNumLun))

                    tdcBins = float(min([self.gateWidth*800 - 2600,4096]))
                    self.regLun.set(self.totalLunRegNum)
                    
                    #tdcBins = max([self.gatewidth*800 - 2600,4096])
                    self.yield_est = self.totalLunRegNum-self.binForReg*num.true_divide(self.totalLunNum-self.totalLunRegNum,3900-self.binForReg)
                
                    #self.regLun.set(self.yield_est)
                    self.regRateLun.set(num.true_divide(self.totalLunRegNum,self.shotNumLun))
                    #self.regRateLun.set(num.true_divide(self.yield_est,self.shotNumLun))
                    self.lunBackgroundWdg.set(self.yield_est)
                    self.lunBackgroundRateWdg.set(num.true_divide(self.lunBackgroundNum,self.shotNumLun))

                # Update return time histogram
                    for i in range(len(chanTimes)):
                        self.lun_return_t_all.addRow((chanTimes[i]-chanPred,))
                        self.lun_return_t.addRow((chanTimes[i]-chanPred,))

                        self.lun_return_raw_t_all.addRow((chanTimes[i],))
                        self.lun_return_raw_t.addRow((chanTimes[i],))
                
                # Update lunar hitgrid

                    if self.hitgridReg == False:
                        for i in range(len(chanTimes)):
                            self.chanAPD = self.chanMap[chanNums[i]-1]
                            weight = num.true_divide(1.0 - 0.0001*self.chanBackground[i],self.chanFlatCorr[i])
                            self.lun_hitgrid_all.addRow((num.remainder(self.chanAPD+4,4)+0.5,3.5-num.floor((self.chanAPD+.5)/4),weight))
                            self.lun_hitgrid.addRow((num.remainder(self.chanAPD+4,4)+0.5,3.5-num.floor((self.chanAPD+.5)/4),weight))

                #Update lunar rate histogram (default displays all hits)

                ntup = self.rep_lun[0].createNTuple()
                ntup.getColumn(1)
                lunHeight = max(ntup.getColumn(1))
                
                self.lunRegLower.addRow((self.lower,0))
                self.lunRegLower.addRow((self.lower,lunHeight))
                
                self.lunRegUpper.addRow((self.upper,0))
                self.lunRegUpper.addRow((self.upper,lunHeight))
                
                self.lun_background_all.addRow((self.lunRegNum ,)) # ignore variable name for now
                self.lun_background.addRow((self.lunRegNum ,))

                recRateLun = self.rep_lun_rate[1].getMean('x') #rate for last n shots shown on rate histogram 
                self.regRateRecLun.set(recRateLun)

                self.lun_rate_all.addRow((len(chanNums),))
                self.lun_rate.addRow((len(chanNums),))

                numReg=0

                if shotNum > self.rateReserve:
                    self.lunTimeSeriesReg_all.addRow((shotNum, recRateLun))
                    self.lunTimeSeriesReg.addRow((shotNum, recRateLun))

        # update time series plot of lunar returns
		if len(chanNums) and self.shotNumLun > 1:

                        for i in range(len(chanTimes)):
                            chanTimesCor.append(chanTimes[i]-chanPred)
                            self.lunTimeSeries_all.addRow((shotNum, chanTimesCor[i]))
                            self.lunTimeSeries.addRow((shotNum, chanTimesCor[i]))
                
                            if chanTimes[i]-chanPred < self.upper and chanTimes[i]-chanPred > self.lower:
                                numReg = numReg+1
                        
                        chanTimesCor.append(shotNum)
                        self.lunDat.append(chanTimesCor)

                        xmin=min(self.lunTimeSeries.getColumn(0))

                        self.lunRegLowerSeries.addRow((xmin,self.lower))
                        self.lunRegLowerSeries.addRow((shotNum,self.lower))

                        self.lunRegUpperSeries.addRow((xmin,self.upper))
                        self.lunRegUpperSeries.addRow((shotNum,self.upper))
                        
                else:
                        self.lunDat.append([-1,shotNum])
                        
                if self.shotNumLun > 1:
                    self.changes_all.addRow((shotNum,0,(self.changeState-1.)*2000.))
                    self.changes.addRow((shotNum,0,(self.changeState-1.)*2000.))

                if shotNum > self.rateReserve:
                    self.lunseries.setRange('y',min(self.lunTimeSeriesReg.getColumn(1)),0.01+max(self.lunTimeSeriesReg.getColumn(1)))
                
                if self.shotNumLun == 2:
                    self.lunSeriesAll.setRange('y',-480,480)
                    self.lun_return_hist.setRange('x',-2000,2000)
                    self.cc_return_hist.setRange('x',-2500,2500)
                    self.raw_hist.setRange('x',0,4000)
                    self.rep_cc[0].setBinWidth('x',40)
                    self.rep_lun[0].setBinWidth('x',40)
                    self.rep_raw[0].setBinWidth('x',40)
                    self.rep_raw[1].setBinWidth('x',40)

                if self.rasterShots:
                    rem = num.remainder(self.shotsHere,int(self.rasterShots))

                if self.raster==1 and self.rasterShots>0 and self.shotsHere > 0 and rem==0:
                    
                    offMag=self.rasterMag

                    guideDict = {'up':(0.,1.),'down':(0.,-1.), 'left':(-self.altCor,0.),'right':(self.altCor,0.),
                                 'upLeft':(-self.altCor,1.)} # corrected for Cos(Alt)
                    offDir = guideDict.get(self.rasterList[self.irasterGuide])
                    
                    offx = offDir[0]*offMag
                    offy = offDir[1]*offMag

                    if num.sqrt(offx**2 + offy**2) < num.true_divide(0.75,3600):
                        self.doCmd('tcc','offset guide %f,%f' % (offx,offy))
                    else:
                        self.doCmd('tcc','offset guide %f,%f /computed' % (offx,offy))
                    
                    self.irasterGuide += 1                    

                    if self.irasterGuide == 9 and self.irasterRxx < 8 and self.offMag != 0.0:
                        self.irasterGuide = 0
                        self.offsetGuide(self.rasterList[self.irasterRxx])
                        self.irasterRxx += 1
                    elif self.irasterGuide == 9 and self.irasterRxx == 8 and self.offMag != 0.0:
                        self.offsetGuide('up')
                        self.offsetGuide('left')
                        self.raster = 0
                        self.irasterGuide = 0
                        self.irasterRxx = 0 
                        self.rasterOnButton.configure(text = 'Raster Ended')
                    elif self.irasterGuide == 9 and self.offMag == 0.0:
                        self.raster = 0
                        self.irasterGuide = 0
                        self.irasterRxx = 0 
                        self.rasterOnButton.configure(text = 'Raster Ended')
                    
                        
        # list of "all" data (accesible from hippodraw)
      
                """self.lun_data.addRow((self.shotNumLun, self.offsetNum,self.offsetAz, self.offsetEl, secAcc, chanPred,
                                chanPred, nhit, self.totalLunNum, self.totalLunRegNum, self.lunBackgroundNum,
                                num.true_divide(self.totalLunNum,self.shotNumLun),
                                num.true_divide(self.totalLunRegNum,self.shotNumLun),
                                num.true_divide(self.lunBackgroundNum,self.shotNumLun),chanArr[14],chanArr[6],chanArr[2],
                                chanArr[4],chanArr[12],chanArr[10],chanArr[0],chanArr[7],chanArr[8],chanArr[15],
                                chanArr[5],chanArr[12],chanArr[4],chanArr[13],chanArr[9],chanArr[1]))"""
                
                
        def newStare(self, stareData, isCurrent, keyVar=None):
		"""Handle new stare data.
		"""
		if not isCurrent:
			return

                for j in self.omitTDCChan:   # omit channels determined from Dark data
                    stareData[j] = 0
                    
		self.stareShot = self.stareShot+1

		self.staresHere = self.staresHere + 1 # stares taken at this guide offset
		self.stareNumHere = self.stareNumHere + num.add.reduce(stareData) - .05*self.sumDarkChans
		self.stareRateHere = num.true_divide(self.stareNumHere,self.staresHere)
		self.stare_rate.addRow((self.offsetAz, self.offsetEl, self.stareRateHere))

                self.stareTimeSeries_all.addRow((self.stareShot,(num.add.reduce(stareData)-.05*self.sumDarkChans)))
                self.stareTimeSeries.addRow((self.stareShot,(num.add.reduce(stareData)-.05*self.sumDarkChans)))

                for i in range(len(stareData)):
                    chanAPD = self.chanMap[i] # not (i - 1) here because no channel # (starts at 0)
                    self.stare_all.addRow((num.remainder(chanAPD+4,4) + 0.5,3.5-num.floor((chanAPD+.5)/4),
                                           (stareData[i]-.05*self.chanBackground[i])))  #.05 = (500 gates)/(10,000 gates)
                    self.stare.addRow((num.remainder(chanAPD+4,4) + 0.5,3.5-num.floor((chanAPD+.5)/4),
                                       (stareData[i]-.05*self.chanBackground[i])))  #.05 = (500 gates)/(10,000 gates)
		
        def newDark(self, darkData, isCurrent, keyVar=None):
		"""Handle new dark background data. values are for 10,000 gates
		"""
		if not isCurrent:
			return
		    
		#self.omitTDCChan = [] # This will be a list of TDC channels omitted from the plots

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
                    self.stare.addRow((num.remainder(chanAPD+4,4) + 0.5,3.5-num.floor((chanAPD+.5)/4),                                      
                                       .05*self.chanBackground[i]))  #.05 = (500 gates)/(10,000 gates)


                for j in self.omitTDCChan:
                    chanAPD = self.chanMap[j]
                    self.darkWdgDict[chanAPD].set(False)
                    
                print(self.omitTDCChan)

        def newFlat(self, flatData, isCurrent, keyVar=None):
		"""Handle newflat data. values are for 10,000 gates
		"""
		if not isCurrent:
			return

		#flatData.pop(0)

                nflat = 0
                flatsum = 0
                
                usable = list(num.zeros(16))
                self.chanFlatCorr= list(num.zeros(16))
                
		for i in range(len(flatData)):  
                    self.chanFlat[i] = flatData[i] - self.chanBackground[i]
                    usable[i] = self.chanFlat[i]
                
                for j in self.omitTDCChan:   # omit channels determined from Dark data
                    usable[j] = 24000       # put a bogus number in the omitted channel slots
                                            # total counts in a channel should never exceed 24000 
                for i in range(16):
                    if usable[i] < 24000:
                        flatsum += usable[i]

                ave = num.true_divide(flatsum,(16-usable.count(24000)))

                for i in range(len(self.chanFlat)):  
                    self.chanFlatCorr[i] = num.true_divide(self.chanFlat[i],ave)

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
            
                offsetAzNew = num.true_divide(offsetData[0].pos,self.altCor)*3600.0  #New Az offset position
                                                                                     #in arcsec, corected for cos(alt)
		offsetElNew = offsetData[1].pos*3600.0  #New Alt (El) offset in arcsec

		print(offsetAzNew,offsetElNew) # print to CRT

		self.trackHist.addRow((self.offsetNum,self.offsetAz,self.offsetEl,self.rateHere))

                if  self.rateHere > 0.0:
                    self.track_ret_all.addRow((self.offsetAz,self.offsetEl,self.rateHere))

                if  self.stareRateHere > 0.0:
                    self.stare_rate_all.addRow((self.offsetAz,self.offsetEl,self.stareRateHere))

                self.shotsHere = 0
                self.lunNumHere = 0
                self.lunRateHere = 0
                self.lunRegNumHere = 0
                self.lunRegRateHere = 0
                self.rateHere = 0.0
                self.track_ret.clear()

                self.staresHere = 0
                self.stareNumHere = 0
                self.stareRateHere = 0.0
                self.stare_rate.clear()

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
                
                offsetAzNew = float(data[0])  #New Az offset position in arcsec, corected for cos(alt)
		offsetElNew = float(data[1])  #New Alt (El) offset in arcsec

		self.trackHist.addRow((self.offsetNum,self.offsetAz,self.offsetEl,self.rateHere))

                if  self.rateHere > 0.0:
                    self.track_ret_all.addRow((self.offsetAz,self.offsetEl,self.rateHere))

                if  self.stareRateHere > 0.0:
                    self.stare_rate_all.addRow((self.offsetAz,self.offsetEl,self.stareRateHere))

                self.shotsHere = 0
                self.lunNumHere = 0
                self.lunRateHere = 0
                self.lunRegNumHere = 0
                self.lunRegRateHere = 0
                self.rateHere = 0.0
                self.track_ret.clear()

                self.staresHere = 0
                self.stareNumHere = 0
                self.stareRateHere = 0.0
                self.stare_rate.clear()

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
                    self.altCor = num.true_divide(1.0,num.cos(num.pi*num.true_divide(self.axisPos[1],180.)))
                    print(axePosData[0], axePosData[1], self.altCor)

                    if not self.lockStatus and None not in newAxisPos:
                        self.doCmd('apollo','houston set axePos="%.4f %.4f %.4f"' % (axePosData[0],axePosData[1],axePosData[2]),write=False)
                        
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
		"""Handle new flowmeter data.
		"""
		global gpsi,HOUSTON
		
                if not isCurrent:
		    return

		HOUSTON = 1

                if gpsi == 0: # on first gpstrig, start recording run seconds, set run state                    
                    gpsi = 1
                    self.runStarted = 1
                    self.shotsInSec = 0
            
                    self.gauss.setParameters([self.histReserve, 6. ,1.])

                else:
                    self.totTime.set(self.shotsInSec) # for subsequent reads, update shot per second display

                    if self.shotsInSec < 19:
                        self.totTime.configure(background = 'red',foreground = 'white')
                    else:
                        self.totTime.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))    

                    self.shotsInSec = 0

                    if self.shotNum > 0 :
                        self.gauss.setParameters([self.intenReserve, 6. ,1.])
                        self.gauss.fit()

        def newState(self, stateData, isCurrent, keyVar=None):
		"""Handle new state data.
		"""
		if not isCurrent:
			return

                state = stateData[0]

                if state == 3 and state != self.state:
                        self.resetCounters()

                if state != 10:
                    self.laser_powerWdg.configure(background='pink')
                if state == 10:
                    self.laser_powerWdg.configure(background=Tk.Label().cget("background"))
                    
                self.state = state
		self.stateWdg.set(self.state)
		for i in range(len(self.stateButtArray)):
                    self.stateButtArray[i].configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))
		self.stateButtArray[self.state-1].configure(background='green')

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

		self.nrunsWdg.set(nrunsData[0])

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

		xlower = -tdc_target
		xupper = 4000 - tdc_target

		self.lun_return_hist.setRange('x',xlower,xupper)

	def newRunfidgw(self, runfidgwData, isCurrent, keyVar=None):
		"""Handle new gatewidth data.
		"""
		if not isCurrent:
			return

		if runfidgwData[0] & 0xf0 != self.gateWidth & 0xf0:
                        self.doCmd('apollo','houston set gatewidth=%d' % runfidgwData[0])

		self.runfidgwWdg.set(runfidgwData[0])
		dat = runfidgwData[0]

		self.runfidgw = runfidgwData[0]

		xlower = -8100+800*dat
		xupper = -3100+800*dat

		self.cc_return_hist.setRange('x',xlower,xupper)

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

		if  self.rateRxx > 0.0:
                    self.rxxRate_all.addRow((self.rxx,self.rxy,self.rateRxx))

		self.rxx = vposxData[0]
		self.rxxcumWdg.set(self.rxx)
		self.rxxCumWdgTune.set(self.rxx)
		self.changeHappened()

                if self.runStarted == 1:
                    zmax = max(self.rxxRate_all.getColumn(2))
                    self.rxxRate_disp.setRange('z',0.,zmax)

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
                self.rxxRate.clear()

                if self.runStarted == 1:
                    zmax = max(self.rxxRate_all.getColumn(2))
                    self.rxxRate_disp.setRange('z',0.,zmax)
		
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
	    
                dtr = num.pi/180.
                ccdx = num.cos(dtr*21.3)*self.rxxTarg + num.sin(dtr*21.3)*self.rxyTarg
                ccdy = -num.sin(dtr*21.3)*self.rxxTarg + num.cos(dtr*21.3)*self.rxyTarg
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

                    a=self.nb.component(' Main -tab')
                    a.configure(background='blue',foreground='white')

                if blockremainingData[0] < 10:
                    if self.wdgFlag == 0:
                        self.wdgFlag = 1
                        self.afscWdg = Tk.Label(master=self.spaceFrame)
                        self.afscWdg.pack()
                        self.afscWdg.configure(image=self.AFSCImage)
                    self.spaceAlertWdg.configure(background = 'yellow')
                    self.spaceAlertWdg.configure(text='Time remaining in blockage: %d s' % blockremainingData[0])

                    a=self.nb.component(' Main -tab')
                    a.configure(background='blue',foreground='white')
                    
                if blockremainingData[0] < 3:
                    if self.wdgFlag == 1:
			self.afscWdg.destroy()
                    	self.wdgFlag = 0
                    self.spaceAlertWdg.configure(background = 'green')
                    self.spaceAlertWdg.configure(text='No Blockage')

                    a=self.nb.component(' Main -tab')
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
			return

		self.chanOffset = []
		chanOffRaw = apdtofpdData
		nGood = 16-chanOffRaw.count(0.0)
                mn = num.add.reduce(chanOffRaw)/nGood

                for i in range(16):
                    if chanOffRaw[i]:
                        self.chanOffset.append(int(round(chanOffRaw[i]-mn)))
                    else:
                        self.chanOffset.append(0)

                print(self.chanOffset)

        def newDphase(self, dphaseData, isCurrent, keyVar=None):
                """ Handle new dphase data
                """
                if not isCurrent:
			return
                dphase = dphaseData[0]
                self.dphase_all.addRow((dphase,))
                self.dphase.addRow((dphase,))
                
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
                self.lPowerNum += 1
                
		laser_power = bolopowerData[0]
		self.laser_powerWdg.set(laser_power)

		self.lPowerTimeSeries.addRow((self.lPowerNum,laser_power))
		self.lPowerTimeSeries20.addRow((self.lPowerNum,laser_power))
		self.lPowerTimeSeries200.addRow((self.lPowerNum,laser_power))

		mean1 = self.lPowerTimeSeries20.getColumn('Bolometer Reading')
		mean2 = num.true_divide(num.add.reduce(mean1),len(mean1))
		self.laser_powerAveWdg.set(mean2)
		self.lPowerAveTimeSeries.addRow((self.lPowerNum,mean2))

		p = self.lPowerTimeSeries200.getColumn('Bolometer Reading')
		pmax=max(p)
		self.hiWdg.set(pmax)
		pmin=min(p)
		self.loWdg.set(pmin)

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
                """ Handle new error text
                """
                    
                if not isCurrent: 
			return

                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                self.cmdRepLog.addOutput(timeStr + "       " + iData[0] + "\n")

        def newH(self, hData, isCurrent, keyVar=None):
                """ Handle new error text
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
                    a=self.nb.component('Alarms-tab')
                    a.configure(background='pink',foreground='white')
                    #self.excLog.addOutput(timeStr + "     " + 'alarms = '+ alarmsData[0] + "\n",category="Error")
                    #self.cmdRepLog.addOutput(timeStr + "       " + 'alarms = '+ alarmsData[0] + "\n",category="Error")
                elif state == 0:
                    self.alarmState = False
                    a=self.nb.component('Alarms-tab')
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
                    a=self.nb.component('Alarms-tab')
                    a.configure(background='red',foreground='white')
                    #self.excLog.addOutput(timeStr + "     " + 'alarms_unack = ' + alarms_unackData[0] + "\n",category="Error")
                    #self.cmdRepLog.addOutput(timeStr + "       " + 'alarms_unack = ' + alarms_unackData[0] + "\n",category="Error")
                elif state == 0:
                    if self.alarmState:
                        a=self.nb.component('Alarms-tab')
                        a.configure(background='pink',foreground='white')
                    else:
                        a=self.nb.component('Alarms-tab')
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
                    
                if not isCurrent: 
			return

		self.cmdText = cmdTextData[0]

		checkID = self.cmdr[0:4]

		invalidForms = ['houston set axePos','houston set airtem','houston set pressu','houston set humidi',
                                'houston set guideO','houston set boreOf']
		if self.cmdText[0:18] in invalidForms:
                    return

		me = self.tuiModel.getCmdr()
		timeStr = time.strftime("%H:%M:%S", time.gmtime())
		
		if checkID == 'ZA01' and self.cmdr != me and self.cmdActor != 'keys':
                    self.cmdRepLog.addOutput('%s %s to %s %s %s \n' % (timeStr,self.cmdr,self.cmdActor.upper(),str(self.cmdrMID),self.cmdText))
                    	
## Various Function definitions for buffer/clear controls and entry boxes, etc.

        def clearTab(self):
                self.doLineCmd('set alarms_unack=0')
                #a=self.nb.component('Alarms-tab')
                #a.configure(background=Tk.Label().cget("background"),foreground=Tk.Label().cget("foreground"))
                

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

            ntup = self.rep_cc[0].createNTuple()
            ntup.getColumn(1)
            fidHeight = max(ntup.getColumn(1))                    

            self.fidRegLower.addRow((self.lowerFid,0))
            self.fidRegLower.addRow((self.lowerFid,fidHeight))
                
            self.fidRegUpper.addRow((self.upperFid,0))
            self.fidRegUpper.addRow((self.upperFid,fidHeight))
            
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
                           'alarms_unack': self.alarms_unackWdg}
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

                """ntup = self.rep_lun[0].createNTuple()
                ntup.getColumn(1)
                lunHeight = max(ntup.getColumn(1))                    

                self.lunRegLower.addRow((self.lower,0))
                self.lunRegLower.addRow((self.lower,lunHeight))
                
                self.lunRegUpper.addRow((self.upper,0))
                self.lunRegUpper.addRow((self.upper,lunHeight))

                xmin=min(self.lunTimeSeries.getColumn(0))

                self.lunRegLowerSeries.addRow((xmin,self.lower))
                self.lunRegLowerSeries.addRow((self.shotNumLun,self.lower))
                
                self.lunRegUpperSeries.addRow((xmin,self.upper))
                self.lunRegUpperSeries.addRow((self.shotNumLun,self.upper))"""

        def predSkew1(self,evt):

                #if self.shotNumLun < 2: return
                self.regCenter=self.predskewSlider.get()
                self.lower=self.regCenter-self.binForReg/2
                self.upper=self.regCenter+self.binForReg/2

                ntup = self.rep_lun[0].createNTuple()
                ntup.getColumn(1)
                lunHeight = max(ntup.getColumn(1))

                self.lunRegLower.addRow((self.lower,0))
                self.lunRegLower.addRow((self.lower,lunHeight))
                
                self.lunRegUpper.addRow((self.upper,0))
                self.lunRegUpper.addRow((self.upper,lunHeight))

                if len(self.lunTimeSeries.getColumn(0)) >0:
                    xmin=min(self.lunTimeSeries.getColumn(0))
                else:
                    xmin=0

                self.lunRegLowerSeries.addRow((xmin,self.lower))
                self.lunRegLowerSeries.addRow((self.shotNumLun,self.lower))
                
                self.lunRegUpperSeries.addRow((xmin,self.upper))
                self.lunRegUpperSeries.addRow((self.shotNumLun,self.upper))

        def predSkew2(self,evt):
                self.regCenter=self.predskewSlider.get()
                self.lower=self.regCenter-self.binForReg/2
                self.upper=self.regCenter+self.binForReg/2

                self.doLineCmd('set predskew=%d' % self.regCenter)

                #if not self.lockStatus:
                self.predskewSlider.configure(from_ = self.regCenter-400)
                self.predskewSlider.configure(to = self.regCenter+400)
                self.lunSeriesAll.setRange('y',self.regCenter-480,self.regCenter+480)

                if not self.lunTimeSeries_all.rows:
                    shotNum=[1]
                else:
                    shotNum = list(self.lunTimeSeries_all.getColumn(0))
                
                all = list(self.lunTimeSeries_all.getColumn(1))

                regNum = 0
                regRecNum = 0
                
                for i in range(len(all)):
                    if all[i] > self.lower and all[i] < self.upper:
                            regNum = regNum+1

                regRate = float(regNum)/shotNum[-1]

                self.totalLunRegNum = regNum
                
                tdcBins = min([self.gateWidth*800 - 2600,4096])
                self.yield_est = self.totalLunRegNum-self.binForReg*num.true_divide(self.totalLunNum-self.totalLunRegNum,3900-self.binForReg)

                self.lunBackgroundWdg.set(self.yield_est)
                
                self.regLun.set(self.totalLunRegNum)
                self.regRateLun.set(regRate)

                self.lun_background_all.clear()
                self.lun_background.clear()

                for i in range(len(self.lunDat)):
                    regNum = 0
                    if self.lunDat[i][0] > -1:
                        times = self.lunDat[i][:-1]
                        for j in range(len(times)):
                            if times[j] > self.lower and times[j] < self.upper:
                                regNum = regNum + 1
                    else:
                        regNum = 0
                        
                    self.lun_background_all.addRow((regNum,))
                     
                for (var,var_all,var_len,res) in ((self.lun_background,self.lun_background_all,
                                                   self.lun_background_all.rows,self.rateReserve),):#,

                    if var_len - res < 0:
                        var_start = 0
                        itLen = var_len
                    else:
                        var_start = var_len - res
                        itLen = res 

                    for j in range(itLen):
                        var.addRow(var_all.getRow(j + var_start))

                recRateLun = self.rep_lun_rate[1].getMean('x') #rate for last n shots shown on rate histogram 
                self.regRateRecLun.set(recRateLun)
                
                self.lunRegNumHere = 0
                self.lunRegRateHere = 0
                self.shotsHere = 0

                self.changeHappened()
                          
        def fidSkew2(self,evt):
                self.regCenterFid = self.fidskewWdg.get()
                self.lowerFid = self.regCenterFid-self.binForRegFid/2
                self.upperFid = self.regCenterFid+self.binForRegFid/2

                if not self.fidTimeSeries_all.rows:
                    shotNum=[1]
                else:
                    shotNum = list(self.fidTimeSeries_all.getColumn(0))
                
                all = list(self.fidTimeSeries_all.getColumn(1))

                regNum = 0
                regRecNum = 0
                
                for i in range(len(all)):
                    if all[i] > self.lowerFid and all[i] < self.upperFid:
                            regNum = regNum+1

                regRate = float(regNum)/shotNum[-1]

                self.fidRegNum = regNum
                self.fidRegWdg.set(regNum)
                self.fidRegRateWdg.set(regRate)

                self.fid_reg_all.clear()
                self.fid_reg.clear()

                for i in range(len(self.fidDat)):
                    regNum = 0
                    if self.fidDat[i][0] > -1:
                        times = self.fidDat[i][:-1]
                        for j in range(len(times)):
                            if times[j] > self.lowerFid and times[j] < self.upperFid:
                                regNum = regNum + 1
                    else:
                        regNum = 0
                        
                    self.fid_reg_all.addRow((regNum,))
                     
                for (var,var_all,var_len,res) in ((self.fid_reg,self.fid_reg_all,
                                                   self.fid_reg_all.rows,self.rateReserve),):

                    if var_len - res < 0:
                        var_start = 0
                        itLen = var_len
                    else:
                        var_start = var_len - res
                        itLen = res 

                    for j in range(itLen):
                        var.addRow(var_all.getRow(j + var_start))

                recRate = self.rep_cc_rate[1].getMean('x') #rate for last n shots shown on rate histogram 
                self.fidRegRateRecWdg.set(recRate)

        def setOff(self,evt,var):
            self.offString.set(float(self.offMagWdg.get())) # get offset magnitude from widget in arcsec
            self.offMag = num.true_divide(float(self.offMagWdg.get()),3600.) #offset increment magnitude in deg
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
            self.rxxOffMag = num.true_divide(float(self.rxxOffMagWdg.get()),3600.) #rxx offset increment magnitude in deg
            self.rxxOffMagWdg.setIsCurrent(True)

        def rasterSetOff(self,evt,var):
            self.rasterMag = num.true_divide(float(self.rasterMagWdg.get()),3600.) #guide offset increment magnitude in deg
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

                dtr = num.pi/180.

                #coordinate rotation angles

                W = 5.0*dtr
                cW = num.cos(W)
                sW = num.sin(W)
                X = 17.0*dtr
                cX = num.cos(X)
                sX = num.sin(X)
                Y = 21.0*dtr
                cY = num.cos(Y)
                sY = num.sin(Y)
                Z = 42.0*dtr
                cZ = num.cos(Z)
                sZ = num.sin(Z)
                
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
                    #theta = 21.*num.pi/180. # rotation angle of coordinates
                    #cTheta = num.cos(theta) # cosine rotation angle
                    #sTheta = num.sin(theta) # sine rotation angle

                    opticsDict = {'up':(0.,1.),'down':(0.,-1.),'left':(-1.,0.),'right':(1.,0.),
                                  'upLeft':(-1,1),'upRight':(1,1),
                                  'downLeft':(-1,-1),'downRight':(1,-1)} # motion direction optics
                    
                    #guideDict = {'up':(self.altCor*cTheta,sTheta),'down':(-self.altCor*cTheta,-sTheta),
                    #             'left':(-self.altCor*sTheta,cTheta),'right':(self.altCor*sTheta,-cTheta),
                    #             'upLeft':(self.altCor*(cTheta-sTheta)/num.sqrt(2),(sTheta+cTheta)/num.sqrt(2)),
                    #             'upRight':(self.altCor*(cTheta+sTheta)/num.sqrt(2),(sTheta-cTheta)/num.sqrt(2)),
                    #             'downLeft': (-self.altCor*(cTheta+sTheta)/num.sqrt(2),(-sTheta+cTheta)/num.sqrt(2)),
                    #             'downRight': (-self.altCor*(cTheta-sTheta)/num.sqrt(2),-(sTheta+cTheta)/num.sqrt(2))} # guide compensation

                    offDirOptics = opticsDict.get(var) # offset direction of rxx or rxy, from buttons
                    #offDirGuide = guideDict.get(var) # offset direction for guide offset

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

                    # corrected TWM 2015.12.20 remove extra offMag term
                    self.offx = self.altCor*(sY*opticsOffx + cY*opticsOffy)
                    self.offy = -cY*opticsOffx + sY*opticsOffy

                    if opticsOffx != 0.0 or opticsOffy != 0.0:
                        self.doCmd('apollo','houston vnudge %f %f' % (opticsOffx, opticsOffy))

                    if self.offMag != 0.0:
                        if num.sqrt(self.offx**2+self.offy**2) < num.true_divide(0.75,3600):
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
                        offx = (-cW*x-sW*y)*self.offMag
                        offy = (-sW*x+cW*y)*self.offMag

                    elif ccdCoords == True:
                        offx = (cZ*x+sZ*y)*self.offMag
                        offy = (sZ*x-cZ*y)*self.offMag

                    if self.offMag != 0.0:
                        if num.sqrt(offx**2 + offy**2) < num.true_divide(0.75,3600):
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
                        if num.sqrt(self.offsetAz**2+self.offsetEl**2) < 0.75:
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
                            self.offx = (sW*x-cW*y)*self.offMag  
                            self.offy = (-cW*x-sW*y)*self.offMag
                            
                        elif ccdCoords == True:
                            self.offx = (-sZ*x+cZ*y)*self.offMag  
                            self.offy = (cZ*x+sZ*y)*self.offMag

                        self.offx*=self.altCor # corrected for Cos(Alt)
                        
                        #self.doCmd('tcc','offset guide %f,%f /PAbsolute' % (self.offx,self.offy))
                        if num.sqrt(self.offx**2+self.offy**2) < num.true_divide(0.75,3600):
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
                        for j in range(itLen):circ_var.addRow(allVar.getRow(j + var_start))
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

            self.changes_all.addRow((self.shotNumLun,0.5,(self.changeState-1.)*2000.))
            self.changes.addRow((self.shotNumLun,0.5,(self.changeState-1.)*2000.))

        def vMove(self,evt):
            vx = float(self.rxxTargWdg.get())
            vy = float(self.rxyTargWdg.get())
            cmd = 'houston vmove %f %f' % (vx,vy)
            self.doCmd('apollo',cmd)

        def vMove2(self,evt):
            vx = float(self.rxxcumWdg.get())
            vy = float(self.rxycumWdg.get())
            cmd = 'houston vmove %f %f' % (vx,vy)
            self.doCmd('apollo',cmd)

        def clear(self, varlist):
            for i in range(len(varlist)):
                varlist[i].clear()

        def clearPower(self):
            varlist = (self.lPowerTimeSeries,self.lPowerTimeSeries20,self.lPowerTimeSeries200,
                       self.lPowerAveTimeSeries)
            for i in range(len(varlist)):
                varlist[i].clear()

            self.laser_powerWdg.set(0.00)   # laser power stuff
            self.laser_powerAveWdg.set(0.00)
            self.loWdg.set(0.00)
            self.hiWdg.set(0.00)

            self.lPowerNum = 0

        def setBackground(self, evt, var):
            var.setIsCurrent(False)

        def setCurrent(self, evt, var):
            var.setIsCurrent(True)

        def replay(self, evt):

                from . import TestData
                
                dataDir=pathStuff.dataDir()
                replayFile = self.replayWdg.get()
                replayStart = self.replayStartWdg.get()
                length = self.replayLengthWdg.get()
                if replayStart == 'None':
                    TestData.dispatchFile(dataDir+replayFile,None,length)
                else:
                    TestData.dispatchFile(dataDir+replayFile,replayStart,length)

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
                self.lun_hitgrid.clear()
                self.lun_hitgrid_all.clear()
                self.regButton.configure(text = 'Now: Reg')
            elif self.hitgridReg == True:
                self.hitgridReg = False
                self.lun_hitgrid.clear()
                self.lun_hitgrid_all.clear()
                self.regButton.configure(text = 'Now: All')

        def lock(self):
                if self.lockStatus:
                    self.lockStatus = False
                    self.wdg6.state = 1
                    self.wdg9.state = 1
                    self.wdg2.go_But.configure(state='normal')
                    self.wdg2.new_go_But.configure(state='normal')
                    
                    self.wdg6.snapButt.configure(state='normal')
                    self.wdg6.saveButt.configure(state='normal')
                    self.wdg6.cursorButt.configure(state='normal')

                    self.wdg9.b2.configure(state='normal')
                    self.wdg9.b3.configure(state='normal')
                    self.wdg9.b4.configure(state='normal')

                    self.boloInButton.configure(state='normal')
                    self.boloOutButton.configure(state='normal')

                    a=self.nb.component(' Main -tab')
                    a.configure(text='Active')
                    
                    self.lockButton.configure(text='Houston:\nActive Control',background='green')#,foreground='white')

                    for i in range(len(self.buttList)):
                        self.buttList[i].configure(state='normal')

                elif not self.lockStatus:
                    self.lockStatus = True
                    self.wdg6.state = 0
                    self.wdg9.state = 0
                    self.wdg2.go_But.configure(state='disabled')
                    self.wdg2.new_go_But.configure(state='disabled')

                    self.wdg6.snapButt.configure(state='disabled')
                    self.wdg6.saveButt.configure(state='disabled')
                    self.wdg6.cursorButt.configure(state='disabled')

                    self.wdg9.b2.configure(state='disabled')
                    self.wdg9.b3.configure(state='disabled')
                    self.wdg9.b4.configure(state='disabled')

                    self.boloInButton.configure(state='disabled')
                    self.boloOutButton.configure(state='disabled')

                    a=self.nb.component(' Main -tab')
                    a.configure(text=' Main ',foreground=Tk.Label().cget("foreground"))
                    
                    self.lockButton.configure(text='Take Control',background=Tk.Label().cget("background"),
                                              foreground=Tk.Label().cget("foreground"))

                    for i in range(len(self.buttList)):
                        self.buttList[i].configure(state='disabled')
                    
        def resetCounters(self):
                i = 0

                while i < 5:

                        global gpsi
                        gpsi = 0
                        #self.runStartTime = 0.
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
                        self.lunBackgroundRateWdg.set(0)

                        self.noConvergence=0
                        self.convWdg.set(0)

                        self.chanAPD = 0

                        self.shotNum = 0
                        self.shotNumLun = 0

                        self.totalFidNum = 0        # Total Photons and rates
                        self.fidRegNum = 0          # total registered fiducials
                        self.fidRate = 0.0          # fiducial photon rate
                        self.fidRegRate =0.0        # registered fiducial rate
                        self.fidDat=[]

                        self.totalLunNum = 0
                        self.lunRate = 0
                        self.totalLunRegNum = 0     # Registered Photons and rates
                        self.lunRegRate = 0
                        self.lunRegNum = 0
                        self.yield_est = 0.0
                        self.lunBackgroundNum = 0   # background Photons and rates
                        self.lunBackgroundRate = 0
                        self.lunDat=[]

                        self.stareShot = 0
                        self.staresHere = 0
                        self.stareNumHere = 0
                        self.stareRateHere = 0.0

                        # tracking stuff
                        self.offsetNum = 0      # Guide offset #
                        self.shotsHere = 0      # shots at this guide offset
                        self.rateHere = 0.0
                        self.lunNumHere = 0
                        self.lunRegNumHere = 0
                        self.lunRateHere = 0
                        self.lunRegRateHere = 0

                        self.irasterGuide = 0
                        self.irasterRxx = 0

                        self.shotsRxx = 0           # shots at this rxx,rxy
                        self.rateRxx = 0.0         # rate at thie rxx,rxy
                        self.lunNumRxx = 0         # total lunar # at this rxx,rxy
                        self.lunRegNumRxx = 0      # total registered # of lunars at this rxx,rxy
                        self.lunRateRxx = 0        # lunar rate at this rxx,rxy
                        self.lunRegRateRxx = 0     # lunar registered at this rxx,rxy

                        self.fid_data.clear()
                        self.lun_data.clear()

                        self.fid_hitgrid_all.clear()
                        self.fid_hitgrid.clear()
                        self.lun_hitgrid_all.clear()
                        self.lun_hitgrid.clear()

                        self.track_ret_all.clear()
                        self.track_ret.clear()
                        self.trackHist.clear()

                        self.rxxRate_all.clear()
                        self.rxxRate.clear()

                        self.cc_return_t_all.clear()
                        self.cc_return_t.clear()
                        self.cc_return_raw_t_all.clear()
                        self.cc_return_raw_t.clear()
                        self.fpd_all.clear()
                        self.fpd.clear()

                        self.lun_return_t_all.clear()
                        self.lun_return_t.clear()
                        self.lun_return_raw_t_all.clear()
                        self.lun_return_raw_t.clear()

                        self.cc_rate_all.clear()
                        self.cc_rate.clear()
                        self.fid_reg_all.clear()
                        self.fid_reg.clear()

                        self.lun_rate_all.clear()
                        self.lun_rate.clear()
                        self.lun_background_all.clear()
                        self.lun_background.clear()

                        self.fidTimeSeries_all.clear()
                        self.fidTimeSeries.clear()
                        self.fidTimeSeries_raw_all.clear()
                        self.fidTimeSeries_raw.clear()

                        self.lunTimeSeries_all.clear()
                        self.lunTimeSeries.clear()
                        self.lunTimeSeries_raw_all.clear()
                        self.lunTimeSeries_raw.clear()
                        self.lunTimeSeriesReg.clear()
                        self.lunTimeSeriesReg_all.clear()
                        self.changes.clear()
                        self.changes_all.clear()

                        self.inten_all.clear()
                        self.inten.clear()

                        self.dphase_all.clear()         ## new 2/17/06
                        self.dphase.clear()

                        self.laser_powerWdg.set(0.00)   # laser power stuff
                        self.laser_powerAveWdg.set(0.00)
                        self.loWdg.set(0.00)
                        self.hiWdg.set(0.00)
                        
                        self.stare.clear()
                        self.stare_all.clear()
                        self.stareTimeSeries.clear()
                        self.stareTimeSeries_all.clear()
                        self.stare_rate.clear()
                        self.stare_rate_all.clear()

                        i = i+1
        
def vp_start_gui():
    root = RO.Wdg.PythonTk()
    w = NoteBook(root)
    root.mainloop()

if __name__ == '__main__':
    def vp_start_gui():
        root = RO.Wdg.PythonTk()
        w = NoteBook(root)
        root.mainloop()
    vp_start_gui()

"""import profile
profile.run('vp_start_gui()','profile_results')

import pstats
p=pstats.Stats('profile_results')
p.sort_stats('per call').print_stats(50)"""
