#!/usr/bin/env python3
import argparse
import configparser
import math
import matplotlib.pyplot as plt


# 2.44
# 3.62

# foto triac taglia a 0.6 volt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='sinus-table',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    args = parser.parse_args()

    vpk = 3.62
    vtriac = 0.85
    zerocrossing_offset = 420 # in uSec, from rising edge to 0 crossing of sinus

    # vtriac, normalized
    vtriac_norm = vtriac / vpk
    #print(f"vpk: {vpk}, vtriac: {vtriac}, vtriac_norm: {vtriac_norm}")

    steps = 1000
    rad = 0
    rad_step = math.pi / steps

    x = []
    y = []
    rmsa = []

    rmsacc = 0
    i = 0
    while rad < math.pi:
        v = math.sin(rad)
        v = v-vtriac_norm
        if v < 0:
            v = 0
        deg = math.degrees(rad)
        x += [deg]
        y += [v]
        rmsacc += v**2
        rmsavg = rmsacc/steps
        rmsa += [math.sqrt(rmsavg)]

        #print(deg, v)
        rad = rad + rad_step
        i += 1

    plt.plot(x, y, label='sinus')
    plt.plot(x, rmsa, label='rms')
    plt.xlabel('deg')
    plt.ylabel('v')
    plt.legend()
    #plt.show()

# prende il massimo da rmstable e normalizza l'intero array
    maxv = rmsa[-1]
    lktable = {}
    i = 0
    for v in rmsa:
        lkindex = int(v/maxv * 999.)
        if i < steps/2:
            lktable[lkindex] = i
        else:
            if lkindex not in lktable:
                lktable[lkindex] = i
        i += 1

    # normalizza tabella in base a delay ..
    # ritardo triac 10000 = sempre chiuso, 0 = sempre aperto
    lktable2 = {}
    for v, delay in lktable.items():
        delay_open_triac = 10000+zerocrossing_offset - delay*10
        #print(v, delay, delay_open_triac)
        lktable2[v] = delay_open_triac

    #print(lktable2)
    #print(len(lktable2))

    pwr2delay = [-1 for i in range(1000)]
    for v, delay in lktable2.items():
        pwr2delay[v] = delay

    i = 0
    oldv = pwr2delay[0]
    while i < 1000:
        v = pwr2delay[i]
        if v == -1:
            pwr2delay[i] = oldv
        else:
            oldv = v
        i += 1

# pwr2delay
    print(f"pwr2delay = {pwr2delay}")

# delay2pwr ( delay / 10 )
    delay2pwr = [-1 for i in range(1000)]
    i = 0
    for delay in pwr2delay:
        delay2pwr[int(delay/10.)] = i
        i += 1

    old_pwr = 999
    i = 0
    for pwr in delay2pwr:
        if pwr == -1:
            delay2pwr[i] = old_pwr
        else:
            old_pwr = pwr
        i += 1

    print(f"delay2pwr = {delay2pwr}")













