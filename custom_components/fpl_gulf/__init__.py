import logging
import asyncio
from datetime import datetime, timedelta
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, 
    COGNITO_URL, 
    COGNITO_CLIENT_ID, 
    URL_REM_ACCOUNT_SUMMARY,
    URL_ACCOUNT_LITE_INFO,
    URL_BILLING_HISTORY,
    URL_METER_INSTALLATIONS,
    URL_MONTHLY_USAGE,
    URL_USAGE_COMPARISON,
    URL_DISAGGREGATION,
    URL_LIVE_ACCOUNT_SUMMARY,
    CONF_USERNAME,
    CONF_PASSWORD
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up FPL Gulf from a live config entry."""
    session = async_get_clientsession(hass)
    coordinator = FPLGulfDataUpdateCoordinator(hass, session, entry.data)
    
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class FPLGulfDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching fields from multiple sequential/concurrent endpoints."""

    def __init__(self, hass, session, config):
        self.session = session
        self.username = config.get(CONF_USERNAME)
        self.password = config.get(CONF_PASSWORD)
        self.account = config.get("account_number")
        
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=1))

    async def _async_fetch_endpoint(self, url, headers, method="GET", json_payload=None):
        """Helper to safely fetch or post to a single utility endpoint."""
        try:
            if method == "POST":
                async with self.session.post(url, headers=headers, json=json_payload) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
                    _LOGGER.warning("POST to %s failed with status: %s", url, response.status)
                    return None
            else:
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
                    _LOGGER.warning("GET from %s failed with status: %s", url, response.status)
                    return None
        except Exception as e:
            _LOGGER.error("Network fault on %s: %s", url, e)
            return None

    async def _async_update_data(self):
        """Fetch active metrics from all configured endpoints sequentially and concurrently."""
        cognito_headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
        }

        auth_payload = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": COGNITO_CLIENT_ID,
            "AuthParameters": {
                "USERNAME": str(self.username), 
                "PASSWORD": str(self.password)
            }
        }

        try:
            async with async_timeout.timeout(30):
                # STEP 1: Cognito Authentication Handshake
                async with self.session.post(COGNITO_URL, json=auth_payload, headers=cognito_headers) as auth_resp:
                    if auth_resp.status != 200:
                        err_text = await auth_resp.text()
                        raise UpdateFailed(f"Auth Failed: {err_text}")
                    
                    auth_data = await auth_resp.json(content_type=None)
                    access_token = auth_data["AuthenticationResult"]["AccessToken"]
                    id_token = auth_data["AuthenticationResult"]["IdToken"]

                headers = {
                    "accept": "application/json, text/plain, */*",
                    "authorization": f"Bearer {id_token}",
                    "accesstoken": access_token,
                    "jwttoken": id_token,
                    "x-param-channel": "web",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }

                # STEP 2: Fetch base account summary first to get contract and premise IDs
                summary_url = URL_REM_ACCOUNT_SUMMARY.format(account=self.account)
                summary_data = await self._async_fetch_endpoint(summary_url, headers)
                if not summary_data or not isinstance(summary_data, dict):
                    raise UpdateFailed("Failed to retrieve core account summary mapping data.")

                # Cleaned default fallbacks to protect personal identifiers
                contract_id = summary_data.get("contractId")
                premise_id = summary_data.get("premiseNumber")

                if not contract_id or not premise_id:
                    raise UpdateFailed("Account metadata mapping attributes are missing or unavailable.")

                # Dynamically compile standard window dates targeting the past month
                now = datetime.now()
                from_date = (now - timedelta(days=35)).strftime("%Y-%m-%d")
                to_date = now.strftime("%Y-%m-%d")

                disagg_body = {
                    "accountNumber": str(self.account),
                    "contractId": str(contract_id),
                    "premiseId": str(premise_id),
                    "fromDate": from_date,
                    "toDate": to_date
                }

                # STEP 3: Concurrently pull all remaining auxiliary data
                lite_url = URL_ACCOUNT_LITE_INFO.format(account=self.account)
                history_url = URL_BILLING_HISTORY.format(account=self.account)
                installations_url = URL_METER_INSTALLATIONS.format(account=self.account)
                monthly_url = URL_MONTHLY_USAGE.format(account=self.account, contract_id=contract_id)
                comparison_url = URL_USAGE_COMPARISON.format(account=self.account, contract_id=contract_id)
                disagg_url = URL_DISAGGREGATION.format(account=self.account)
                live_summary_url = URL_LIVE_ACCOUNT_SUMMARY.format(account=self.account)

                lite_task = self._async_fetch_endpoint(lite_url, headers)
                history_task = self._async_fetch_endpoint(history_url, headers)
                installations_task = self._async_fetch_endpoint(installations_url, headers)
                monthly_task = self._async_fetch_endpoint(monthly_url, headers)
                comparison_task = self._async_fetch_endpoint(comparison_url, headers)
                disagg_task = self._async_fetch_endpoint(disagg_url, headers, method="POST", json_payload=disagg_body)
                live_summary_task = self._async_fetch_endpoint(live_summary_url, headers)

                (lite_data, history_data, installations_data, monthly_data, 
                 comparison_data, disagg_data, live_summary_data) = await asyncio.gather(
                    lite_task, history_task, installations_task, monthly_task, 
                    comparison_task, disagg_task, live_summary_task
                )

                return {
                    "summary": summary_data,
                    "lite": lite_data if isinstance(lite_data, dict) else {},
                    "history": history_data if isinstance(history_data, dict) else {},
                    "installations": installations_data if isinstance(installations_data, dict) else {},
                    "monthly": monthly_data if isinstance(monthly_data, dict) else {},
                    "comparison": comparison_data if isinstance(comparison_data, dict) else {},
                    "disagg": disagg_data if isinstance(disagg_data, dict) else {},
                    "live_summary": live_summary_data if isinstance(live_summary_data, dict) else {}
                }

        except Exception as e:
            raise UpdateFailed(f"Network handling error inside coordinator: {e}")