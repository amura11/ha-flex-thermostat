# HomeAssistant Flex Thermostat
[![GitHub Release][releases-shield]][releases]
[![HACS Validation][validation-shield]](validation)
[![hacs][hacsbadge]][hacs]

[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

Flex Thermostat is a Home Assistant integration designed for straightforward setup and extensive customization of thermostat controls in your smart home. Key features include:

- **Custom Configurable Presets:**

  Easily define and switch between personalized temperature presets to suit your preferences and daily routines.

- **Independent Heating, Cooling, and Fan Control via Switch Entities:**

  Gain precise control over your HVAC system with separate switch entities for heating, cooling, and fan functions.

- **Openings with Customizable Delays:**

  Seamlessly integrate door or window openings into your climate control strategy, with customizable delays for enhanced energy efficiency.

Flex Thermostat offers a balance between simplicity and flexibility, providing users with a customizable solution for effective climate management within Home Assistant.


## Basic Configuration Options

 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`name` | string | The name of the entity | ✔ |
`temp_sensor` | string | The sensor to use as the current temperature. | ✔ |
`heater_switch` | string | The ID of the switch entity to toggle when heating is needed. |
`cooler_switch` | string | The ID of the switch entity to toggle when cooling is needed. |
`fan_switch` | string | The ID of the switch entity to toggle when the fan is needed. |
`min_temp` | number | The minimum temperature the thermostat can be set to. | | 7C/40F/280K
`max_temp` | number | The maximum temperature the thermostat can be set to. | | 35C/80F/308K
`temp_step` | number |  The ammount the temperature will increase/decrease in a single step. | | 1.0
`temp_tolerance` | number | The difference from the target temperature required to start an HVAC cycle. | | 0.75
`openings` | array of [Openings](#opening-configuration-options) | An array of [Openings](#opening-configuration-options) that will be tracked. | |
`presets` | arrar of [Presets](#preset-configuration-options) | An array of custom defined [Presets](#preset-configuration-options). | |
`default_opening_delay` | [Time Delay](#time-delay) | The default delay to use when an opening changes state before taking any action. | | 30 Seconds (`00:00:30`)
`default_preset_hvac_mode` | [HVACMode](#hvac-modes) | The default `HVACMode` to use for presets that don't specify a mode. | | `off`
`default_preset_fan_mode` | [FanMode](#fan-modes) | The default `FanMode` to use for presets that don't specify a fan mode. | | `off`
`initial_preset` | string | The initial preset to use when the thermostat is first started and has no previously stored state. | |
`initial_settings` | [Initial Settings](#initial-settings-options) | The initial HVAC settings to use when the thermostat is first started and has no previously stored state. | |

### HVAC Modes
This is a subset of the [Home Assistant HVAC Modes](https://developers.home-assistant.io/docs/core/entity/climate/#hvac-modes).
Name | Description
-- | --
`OFF` | The device is turned off.
`HEAT` | The device is set to heat to a target temperature.
`COOL` | The device is set to cool to a target temperature.
`HEAT_COOL` | The device is set to heat/cool to a target temperature range.
`FAN_ONLY` | The device only has the fan on. No heating or cooling taking place.

### Fan Modes
These modes are different than the built in Home Assistant Fan modes
Name | Description
-- | --
`on` | The fan is set be on at all times.
`off` | The fan is set to be off at all times.
`auto` | The fan is only turned on when heating or cooling is taking place.

### Time Delay
In a Home Assistant a time delay can be represented in a variety of ways listed below. All formats are designed to represent a positive length of time.

Format | Example
-- | --
`DD HH:MM:SS.uuuuuu` | 3 04:05:06.7
`DD HH:MM:SS,uuuuuu` | 3 04:05:06,7
[ISO 8601 Duration](https://en.wikipedia.org/wiki/ISO_8601#Durations) | P3DT4H5M6S
PostgreSQL day-time interval | 3 days 04:05:06

### Opening Configuration Options
 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`entity_id` | string | The ID of the opening entity to track. | ✔ |
`delay` | [Time Delay](#time-delay) | The delay to use when the opening changes state before taking any action. | | `default_opening_delay`

### Preset Configuration Options
 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`name` | string | The name of the preset | ✔ |
`target_temp` | number | The target temperature. | ✔* |
`target_temp_low` | number | The target temperature range lower bound. | ✔* |
`target_temp_high` | number | The target temperature range upper bound. | ✔* |
`hvac_mode` | [HVACMode](#hvac-modes) | The HVAC mode to set for the preset. | | `default_preset_hvac_mode`
`fan_mode` | [FanMode](#fan-modes) | The fan mode to set for the preset. | | `default_preset_fan_mode`

\* If the `hvac_mode` is `HEAT_COOL` both `target_temp_low` and `target_temp_high` are required. Otherwise `target_temp` is required

### Initial Settings Options
 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`target_temp` | number | The target temperature. | ✔* |
`target_temp_low` | number | The target temperature range lower bound. | ✔* |
`target_temp_high` | number | The target temperature range upper bound. | ✔* |
`hvac_mode` | [HVACMode](#hvac-modes) | The HVAC mode to set for the preset. | | `default_preset_hvac_mode`
`fan_mode` | [FanMode](#fan-modes) | The fan mode to set for the preset. | | `default_preset_fan_mode`

\* If the `hvac_mode` is `HEAT_COOL` both `target_temp_low` and `target_temp_high` are required. Otherwise `target_temp` is required

## Full Configuration Example
```
climate:
  - platform: flex_thermostat
    name: My Thermostat
    temp_sensor: input_number.fake_temp
    heater_switch: input_boolean.fake_heater
    cooler_switch: input_boolean.fake_cooler
    fan_switch: input_boolean.fake_fan

    min_temp: 15
    max_temp: 32
    temp_step: 0.1
    temp_tolerance: 0.5

    openings:
    - opening: input_boolean.fake_opening_1
      delay: 00:00:10
    - opening: input_boolean.fake_opening_2

    preset_modes:
    - name: Preset1
      hvac_mode: heat
      fan_mode: "off"
      target_temp: 22
    - name: Preset2
      hvac_mode: heat_cool
      target_temp_low: 19
      target_temp_high: 23

    default_opening_delay: 00:00:30
    default_preset_hvac_mode: "off"
    default_preset_fan_mode: "off"

    initial_settings:
      hvac_mode: heat
      fan_mode: "on"
      target_temp: 21
```

[releases-shield]: https://img.shields.io/github/release/amura11/ha-flex-thermostat.svg?style=for-the-badge
[releases]: https://github.com/amura11/ha-flex-thermostat/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/amura11/ha-flex-thermostat.svg?style=for-the-badge
[commits]: https://github.com/amura11/ha-flex-thermostat/commits/main
[license-shield]: https://img.shields.io/github/license/amura11/ha-flex-thermostat.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[validation-shield]: https://img.shields.io/github/actions/workflow/status/amura11/ha-flex-thermostat/validate.yml?style=for-the-badge&label=HACS%20Validation
[validation]: https://github.com/amura11/ha-flex-thermostat/actions/workflows/validate.yml