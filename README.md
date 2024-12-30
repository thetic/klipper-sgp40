# Klipper Nevermore

This is a [Klipper](https://www.klipper3d.org/) module that provides support for monitoring [VOCs](https://en.wikipedia.org/wiki/Volatile_organic_compound) using the SGP40 sensor.

## Installation instructions

The module can be installed into a existing Klipper installation with an install script.

```sh
cd ~
git clone https://github.com/thetic/klipper-sgp40.git
cd klipper-sgp40
./install.sh
```

If your directory structure differs from the usual setup,
you can configure the installation script with parameters:

```
./install.sh [-k <klipper path>] [-s <klipper service name>] [-c <configuration path>] [-u] 1>&2
```

> [!WARNING]
> This module is a work in progress.
> Files are likely to change names and paths as changes are made.
> It is recommended to uninstall with `./install.sh -u` before updating,
> then to reinstall afterwards.

Then, add the following to your `moonraker.conf` to enable automatic updates:

```ini
[update_manager klipper-sgp40]
type: git_repo
path: ~/klipper-sgp40
origin: https://github.com/thetic/klipper-sgp40.git
primary_branch: main
managed_services: klipper
```

## Configuration

```ini
[sgp40]

[temperature_sensor my_sensor]
sensor_type: SGP40
#i2c_address: 89
#   Default is 89 (0x59).
#i2c_mcu:
#i2c_bus:
#i2c_software_scl_pin:
#i2c_software_sda_pin:
#i2c_speed: 100000
#   See the "common I2C settings" at
#   https://www.klipper3d.org/Config_Reference.html#common-i2c-settings
#   for a description of the above parameters.
#   The default "i2c_speed" is 100000.
#ref_temp_sensor:
#   The name of the temperature sensor to use as reference for temperature
#   compensation of the VOC raw measurement. If not defined calculations
#   will assume 25°C.
#ref_humidity_sensor:
#   The name of the temperature sensor to use as reference for humidity
#   compensation of the VOC raw measurement. If not defined calculations
#   will assume 50% humidity.
#baseline: 1000
#   Baseline reading of the sensor.  This should be the "Raw" reading
#   reported by the `QUERY_SGP40` command. gas readings are reported as
#   a percentage of this value. The default "baseline" is 1000.
```

### Example

The following is an example using a [Nevermore PCB](https://github.com/xbst/Nevermore-PCB/tree/master)
from [Isik's Tech](https://store.isiks.tech/collections/nevermore-electronics) and two pairs of BME280 and SGP40 sensors.
Both air intake sensors are wired to I2C1, and exhaust sensors are wired to I2C2.
Edit the I2C bus to match which sensors are connected to which connector on the PCB.

```ini
[mcu nevermore]
# ...

[sgp40]

[temperature_sensor BME_OUT]
sensor_type: BME280
i2c_address: 119
i2c_mcu: nevermore
i2c_bus: i2c1_PB8_PB9

[temperature_sensor BME_IN]
sensor_type: BME280
i2c_address: 119
i2c_mcu: nevermore
i2c_bus: i2c2_PB10_PB11

[temperature_sensor SGP_OUT]
sensor_type: SGP40
i2c_mcu: nevermore
i2c_bus: i2c1_PB8_PB9
ref_temp_sensor: bme280 BME_OUT
ref_humidity_sensor: bme280 BME_OUT

[temperature_sensor SGP_IN]
sensor_type: SGP40
i2c_mcu: nevermore
i2c_bus: i2c2_PB10_PB11
ref_temp_sensor: bme280 BME_IN
ref_humidity_sensor: bme280 BME_IN
```

## Attribution

- This project was adapted from the [Pull Request against Klipper](https://github.com/Klipper3d/klipper/pull/6738) by Stefan Dej
  which was itself adapted from the [Nevermore Max](https://github.com/nevermore3d/Nevermore_Max) project.
