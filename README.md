# Klipper SGP40 Support

This is a Klipper module that provides support for monitoring VOCs using the SGP40 sensor.

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
./install.sh [-k <klipper path>] [-s <klipper service name>] [-c <configuration path>]
```

## Configuration

```ini
[sgp40]

[temperature_sensor voc_exhaust]
sensor_type: SGP40
#i2c_mcu: mcu
#   The name of the micro-controller that the chip is connected to.
#   The default is "mcu".
#i2c_bus:
#   If the micro-controller supports multiple I2C buses then one may
#   specify the micro-controller bus name here. The default depends on
#   the type of micro-controller.
#i2c_speed: 100000
#   The I2C speed (in Hz) to use when communicating with the device.
#   The Klipper implementation on most micro-controllers is hard-coded
#   to 100000 and changing this value has no effect. The default is
#   100000.
#ref_temp_sensor:
#   The name of the temperature sensor to use as reference for temperature
#   compensation of the VOC raw measurement.
#ref_humidity_sensor:
#   The name of the temperature sensor to use as reference for humidity
#   compensation of the VOC raw measurement.
#plot_voc: False
#   Limit output to output only VOC instead of all parameters.
#   The default is False.
#voc_scale: 1.0
#   Scale factor to adjust VOC output for plotting. The default is 1.0.
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

## Mainsail

In order to display the full VOC sensor information in Mainsail,
the following command needs to be run:

```sh
~/klipper-sgp40/patch-mainsail.sh
```

> [!IMPORTANT]
> This command will need to be run each time Mainsail is updated.

If your directory structure differs from the usual setup,
you can configure the script with parameters:

```
~/klipper-sgp40/patch-mainsail.sh [-m <mainsail path>]
```

## Attribution

- This project was adapted from the [Nevermore Max](https://github.com/nevermore3d/Nevermore_Max) project.
- The [voc_algorithm.py](src/voc_algorithm.py) module is a slightly modified version of the module found in the [Adafruit CircuitPython SGP40 repository](https://github.com/adafruit/Adafruit_CircuitPython_SGP40).
- Installation scripts were adapted from the [LED Effects for Klipper](https://github.com/julianschill/klipper-led_effect) project.
