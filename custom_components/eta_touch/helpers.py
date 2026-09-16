"""Helpers shared by the ETA touch modules."""

from __future__ import annotations

import hashlib

from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id
from pyetatouch import VarAddress


async def varset_name(hass: HomeAssistant, scope: str) -> str:
    """Return a deterministic variable-set name unique to this HA installation."""
    seed = f"{await instance_id.async_get(hass)}:{scope}"
    return f"ha{hashlib.sha256(seed.encode()).hexdigest()[:10]}"


def variable_unique_id(entry_id: str, address: VarAddress) -> str:
    """Return the entity unique ID for a variable address."""
    return f"{entry_id}_{address.node}_{address.fub}_{address.fkt}_{address.io}_{address.var}"
