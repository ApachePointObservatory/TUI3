import math

def mv3x3(a,b):

  """Takes a 3x3 matrix pointer, a, stored in a 1-d array nine
   elements long (row major, such that elements 0,1,2 go across a
   row, and 0,3,6 go down a column), and a 3x1 vector pointer, b,
   and multiplies a*b = c. """

  c = []

  for i in range(3):
    c.append(a[i][0]*b[0] + a[i][1]*b[1] + a[i][2]*b[2])

  return c

def mm3x3(a, b):

  """Takes two 3x3 matrix pointers, a, b, stored in 1-d arrays nine
   elements long (row major, such that elements 0,1,2 go across a
   row, and 0,3,6 go down a column), and multiplies a*b = c.  Note
   that order matters: a*b is not the same as b*a."""
  
  c = [[],[],[]]

  for i in range(3):
    for j in range(3):
      c[i].append(a[i][0]*b[0][j] + a[i][1]*b[1][j] + a[i][2]*b[2][j])

  return c
  
def vdot3(a, b):

  """Takes a 3-d vector pointer, a,
   a 3-d vector pointer, b,
   and performs dot product:  a.b = c."""

  c = 0.0
  for i in range(3):
    c += a[i]*b[i]

  return c;

def vcross3(a, b):

  """Takes a 3-d vector pointer, a,
   a 3-d vector pointer, b,
   and performs cross product:  a x b = c."""

  c = []

  c.append(a[1]*b[2] - a[2]*b[1])
  c.append(a[2]*b[0] - a[0]*b[2])
  c.append(a[0]*b[1] - a[1]*b[0])

  return c

def vabs3(a):

  """Returns magnitude of a vector"""

  return math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2])
