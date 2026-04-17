"""Constants for the ecocito integration."""

import logging
from dataclasses import dataclass

DOMAIN = "ecocito"
LOGGER = logging.getLogger(__package__)

# Config Flow / Options Flow

CONF_HISTORY_YEARS = "history_years"
DEFAULT_HISTORY_YEARS = 2

# Service Device

DEVICE_ATTRIBUTION = "Données fournies par Ecocito"
DEVICE_NAME = "Ecocito"
DEVICE_MANUFACTURER = "Ecocito"
DEVICE_MODEL = "Calendrier Ecocito"

# Ecocito - Base

ECOCITO_DOMAIN = "{}.ecocito.com"

# Ecocito - Login

ECOCITO_LOGIN_URI = "/Usager/Profil/Connexion"
ECOCITO_LOGIN_ENDPOINT = f"https://{ECOCITO_DOMAIN}{ECOCITO_LOGIN_URI}"
ECOCITO_LOGIN_USERNAME_KEY = "Identifiant"
ECOCITO_LOGIN_PASSWORD_KEY = "MotDePasse"  # noqa: S105

# Ecocito - Collection types
ECOCITO_DEFAULT_COLLECTION_TYPE = -1

# Ecocito - Collection endpoints
ECOCITO_COLLECTION_PAGE_ENDPOINT = f"https://{ECOCITO_DOMAIN}/Usager/Collecte"
ECOCITO_COLLECTION_ENDPOINT = f"https://{ECOCITO_DOMAIN}/Usager/Collecte/GetCollecte"

# Ecocito - Waste deposit visits
ECOCITO_WASTE_DEPOSIT_ENDPOINT = f"https://{ECOCITO_DOMAIN}/Usager/Apport/GetApport"


# ── Collection type hints ──────────────────────────────────────────────────────
# Maps a regex pattern (matched case-insensitively against the API type name)
# to a (translation_key, icon) hint used to give known types a proper icon and
# localised sensor name.  First match wins.
#
# To add a new type: append a tuple (pattern, translation_key, icon).
# If no pattern matches the API name, the generic "collection" fallback is used
# and the raw API name is injected via the {type} translation placeholder.


@dataclass(frozen=True)
class CollectionTypeHint:
    """Translation key and icon for a known collection type."""

    translation_key: str
    icon: str


COLLECTION_TYPE_HINTS: list[tuple[str, CollectionTypeHint]] = [
    # Household waste / ordures ménagères
    (
        r"ordures?\s+m[eé]nag[eè]res?|\bOM\b",
        CollectionTypeHint(translation_key="garbage", icon="mdi:trash-can"),
    ),
    # Selective sorting / collecte sélective / recyclage
    (
        r"recyclage|tri\s+s[eé]lectif|\bCS\b",
        CollectionTypeHint(translation_key="recycling", icon="mdi:recycle"),
    ),
    # Green waste / déchets verts
    (
        r"d[eé]chets?\s+verts?|\bDV\b",
        CollectionTypeHint(translation_key="green_waste", icon="mdi:leaf"),
    ),
    # Badge / access card deposits
    (
        r"badge",
        CollectionTypeHint(translation_key="badge", icon="mdi:card-account-details"),
    ),
]

# Fallback used when no hint pattern matches the API type name.
COLLECTION_TYPE_DEFAULT_HINT = CollectionTypeHint(
    translation_key="collection", icon="mdi:trash-can"
)
