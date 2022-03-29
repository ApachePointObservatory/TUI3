#!/usr/local/bin/python
"""Model for Apollo lunar laser ranging instrument.

2005-02-11 ROwen	Very preliminary; more keywords will be added and I sincerely hope
					that the current ones will be cleaned up.
2005-02-17 ROwen	Bug fix: lunar data with no channel info was being rejected.
"""
__all__ = ['getModel']

import RO.CnvUtil # potentially useful converter functions
import RO.KeyVariable
import TUI.TUIModel

# model
_model = None

def getModel():
	global _model
	if _model == None:
		_model = _Model()
	return _model
	
def _parseChanDict(chanStr):
	if not chanStr:
		return {}

	chanList = chanStr.split(",")
	chanDict = {}
	for chanItem in chanList:
		chan, val = chanItem.split(":")
		chanDict[int(chan)] = int(val)
	return chanDict

def _datFileChop(chanStr):
        if not chanStr:
		return {}
	return chanStr[30:]

def _logFileChop(chanStr):
        if not chanStr:
		return {}
	return chanStr[27:]

def _polyFileChop(chanStr):
        if not chanStr:
		return 'error'
	return chanStr[6:]

class _Model (object):
	def __init__(self):
		self.actor = "apollo"

		self.tuiModel = TUI.TUIModel.getModel()
		
		keyVarFact = RO.KeyVariable.KeyVarFactory(
			actor = self.actor,
			dispatcher = self.tuiModel.dispatcher,
			converters = str,
			allowRefresh = True,
		)

		keyVarFactTCC = RO.KeyVariable.KeyVarFactory( # parse weather here for now
			actor = "tcc",
			dispatcher = self.tuiModel.dispatcher,
			converters = str,
			allowRefresh = True,
		)

		keyVarFactHub = RO.KeyVariable.KeyVarFactory( # parse hub replies
			actor = "hub",
			dispatcher = self.tuiModel.dispatcher,
			converters = str,
			allowRefresh = True,
		)

		keyVarFactCmds = RO.KeyVariable.KeyVarFactory( # parse hub cmds replies
			actor = "cmds",
			dispatcher = self.tuiModel.dispatcher,
			converters = str,
			allowRefresh = True,
		)

		self.oldfid = keyVarFact(
			keyword="OldFid",
			converters = (int, int, int, int, int,  _parseChanDict),
			description="""Data for a fiducial return
1.  	        shot number
2		Accumulated seconds
3		intensity
4		photodiode TDC channel
5		number of hits
6		channel data: "c1:t1, c2:t2, ..." where cN is channel number and tN is the return time
Notes:
- in channel data: channel 15 is the photodiode
- channel data may be an empty dictionary
""",
			nval = 6,
			allowRefresh = False,
		)

		self.fiducial = keyVarFact(
			keyword="Fiducial",
			converters = (int, int, int, int, int, int, int, _parseChanDict),
			description="""Data for a fiducial return with diffuser phase record
1  	        shot number
2		Accumulated seconds
3		intensity
4               diffuser phase
5		fast photodiode TDC channel
6		number of hits
7               time within seconds (TWS)
8		channel data: "c1:t1, c2:t2, ..." where cN is channel number and tN is the return time
Notes:
- in channel data: channel 15 is the photodiode
- channel data may be an empty dictionary
""",
			nval = 8,
			allowRefresh = False,
		)


		self.lunar = keyVarFact(
			keyword="Lunar",
			converters = (int, int, int, int, int, int, _parseChanDict),
			description="""Data for a lunar return - need to fix
1.  	        shot number
2		Accumulated seconds
3		photodiode prediction
4		corrected prediction
5		number of hits
6               time within seconds (TWS)
7		channel data: "c1:t1, c2:t2, ..." where cN is channel number and tN is the return time
Note: identical to fiducial except:
- field 6 is predicted time instead of intensity
- channel data may not include a channel 0
""",
			nval = 7,
			allowRefresh = False,
		)

		self.stare = keyVarFact(
			keyword="Stare",
			converters = (int, int, int, int, int, int, int, int,
                                      int, int, int, int, int, int, int, int),
			description="""'Stare' data (hits per channel) """,
			nval = 16,
			allowRefresh = False,
		)

		self.dark = keyVarFact(
			keyword="Dark",
			converters = (int, int, int, int, int, int, int, int,
                                      int, int, int, int, int, int, int, int),
			description="""Dark current 'Dark' data (hits per channel) """,
			nval = 16,
			allowRefresh = False,
		)

		self.flat = keyVarFact(
			keyword="Flat",
			converters = (int, int, int, int, int, int, int, int,
                                      int, int, int, int, int, int, int, int),
			description="""Flat data (hits per channel) """,
			nval = 16,
			allowRefresh = False,
		)
## temporary
		self.guideOff = keyVarFact(
			keyword="guideOff",
			converters = (str),
			description="""Guide offset values for pointing acquisition (only for test mode)""",
			nval = 1,
			allowRefresh = False,
		)
		self.boreOff = keyVarFact(
			keyword="boreOff",
			converters = (str),
			description="""Boresight offset values for pointing acquisition (only for test mode)""",
			nval = 1,
			allowRefresh = False,
		)
		
##
		self.gps = keyVarFact(
			keyword="gpstrig",
			converters = (str),
			description="""GPS reading""",
			nval = 1,
			allowRefresh = False,
		)
		self.state = keyVarFact(
			keyword="state",
			converters = (int),
			description="""Houston State""",
			nval = 1,
			allowRefresh = False,
		)
		self.polyname = keyVarFact(
			keyword="polyname",
			converters = (_polyFileChop),
			description="""Polynomial Name file""",
			nval = 1,
			allowRefresh = False,
		)
		self.motrps = keyVarFact(
			keyword="motrps",
			converters = (float),
			description="""T/R motor rps""",
			nval = 1,
			allowRefresh = False,
		)
		self.mirrorphase = keyVarFact(
			keyword="mirrorphase",
			converters = (int),
			description="""phase at which to fire laser""",
			nval = 1,
			allowRefresh = False,
		)
		self.nruns = keyVarFact(
			keyword="nruns",
			converters = (int),
			description="""# of shots for RUN, FIDLUN""",
			nval = 1,
			allowRefresh = False,
		)
		self.gatewidth = keyVarFact(
			keyword="gatewidth",
			converters = (int),
			description="""RUN lunar/STARE/FIDLUN gatewidth (ns)""",
			nval = 1,
			allowRefresh = False,
		)
		self.tdc_target = keyVarFact(
			keyword="tdc_target",
			converters = (int),
			description="""desired average lunar TDC value""",
			nval = 1,
			allowRefresh = False,
		)
		self.runfidgw = keyVarFact(
			keyword="runfidgw",
			converters = (int),
			description="""RUN fiducial gatewidth (ns)""",
			nval = 1,
			allowRefresh = False,
		)
		self.huntstart = keyVarFact(
			keyword="huntstart",
			converters = (float),
			description="""Time hunt starting offset""",
			nval = 1,
			allowRefresh = False,
		)
		self.huntdelta = keyVarFact(
			keyword="huntdelta",
			converters = (float),
			description="""Time hunt increment""",
			nval = 1,
			allowRefresh = False,
		)
		self.thunt = keyVarFact(
			keyword="thunt",
			converters = (float),
			description="""Time hunt current offset""",
			nval = 1,
			allowRefresh = False,
		)
		self.dskew = keyVarFact(
			keyword="dskew",
			converters = (float),
			description="""dskew parameter""",
			nval = 1,
			allowRefresh = False,
		)
		self.predskew = keyVarFact(
			keyword="predskew",
			converters = (int),
			description="""predskew parameter""",
			nval = 1,
			allowRefresh = False,
		)
		self.starerate = keyVarFact(
			keyword="starerate",
			converters = (int),
			description="""Stare rate""",
			nval = 1,
			allowRefresh = False,
		)
		self.nstares = keyVarFact(
			keyword="nstares",
			converters = (int),
			description="""# of stares to take""",
			nval = 1,
			allowRefresh = False,
		)
		self.binning = keyVarFact(
			keyword="binning",
			converters = (int),
			description="""binning for STARE data""",
			nval = 1,
			allowRefresh = False,
		)
		self.ndarks = keyVarFact(
			keyword="ndarks",
			converters = (int),
			description="""# of DARKs to take""",
			nval = 1,
			allowRefresh = False,
		)
		self.flashrate = keyVarFact(
			keyword="flashrate",
			converters = (float),
			description="""FIDLUN flash rate""",
			nval = 1,
			allowRefresh = False,
		)
		self.flashcum = keyVarFact(
			keyword="flashcum",
			converters = (int),
			description="""cumulative flash count""",
			nval = 1,
			allowRefresh = False,
		)
		self.vposx = keyVarFact(
			keyword="vposx",
			converters = (float),
			description="""mirror position in x (rxx)""",
			nval = 1,
			allowRefresh = False,
		)
		self.vposy = keyVarFact(
			keyword="vposy",
			converters = (float),
			description="""mirror position in y (rxy)""",
			nval = 1,
			allowRefresh = False,
		)
		self.vtargetx = keyVarFact(
			keyword="vtargetx",
			converters = (float),
			description="""target position in x (rxx)""",
			nval = 1,
			allowRefresh = False,
		)
		self.vtargety = keyVarFact(
			keyword="vtargety",
			converters = (float),
			description="""target position in y (rxy)""",
			nval = 1,
			allowRefresh = False,
		)
		self.fakertt = keyVarFact(
			keyword="fakertt",
			converters = (float),
			description="""Forced round-trip time""",
			nval = 1,
			allowRefresh = False,
		)
		self.blockremaining = keyVarFact(
			keyword="blockremaining",
			converters = (int),
			description="""Seconds remaining in Space Command Blockage""",
			nval = 1,
			allowRefresh = False,
		)
		self.releaseremaining = keyVarFact(
			keyword="releaseremaining",
			converters = (int),
			description="""Seconds remaining in Space Command Release""",
			nval = 1,
			allowRefresh = False,
		)
		self.releaseremaining = keyVarFact(
			keyword="releaseremaining",
			converters = (int),
			description="""Seconds remaining until next Space Command Blockage""",
			nval = 1,
			allowRefresh = False,
		)
		self.apdtofpd = keyVarFact(
			keyword="apdtofpd",
			converters = (float,float,float,float,float,float,float,float,float,
                                      float,float,float,float,float,float,float),
			description="""APD channel offsets""",
			nval = 16,
			allowRefresh = False,
		)
		self.dphase = keyVarFact(
			keyword="dphase",
			converters = (int),
			description="""Current diffuser motor phase""",
			nval = 1,
			allowRefresh = False,
		)
		self.dphase_target = keyVarFact(
			keyword="dphase_target",
			converters = (int),
			description="""Target diffuser target""",
			nval = 1,
			allowRefresh = False,
		)
		self.bolopower = keyVarFact(
			keyword="bolopower",
			converters = (float),
			description="""Bolometer reading""",
			nval = 1,
			allowRefresh = False,
		)
		self.bolopos = keyVarFact(
			keyword="bolopos",
			converters = (int),
			description="""Bolometer position (-1,0,1)""",
			nval = 1,
			allowRefresh = False,
		)
		self.powerstatus = keyVarFact(
			keyword="powerstatus",
			converters = (str),
			description="""Power status""",
			nval = 1,
			allowRefresh = False,
		)
		self.powerstate = keyVarFact(
			keyword="powerstate",
			converters =(int,int,int,int,int,int,int,int,int,
                                     int,int,int,int,int,int,int,int,int,int,
                                     int,int,int,int,int,int,),
			description="""Power state""",
			nval = 25,
			allowRefresh = False,
		)
		self.statusline = keyVarFact(
			keyword="statusline",
			converters = (str),
			description="""Status Line""",
			nval = 1,
			allowRefresh = False,
		)
		self.datafile = keyVarFact(
			keyword="datafile",
			converters = (_datFileChop),
			description="""Current data file name""",
			nval = 1,
			allowRefresh = False,
		)
		self.logfile = keyVarFact(
			keyword="logfile",
			converters = (_logFileChop),
			description="""Current log file name""",
			nval = 1,
			allowRefresh = False,
		)
		self.las_display = keyVarFact(
			keyword="las_display",
			converters = (str),
			description="""Laser box text display""",
			nval = 1,
			allowRefresh = False,
		)
		self.stv_display = keyVarFact(
			keyword="stv_display",
			converters = (str),
			description="""STV box text display""",
			nval = 1,
			allowRefresh = False,
		)
		self.text = keyVarFact(
			keyword="text",
			converters = (str),
			description="""Error String""",
			nval = 1,
			allowRefresh = False,
		)
		self.g = keyVarFact(
			keyword="g",
			converters = (str),
			description="""Error String""",
			nval = 1,
			allowRefresh = False,
		)
		self.i = keyVarFact(
			keyword="i",
			converters = (str),
			description="""Information String""",
			nval = 1,
			allowRefresh = False,
		)
		self.h = keyVarFact(
			keyword="h",
			converters = (str),
			description="""Help String""",
			nval = 1,
			allowRefresh = False,
		)
		self.oscVoltR = keyVarFact(
			keyword="oscvolt_r",
			converters = (int),
			description="""Oscillator Voltage digipot setting (Ohms)""",
			nval = 1,
			allowRefresh = False,
		)
                self.ampdelay = keyVarFact(
			keyword="ampdelay",
			converters = (int),
			description="""Amplifier Delay digipot setting (Ohms)""",
			nval = 1,
			allowRefresh = False,
		)       
                # FIXME: this keyword is not yet implemented in housctl...
                # FIXME: perhaps can look at 'informational text' (namely, see: self.i)
		#self.shgRot = keyVarFact(
		#	keyword="shgRot",
		#	converters = (str),   # either 'cw' or 'ccw'
		#	description="""Leopard Laser SHG Adjustment (cw or ccw)""",
		#	nval = 1,
		#	allowRefresh = False,  # not sure what this means...
		#)
		self.alarms = keyVarFact(
			keyword="alarms",
			converters = (str),
			description="""Persistent alarms""",
			nval = 1,
			allowRefresh = False,
		)
		self.alarms_unack = keyVarFact(
			keyword="alarms_unack",
			converters = (str),
			description="""Transient alarms""",
			nval = 1,
			allowRefresh = False,
		)
   ###             
		self.airTemp = keyVarFactTCC(
			keyword="AirTemp",
			converters = (float),
			description="""Air Temperature reported by TCC""",
			nval = 1,
			allowRefresh = False,
		)
		self.pressure = keyVarFactTCC(
			keyword="Pressure",
			converters = (float),
			description="""Pressure reported by TCC""",
			nval = 1,
			allowRefresh = False,
		)
		self.humidity = keyVarFactTCC(
			keyword="Humidity",
			converters = (float),
			description="""Humidity reported by TCC""",
			nval = 1,
			allowRefresh = False,
		)





                self.pulseper = keyVarFact(
			keyword="pulseper",
			converters = (int),
			description="""ACM pulse period""",
			nval = 1,
			allowRefresh = False,
		)
                self.pulsegw = keyVarFact(
			keyword="pulsegw",
			converters = (int),
			description="""ACM pulse gate width""",
			nval = 1,
			allowRefresh = False,
		)
###  ACS Stuff
                self.acsDACExtremizeStatus = keyVarFact(
			keyword="acs_extremize_status",
			converters = (int),
			description="""A new DAC extremize operation has begun (1) or ended (0)""",
			nval = 1,
			allowRefresh = False,
                )
                self.acsDACExtremize = keyVarFact(
			keyword="acs_dac_extremize",
			converters = (int,int,int,int,int),
			description="""Values from the DAC extremize run (DAC, IRupstream,IRdownstream,ModulatorMonitorPD,GreenPD)""",
			nval = 5,
			allowRefresh = False,
		)
		self.acsLaserDC = keyVarFact(
			keyword="ACS_laser_DC",
			converters = (int),
			description="""Laser DC power""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsLaserLockState = keyVarFact(
			keyword="ACS_laser_lockstate",
			converters = (int),
			description="""Laser lock state""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsADC = keyVarFact(
			keyword="ACS_adcs",
			converters = (int,int,int,int),
			description="""ADC values for PD0 through PD3""",
			nval = 4,
			allowRefresh = False,
		)
		self.acsLunEn = keyVarFact(
			keyword="ACS_LUN_EN",
			converters = (int),
			description="""LUN_EN status (0=disabled, 1=enabled)""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsFidEn = keyVarFact(
			keyword="ACS_FID_EN",
			converters = (int),
			description="""FID_EN status (0=disabled, 1=enabled)""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsDacVal = keyVarFact(
			keyword="ACS_mod_DAC",
			converters = (int),
			description="""Value of the DAC driving the modulator DC bias 0-4095 (maps onto 0-10V)""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsDelayVal = keyVarFact(
			keyword="ACS_DW",
			converters = (int,int,int,int),
			description="""FID0, FID1, LUN0, LUN1 values for delay/width generation""",
			nval = 4,
			allowRefresh = False,
		)
		self.acsDACScanVal = keyVarFact(
			keyword="acs_dac_scan",
			converters = (int,int,int,int,int,float),
			description="""DAC scan return values (DAC, PD0, PD1, PD2, PD3, PD0/PD1)""",
			nval = 6,
			allowRefresh = False,
		)
		self.acsDACSweepStatus = keyVarFact(
                        # at the start of a sweep:  ACS_dacsweep_status=1
                        # at the end   of a sweep:  ACS_dacsweep_status=0
			keyword="ACS_dacsweep_status",
			converters = (int),
			description="""A new DAC sweep has begun (1) or ended (0)""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsDACScanDone = keyVarFact(
			keyword="acs_dac_scan_done",
			converters = (int),
			description="""The notification that the DAC scan is finished""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsPhaseSweepStatus = keyVarFact(
			keyword="ACS_phasesweep_status",
			converters = (int),
			description="""A new phase sweep has begun (1) or ended (0)""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsPhaseSweepVal = keyVarFact(
			keyword="acs_phase_scan",
			converters = (int,float,float,float),
			description="""Phase sweep return values (phase, PD0, PD1, PD0/PD1)""",
			nval = 4,
			allowRefresh = False,
		)
                # NOT USED???  redundant with acsPhaseSweepStatu() ?
		self.acsPhaseScanDone = keyVarFact(
			keyword="acs_phase_scan_done",
			converters = (int),
			description="""The notification that the Phase scan is finished""",
			nval = 1,
			allowRefresh = False,
		)
		self.acsClockPhaseBumpAmt = keyVarFact(
			keyword="acs_phase_bump",
			converters = (int),
			description="""Confirmation of new Clock Phase value""",
			nval = 1,
			allowRefresh = False,
		)
###             

                self.cmdr = keyVarFactCmds(
			keyword="Cmdr",
			converters = (str),
			description="""Last commander""",
			nval = 1,
			allowRefresh = False,
		)

                self.cmdrMID = keyVarFactCmds(
			keyword="CmdrMID",
			converters = (int),
			description="""Last command #""",
			nval = 1,
			allowRefresh = False,
		)

                self.cmdActor = keyVarFactCmds(
			keyword="CmdActor",
			converters = (str),
			description="""Last command actor""",
			nval = 1,
			allowRefresh = False,
		)

                self.cmdText = keyVarFactCmds(
			keyword="CmdText",
			converters = (str),
			description="""Last commander sender""",
			nval = 1,
			allowRefresh = False,
		)

		keyVarFact.setKeysRefreshCmd(getAllKeys=True)
		keyVarFactTCC.setKeysRefreshCmd(getAllKeys=True)
		keyVarFactHub.setKeysRefreshCmd(getAllKeys=True)


if __name__ == "__main__":
	getModel()
