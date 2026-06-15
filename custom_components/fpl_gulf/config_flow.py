import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD

class FPLGulfConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FPL NW."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step via the user interface."""
        errors = {}

        if user_input is not None:
            # Dynamically pass user-submitted text fields into the secure storage entry
            return self.async_create_entry(
                title=f"FPL NW ({user_input['account_number']})", 
                data={
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    "account_number": user_input["account_number"]
                }
            )

        # Force dynamic form rendering so secrets remain safely input-driven
        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required("account_number"): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema,
            errors=errors
        )