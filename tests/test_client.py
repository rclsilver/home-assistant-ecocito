"""Tests for EcocitoClient."""

from __future__ import annotations

import re

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from custom_components.ecocito.client import (
    CollectionEvent,
    EcocitoClient,
    WasteDepotVisit,
)
from custom_components.ecocito.const import (
    ECOCITO_COLLECTION_ENDPOINT,
    ECOCITO_GARBAGE_COLLECTION_TYPE,
    ECOCITO_LOGIN_ENDPOINT,
    ECOCITO_WASTE_DEPOSIT_ENDPOINT,
)
from custom_components.ecocito.errors import (
    CannotConnectError,
    EcocitoError,
    InvalidAuthenticationError,
)

_TEST_SUBDOMAIN = "test"
_LOGIN_URL = ECOCITO_LOGIN_ENDPOINT.format(_TEST_SUBDOMAIN)
_COLLECTION_URL = ECOCITO_COLLECTION_ENDPOINT.format(_TEST_SUBDOMAIN)
_WASTE_DEPOT_URL = ECOCITO_WASTE_DEPOSIT_ENDPOINT.format(_TEST_SUBDOMAIN)

# Regex patterns to match URLs regardless of query params
_COLLECTION_RE = re.compile(re.escape(_COLLECTION_URL))
_WASTE_DEPOT_RE = re.compile(re.escape(_WASTE_DEPOT_URL))

_VALID_COLLECTION_JSON = {
    "data": [
        {
            "DATE_DONNEE": "2024-03-15T00:00:00",
            "LIBELLE_ADRESSE": "12 rue de la Paix",
            "QUANTITE_NETTE": 120.0,
        }
    ]
}
_VALID_WASTE_DEPOT_JSON = {
    "data": [
        {"DATE_DONNEE": "2024-04-10T00:00:00"},
    ]
}

_HTML_SUCCESS = "<html><body>Bienvenue</body></html>"
_HTML_LOGIN_FORM = (
    '<html><body><form action="/Usager/Profil/Connexion"></form></body></html>'
)
_HTML_INVALID_CREDENTIALS = (
    "<html><body>"
    '<div class="validation-summary-errors">'
    "<ul><li>Identifiants invalides</li></ul>"
    "</div></body></html>"
)


def _make_client() -> EcocitoClient:
    """Return a fresh EcocitoClient pointed at the test subdomain."""
    return EcocitoClient("test.ecocito.com", "user@test.com", "password123")


def _populate_cookies(client: EcocitoClient) -> None:
    """Pre-populate the cookie jar so the post-auth non-empty check passes."""
    client._cookies.update_cookies(
        {"session": "fake_session_token"},
        URL(f"https://{_TEST_SUBDOMAIN}.ecocito.com/"),
    )


async def test_authenticate_success() -> None:
    """POST returns 200 + HTML without errors → no exception raised."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.post(_LOGIN_URL, status=200, body=_HTML_SUCCESS.encode())
        await client.authenticate()


async def test_authenticate_invalid_credentials() -> None:
    """POST returns HTML with validation-summary-errors → InvalidAuthenticationError."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.post(_LOGIN_URL, status=200, body=_HTML_INVALID_CREDENTIALS.encode())
        with pytest.raises(InvalidAuthenticationError):
            await client.authenticate()


async def test_authenticate_network_error() -> None:
    """POST raises aiohttp.ClientError → CannotConnectError."""
    client = _make_client()
    with aioresponses() as m:
        m.post(_LOGIN_URL, exception=aiohttp.ClientConnectionError("network failure"))
        with pytest.raises(CannotConnectError):
            await client.authenticate()


async def test_get_collection_events_success() -> None:
    """GET returns valid JSON → list of CollectionEvent."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.get(_COLLECTION_RE, payload=_VALID_COLLECTION_JSON)
        events = await client.get_collection_events(
            ECOCITO_GARBAGE_COLLECTION_TYPE, 2024
        )

    assert len(events) == 1
    assert isinstance(events[0], CollectionEvent)
    assert events[0].location == "12 rue de la Paix"
    assert events[0].quantity == 120.0


async def test_get_collection_events_session_expired() -> None:
    """First GET returns login HTML → re-auth → second GET returns JSON."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.get(_COLLECTION_RE, status=200, body=_HTML_LOGIN_FORM.encode())
        m.post(_LOGIN_URL, status=200, body=_HTML_SUCCESS.encode())
        m.get(_COLLECTION_RE, payload=_VALID_COLLECTION_JSON)
        events = await client.get_collection_events(
            ECOCITO_GARBAGE_COLLECTION_TYPE, 2024
        )

    assert len(events) == 1
    assert events[0].location == "12 rue de la Paix"


async def test_get_collection_events_max_retries() -> None:
    """GET always returns login HTML → after 3 attempts → EcocitoError."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        for _ in range(3):
            m.get(_COLLECTION_RE, status=200, body=_HTML_LOGIN_FORM.encode())
            m.post(_LOGIN_URL, status=200, body=_HTML_SUCCESS.encode())
        with pytest.raises(EcocitoError):
            await client.get_collection_events(ECOCITO_GARBAGE_COLLECTION_TYPE, 2024)


async def test_get_collection_events_network_error() -> None:
    """GET raises aiohttp.ClientError → CannotConnectError."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.get(
            _COLLECTION_RE,
            exception=aiohttp.ClientConnectionError("network failure"),
        )
        with pytest.raises(CannotConnectError):
            await client.get_collection_events(ECOCITO_GARBAGE_COLLECTION_TYPE, 2024)


async def test_get_waste_depot_visits_success() -> None:
    """GET returns valid JSON → list of WasteDepotVisit."""
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.get(_WASTE_DEPOT_RE, payload=_VALID_WASTE_DEPOT_JSON)
        visits = await client.get_waste_depot_visits(2024)

    assert len(visits) == 1
    assert isinstance(visits[0], WasteDepotVisit)


async def test_get_addresses() -> None:
    """Garbage + recycling with overlapping locations → sorted unique addresses."""
    garbage_json = {
        "data": [
            {
                "DATE_DONNEE": "2024-03-15T00:00:00",
                "LIBELLE_ADRESSE": "12 rue de la Paix",
                "QUANTITE_NETTE": 1.0,
            },
            {
                "DATE_DONNEE": "2024-03-22T00:00:00",
                "LIBELLE_ADRESSE": "20 avenue des Fleurs",
                "QUANTITE_NETTE": 1.0,
            },
        ]
    }
    recycling_json = {
        "data": [
            {
                "DATE_DONNEE": "2024-03-16T00:00:00",
                "LIBELLE_ADRESSE": "12 rue de la Paix",
                "QUANTITE_NETTE": 1.0,
            },
        ]
    }
    client = _make_client()
    _populate_cookies(client)
    with aioresponses() as m:
        m.get(_COLLECTION_RE, payload=garbage_json)
        m.get(_COLLECTION_RE, payload=recycling_json)
        addresses = await client.get_addresses(2024)

    assert addresses == ["12 rue de la Paix", "20 avenue des Fleurs"]
