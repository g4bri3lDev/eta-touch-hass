"""Presentation metadata for catalog keys."""

from __future__ import annotations

from dataclasses import dataclass, replace

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)


@dataclass(frozen=True, kw_only=True, slots=True)
class Meta:
    """How a catalog key is presented."""

    unit: str | None = None
    sensor_class: SensorDeviceClass | None = None
    number_class: NumberDeviceClass | None = None
    suggested_unit: str | None = None
    precision: int | None = None
    config: bool = False
    # numbers only: shown value = raw value / scale / number_divisor, in number_unit
    number_unit: str | None = None
    number_divisor: int = 1


PLAIN = Meta()
CONFIG = Meta(config=True)
TEMP = Meta(
    unit=UnitOfTemperature.CELSIUS,
    sensor_class=SensorDeviceClass.TEMPERATURE,
    number_class=NumberDeviceClass.TEMPERATURE,
    precision=1,
)
TEMP_CONFIG = replace(TEMP, config=True)
DELTA_CONFIG = Meta(unit=UnitOfTemperature.CELSIUS, precision=1, config=True)
PERCENT = Meta(unit=PERCENTAGE, precision=0)
WEIGHT = Meta(
    unit=UnitOfMass.KILOGRAMS,
    sensor_class=SensorDeviceClass.WEIGHT,
    number_class=NumberDeviceClass.WEIGHT,
    precision=0,
)
WEIGHT_CONFIG = replace(WEIGHT, config=True)
HOURS = Meta(
    unit=UnitOfTime.SECONDS,
    sensor_class=SensorDeviceClass.DURATION,
    suggested_unit=UnitOfTime.HOURS,
    precision=0,
)

META: dict[str, Meta] = {
    # shared
    "power": PLAIN,
    "outdoor_temperature": TEMP,
    "flow_temperature": TEMP,
    "return_temperature": TEMP,
    "hot_water_charge_now": PLAIN,
    "switch_on_difference": DELTA_CONFIG,
    "priority": CONFIG,
    "requested_power": Meta(
        unit=UnitOfPower.KILO_WATT, sensor_class=SensorDeviceClass.POWER, precision=1
    ),
    # boiler
    "boiler_state": PLAIN,
    "boiler_temperature": TEMP,
    "boiler_target_temperature": TEMP,
    "boiler_return_temperature": TEMP,
    "flue_gas_temperature": TEMP,
    "residual_oxygen": Meta(unit=PERCENTAGE, precision=1),
    "boiler_pressure": Meta(
        unit=UnitOfPressure.BAR, sensor_class=SensorDeviceClass.PRESSURE, precision=2
    ),
    "requested_temperature": TEMP,
    "flue_gas_fan_speed": Meta(unit=REVOLUTIONS_PER_MINUTE, precision=0),
    "boiler_pump": PERCENT,
    "stoker_screw": PERCENT,
    "ignition": PLAIN,
    "suction_turbine": PLAIN,
    "ash_box": PLAIN,
    "pellet_container": PLAIN,
    "pellet_container_content": WEIGHT,
    "total_consumption": WEIGHT,
    "consumption_since_ash_box_emptied": WEIGHT,
    "consumption_since_deashing": WEIGHT,
    "empty_ash_box_after": WEIGHT_CONFIG,
    "full_load_hours": HOURS,
    "full_load_hours_since_service": HOURS,
    "full_load_hours_since_cleaning": HOURS,
    "ignition_count": PLAIN,
    "heating_run_count": PLAIN,
    "fill_pellet_container": PLAIN,
    "pellet_suction_time": PLAIN,
    "quiet_time_start": CONFIG,
    "quiet_time_duration": Meta(
        unit=UnitOfTime.SECONDS,
        sensor_class=SensorDeviceClass.DURATION,
        suggested_unit=UnitOfTime.HOURS,
        number_class=NumberDeviceClass.DURATION,
        number_unit=UnitOfTime.MINUTES,
        number_divisor=60,
        config=True,
    ),
    # pellet store
    "discharge_state": PLAIN,
    "pellet_stock": WEIGHT,
    "pellet_stock_warning_limit": WEIGHT_CONFIG,
    "discharge_screw": PERCENT,
    # heating circuit
    "heating_circuit_state": PLAIN,
    "operating_mode": PLAIN,
    "heating_circuit_pump": PLAIN,
    "curve_offset": PERCENT,
    "flow_at_minus_10": TEMP_CONFIG,
    "flow_at_plus_10": TEMP_CONFIG,
    "setback_reduction": DELTA_CONFIG,
    "heating_limit_day": TEMP_CONFIG,
    "heating_limit_night": TEMP_CONFIG,
    "heat_button": PLAIN,
    "auto_button": PLAIN,
    "setback_button": PLAIN,
    "come_button": PLAIN,
    "go_button": PLAIN,
    # hot water
    "hot_water_state": PLAIN,
    "hot_water_temperature": TEMP,
    "hot_water_bottom_temperature": TEMP,
    "hot_water_target_temperature": TEMP,
    "charge_now_target_temperature": TEMP_CONFIG,
    "hot_water_charging_pump": PLAIN,
    # buffer
    "buffer_state": PLAIN,
    "buffer_charge_level": PERCENT,
    "buffer_top_temperature": TEMP,
    "buffer_bottom_temperature": TEMP,
    "buffer_sensor_2_temperature": TEMP,
    "buffer_sensor_3_temperature": TEMP,
    "buffer_sensor_4_temperature": TEMP,
    "buffer_top_target_temperature": TEMP,
    "buffer_charge_now": PLAIN,
    "buffer_charge_count": PLAIN,
    # solar
    "solar_state": PLAIN,
    "collector_temperature": TEMP,
    "collector_pump": PERCENT,
    "storage_1_bottom_temperature": TEMP,
    # system
    "fault_status": PLAIN,
    "anti_seize_time": CONFIG,
}
