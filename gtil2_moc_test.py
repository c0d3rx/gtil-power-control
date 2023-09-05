#!/usr/bin/env python3

import argparse
import logging.config

from gtil2.Gtil2Moc import Gtil2Moc


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='gtil2 tester',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--conf-file", help="conf file", default="bberry2.yaml", required=False)
    parser.add_argument("--read", action='store_true', required=False, default=False, help="read pwr settings")
    parser.add_argument("--set-pwr", type=float, required=False, default=-1, help="set pwr in watts")
    parser.add_argument("--rel2delay", type=float, required=False, default=-1, help="test rel2delay method")
    parser.add_argument("--delay2rel", type=float, required=False, default=-1, help="test delay2rel method")
    parser.add_argument("--set-raw-pwr", type=int, required=False, default=-1, help="set raw pwr in increments")

    args = parser.parse_args()
    with open(args.conf_file, "r") as stream:
        conf = yaml.safe_load(stream)

    # init & get main logger
    logging.config.dictConfig(conf.get("logging"))

    log = logging.getLogger("bberry2")
    log.info("started")

    # init gtil2 arduino
    gtil2_control_conf: dict = conf.get("gtil2-moc-control")
    gtil2_control_modbusclient = gtil2_control_conf.pop("modbusclient")

    gtil2_control = Gtil2Moc(
        modbusclient_config=gtil2_control_modbusclient,
        **gtil2_control_conf)

    if args.rel2delay >= 0:
        rel2delay = args.rel2delay
        delay = gtil2_control.relative_pwr2delay(rel2delay)
        log.info(f"{delay=} for {rel2delay} pwr")

    if args.delay2rel >= 0:
        delay2rel = args.delay2rel
        relpwr = gtil2_control.delay2relative_pwr(delay2rel)
        log.info(f"{relpwr=} for {delay2rel} uSec")

    if args.read:
        pwr = gtil2_control.get_pwr()
        log.info(f"{pwr=}")

    if args.set_pwr >= 0:
        gtil2_control.set_pwr(args.set_pwr)

    if args.set_raw_pwr >= 0:
        gtil2_control.set_raw_pwr(args.set_raw_pwr)





