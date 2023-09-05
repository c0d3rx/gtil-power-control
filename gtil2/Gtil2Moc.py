# from . import Gtil2Base
import math
import sys

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from . import log


class Gtil2Moc:
    CONVTABLE_SIZE: int = 1000
    __CONVTABLE_FACTOR: float = 10000. / float(CONVTABLE_SIZE)

    def __init__(self, vpk: float = 4, vtriac: float = 1.1, load_resistor:float = 100, zcd_delay: int = 200, turns: int = 100, voltage: float = 230, max_pwr: float = 350, modbusclient_config={}, modbus_unit=1):
        """
        init
        :param vpk: peak voltage of triac side transformer
        :param vtriac: triac threshold voltage
        :param load_resistor: load resistor, R + coil
        :param zcd_delay: delay from zero crossing detector rising edge to true zero crossing in uSec
        :param turns: turns, Current transformer reverse current coil turn
        :param voltage: ref voltage, in volts, e.g. 230
        :param max_pwr: max delivered power, in watts
        :param modbusclient_config:
        :param modbus_unit:
        """
        self.pwr: float = 0
        self.__raw_value: int = -1
        self.rel_pwr: float = 0
        self.max_raw_level = 9800  # full off
        self.min_raw_level = 100   # full on

        self.vpk = vpk
        self.vtriac = vtriac
        self.load_resistor = load_resistor
        self.zcd_delay = zcd_delay

        self.gtil_client = gtil_client = ModbusClient(method="rtu", **modbusclient_config)
        self.modbus_unit = modbus_unit

        self.turns = turns
        self.voltage = voltage
        self.max_pwr = max_pwr
        self.delay2pwr = None
        self.pwr2delay = None
        self.max_rms = None
        self.full_pwr: float = None
        self.maxdelay: float = None
        self.factor_delay2pwr: float = None
        self.init_conversion_tables()

        log.debug(f"{modbusclient_config=}, "
                  f"{self.modbus_unit=}, "
                  f"{self.max_raw_level=}, "
                  f"{self.modbus_unit=}, "
                  f"{self.vpk=} (Volts), "
                  f"{self.vtriac=} (Volts), "
                  f"{self.load_resistor=} (ohm), "
                  f"{self.zcd_delay=} (uSec), "
                  f"{self.max_rms=} (Volts), "
                  f"{self.turns=}, "
                  f"{self.voltage=} (Volts), "                  
                  f"{self.full_pwr=} (Watts), "
                  f"{Gtil2Moc.CONVTABLE_SIZE=}, "
                  f"{Gtil2Moc.__CONVTABLE_FACTOR=}, "
                  f"{self.max_pwr=} (Watts), ")

    def init_conversion_tables(self):
        """
        init conversions tables..
        :return:
        """
        vtriac_norm = self.vtriac / self.vpk

        steps = Gtil2Moc.CONVTABLE_SIZE
        rad = 0
        rad_step = math.pi / steps

        # rms
        rmsa = []
        rmsacc = 0
        # current
        ia = []
        iacc = 0
        # energy
        ea = []
        eacc: float = 0

        i = 0
        while i < steps:
            v = math.sin(rad) * self.vpk
            vt = v-self.vtriac if v > 0 else v+self.vtriac
            if vt < 0:
                vt = 0
            # rms
            rmsacc += vt**2
            rmsavg = rmsacc/steps
            rmsa += [math.sqrt(rmsavg)]
            # current
            iacc += (vt/self.load_resistor)
            iavg = iacc/steps
            ia += [iavg]
            # energy ( joule )
            energy = (vt**2)/self.load_resistor
            energy /= Gtil2Moc.CONVTABLE_SIZE
            energy *= Gtil2Moc.__CONVTABLE_FACTOR
            eacc += energy
            eavg = eacc/steps
            ea += [eavg]

            rad += rad_step
            i += 1
        # maxes
        maxrms = max(rmsa)
        maxi = max(ia)
        maxe = max(ea)
        log.debug(f"{maxrms=}, {maxi=}, {maxe=}")
        self.max_rms = maxrms
        self.full_pwr = maxrms/self.load_resistor * self.turns * self.voltage

        # normalizzo ia
        ia = [i/maxi for i in ia]

        # ritardo triac 10000 ( uSec )
        # l'interrupt avviene sul fronte a salire quindi va aggiunto il tempo
        # che intercorre tra il fronte a salire e lo zero crossing della sinusoide al
        # ritardo

        lktable = {}
        lktablecnt = {}
        for delay, i in enumerate(ia):
            lkindex = int(i * float(Gtil2Moc.CONVTABLE_SIZE))
            value = 10000 - int(delay * Gtil2Moc.__CONVTABLE_FACTOR)
            if lkindex not in lktable:
                lktable[lkindex] = value
                lktablecnt[lkindex] = 1
            else:
                lktable[lkindex] += value
                lktablecnt[lkindex] += 1

        pwr2delay = [-1 for i in range(Gtil2Moc.CONVTABLE_SIZE+1)]
        for rms, delay in lktable.items():
            pwr2delay[rms] = int(delay / lktablecnt[rms]) + self.zcd_delay

        # riempie i buchi
        old_delay = self.max_raw_level
        for rms, delay in enumerate(pwr2delay):
            if delay == -1:
                pwr2delay[rms] = old_delay
            else:
                old_delay = delay

        self.pwr2delay = pwr2delay
        # delay2pwr
        maxdelay = max(pwr2delay)
        log.debug(f"{maxdelay=}")
        self.maxdelay = maxdelay
        factor_delay2pwr = maxdelay/Gtil2Moc.CONVTABLE_SIZE
        self.factor_delay2pwr = factor_delay2pwr
        delay2pwr = [-1 for i in range(Gtil2Moc.CONVTABLE_SIZE+1)]
        for rms, delay in enumerate(pwr2delay):
            index = int(delay / factor_delay2pwr)
            if delay2pwr[index] == -1:
                delay2pwr[index] = rms/Gtil2Moc.CONVTABLE_SIZE
            # log.debug(f"{rms}, {delay}")

        old_pwr = 1
        for i, pwr in enumerate(delay2pwr):
            if pwr == -1:
                delay2pwr[i] = old_pwr
            else:
                old_pwr = pwr
        self.delay2pwr = delay2pwr

    def relative_pwr2delay(self, relative_pwr: float):
        """
        get relative pwr using tables
        :param relative_pwr: 0 = min, 1 = max
        :return: delay in uSec
        """
        if relative_pwr < 0 or relative_pwr > 1:
            raise Exception("relative power not in 0 to 1 range")

        relative_pwr_index = int(relative_pwr * Gtil2Moc.CONVTABLE_SIZE)
        delay = self.pwr2delay[relative_pwr_index]
        return delay

    def delay2relative_pwr(self, delay) -> float:
        """
        get relative pwr, given delay in uSec
        :param delay:
        :return: relative pwr
        """
        if delay < 0:
            delay = 0
        if delay > self.maxdelay:
            delay = self.maxdelay

        delay_index = int(delay/self.factor_delay2pwr)
        return self.delay2pwr[delay_index]

    def read_raw_pwr(self):
        regs = self.gtil_client.read_holding_registers(address=0, count=1, unit=self.modbus_unit)
        self.__raw_value = regs.getRegister(0)
        log.debug(f"from modbus: {self.__raw_value=}")

    def read_rel_pwr(self):
        """
        read actual relative pwr
        :return:
        """
        self.read_raw_pwr()
        self.rel_pwr = self.delay2relative_pwr(self.__raw_value)

    def get_rel_pwr(self):
        self.read_rel_pwr()
        return self.rel_pwr

    def get_pwr(self) -> float:
        self.read_rel_pwr()
        self.pwr = self.rel_pwr * self.full_pwr
        return self.pwr

    def set_raw_pwr(self, raw_value: int):
        """
        set raw pwr
        :param raw_value: delay in uSec after triac fire: min 10 max 9999
        :return:
        """
        if raw_value < self.min_raw_level:
            raw_value = self.min_raw_level
        if raw_value > self.max_raw_level:
            raw_value = self.max_raw_level

        if raw_value != self.__raw_value:
            log.debug(f"to modbus: {raw_value=}")
            self.gtil_client.write_register(0, raw_value, unit=self.modbus_unit)
            self.__raw_value = raw_value

    def set_relative_pwr(self, rel_pwr: float):
        """
        set relative pwr: 0=min, 1=max
        :param rel_pwr:
        :return:
        """

        #   compute raw value

        log.debug(f"Attempt to set rel_pwr to {rel_pwr*100:.1f}%")
        raw_value = self.relative_pwr2delay(rel_pwr)
        self.set_raw_pwr(raw_value)

    def set_pwr(self, pwr: float):
        if pwr < 0:
            pwr = 0
        if pwr > self.full_pwr:
            pwr = self.full_pwr

        if pwr > self.max_pwr:
            pwr = self.max_pwr

        log.debug(f"Attempt to set pwr to {pwr}")
        relative_pwr = pwr / self.full_pwr
        self.set_relative_pwr(relative_pwr)
        self.pwr = pwr
