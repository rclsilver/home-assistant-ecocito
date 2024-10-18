"""Client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup as bs  # noqa: N813

from .const import (
    ECOCITO_COLLECTION_ENDPOINT,
    ECOCITO_DEFAULT_COLLECTION_TYPE,
    ECOCITO_GARBAGE_COLLECTION_TYPE,
    ECOCITO_LOGIN_ENDPOINT,
    ECOCITO_LOGIN_PASSWORD_KEY,
    ECOCITO_LOGIN_USERNAME_KEY,
    ECOCITO_RECYCLING_COLLECTION_TYPE,
    ECOCITO_WASTE_DEPOSIT_ENDPOINT,
    LOGGER,
)
from .errors import EcocitoError, InvalidAuthenticationError


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
        self._domain = domain.split(".")[0]
        self._username = username
        self._password = password
        self._cookies = aiohttp.CookieJar()

    async def authenticate(self) -> None:
        """Authenticate to Ecocito."""
        async with aiohttp.ClientSession(cookie_jar=self._cookies) as session:
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
            except aiohttp.ClientError as e:
                raise EcocitoError(f"Authentication error: {e}") from e

    async def get_collection_events(
        self, event_type: str, year: int
    ) -> list[CollectionEvent]:
        """Return the list of the collection events for a type and a year."""
        async with aiohttp.ClientSession(cookie_jar=self._cookies) as session:
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

                    try:
                        return [
                            CollectionEvent(
                                type=event_type,
                                date=datetime.fromisoformat(row["DATE_DONNEE"]),
                                location=row["LIBELLE_ADRESSE"],
                                quantity=row["QUANTITE_NETTE"],
                            )
                            for row in json.loads(content).get("data", [])
                        ]
                    except json.decoder.JSONDecodeError:
                        html = bs(content, "html.parser")
                        error = html.find_all("div", {"class": "error"})
                        if error:
                            raise EcocitoError(error[0].text)  # noqa: B904
                        raise

            except aiohttp.ClientError as e:
                raise EcocitoError(f"Unable to get collection events: {e}") from e

    async def get_garbage_collections(self, year: int) -> list[CollectionEvent]:
        """Return the list of the garbage collections for a year."""
        return await self.get_collection_events(ECOCITO_GARBAGE_COLLECTION_TYPE, year)

    async def get_recycling_collections(self, year: int) -> list[CollectionEvent]:
        """Return the list of the recycling collections for a year."""
        return await self.get_collection_events(ECOCITO_RECYCLING_COLLECTION_TYPE, year)

    async def get_waste_depot_visits(self, year: int) -> list[WasteDepotVisit]:
        """Return the list of the waste depot visits for a year."""
        async with aiohttp.ClientSession(cookie_jar=self._cookies) as session:
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

                    try:
                        return [
                            WasteDepotVisit(
                                date=datetime.fromisoformat(row["DATE_DONNEE"])
                            )
                            for row in json.loads(content).get("data", [])
                        ]
                    except json.decoder.JSONDecodeError:
                        html = bs(content, "html.parser")
                        error = html.find_all("div", {"class": "error"})
                        if error:
                            raise EcocitoError(error[0].text)  # noqa: B904
                        raise

            except aiohttp.ClientError as e:
                raise EcocitoError(f"Unable to get waste deposit visits: {e}") from e
