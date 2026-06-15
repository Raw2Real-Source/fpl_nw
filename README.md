# FPL Northwest Region (Gulf) for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home__Assistant-Community__Integration-blue.svg?style=for-the-badge&logo=home-assistant)]()

A comprehensive Home Assistant custom integration for Florida Power & Light (FPL) customers residing in the Northwest/Gulf region. This integration interfaces directly with the private FPL SSP API layers to pull highly granular, multi-device tracking metrics, financial projections, and disaggregated utility breakdown configurations.

Unlike traditional utility integrations that dump everything into a monolithic entity heap, this integration organizes your account into **three distinct architectural device containers** matching Home Assistant Core hardware guidelines.

---

## 🛠️ Installation

### Method 1: HACS Custom Repository (Recommended)
1. Ensure **HACS** is installed and functioning in your Home Assistant instance.
2. Navigate to the **HACS** dashboard.
3. Click the **three dots** in the top-right corner and select **Custom repositories**.
4. Paste the repository URL: `https://github.com/Raw2Real-Source/fpl_nw`
5. Select **Integration** from the category dropdown menu.
6. Click **Add**.
7. Locate the **FPL Northwest Region** integration inside HACS and click **Download**.
8. **Restart Home Assistant** to load the custom component layers.

### Method 2: Manual Installation
1. Download the source code archive from the latest repository release.
2. Extract the archive and copy the folder `custom_components/fpl_gulf` into your local Home Assistant dynamic configuration directory (e.g., `/config/custom_components/fpl_gulf`).
3. Ensure the folder permissions match your Home Assistant installation.
4. **Restart Home Assistant**.

---

## ⚙️ Configuration Setup

1. In the Home Assistant UI, navigate to **Settings** ➡️ **Devices & Services**.
2. Click the **+ Add Integration** button in the bottom-right corner.
3. Search for **FPL Northwest Region** (or **FPL NW**) and select it.
4. Enter your credentials into the dynamic configuration wizard:
   - **FPL Portal Username** (Email address used for web authentication)
   - **FPL Portal Password**
   - **FPL Account Number** (Your standard utility billing account identifier)
5. Click **Submit**.

The integration will perform a secure session initialization using Amazon Cognito token pools, discover your physical hardware parameters, and instantly spawn your tracking environment.

---

## 📐 Device & Entity Architecture

This custom integration implements a strict device registry abstraction. Data properties map into three separate logical physical profiles:

### 📱 Device 1: FPL Account Profile
Houses live billing cycle analytics, predictive invoice algorithms, financial operational burn rates, and ongoing operational metrics.

| Entity Name | Sensor Class / Unit | Key Extra State Attributes |
| :--- | :--- | :--- |
| **FPL Account Number** | String / Text | `billing_city`, `billing_state`, `billing_zip` |
| **FPL Account Type** | String / State | *None* |
| **FPL Customer Number** | String / ID | *None* |
| **FPL Contract ID** | String / ID | *None* |
| **FPL Estimated Daily Avg Consumption** | Energy / `kWh` | *None* |
| **FPL Avg Daily Cost** | Financial / `USD` | `prior_cycle_avg_daily_cost`, `prior_cycle_service_days`, `prior_cycle_start_date`, `prior_cycle_end_date` |
| **FPL Current Cycle Accrued Cost** | Financial / `USD` | `consumed_kwh_to_date`, `meter_hardware_model`, `meter_internal_id`, `is_net_metering`, `cycle_start_date`, `days_accumulated_in_cycle` |
| **FPL Projected Bill** | Financial / `USD` | `forecasted_cycle_kwh`, `projected_base_infrastructure_charge`, `next_scheduled_reading_date`, `days_in_next_billing_cycle` |
| **FPL Recent Bill** | Financial / `USD` | `invoice_id`, `due_date`, `statement_date`, `billing_cycle_portion`, `is_final_bill` |

---

### 📟 Device 2: FPL Smart Meter Hardware
Represents your physical Advanced Metering Infrastructure (AMI) grid deployment tracking hardware. It maps properties tied directly to physical data registers and historical billing blocks.

| Entity Name | Sensor Class / Unit | Key Extra State Attributes |
| :--- | :--- | :--- |
| **FPL Meter Number** | String / Serial | `meter_model_design`, `hardware_material_id`, `register_group`, `device_location_id`, `ami_enabled_flag`, `installation_status`, `hardware_installed_date`, `last_meter_reading_date`, `next_meter_reading_date`, `service_city`, `service_state`, `service_zipcode` |
| **FPL Premise Number** | String / ID | *None* |
| **FPL Account Class** | String / Category | *None* |
| **FPL Rate Category** | String / Model | `rate_code_key` |
| **FPL Last Cycle Consumption** | Energy / `kWh` | `billing_period_start`, `billing_period_end`, `cycle_cost_invoiced`, `kwh_variance_vs_previous_year`, `cost_variance_vs_previous_year` |

---

### 📊 Device 3: FPL Appliance Energy Breakdown
Exposes the disaggregation mathematical backend calculations parsed via FPL’s utility data analytics engine. These sensors populate dynamically to track consumption estimations over your active billing month.

All entities within this container use the standard `SensorDeviceClass.ENERGY` class (`kWh`) and inherit shared scheduling metadata within their attributes: `billing_period_start`, `billing_period_end`, and `billing_days`.

| Entity Name | Target Category | Category-Specific Attributes |
| :--- | :--- | :--- |
| **FPL Category Usage Cooling** | Air Conditioning / HVAC | `estimated_cost_usd`, `percentage_of_total_bill` |
| **FPL Category Usage Water Heater** | Hot Water Systems | `estimated_cost_usd`, `percentage_of_total_bill` |
| **FPL Category Usage Laundry** | Washers & Dryers | `estimated_cost_usd`, `percentage_of_total_bill` |
| **FPL Category Usage Refrigeration** | Fridges & Freezers | `estimated_cost_usd`, `percentage_of_total_bill` |
| **FPL Category Usage Entertainment** | Media & Home Theatre | `estimated_cost_usd`, `percentage_of_total_bill` |
| **FPL Category Usage Lighting** | Household Lighting | `estimated_cost_usd`, `percentage_of_total_bill` |
| **FPL Category Usage Always On** | Standby & Vampire Loads | `estimated_cost_usd`, `percentage_of_total_bill` |

---

## 🔒 Privacy & Security Blueprint
This integration has been explicitly audited against the strict **Home Assistant Core Privacy Design Guidelines**. 
- **Zero Hardcoded Secrets:** No default credentials or tokens are saved inside the package codebase. 
- **Dynamic Session Vaulting:** Access keys exist entirely in Home Assistant’s isolated, runtime config-entry data-store.
- **PII Scrubbing Enforced:** High-risk Personally Identifiable Information (such as full legal customer names, street names, precise home numbers, telephone numbers, and email accounts) is actively stripped from the code logic. Troubleshooting logs and diagnostics are safe to share publicly.

## 🛠️ Troubleshooting & Debugging
If you encounter data collection hitches, you can force verbose system logs. Add the following logging block directly into your local `configuration.yaml` file:

```yaml
logger:
  default: info
  logs:
    custom_components.fpl_gulf: debug