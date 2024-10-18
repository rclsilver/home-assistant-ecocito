"""Constants for the ecocito integration."""

import logging

DOMAIN = "ecocito"
LOGGER = logging.getLogger(__package__)

# Config Flow

# Service Device

DEVICE_ATTRIBUTION = "Données fournies par Ecocito"
DEVICE_NAME = "Ecocito"
DEVICE_MANUFACTURER = "Ecocito"
DEVICE_MODEL = "Calendrier Ecocito"

# Ecocito - Base

ECOCITO_DOMAIN = "{}.ecocito.com"

# Ecocito - Login

ECOCITO_LOGIN_ENDPOINT = f"https://{ECOCITO_DOMAIN}/Usager/Profil/Connexion"
ECOCITO_LOGIN_USERNAME_KEY = "Identifiant"
ECOCITO_LOGIN_PASSWORD_KEY = "MotDePasse"  # noqa: S105

# Ecocito - Collection types
ECOCITO_DEFAULT_COLLECTION_TYPE = -1
ECOCITO_GARBAGE_COLLECTION_TYPE = 15
ECOCITO_RECYCLING_COLLECTION_TYPE = 16

# Ecocito - Collection endpoint
ECOCITO_COLLECTION_ENDPOINT = f"https://{ECOCITO_DOMAIN}/Usager/Collecte/GetCollecte"

# Ecocito - Waste deposit visits
ECOCITO_WASTE_DEPOSIT_ENDPOINT = f"https://{ECOCITO_DOMAIN}/Usager/Apport/GetApport"
