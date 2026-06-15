import re
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up FPL Gulf sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        # --- Device Group 1: Account Profile Device ---
        FPLAccountNumberSensor(coordinator),
        FPLAccountTypeSensor(coordinator),
        FPLCustomerNumberSensor(coordinator),
        FPLContractIdSensor(coordinator),
        FPLRecentBillSensor(coordinator),
        FPLAvgDailyCostSensor(coordinator),
        FPLEstimatedDailyAvgKwhSensor(coordinator),
        FPLCurrentCycleAccruedCostSensor(coordinator),
        FPLProjectedBillSensor(coordinator),
        
        # --- Device Group 2: Smart Meter Hardware Device ---
        FPLMeterNumberSensor(coordinator),
        FPLPremiseNumberSensor(coordinator),
        FPLAccountClassSensor(coordinator),
        FPLRateCategorySensor(coordinator),
        FPLLastCycleConsumptionSensor(coordinator)
    ]

    tracked_categories = ["cooling", "waterHeater", "laundry", "refrigeration", "entertainment", "alwaysOn", "lighting"]
    for category in tracked_categories:
        entities.append(FPLCategoryUsageSensor(coordinator, category))

    # 🟢 FIXED: This line was missing, which caused all appliances to vanish!
    async_add_entities(entities)


def parse_fpl_date(date_str):
    """Helper to convert FPL's /Date(MilliSeconds)/ string formatting into clean text."""
    if not date_str or not isinstance(date_str, str):
        return None
    match = re.search(r"\/Date\((\d+)\)\/", date_str)
    if match:
        timestamp = int(match.group(1)) / 1000.0
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    return date_str


# =====================================================================
# DEVICE GROUP 1: LIVE & HISTORICAL ACCOUNT PROFILE METRICS
# =====================================================================

class FPLAccountBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class providing shared account profile device mapping."""
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"account_profile_{self.coordinator.account}")},
            "name": "FPL Account Profile",
            "manufacturer": "Florida Power & Light",
            "model": "Customer Live & Billing Profile",
            "sw_version": "1.1.4",
        }

class FPLEstimatedDailyAvgKwhSensor(FPLAccountBaseSensor):
    """Tracks live ongoing daily average energy consumption (kWh) for the active cycle."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Estimated Daily Avg Consumption"
        self._attr_unique_id = f"{coordinator.account}_estimated_daily_avg_kwh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "kWh"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        info = (
            self.coordinator.data.get("live_summary", {})
            .get("accountSummary", {})
            .get("accountSummaryData", {})
            .get("billAndMeterInfo", {})
        )
        val = info.get("dailyAvgKwh")
        return float(val) if val is not None else None


class FPLAvgDailyCostSensor(FPLAccountBaseSensor):
    """Tracks live ongoing daily financial operational burn rate for the active cycle."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Avg Daily Cost"
        self._attr_unique_id = f"{coordinator.account}_avg_daily_cost"
        self._attr_native_unit_of_measurement = "USD"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        info = (
            self.coordinator.data.get("live_summary", {})
            .get("accountSummary", {})
            .get("accountSummaryData", {})
            .get("billAndMeterInfo", {})
        )
        val = info.get("dailyAvgAmount")
        return float(val) if val is not None else None

    @property
    def extra_state_attributes(self):
        attrs = {}
        if not self.coordinator.data:
            return attrs

        results = self.coordinator.data.get("comparison", {}).get("results", [])
        if results and isinstance(results, list):
            latest_comparison = results[0]
            attrs["prior_cycle_avg_daily_cost"] = latest_comparison.get("avgDailyAmount")
            attrs["prior_cycle_service_days"] = latest_comparison.get("DaysInBill")
            attrs["prior_cycle_start_date"] = latest_comparison.get("FromDate")
            attrs["prior_cycle_end_date"] = latest_comparison.get("ToDate")
            attrs["benchmark_last_year_date"] = latest_comparison.get("lastYear")
            
        return attrs


class FPLCurrentCycleAccruedCostSensor(FPLAccountBaseSensor):
    """Tracks running financial cost safely incurred within the active billing cycle period."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Current Cycle Accrued Cost"
        self._attr_unique_id = f"{coordinator.account}_current_cycle_accrued_cost"
        self._attr_native_unit_of_measurement = "USD"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        info = (
            self.coordinator.data.get("live_summary", {})
            .get("accountSummary", {})
            .get("accountSummaryData", {})
            .get("billAndMeterInfo", {})
        )
        val = info.get("asOfDateAmount")
        return float(val) if val is not None else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        info = (
            self.coordinator.data.get("live_summary", {})
            .get("accountSummary", {})
            .get("accountSummaryData", {})
            .get("billAndMeterInfo", {})
        )
        
        attrs = {
            "consumed_kwh_to_date": info.get("asOfDateUsage"),
            "meter_hardware_model": info.get("meterType"),
            "meter_internal_id": info.get("meterNumber"),
            "is_net_metering": info.get("netMeterFlag"),
            "service_establishment_date": info.get("serviceStartDate")
        }

        try:
            usage = float(info.get("asOfDateUsage", 0))
            daily_kwh = float(info.get("dailyAvgKwh", 0))
            if usage > 0 and daily_kwh > 0:
                days_into_cycle = int(round(usage / daily_kwh))
                cycle_start = datetime.now() - timedelta(days=days_into_cycle)
                attrs["cycle_start_date"] = cycle_start.strftime("%Y-%m-%d")
                attrs["days_accumulated_in_cycle"] = days_into_cycle
        except (ValueError, TypeError):
            attrs["cycle_start_date"] = "Unknown"

        return attrs


class FPLProjectedBillSensor(FPLAccountBaseSensor):
    """Tracks the utility predictive algorithm machine forecast total calculation."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Projected Bill"
        self._attr_unique_id = f"{coordinator.account}_projected_bill"
        self._attr_native_unit_of_measurement = "USD"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        info = (
            self.coordinator.data.get("live_summary", {})
            .get("accountSummary", {})
            .get("accountSummaryData", {})
            .get("billAndMeterInfo", {})
        )
        val = info.get("projBillAmount")
        return float(val) if val is not None else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        info = (
            self.coordinator.data.get("live_summary", {})
            .get("accountSummary", {})
            .get("accountSummaryData", {})
            .get("billAndMeterInfo", {})
        )
        return {
            "forecasted_cycle_kwh": info.get("projBillKWH"),
            "projected_base_infrastructure_charge": info.get("projBaseCharge"),
            "next_scheduled_reading_date": info.get("nextReadDate"),
            "days_in_next_billing_cycle": info.get("nextMonthCycleDays")
        }


class FPLRecentBillSensor(FPLAccountBaseSensor):
    """Tracks the total charge of the most recent historical invoice statement."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Recent Bill"
        self._attr_unique_id = f"{coordinator.account}_recent_bill"
        self._attr_native_unit_of_measurement = "USD"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        results = self.coordinator.data.get("history", {}).get("data", {}).get("results", [])
        if not results or not isinstance(results, list):
            return None
        return results[0].get("totalAmount")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        results = self.coordinator.data.get("history", {}).get("data", {}).get("results", [])
        if not results or not isinstance(results, list):
            return {}
            
        latest_invoice = results[0]
        return {
            "invoice_id": latest_invoice.get("invoiceId"),
            "due_date": parse_fpl_date(latest_invoice.get("dueDate")),
            "statement_date": parse_fpl_date(latest_invoice.get("invoiceDate")),
            "billing_cycle_portion": latest_invoice.get("portion"),
            "is_final_bill": latest_invoice.get("finalBill"),
            "currency_code": latest_invoice.get("currency")
        }


class FPLAccountNumberSensor(FPLAccountBaseSensor):
    """Monitors the FPL account identifier."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Account Number"
        self._attr_unique_id = f"{coordinator.account}_account_number"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        summary_block = self.coordinator.data.get("summary", {})
        if not summary_block or not isinstance(summary_block, dict):
            return None
        return summary_block.get("accountNumber")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
            
        details = self.coordinator.data.get("lite", {}).get("data", {}).get("contractAccountDetails", {})
        address = details.get("address", {})
        
        # 🟢 PRIVACY COMPLIANT: Only safe regional properties
        return {
            "billing_city": address.get("city"),
            "billing_state": address.get("region"),
            "billing_zip": address.get("zip"),
        }


class FPLAccountTypeSensor(FPLAccountBaseSensor):
    """Monitors the account type description from lite-info."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Account Type"
        self._attr_unique_id = f"{coordinator.account}_account_type"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        details = self.coordinator.data.get("lite", {}).get("data", {}).get("contractAccountDetails", {})
        return details.get("accountType")


class FPLCustomerNumberSensor(FPLAccountBaseSensor):
    """Monitors the master customer profile identifier number."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Customer Number"
        self._attr_unique_id = f"{coordinator.account}_customer_number"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("summary", {}).get("customerNumber")


class FPLContractIdSensor(FPLAccountBaseSensor):
    """Monitors the unique active contract agreement tracking token ID."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Contract ID"
        self._attr_unique_id = f"{coordinator.account}_contract_id"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("summary", {}).get("contractId")


# =====================================================================
# DEVICE GROUP 2: SMART METER HARDWARE
# =====================================================================

class FPLMeterBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class providing shared physical utility meter device mapping."""
    
    @property
    def device_info(self):
        summary_block = self.coordinator.data.get("summary", {}) if self.coordinator.data else {}
        meter_id = summary_block.get("meterNumber", "unknown_meter")
        return {
            "identifiers": {(DOMAIN, f"smart_meter_{meter_id}")},
            "name": f"FPL Smart Meter ({meter_id})",
            "manufacturer": "Florida Power & Light",
            "model": "Advanced Metering Infrastructure (AMI)",
            "via_device": (DOMAIN, f"account_profile_{self.coordinator.account}"),
        }


class FPLLastCycleConsumptionSensor(FPLMeterBaseSensor):
    """Tracks total kWh energy registration from the last completed monthly statement cycle."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Last Cycle Consumption"
        self._attr_unique_id = f"{coordinator.account}_last_cycle_consumption"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "kWh"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        results = self.coordinator.data.get("monthly", {}).get("results", [])
        if not results or not isinstance(results, list):
            return None
        return results[0].get("billedConsKwh")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        results = self.coordinator.data.get("monthly", {}).get("results", [])
        if not results or not isinstance(results, list):
            return {}
            
        latest_cycle = results[0]
        return {
            "billing_period_start": latest_cycle.get("fromDate"),
            "billing_period_end": latest_cycle.get("toDate"),
            "cycle_cost_invoiced": latest_cycle.get("actualBillAmount"),
            "kwh_variance_vs_previous_year": latest_cycle.get("diffConsKwh"),
            "cost_variance_vs_previous_year": latest_cycle.get("diffConsAmt"),
            "program_indicator_code": latest_cycle.get("programIndicator")
        }


class FPLMeterNumberSensor(FPLMeterBaseSensor):
    """Monitors the physical utility hardware serial number registry entry."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Meter Number"
        self._attr_unique_id = f"{coordinator.account}_meter_number"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("summary", {}).get("meterNumber")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
            
        results = self.coordinator.data.get("installations", {}).get("data", {}).get("results", [])
        lite_address = self.coordinator.data.get("lite", {}).get("data", {}).get("serviceAddress", {})
        
        attrs = {}
        if results and isinstance(results, list):
            record = results[0]
            device = record.get("deviceInfo", {})
            
            attrs.update({
                "meter_model_design": device.get("deviceInfo"),
                "hardware_material_id": device.get("material"),
                "register_group": device.get("registerGroup"),
                "device_location_id": device.get("deviceLocationId"),
                "ami_enabled_flag": device.get("amiMeter"),
                "meter_symbol_type": device.get("meterSymbol"),
                "installation_status": device.get("meterStatus", {}).get("description"),
                "hardware_installed_date": parse_fpl_date(device.get("installationDate")),
                "ami_certified_date": parse_fpl_date(device.get("amiDateCertified")),
                "last_meter_reading_date": parse_fpl_date(record.get("lastMeterReadingDate")),
                "next_meter_reading_date": parse_fpl_date(record.get("nextMeterReadingDate")),
                "move_in_date": parse_fpl_date(record.get("contractDetails", {}).get("moveInDate")),
                "meter_reading_unit": record.get("meterReadingUnitDescription")
            })
            
        # 🟢 PRIVACY COMPLIANT: Only generic location parameters are appended here
        if lite_address and isinstance(lite_address, dict):
            attrs.update({
                "service_city": lite_address.get("city"),
                "service_state": lite_address.get("state"),
                "service_zipcode": lite_address.get("zipcode")
            })
            
        return attrs


class FPLRateCategorySensor(FPLMeterBaseSensor):
    """Monitors the current active grid rate billing plan model description."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Rate Category"
        self._attr_unique_id = f"{coordinator.account}_rate_category"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        results = self.coordinator.data.get("installations", {}).get("data", {}).get("results", [])
        if not results or not isinstance(results, list):
            return None
        return results[0].get("rateCategoryDescription")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        results = self.coordinator.data.get("installations", {}).get("data", {}).get("results", [])
        if not results or not isinstance(results, list):
            return {}
        return {
            "rate_code_key": results[0].get("rateCategory")
        }


class FPLPremiseNumberSensor(FPLMeterBaseSensor):
    """Monitors the physical premise location ID tracking record."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Premise Number"
        self._attr_unique_id = f"{coordinator.account}_premise_number"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("summary", {}).get("premiseNumber")


class FPLAccountClassSensor(FPLMeterBaseSensor):
    """Monitors the account classification class from lite-info."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "FPL Account Class"
        self._attr_unique_id = f"{coordinator.account}_account_class"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        details = self.coordinator.data.get("lite", {}).get("data", {}).get("contractAccountDetails", {})
        return details.get("accountClass")


# =====================================================================
# DEVICE GROUP 3: DISAGGREGATED ENERGY CATEGORIES
# =====================================================================

class FPLCategoryBaseSensor(CoordinatorEntity, SensorEntity):
    """Shared base class to link appliance metrics to a Breakdown Device Group."""

    @property
    def device_info(self):
        summary_block = self.coordinator.data.get("summary", {}) if self.coordinator.data else {}
        meter_id = summary_block.get("meterNumber", "unknown_meter")
        return {
            "identifiers": {(DOMAIN, f"energy_breakdown_{self.coordinator.account}")},
            "name": "FPL Appliance Energy Breakdown",
            "manufacturer": "Florida Power & Light",
            "model": "Disaggregation Analytics System",
            "via_device": (DOMAIN, f"smart_meter_{meter_id}"),
        }


class FPLCategoryUsageSensor(FPLCategoryBaseSensor):
    """Tracks estimated energy consumption (kWh) consumed by a single category."""

    def __init__(self, coordinator, category):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.category = category
        
        clean_name = category.replace("Heater", " Heater").title()
        self._attr_name = f"FPL Category Usage {clean_name}"
        self._attr_unique_id = f"{coordinator.account}_usage_cat_{category}"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "kWh"

    def _get_category_node(self):
        if not self.coordinator.data:
            return None
        periods = self.coordinator.data.get("disagg", {}).get("data", {}).get("billPeriods", [])
        if not periods or not isinstance(periods, list):
            return None
        categories = periods[0].get("categories", [])
        for item in categories:
            if item.get("category") == self.category:
                return item
        return None

    @property
    def native_value(self):
        node = self._get_category_node()
        if node:
            return node.get("kwh")
        return None

    @property
    def extra_state_attributes(self):
        attrs = {}
        if not self.coordinator.data:
            return attrs
            
        periods = self.coordinator.data.get("disagg", {}).get("data", {}).get("billPeriods", [])
        if periods and isinstance(periods, list):
            attrs["billing_period_start"] = periods[0].get("startDate")
            attrs["billing_period_end"] = periods[0].get("endDate")
            attrs["billing_days"] = periods[0].get("billingDays")

        node = self._get_category_node()
        if node:
            attrs["estimated_cost_usd"] = node.get("cost")
            attrs["percentage_of_total_bill"] = node.get("percentage")
            attrs["precise_percentage"] = node.get("percentage2")
        return attrs