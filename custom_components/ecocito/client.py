"""Client."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup as bs  # noqa: N813

from .const import (
    ECOCITO_COLLECTION_ENDPOINT,
    ECOCITO_COLLECTION_PAGE_ENDPOINT,
    ECOCITO_DEFAULT_COLLECTION_TYPE,
    ECOCITO_LOGIN_ENDPOINT,
    ECOCITO_LOGIN_PASSWORD_KEY,
    ECOCITO_LOGIN_URI,
    ECOCITO_LOGIN_USERNAME_KEY,
    ECOCITO_WASTE_DEPOSIT_ENDPOINT,
    LOGGER,
)
from .errors import CannotConnectError, EcocitoError, InvalidAuthenticationError

_MAX_RETRIES = 3
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass(kw_only=True, slots=True)
class CollectionType:
    """Represents a collection type (e.g., garbage, recycling)."""

    id: str
    name: str


@dataclass(kw_only=True, slots=True)
class EcocitoEvent:
    """Represent a Ecocito event."""

    date: datetime


@dataclass(kw_only=True, slots=True)
class CollectionEvent(EcocitoEvent):
    """Represents a garbage or recycling collection event."""

    date: datetime
    location: str
    type: str
    quantity: float


@dataclass(kw_only=True, slots=True)
class WasteDepotVisit(EcocitoEvent):
    """Represents a voluntary waste depot visit."""


class EcocitoClient:
    """Ecocito client."""

    def __init__(self, domain: str, username: str, password: str) -> None:
        """Init the Ecocito client."""
        self._domain = domain.split(".", maxsplit=1)[0]
        self._username = username
        self._password = password
        self._cookies = aiohttp.CookieJar()
        self._auth_lock = asyncio.Lock()

    async def authenticate(self) -> None:
        """Authenticate to Ecocito."""
        async with (
            self._auth_lock,
            aiohttp.ClientSession(
                cookie_jar=self._cookies, timeout=_HTTP_TIMEOUT
            ) as session,
        ):
            try:
                async with session.post(
                    ECOCITO_LOGIN_ENDPOINT.format(self._domain),
                    data={
                        ECOCITO_LOGIN_USERNAME_KEY: self._username,
                        ECOCITO_LOGIN_PASSWORD_KEY: self._password,
                    },
                    raise_for_status=True,
                ) as response:
                    if not self._cookies:
                        raise InvalidAuthenticationError
                    html = bs(await response.text(), "html.parser")
                    error = html.find_all("div", {"class": "validation-summary-errors"})
                    if error:
                        raise InvalidAuthenticationError(error[0].find("li").text)
                    LOGGER.debug("Connected as %s", self._username)
            except aiohttp.ClientResponseError as e:
                if e.status in (401, 403):
                    msg = f"Authentication error: {e}"
                    raise InvalidAuthenticationError(msg) from e
                msg = f"Unexpected server response during authentication: {e}"
                raise EcocitoError(msg) from e
            except aiohttp.ClientError as e:
                msg = f"Cannot connect to Ecocito: {e}"
                raise CannotConnectError(msg) from e

    async def get_collection_types(self) -> list[CollectionType]:
        """Return the list of collection types from the collection page."""
        async with aiohttp.ClientSession(
            cookie_jar=self._cookies, timeout=_HTTP_TIMEOUT
        ) as session:
            for attempt in range(_MAX_RETRIES):
                try:
                    async with session.get(
                        ECOCITO_COLLECTION_PAGE_ENDPOINT.format(self._domain),
                        raise_for_status=True,
                    ) as response:
                        content = await response.text()
                except aiohttp.ClientResponseError as e:
                    if e.status in (401, 403):
                        msg = (
                            f"Authentication error while fetching collection types: {e}"
                        )
                        raise InvalidAuthenticationError(msg) from e
                    msg = (
                        f"Unexpected server response while fetching"
                        f" collection types: {e}"
                    )
                    raise EcocitoError(msg) from e
                except aiohttp.ClientError as e:
                    msg = f"Unable to get collection types: {e}"
                    raise CannotConnectError(msg) from e

                html = bs(content, "html.parser")

                # Session may have expired; check for login form.
                form = html.find("form", action=re.compile(f"{ECOCITO_LOGIN_URI}"))
                if form:
                    LOGGER.debug("The session has expired, re-authenticating.")
                    await self.authenticate()
                    if attempt == _MAX_RETRIES - 1:
                        msg = "Max retries reached while fetching collection types"
                        raise EcocitoError(msg) from None
                    continue

                # The collection type selector uses Filtres_IdMatiere as its
                # identifier (name: Filtres.IdMatiere).
                select = html.find("select", {"id": "Filtres_IdMatiere"}) or html.find(
                    "select", {"name": "Filtres.IdMatiere"}
                )
                if not select:
                    # Log all select elements found to help diagnose the issue.
                    all_selects = html.find_all("select")
                    LOGGER.debug(
                        "IdMatiere select not found. All <select> elements: %s",
                        [(s.get("id"), s.get("name")) for s in all_selects],
                    )
                    msg = "Cannot find collection type selector on the Ecocito page"
                    raise EcocitoError(msg)

                types = [
                    CollectionType(id=opt["value"], name=opt.get_text(strip=True))
                    for opt in select.find_all("option")
                    if opt.get("value", "")
                    not in (
                        "",
                        str(ECOCITO_DEFAULT_COLLECTION_TYPE),
                    )
                ]
                if not types:
                    msg = "No collection types found on the Ecocito page"
                    raise EcocitoError(msg)

                LOGGER.debug("Discovered %d collection type(s)", len(types))
                return types
        msg = "Max retries reached while fetching collection types"
        raise EcocitoError(msg)

    async def get_collection_events(
        self, event_type: str, year: int
    ) -> list[CollectionEvent]:
        """Return the list of the collection events for a type and a year."""
        async with aiohttp.ClientSession(
            cookie_jar=self._cookies, timeout=_HTTP_TIMEOUT
        ) as session:
            for attempt in range(_MAX_RETRIES):
                try:
                    async with session.get(
                        ECOCITO_COLLECTION_ENDPOINT.format(self._domain),
                        params={
                            "charger": "true",
                            "skip": "0",
                            "take": "1000",
                            "requireTotalCount": "true",
                            "idMatiere": str(event_type),
                            "dateDebut": f"{year}-01-01T00:00:00.000Z",
                            "dateFin": f"{year}-12-31T23:59:59.999Z",
                        },
                        raise_for_status=True,
                    ) as response:
                        content = await response.text()
                except aiohttp.ClientResponseError as e:
                    if e.status in (401, 403):
                        msg = (
                            f"Authentication error while fetching"
                            f" collection events: {e}"
                        )
                        raise InvalidAuthenticationError(msg) from e
                    msg = (
                        f"Unexpected server response while fetching"
                        f" collection events: {e}"
                    )
                    raise EcocitoError(msg) from e
                except aiohttp.ClientError as e:
                    msg = f"Unable to get collection events: {e}"
                    raise CannotConnectError(msg) from e

                try:
                    payload = json.loads(content)
                except json.JSONDecodeError:
                    # Non-JSON response likely means the session has expired
                    # and the server returned an HTML login page.
                    await self._handle_expired_session(content)
                    if attempt == _MAX_RETRIES - 1:
                        msg = "Max retries reached while fetching collection events"
                        raise EcocitoError(msg) from None
                    continue

                try:
                    return [
                        CollectionEvent(
                            type=event_type,
                            date=datetime.fromisoformat(row["DATE_DONNEE"]),
                            location=row["LIBELLE_ADRESSE"],
                            quantity=row["QUANTITE_NETTE"],
                        )
                        for row in payload.get("data", [])
                    ]
                except (KeyError, ValueError) as e:
                    msg = f"Unexpected server response from Ecocito: {e}"
                    raise EcocitoError(msg) from e
        msg = "Max retries reached while fetching collection events"
        raise EcocitoError(msg)

    async def get_addresses(
        self, year: int, collection_types: list[CollectionType]
    ) -> list[str]:
        """Return sorted unique addresses from all collection types."""
        locations: set[str] = set()
        for ctype in collection_types:
            events = await self.get_collection_events(ctype.id, year)
            locations.update(event.location for event in events if event.location)
        return sorted(locations)

    async def get_waste_depot_visits(self, year: int) -> list[WasteDepotVisit]:
        """Return the list of the waste depot visits for a year."""
        async with aiohttp.ClientSession(
            cookie_jar=self._cookies, timeout=_HTTP_TIMEOUT
        ) as session:
            for attempt in range(_MAX_RETRIES):
                try:
                    async with session.get(
                        ECOCITO_WASTE_DEPOSIT_ENDPOINT.format(self._domain),
                        params={
                            "charger": "true",
                            "skip": "0",
                            "take": "1000",
                            "requireTotalCount": "true",
                            "idMatiere": str(ECOCITO_DEFAULT_COLLECTION_TYPE),
                            "dateDebut": f"{year}-01-01T00:00:00.000Z",
                            "dateFin": f"{year}-12-31T23:59:59.999Z",
                        },
                        raise_for_status=True,
                    ) as response:
                        content = await response.text()
                except aiohttp.ClientResponseError as e:
                    if e.status in (401, 403):
                        msg = (
                            f"Authentication error while fetching"
                            f" waste depot visits: {e}"
                        )
                        raise InvalidAuthenticationError(msg) from e
                    msg = (
                        f"Unexpected server response while fetching"
                        f" waste depot visits: {e}"
                    )
                    raise EcocitoError(msg) from e
                except aiohttp.ClientError as e:
                    msg = f"Unable to get waste depot visits: {e}"
                    raise CannotConnectError(msg) from e

                try:
                    payload = json.loads(content)
                except json.JSONDecodeError:
                    await self._handle_expired_session(content)
                    if attempt == _MAX_RETRIES - 1:
                        msg = "Max retries reached while fetching waste depot visits"
                        raise EcocitoError(msg) from None
                    continue

                try:
                    return [
                        WasteDepotVisit(date=datetime.fromisoformat(row["DATE_DONNEE"]))
                        for row in payload.get("data", [])
                    ]
                except (KeyError, ValueError) as e:
                    msg = f"Unexpected server response from Ecocito: {e}"
                    raise EcocitoError(msg) from e
        msg = "Max retries reached while fetching waste depot visits"
        raise EcocitoError(msg)

    async def _handle_expired_session(self, content: str) -> None:
        """Re-authenticate if the session has expired, raise otherwise."""
        html = bs(content, "html.parser")
        form = html.find("form", action=re.compile(f"{ECOCITO_LOGIN_URI}"))
        if form:
            LOGGER.debug("The session has expired, re-authenticating.")
            await self.authenticate()
        else:
            msg = "Unexpected response from Ecocito server"
            raise EcocitoError(msg)
