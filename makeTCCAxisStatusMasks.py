#!/usr/bin/env python
"""
Compute status masks for the TCC file tdat:axelim.dat
based on TUI's error and warn masks.
"""
import TUI.TCC.StatusWdg.AxisStatus as AxisStatus

StopButtonBit = 11

MaxBit = 31
MaxWidth = len("%s" % (2**MaxBit,))

def bitList(num):
    bitList = []
    bit = 0
    while (1<<bit) <= num:
        if num & (1<<bit) != 0:
            bitList.append(bit)
        bit += 1
    return bitList

def fmtList(alist):
    return ", ".join([str(elt) for elt in alist])

errMask = 0
for bit, name in AxisStatus.ErrorBits:
    if bit == StopButtonBit: # avoid stop button
        continue
    errMask += 1<<bit

warnMask = 0
for bit, name in AxisStatus.WarningBits:
    if bit == 11: # avoid stop button
        continue
    warnMask += 1<<bit

print("BadStatusMask  %*d ! 0x%08X = bits %s" % (MaxWidth, errMask, errMask, fmtList(bitList(errMask))))
print("WarnStatusMask %*d ! 0x%08X = bits %s" % (MaxWidth, warnMask, warnMask, fmtList(bitList(warnMask))))
