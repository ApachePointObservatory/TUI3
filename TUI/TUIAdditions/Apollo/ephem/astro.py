import sys
import os
import math
import matrix

thisdir = sys.path[0]
nutFile = os.path.join(thisdir,'nut.dat')

PI = 3.14159265358979
DTR = PI/180.0
RTD = 180.0/PI
APOLAT = 32.780361

def julianday(month, day, year):

  m = int(month)
  y = int(year)

  if (month < 3):
    m += 12
    y -= 1

  if (year > 1582 or (year == 1582 and month > 9 and day > 5.0)):
    a = int(math.floor(y/100))
    b = 2 - a + int(math.floor(a/4))
  else:
    b = 0

  intjd = int(math.floor(365.25*(y+4716))) + int(math.floor(30.6001*(m+1))) + b

  jd = float(intjd + day - 1524.5)

  return jd

def dyntime(julianday):

  mjd = julianday - 2400000.5
  jd = julianday + 0.5
  ip = int(math.floor(jd))
  fp = jd - ip

  if (ip < 2299161):
    a = ip
  else:
    alpha = int(math.floor((float(ip) - 1867216.25)/36524.25))
    a = ip + 1 + alpha - int(math.floor(float(alpha)/4.0))

  b = a + 1524
  c = int(math.floor((float(b) - 122.1)/365.25))
  d = int(math.floor(365.25 * c))
  e = int(math.floor(float(b - d) / 30.6001))

  day = b - d - int(math.floor(30.6001 * e)) + fp

  if (e < 14):
   month = e - 1
  else:
    month = e - 13

  if (month > 2):
    year = c - 4716
  else:
    year = c - 4715

  t = float(year - 2000) / 100.0

  if (year < 948):
    dt = 2177 + 497*t + 44.1*t*t
  else:
    dt = 102 + 102*t + 25.3*t*t

  if (year > 1997 and year < 2100):
    dt += 0.37*float(year - 2100)
    dt = 65.184 + 0.2221 + 0.00092*(mjd - 54399.0)

  arg = (jd - 2415020.5)/36525.0
  if (year > 1899 and year < 1998):
    dt = -2.44 + arg*(87.24 + arg*(815.20 - arg*(2637.80 + arg*(18756.33 \
         - arg*(124906.66 - arg*(303191.19 - arg*(372919.88 - arg*(232424.66 \
         - 58353.42*arg))))))))

  if (year > 1799 and year < 1900):
    dt = -2.50 + arg*(228.95 + arg*(5218.61 + arg*(56282.84 + arg*(324011.78 \
         + arg*(1061660.75 + arg*(2087298.89 + arg*(2513807.78 \
         + arg*(1818961.41 + arg*(727058.63 + arg*123563.95)))))))))

  return dt;

def nutation(jd):

  dt = dyntime(jd)
  jde = jd + dt/86400.0
  bt = (jde - 2451545.0) / 36525.0

  D = 297.85036 + (445267.111480 - (0.0019142 - (bt/189474.0))*bt)*bt

  M = 357.52772 + (35999.050340 - (0.0001603 + (bt/300000.0))*bt)*bt

  MP =134.96298 + (477198.867398 + (0.0086972 + (bt/56250.0))*bt)*bt

  F = 93.27191 + (483202.017538 - (0.0036825 - (bt/327270.0))*bt)*bt

  OM = 125.04452 - (1934.136261 - (0.0020708 + (bt/450000.0))*bt)*bt

  D  %= 360.0
  M  %= 360.0
  MP %= 360.0
  F  %= 360.0
  OM %= 360.0

  sumpsi = 0.0
  sumeps = 0.0
  
  nut = open(nutFile,'r')
  line = nut.readline()
  while (line.find('END') < 0):
    params = line.split()
    m1 = int(params[0])
    m2 = int(params[1])
    m3 = int(params[2])
    m4 = int(params[3])
    m5 = int(params[4])
    amppsi0 = int(params[5])
    amppsi1 = float(params[6])
    ampeps0 = int(params[7])
    ampeps1 = float(params[8])
    multpsi = (float(amppsi0) + amppsi1*bt) * 0.0001
    multeps = (float(ampeps0) + ampeps1*bt) * 0.0001
    arg = (m1*D + m2*M + m3*MP + m4*F + m5*OM) * DTR
    sumpsi += multpsi * math.sin(arg)
    sumeps += multeps * math.cos(arg)
    line = nut.readline()
  nut.close()

  eps = sumeps
  psi = sumpsi
  obliq = 23.4392911111 - (46.8150 + (0.00059 - (0.001813*bt))*bt)*bt/3600.0;
  return (psi, eps, obliq)

def siderial(jd):
  """returns mean siderial time for the given julian date.    
   does not correct for nutation to give apparent siderial 
   time.  This is accomplished by adding Dpsi * cos(obliq)"""

  djd = jd - 2451545.0
  ip = int(math.floor(djd))
  fp = djd - ip
  bt = djd/36525.0

  st = 280.46061837 + 360.98564736629*fp + 0.98564736629*ip
  st += (0.000387933 - (bt/38710000.0))*bt*bt

  st %= 360.0

  return st


def ecliptoeq(jd, lamb, beta):
  """transforms from apparent ecliptic coords (longitude corrected for
   nutation) to apparent equatorial (R.A. and dec.), using the true
   obliquity of the ecliptic for the date.
   ...
   input is JD in days, all angles in in radians, out in degrees"""

  nut_tup = nutation(jd)
  psi = nut_tup[0]
  eps = nut_tup[1]
  obliq = nut_tup[2]
  obliq += eps/3600.0
  obliq *= DTR

  if (math.cos(lamb) == 0.0):
    alpha = lamb
  else:
    alpha = math.atan((math.sin(lamb)*math.cos(obliq) \
            - math.tan(beta)*math.sin(obliq))/math.cos(lamb));

  delta = math.asin(math.sin(beta)*math.cos(obliq) \
          + math.cos(beta)*math.sin(obliq)*math.sin(lamb));

  alpha *= RTD
  delta *= RTD

  if (math.cos(lamb) < 0.0):
    alpha += 180.0

  alpha %= 360.0

  return (alpha, delta)


def moonfeat(slong, slat, srad, totrot, rmoon):
  """This routine performs the 3D vector arithmetic to compute the
   apparent geocentric position of a feature on the moon.  Passed in
   are: selenographic longitude and latitude (in degrees), radius, 
   the 9-element rotation matrix including libration, position angle,
   and lunar position, and the 3D XYZ vector to the moon in km (X ->
   RA=DEC=0).  The returned values are the declination, right ascension
   (both deg.), and range in km (all geocentric) of the lunar feature."""

  cl = math.cos(slong * DTR)
  sl = math.sin(slong * DTR)
  cb = math.cos(slat * DTR)
  sb = math.sin(slat * DTR)

  #mrad = 1737.4
  xmoon = [0.0,0.0,0.0]
  xmoon[0] = srad*cl*cb
  xmoon[1] = srad*sl*cb
  xmoon[2] = srad*sb

  rfeat = matrix.mv3x3(totrot,xmoon)

  x = rmoon[0] + rfeat[0]
  y = rmoon[1] + rfeat[1]
  z = rmoon[2] + rfeat[2]

  rangefeat = math.sqrt(x*x + y*y + z*z)

  decfeat = RTD * math.asin(z/rangefeat)
  rafeat = RTD * math.atan2(y,x)
  rafeat %= 360.0

  return (decfeat, rafeat, rangefeat)

def topo(st, alpha, delta, range, latitude, elevation):
  """Converts geocentric apparent coordinates (RA & dec) and geocentric
   range in km into topocentric apparent coordinates.  The latitude is
   expressed in degrees, the elevation is in meters above MSL. The
   apparent siderial time (in deg) is also passed as the first argument."""

  flat = 0.99664719
  r_earth = 6378.136
  x = flat * math.tan(latitude * DTR)
  rhost = flat * x/math.sqrt(1.0 + x*x) \
          + elevation*math.sin(latitude * DTR)/(r_earth*1000.0)
  rhoct = 1.0/math.sqrt(1.0 + x*x) \
          + elevation*math.cos(latitude * DTR)/(r_earth*1000.0)
  rho = r_earth*math.sqrt(rhost*rhost + rhoct*rhoct)
  print("rho = %f\n" % (rho*1000.0))

  cst = math.cos(st*DTR)
  sst = math.sin(st*DTR)
  cdec = math.cos(delta*DTR)
  sdec = math.sin(delta*DTR)
  cra = math.cos(alpha*DTR)
  sra = math.sin(alpha*DTR)

  paral = r_earth / range
  hourang = st - alpha
  denom = cdec - rhoct*paral*math.cos(hourang*DTR)
  da = math.atan(-rhoct*paral*math.sin(hourang*DTR)/denom)
  numer = (sdec - rhost*paral)*math.cos(da)
  topodelt = math.atan(numer/denom) * RTD
  topora = alpha + da * RTD
  topora %= 360.0

  r2 = range*range + rho*rho
  r2 -= 2.0*range*r_earth*(rhoct*cst*cra*cdec + rhoct*sst*sra*cdec + rhost*sdec)

  print("surface-to-surface range is %f" % math.sqrt(r2))

  return  (topodelt, topora)


def azel(hourang, topodelt):
  """Takes in hour angle and topocentric declination (both in degrees),
   and computes the azimuth and elevation of the coordinates at the 
   location of APO, as defined in apo.h.  Az and el are in degrees."""

  if (hourang < -180.0):
     hourang += 360.0
  hourang *= DTR
  topodelt *= DTR
  numer = math.sin(hourang);
  denom = math.cos(hourang)*math.sin(APOLAT*DTR)
  denom -= math.tan(topodelt)*math.cos(APOLAT*DTR)
  azimuth = 180.0 + RTD * math.atan2(numer,denom)
  azimuth %= 360.0
  arg = math.sin(APOLAT*DTR)*math.sin(topodelt)
  arg += math.cos(APOLAT*DTR)*math.cos(topodelt)*math.cos(hourang)
  elev = RTD * math.asin(arg)

  return (azimuth, elev)


def refraction(elev, temp, press):
  """Takes elevation above horizon, in degrees, and computes the refaction,
   also in degrees, based on the temperature (kelvin) and pressure (mB)
   passed in. """

  if (elev < -1.0):
    return 0.0

  if (temp < 200.0 or temp > 320.0):
    temp = 273.15
    press = 1013.25
    print("Assuming standard temperature and pressure for refraction\n")

  refrac = 1.0/math.tan(DTR*(elev + 7.31/(elev + 4.4))) + 0.0013515
  refrac -= 0.06*math.sin(DTR*(14.7*refrac + 13))

  correc = press/1013.25 * 283.0 / temp

  return (refrac * correc)/60.0

def repr_hms(dec_value):
  if (dec_value < 0.0):
    sign = -1
  else:
    sign = 1

  dec = dec_value
  dec *= sign
  hh = int(dec)
  resid = dec - hh
  mm = int(resid*60.0)
  ss = (resid*60.0 - mm)*60.0
  hh *= sign

  outstring = "%d:%02d:%05.2f" % (hh,mm,ss)
  return outstring
