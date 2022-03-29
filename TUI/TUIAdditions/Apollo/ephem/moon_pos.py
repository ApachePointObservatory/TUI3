#!/usr/bin/env python

import sys
import os
import os.path
import time
import math
import astro
import matrix

feature = 'CENTER'
APOLAT = 32.780361
APOLONG = -105.820417
APOELEV = 2788.0
GEOCLAT = 32.6054942
R_APO = 6374.69213
PI = 3.14159265358979
DTR = PI/180.0
RTD = 180.0/PI
RTARC = 206264.806248
TAI_UTC = 33
TDT_TAI = 32.184
REARTH = 6378136.0
GMEARTH = 3.986e14
AUTOKM = 1.4959787066e8
C = 299792.458

# the first element of sys.path is the
# directory of the code that invoked python
# so if you run
# > python moon_pos.py
# the sys.path[0] will be the directory in which moon_pos.py lives
# the same would be true if you ran:
# > python ../moon_pos.py
# from a subdir of the dir where moon_pos.py lived
thisdir = sys.path[0]

# make a list of the files to be opened
dut1File        = os.path.join(thisdir, 'dut1.dat')
lunarTablesFile = os.path.join(thisdir, 'lunar_tables.dat')
featuresFile    = os.path.join(thisdir, 'features.dat')

if (len(sys.argv) < 7):		# supply time as computer clock time now
  gmt = time.time()
  time_tuple = time.gmtime(gmt)
  year = time_tuple[0]
  month = time_tuple[1]
  intday = time_tuple[2]
  hour = time_tuple[3]
  minute = time_tuple[4]
  second = float(time_tuple[5])

if (len(sys.argv) == 2):
  feature = sys.argv[1]
if (len(sys.argv) == 7): 	# read in time from command line
  month = int(sys.argv[1])
  intday = int(sys.argv[2])
  year = int(sys.argv[3])
  hour = int(sys.argv[4])
  minute = int(sys.argv[5])
  second = float(sys.argv[6])

if (len(sys.argv) == 8): 	# read in feature & time from command line 
  feature = sys.argv[1]
  month = int(sys.argv[2])
  intday = int(sys.argv[3])
  year = int(sys.argv[4])
  hour = int(sys.argv[5])
  minute = int(sys.argv[6])
  second = float(sys.argv[7])

if (len(sys.argv) == 10):	# read in feature & time from command line
  year = int(sys.argv[1])	# note order of yyyy/mm/dd changed
  month = int(sys.argv[2])
  intday = int(sys.argv[3])
  hour = int(sys.argv[4])
  minute = int(sys.argv[5])
  second = float(sys.argv[6])
  xpos = float(sys.argv[7])/1000.0	# put in km
  ypos = float(sys.argv[8])/1000.0	# put in km
  zpos = float(sys.argv[9])/1000.0	# put in km
  feature='COORDS'

second = second + TAI_UTC + TDT_TAI 	 # convert UTC input to TDT

feature = feature.upper()

# Compute Julian day: INPUT TIME IS IN TDT, NOT UT

day = intday + (hour + (minute + second/60.0)/60.0)/24.0
jde = astro.julianday(month,day,year)
mjd = jde - 2400000.5
tdt = 24.0*(mjd - int(math.floor(mjd)))
utc = tdt - (TDT_TAI + TAI_UTC)/3600.0
utc %= 24.0
# Compute TDT - UT = DT and also convert to TAI in MJD seconds

dt = astro.dyntime(jde)

if (mjd > 54392.5 and mjd < 54755.5):
  dtdat = open(dut1File,'r')
  line = dtdat.readline()
  while (line.find('END') < 0):
    params = line.split()
    mjdin = int(params[3])
    tmp = float(params[6])
    if (math.fabs(mjd - float(mjdin)) < 0.5):
      dut1 = tmp
    line = dtdat.readline()

  dtdat.close();
  dt = TDT_TAI + TAI_UTC - dut1;

print("DT = %f" % dt)

jd1 = jde - dt/86400.0;
mjdtai = (jde - TDT_TAI/86400.0 - 2400000.5)*86400.0;

# adjust time by light-time to point ahead
mjdtai -= 1.27  # I want you there yesterday: average one-way delay

# This is the T (big-T) argument: julian centuries from 2000.0

bt = (jde - 2451545.0)/36525.0;

#  Arguments from Meeus, reportedly from Chapront (1998) French publ.	
OM = 125.0445479 - (1934.1362891 - (0.0020754 + (1.0/467441.0 - \
       (bt/60616000.0))*bt)*bt)*bt;
P = 83.3532465 + (4069.0137287 - (0.0103200 + (1.0/80053.0 - \
       (bt/18999000.0))*bt)*bt)*bt;

#  Arguments from Chapronts' Lunar Tables... (1991), Willmann-Bell
#  LP -> L; M -> l-prime; MP -> l; 				
LP = 218.31665436 + (481267.88134240 - (0.00013268 - (1.0/538793.0 - \
       (bt/65189000.0))*bt)*bt)*bt;
D = 297.85020420 + (445267.11151675 - (0.0001630 - (1.0/545841.0 - \
      (bt/113122000.0))*bt)*bt)*bt;
M = 357.52910918 + (35999.05029094 - (0.0001536 - (bt/24390240.0))*bt)*bt;

MP = 134.96341138 + (477198.86763133 + (0.0089970 + (1.0/69696.0 - \
       (bt/14712000.0))*bt)*bt)*bt;
F = 93.27209932 + (483202.01752731 - (0.0034029 + (1.0/3521000.0 - \
       (bt/862070000.0))*bt)*bt)*bt;
L0 = 280.46646 + (36000.76983 + 0.0003032*bt)*bt;

# Correction term for changing eccentricity (not used by Chapronts)

E = 1.0 - 0.002516*bt - 0.0000074*bt*bt;
  
LP %= 360.0
D  %= 360.0
M  %= 360.0
MP %= 360.0
F  %= 360.0
OM %= 360.0
P  %= 360.0
L0 %= 360.0

print("%02u/%02u/%4u at %02u:%02u:%07.4f" % \
         (month,intday,year,hour,minute,second))
print("JD = %lf; JDE= %lf; MJDTAI = %lf" % (jd1,jde,mjdtai))
print("T  = %14.12lf" % (bt))

sv = 0.0
svp = 0.0
svpp = 0.0
svppp = 0.0
su = 0.0
sup = 0.0
supp = 0.0
suppp = 0.0
sr = 0.0
srp = 0.0
srpp = 0.0
srppp = 0.0
vdot = 481267.88
udot = 0.0

# read terms from files and add series for long, lat, range, vdot, udot 

  
lun = open(lunarTablesFile,'r')
line = lun.readline()

while (line.find('SV-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  sv += ampl * 0.00000001 * math.sin(arg)
  line = lun.readline()
  
while (line.find('SVP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  ampl = float(params[0])
  c0 = float(params[1])
  c1 = float(params[2])
  arg = DTR * math.fmod(c0 + c1*bt, 360.0)
  svp += ampl * 0.00001 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SVPP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  ampl = float(params[0])
  c0 = float(params[1])
  c1 = float(params[2])
  arg = DTR * math.fmod(c0 + c1*bt, 360.0)
  svpp += ampl * 0.00001 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SVPPP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  svppp += ampl * 0.01 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SU-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  su += ampl * 0.00000001 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SUP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  ampl = float(params[0])
  c0 = float(params[1])
  c1 = float(params[2])
  arg = DTR * math.fmod(c0 + c1*bt, 360.0)
  sup += ampl * 0.00001 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SUPP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  supp += ampl * 0.00001 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SUPPP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  suppp += ampl * 0.01 * math.sin(arg)
  line = lun.readline()

  
while (line.find('SR-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  sr += ampl * 0.0001 * math.cos(arg)
  line = lun.readline()

  
while (line.find('SRP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  ampl = float(params[0])
  c0 = float(params[1])
  c1 = float(params[2])
  arg = DTR * math.fmod(c0 + c1*bt, 360.0)
  srp += ampl * 0.0001 * math.cos(arg)
  line = lun.readline()

  
while (line.find('SRPP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  srpp += ampl * 0.0001 * math.cos(arg)
  line = lun.readline()

  
while (line.find('SRPPP-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  srppp += ampl * 0.1 * math.cos(arg)
  line = lun.readline()

  
while (line.find('VDOT-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  vdot += ampl * math.cos(arg)
  line = lun.readline()

  
while (line.find('UDOT-DATA') < 0):
  line = lun.readline()
line = lun.readline()
while (line.find('END') < 0):
  params = line.split()
  m1 = int(params[0])
  m2 = int(params[1])
  m3 = int(params[2])
  m4 = int(params[3])
  ampl = float(params[4])
  arg = (m1*D + m2*M + m3*MP + m4*F) * DTR
  udot += ampl * math.cos(arg)
  line = lun.readline()

lun.close()

longitude = LP + sv + 0.001*(svp + svpp*bt + 0.0001*svppp*bt*bt)
latitude = su + 0.001*(sup + supp*bt + 0.0001*suppp*bt*bt)
mrange = 385000.57 + sr + srp + srpp*bt + 0.0001*srppp*bt*bt

# figure out sun's longitude (geocentric, mean equinox of date)

correc = (1.914602 - (0.004817 + 0.000014*bt)*bt)*math.sin(DTR*M)
correc += (0.019993 - 0.000101*bt)*math.sin(2.0*DTR*M)
correc += 0.000289*math.sin(3.0*DTR*M)
sunlong = L0 + correc
sun_true = M + correc
ecc = 0.016708634 - 0.000042037*bt
sun_range = AUTOKM*1.000001018*(1-ecc*ecc)/(1+ecc*math.cos(sun_true*DTR))
moonphase = longitude - sunlong
moonphase %= 360.0

print("Solar (lon,lat,range) = (%f, 0.0, %f)" % (sunlong,sun_range))
sunlong *= DTR

print("Lunar phase angle: %f" % moonphase)

longitude -= 0.00019524 + 0.00001059*math.sin(DTR*(MP+90.0))
latitude -= 0.00001754*math.sin(DTR*(F+90.0))
mrange += 0.0708*math.cos(DTR*(MP+90.0))

print("\nMoon apparent (lon,lat,range) = (%f, %f, %f)" % \
          (longitude,latitude,mrange))

nut_tup =  astro.nutation(jde)
psi = nut_tup[0]
eps = nut_tup[1]
obliq = nut_tup[2]
eclip = DTR * (obliq + eps/3600.0)

# print "Nutation is: (%f,%f), obliquity is: %f" % (psi,eps,obliq) 

# Compute Lunar optical librations		

incl = 1.54242 * DTR
lamb = (longitude  + psi/3600.0)* DTR
beta = latitude * DTR
W = lamb - OM * DTR
tana = (math.sin(W)*math.cos(beta)*math.cos(incl) \
       - math.sin(beta)*math.sin(incl))/(math.cos(W)*math.cos(beta))
liblon = math.atan(tana)*RTD - F
liblon %= 360.0
liblon -= 180.0
if (liblon >  20.0):
  liblon -= 180.0
if (liblon < -20.0):
  liblon += 180.0
anga = (liblon + F)*DTR
liblat = -math.asin(math.sin(W)*math.cos(beta)*math.sin(incl) \
         + math.sin(beta)*math.cos(incl))*RTD

print("\nOptical libration in long., lat. is: (%f,%f)" % (liblon,liblat))

# Compute Lunar physical librations		

k1 = 119.75 + 131.849*bt
k2 = 72.56  +  20.186*bt
k1 %= 360.0
k2 %= 360.0

MP *= DTR
D  *= DTR
F  *= DTR
M  *= DTR

rho = -0.02752*math.cos(MP) - 0.02245*math.sin(F) + 0.00684*math.cos(MP-2*F)
rho += -0.00293*math.cos(2*F) - 0.00085*math.cos(2*(F-D))
rho += -0.00054*math.cos(MP-2*D) - 0.00020*math.sin(MP+F)
rho += -0.00020*math.cos(MP+2*F) - 0.00020*math.cos(MP-F) 
rho += 0.00014*math.cos(MP+2*F-2*D)

sigma = -0.02816*math.sin(MP) + 0.02244*math.cos(F)
sigma += -0.00682*math.sin(MP-2*F) - 0.00279*math.sin(2*F)
sigma += -0.00083*math.sin(2*(F-D)) + 0.00069*math.sin(MP-2*D)
sigma +=  0.00040*math.cos(MP+F) - 0.00025*math.sin(2*MP)
sigma += -0.00023*math.sin(MP+2*F) + 0.00020*math.cos(MP-F)
sigma +=  0.00019*math.sin(MP-F) + 0.00013*math.sin(MP+2*(F-D))
sigma -=  0.00010*math.cos(MP-3*F)

tau = 0.02520*E*math.sin(M) + 0.00473*math.sin(2*(MP-F))
tau += -0.00467*math.sin(MP) + 0.00396*math.sin(k1*DTR)
tau +=  0.00276*math.sin(2*(MP-D)) + 0.00196*math.sin(OM*DTR)
tau += -0.00183*math.cos(MP-F) + 0.00115*math.sin(MP-2*D)
tau += -0.00096*math.sin(MP-D) + 0.00046*math.sin(2*(F-D))
tau += -0.00039*math.sin(MP-F) - 0.00032*math.sin(MP-M-D)
tau +=  0.00027*math.sin(2*MP - M - 2*D) + 0.00023*math.sin(k2*DTR)
tau += -0.00014*math.sin(2*D) + 0.00014*math.cos(2*(MP-F))
tau += -0.00012*math.sin(MP-2*F) - 0.00012*math.sin(2*MP)
tau +=  0.00011*math.sin(2*(MP-M-D))

pliblon = -tau + (rho*math.cos(anga)+sigma*math.sin(anga))*math.tan(liblat*DTR)
pliblat = sigma*math.cos(anga) - rho*math.sin(anga)

# Add physical libration to optical libration to get total
liblon += pliblon
liblat += pliblat

print("Moon's physical librations are: (%f,%f)" % (pliblon,pliblat))
print("Total libration is: (%f,%f)" % (liblon,liblat))

# Compute the local apparent siderial time	

st = astro.siderial(jd1) + APOLONG
st += psi*math.cos((obliq + eps/3600.0)*DTR)/3600.0
st %= 360.0

# transform ecliptic to equatorial coordinates	

conv = astro.ecliptoeq(jd1,lamb,beta);
alpha = conv[0]
delta = conv[1]
conv = astro.ecliptoeq(jd1,sunlong,0.0);
sunra = conv[0]
sundec = conv[1]

# Compute time derivatives of RA & dec in deg/s

vdot /= (86400.0 * 36525.0);
udot /= (86400.0 * 36525.0);

decdot = udot*(math.cos(beta)*math.cos(eclip) \
         - math.sin(beta)*math.sin(eclip)*math.sin(lamb))
decdot += vdot*math.cos(beta)*math.sin(eclip)*math.cos(lamb)
decdot /= math.cos(delta * DTR)
radot = vdot*(math.cos(eclip) - math.sin(lamb)*math.tan(beta)*math.sin(eclip))
radot -= udot*math.sin(eclip)*math.cos(lamb)/(math.cos(beta)*math.cos(beta))
denom = math.cos(lamb)*math.cos(lamb)
denom += pow(math.sin(lamb)*math.cos(eclip) \
         - math.tan(beta)*math.sin(eclip),2.0)
radot /= denom

# Compute position angle of moon's rotation axis

v = (OM + psi/3600.0 + sigma/math.sin(incl))*DTR
x = math.sin(incl + rho*DTR)*math.sin(v)
y = math.sin(incl + rho*DTR)*math.cos(v)*math.cos(eclip) \
     - math.cos(incl + rho*DTR)*math.sin(eclip)
omega = math.atan2(x,y)
p = math.asin(math.sqrt(x*x+y*y)*math.cos(alpha*DTR - omega) \
    / math.cos(DTR*liblat))

# Compute topocentric libration corrections (comb. of Meeus and Expl. Suppl.)

Hrad = (st - alpha)*DTR				# geocentric hour angle, rad
tanq = math.cos(APOLAT*DTR)*math.sin(Hrad)
tanq /= (math.cos(delta*DTR)*math.sin(APOLAT*DTR) - \
         math.sin(delta*DTR)*math.cos(APOLAT*DTR)*math.cos(Hrad))
Q = math.atan(tanq)
cosz = math.sin(delta*DTR)*math.sin(APOLAT*DTR) + \
       math.cos(delta*DTR)*math.cos(APOLAT*DTR)*math.cos(Hrad)
zrad = math.acos(cosz)				# geocentric zenith angle
#print "z = %f; Q = %f, P = %f" % (zrad*RTD, Q*RTD, p*RTD)
sinHP = REARTH/(1000*mrange)			# horizontal parallax
HPprime = math.asin(math.sin(zrad)*sinHP/(1.0 - math.sin(zrad)*sinHP))

# now the adjustments to l, b, and P (liblon, liblat, p)
dliblon = (-HPprime*math.sin(Q-p)/math.cos(liblat*DTR))*RTD
dliblat = HPprime*math.cos(Q-p)*RTD
dp = dliblon*math.sin((liblat + dliblat)*DTR) - \
     HPprime*math.sin(Q)*math.tan(delta*DTR)

print("Libration topocentric corrections: (%.3f, %.3f); P.A.: %.3f" % \
       (dliblon,dliblat,dp*RTD))

# Print out equatorial coordinates			

outstring = "\nApparent RA,dec: (%f, %f); (" % (alpha,delta)
outstring += astro.repr_hms(alpha/15.0) + ", " + astro.repr_hms(delta) + ")"
print(outstring)
print("RAdot, decdot = %11.9f, %11.9f" % (radot,decdot))

# Compute position to lunar feature			

l = liblon * DTR
b = liblat * DTR
cl = math.cos(l);  sl = math.sin(l)
cb = math.cos(b);  sb = math.sin(b)
cp = math.cos(p);  sp = math.sin(p)

mrot = [[],[],[]]
mrot[0] = [cb*cl, cb*sl, sb]
mrot[1] = [sp*sb*cl-cp*sl, sp*sb*sl+cp*cl, -sp*cb]
mrot[2] = [-cp*sb*cl-sp*sl, sp*cl-cp*sb*sl, cp*cb]

ca = math.cos(alpha * DTR);  sa = math.sin(alpha * DTR)
cd = math.cos(delta * DTR);  sd = math.sin(delta * DTR)

crot = [[],[],[]]
crot[0] = [-ca*cd, sa, -ca*sd]
crot[1] = [-sa*cd, -ca, -sa*sd]
crot[2] = [-sd, 0.0, cd]

totrot = matrix.mm3x3(crot,mrot)

rmoon = [0.0,0.0,0.0]
rmoon[0] = mrange*ca*cd;  rmoon[1] = mrange*sa*cd;  rmoon[2] = mrange*sd

# Figure out which lunar feature to go for		

if (feature != 'COORDS'):
  fp = open(featuresFile,'r')
  line = fp.readline()
  while (line.find(feature) < 0):
    line = fp.readline()
    if (line.find('END') > -1):
      print("Failed to find %s in features.dat file\n" % (feature))
      sys.exit()
  fp.close()

  params = line.split()
  slong = float(params[1])
  slat = float(params[2])
  srad = float(params[3])
  if (slong == 0.000 and slat == 0.000):
    slong = liblon;
    slat = liblat;

  # For N,S poles, guard against possible singularity (problem?)
  if (math.fabs(math.fabs(slat) - 90.0) < 0.001):
    sign = slat / math.fabs(slat)
    slat = sign * 89.9999
  # For E,W limbs, correct for libration in longitude	
  if (math.fabs(math.fabs(slong) - 90.0) < 0.001):
    slong += liblon

else:
  srad = math.sqrt(xpos*xpos + ypos*ypos + zpos*zpos)
  slat = math.asin(zpos/srad)*RTD
  slong = math.atan2(ypos,xpos)*RTD

print("\nFeature [%s] at selenographic: (%f, %f)" % \
        (feature,slong,slat))

feat_tup = astro.moonfeat(slong,slat,srad,totrot,rmoon)
decfeat = feat_tup[0]
rafeat = feat_tup[1]
rangefeat = feat_tup[2]

# From here on, set RA, dec, range equal to feature coordinates

ra = rafeat
dec = decfeat
rng = rangefeat

# Accomodate request for SELENOCENTER apparent coordinates 	

if (feature.find('SELENOCENTER') > -1):
  ra = alpha
  dec = delta
  rng = mrange

# Print out equatorial coordinates of lunar feature

print("Feature at: (%f, %f); Range: %10.3lf km = %10.8lf A.U." % \
          (ra,dec,rng,rng/149597900.0))

# Convert to topocentric coordinates at APO location	

stationlat = APOLAT
stationelev = APOELEV
topo_tup = astro.topo(st,ra,dec,rng,stationlat,stationelev)
topodelt = topo_tup[0]
topora = topo_tup[1]

outstring = "Topocentric RA,dec: (%f, %f); (" % (topora,topodelt)
outstring += astro.repr_hms(topora/15.0)
outstring += ", " + astro.repr_hms(topodelt) + ")"
print(outstring)

# Convert topocentric equatorial into azimuth and elevation

hourang = st - topora
ha_geo = st - ra
azel_tup = astro.azel(hourang,topodelt)
azimuth = azel_tup[0]
elev = azel_tup[1]
sunha = st - sunra
azel_tup = astro.azel(sunha,sundec)
sunaz = azel_tup[0]
sunelev = azel_tup[1]
print("Hour angle = %f; geocentric = %f" % (hourang,ha_geo))

# Correct for atmospheric refraction			

temp = 283.0
press = 717.0
ref = astro.refraction(elev,temp,press)
refsun = astro.refraction(sunelev,temp,press)
sunel = sunelev + refsun

print("Sun azimuth, elevation = (%f,%f)" % (sunaz,sunel))

outstring = "Azimuth, elevation: (%f, %f); (" % (azimuth,elev+ref)
outstring += astro.repr_hms(azimuth)
outstring += ", " + astro.repr_hms(elev+ref) + ")"
print(outstring)
if (math.fabs(ref) > 0.0):
  print("Refracted by %f arcsec" % (ref*3600.0))

# compute velocity offset

earth_omega = 2.0*PI/(86400.0 - 236.0)
lat = GEOCLAT*DTR
decrad = dec*DTR
ha = ha_geo*DTR

v_earth = [0.0,0.0,0.0]
v_earth[0] = -earth_omega*R_APO*math.cos(lat);

v_moon = [0.0,0.0,0.0]
v_moon[0] = -rangefeat*(math.cos(ha)*math.cos(decrad)*radot*DTR 
            + math.sin(ha)*math.sin(decrad)*decdot*DTR)
v_moon[1] = rangefeat*(math.sin(ha)*math.cos(decrad)*radot*DTR 
            - math.cos(ha)*math.sin(decrad)*decdot*DTR)
v_moon[2] = rangefeat*math.cos(decrad)*decdot*DTR

dv = [0.0,0.0,0.0]
for i in range(3):
  dv[i] = v_moon[i] - v_earth[i];

zen = [0.0,0.0,0.0]
zen[1] = math.cos(lat)
zen[2] = math.sin(lat)

rvect = [0.0,0.0,0.0]
rvect[0] = rangefeat*math.sin(ha)*math.cos(decrad)
rvect[1] = rangefeat*math.cos(ha)*math.cos(decrad) - R_APO*math.cos(lat)
rvect[2] = rangefeat*math.sin(decrad) - R_APO*math.sin(lat)

rhat = [0.0,0.0,0.0]
rmag = matrix.vabs3(rvect)
for i in range(3):
  rhat[i] = rvect[i] / rmag

vmult = matrix.vdot3(dv,rhat)
vr = [0.0,0.0,0.0]
for i in range(3):
  vr[i] = vmult*rhat[i]

vt = [0.0,0.0,0.0]
for i in range(3):
  vt[i] = dv[i] - vr[i]

azvect = matrix.vcross3(rhat,zen)
elvect = matrix.vcross3(azvect,rhat)
azmag = matrix.vabs3(azvect)
elmag = matrix.vabs3(elvect)
azhat = [0.0,0.0,0.0]
elhat = [0.0,0.0,0.0]
for i in range(3):
  azhat[i] = azvect[i]/azmag
  elhat[i] = elvect[i]/elmag

vaz = matrix.vdot3(vt,azhat)*2.0*RTARC/C
vel = matrix.vdot3(vt,elhat)*2.0*RTARC/C

print("v_offset_az =  %f ; v_offset_el = %f (arcseconds)" % (vaz,vel))

outstring = "UTC = " + astro.repr_hms(utc)
print(outstring)

track = "tcc track %lf, %lf/distance=%10.8lf geo /keep=(bore,gcorr)" % \
         (ra,dec,rng/149597870.7)
print(track)

track = "tcc offset arc 0.0, 0.0, %11.9lf, %11.9lf, %13.2lf /computed" % \
          (radot*math.cos(delta * DTR),decdot,mjdtai)
print(track)

new_track = "new tcc track %lf, %lf/distance=%10.8lf geo /scanVel=(%11.9lf, %11.9lf, %13.2lf) /keep=(bore,gcorr)" % \
         (ra,dec,rng/149597870.7,radot*math.cos(delta * DTR),decdot,mjdtai)
print(new_track)
