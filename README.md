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
./install.sh [-k <klipper path>] [-s <klipper service name>] [-c <configuration path>] [-v <klippy venv path>] [-u] 1>&2
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
virtualenv: ~/klippy-env
requirements: requirements.txt
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
#sampling_interval: 1.0
#   Time in seconds to wait between sensor measurements.
#   Values must be between 1.0 and 10.0.
#   The default "sampling_interval" is 1.0.
#ref_temp_sensor:
#   The name of the temperature sensor to use as reference for temperature
#   compensation of the VOC raw measurement. If not defined calculations
#   will assume 25°C.
#ref_humidity_sensor:
#   The name of the temperature sensor to use as reference for humidity
#   compensation of the VOC raw measurement. If not defined calculations
#   will assume 50% humidity.
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

## Calibration

> [!INFO]
> The printer cannot be used during calibration.

Calibration establishes a baseline corresponding to "clean air", where "clean air" means as clean as the air in the room.
This will take at least 8 hours and ideally 24 hours.

> [!WARNING]
> Wash your printer if there is _any_ smell prior to calibration.
> There is no point calibrating a baseline if it is dirty and off gassing.
> Use hot water & soap to scrub the panels, enclosures, print sheets, beds, etc.
>
> A dirty printer will result in VOC readings that start around 100, but then rise to 400+.
> The air is steadily getting dirtier from whatever is off-gassing.
> The air will keep getting worse until it reaches saturation.
> If you were to plot the raw response, you’d see it steadily degrade over time.
>
> The initial plateau at 100 VOC Index is because the system will assume the initial conditions are nominal before adjusting the expected range;
> this is when the VOC Index will begin to increase.

1. Cool down the printer
2. Make sure any air filter fans are turned off.
3. Open the printer enclosure
4. (_Optional_) Remove any filter material (e.g. carbon).
   This helps ensure all sensors are exposed to the same air and reach similar calibrations.
5. Let some fresh air into the room for a minute or two.
   Open a window for a few minutes, flap a hand towel in the doorway, whatever.
   The objective is to get clean air into the enclosure.
   **This air will serve as reference for the baseline.**
   If you’re not happy breathing it, it isn't clean air.
6. Close the printer enclosure.
7. Leave the printer alone for at least 8 hours, and up to 24 hours if possible.
8. Run the [`CALIBRATE_SGP40`](#CALIBRATE_SGP40) for each configured sensor.
9. Run the [`SAVE_CONFIG`](https://www.klipper3d.org/G-Codes.html#save_config) command.
   This will add the baseline values to `printer.cfg`.
10. Reinstall any filter media removed in step 4.

The system should now have a good baseline for the sensors.

> [!INFO]
> Sensor readings may drift over time requiring recalibration.

## G-Code Commands

### `CALIBRATE_SGP40`

`CALIBRATE_SGP40 SENSOR=config_name`:
Store the SGP40 sensor's calibrated baseline.

### QUERY_SGP40

`QUERY_SGP40 SENSOR=config_name`:
Queries the current state of the SGP40 sensor.
The data displayed on the terminal.

## Attribution

- This project was adapted from the [Pull Request against Klipper](https://github.com/Klipper3d/klipper/pull/6738) by Stefan Dej
  which was itself adapted from the [Nevermore Max](https://github.com/nevermore3d/Nevermore_Max) project.
- Many features were adapted from the [Nevermore Controller](https://github.com/SanaaHamel/nevermore-controller) project.
