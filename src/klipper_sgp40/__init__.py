# Support for SGP40 VOC sensor
#
# Copyright (C) 2022 Adrien Le Masle
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging
import math
from struct import unpack_from

from .. import bus  # type:ignore

SGP40_REPORT_TIME = 1
SGP40_CHIP_ADDR = 0x59
SGP40_WORD_LEN = 2

SELF_TEST_CMD = [0x28, 0x0E]
MEASURE_RAW_CMD_PREFIX = [0x26, 0x0F]


def _generate_crc(data):
    # From SGP40 data sheet
    crc = 0xFF
    for i in range(2):
        crc ^= data[i]
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc = crc << 1
    return crc & 0xFF


def _check_crc8(data, crc):
    return crc == _generate_crc(data)


def _estimate_humidity(temp):
    # Magnus formula for estimating the saturation vapor pressure curve
    a = 17.62
    b = 243.12
    saturation_vapor_pressure = 6.112 * math.exp((a * temp) / (b + temp))
    actual_vapor_pressure = 6.112 * math.exp((a * 25) / (b + 25))
    relative_humidity = (actual_vapor_pressure / saturation_vapor_pressure) * 50
    return max(0, min(100, relative_humidity))


def _temperature_to_ticks(temperature):
    ticks = int(round(((temperature + 45) * 65535) / 175)) & 0xFFFF
    data = [(ticks >> 8) & 0xFF, ticks & 0xFF]
    crc = _generate_crc(data)

    return data + [crc]


def _humidity_to_ticks(humidity):
    ticks = int(round((humidity * 65535) / 100)) & 0xFFFF
    data = [(ticks >> 8) & 0xFF, ticks & 0xFF]
    crc = _generate_crc(data)

    return data + [crc]


class SGP40:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.i2c = bus.MCU_I2C_from_config(
            config, default_addr=SGP40_CHIP_ADDR, default_speed=100000
        )
        self.mcu = self.i2c.get_mcu()
        self.temp_sensor = config.get("ref_temp_sensor", None)
        self.humidity_sensor = config.get("ref_humidity_sensor", None)
        self.baseline = config.getint("baseline", 1000, minval=1)

        self.raw = 0
        self.min_temp = self.max_temp = 0
        self.max_sample_time = 1
        self.sample_timer = None

        self.printer.add_object("sgp40 " + self.name, self)
        if self.printer.get_start_args().get("debugoutput") is not None:
            return
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
        self._register_commands()

    def _register_commands(self):
        gcode = self.printer.lookup_object("gcode")
        gcode.register_mux_command(
            "QUERY_SGP40",
            "SENSOR",
            self.name,
            self.cmd_QUERY_SGP40,
            desc=self.cmd_QUERY_SGP40_help,
        )

    cmd_QUERY_SGP40_help = "Query sensor for the current values"

    def cmd_QUERY_SGP40(self, gcmd):
        gcmd.respond_info("Gas: %.2f %%\nRaw: %d" % (self.gas, self.raw))

    def _check_ref_sensor(self, name, value=None):
        sensor = self.printer.lookup_object(name)
        # check if sensor has get_status function and
        # get_status has the requested value
        if not hasattr(sensor, "get_status"):
            raise self.printer.config_error("'%s' does not report %s." % (name, value))

        reported = sensor.get_status(self.reactor.monotonic()).keys()
        if value and value not in reported:
            raise self.printer.config_error("'%s' does not report %s." % (name, value))

    def _handle_connect(self):
        if self.temp_sensor:
            self._check_ref_sensor(self.temp_sensor, "temperature")
        if self.humidity_sensor:
            # BME280 does not start reporting humidity until after connection.
            self._check_ref_sensor(self.humidity_sensor)

        self._init_sgp40()

        # Dirty way of using more retries
        # This is harcoded in serialhdl.py in Klipper
        def get_response(self, cmds, cmd_queue, minclock=0, reqclock=0):
            retries = 15
            retry_delay = 0.010
            while 1:
                for cmd in cmds[:-1]:
                    self.serial.raw_send(cmd, minclock, reqclock, cmd_queue)
                self.serial.raw_send_wait_ack(cmds[-1], minclock, reqclock, cmd_queue)
                params = self.last_params
                if params is not None:
                    self.serial.register_response(None, self.name, self.oid)
                    return params
                if retries <= 0:
                    self.serial.register_response(None, self.name, self.oid)
                    raise Exception("Unable to obtain '%s' response" % (self.name,))
                reactor = self.serial.reactor
                reactor.pause(reactor.monotonic() + retry_delay)
                retries -= 1
                retry_delay *= 2.0

        self.i2c.i2c_read_cmd._xmit_helper.get_response = get_response

        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_minmax(self, min_temp, max_temp):
        self.min_temp = min_temp
        self.max_temp = max_temp

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return SGP40_REPORT_TIME

    def _init_sgp40(self):
        # Self test
        response = self._read_and_check(SELF_TEST_CMD, wait_time_s=0.5)
        if response[0] != 0xD400:
            logging.error(self._log_message("Self test error"))

        self.sample_timer = self.reactor.register_timer(self._sample_sgp40)

    def _sample_sgp40(self, eventtime):
        # Temperature defaults to 25C
        temperature = 25
        if self.temp_sensor:
            temperature = self.printer.lookup_object(
                "{}".format(self.temp_sensor)
            ).get_status(eventtime)["temperature"]

        humidity = None
        if self.humidity_sensor:
            humidity = (
                self.printer.lookup_object("{}".format(self.humidity_sensor))
                .get_status(eventtime)
                .get("humidity")
            )
        if humidity is None:
            humidity = _estimate_humidity(temperature)

        cmd = (
            MEASURE_RAW_CMD_PREFIX
            + _humidity_to_ticks(humidity)
            + _temperature_to_ticks(temperature)
        )
        response = self._read_and_check(cmd)
        self.raw = response[0]
        self.gas = self.raw / self.baseline * 100

        measured_time = self.reactor.monotonic()
        self._callback(self.mcu.estimated_print_time(measured_time), self.gas)
        return measured_time + SGP40_REPORT_TIME

    def _read_and_check(self, cmd, read_len=1, wait_time_s=0.05):
        reply_len = read_len * (SGP40_WORD_LEN + 1)  # CRC every word

        self.i2c.i2c_write(cmd)

        # Wait
        self.reactor.pause(self.reactor.monotonic() + wait_time_s)

        params = self.i2c.i2c_read([], reply_len)
        response = bytearray(params["response"])

        data = []

        for i in range(0, reply_len, 3):
            if not _check_crc8(response[i : i + 2], response[i + 2]):
                logging.warning(self._log_message("Checksum error on read!"))
            data.append(unpack_from(">H", response[i : i + 2])[0])

        return data

    def _log_message(self, message):
        return f"SGP40 {self.name}: {message}"

    def get_status(self, eventtime):
        return {
            "gas_raw": self.raw,
            "gas": self.gas,
        }


def load_config(config):
    # Register sensor
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("SGP40", SGP40)
