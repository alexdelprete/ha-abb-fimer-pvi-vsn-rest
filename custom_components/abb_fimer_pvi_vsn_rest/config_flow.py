"""Config flow."""
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

class ABBFimerPVIVSNRestConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        if user_input:
            return self.async_create_entry(title=user_input["host"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("username", default="admin"): str,
                vol.Required("password"): str,
            })
        )
