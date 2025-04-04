"""Client."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup as bs  # noqa: N813

from .const import (
    ECOCITO_COLLECTION_ENDPOINT,
    ECOCITO_COLLECTION_TYPE_ENDPOINT,
    ECOCITO_DEFAULT_COLLECTION_TYPE,
    ECOCITO_ERROR_AUTHENTICATION,
    ECOCITO_ERROR_FETCHING,
    ECOCITO_ERROR_UNHANDLED,
    ECOCITO_LOGIN_ENDPOINT,
    ECOCITO_LOGIN_PASSWORD_KEY,
    ECOCITO_LOGIN_URI,
    ECOCITO_LOGIN_USERNAME_KEY,
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
                raise EcocitoError(ECOCITO_ERROR_AUTHENTICATION.format(exc=e)) from e

    async def get_collection_types(self) -> dict[int, str]:
        """Return the mapping of collection type ID with their label."""
        async with aiohttp.ClientSession(cookie_jar=self._cookies) as session:
            try:
                async with session.get(
                    ECOCITO_COLLECTION_TYPE_ENDPOINT.format(self._domain),
                    raise_for_status=True,
                ) as response:
                    content = await response.text()
                    html = bs(content, "html.parser")
                    try:
                        select = html.find("select", {"id": "Filtres_IdMatiere"})
                        return {
                            int(item.attrs["value"]): item.text
                            for item in select.find_all("option")
                            if "value" in item.attrs
                        }
                    except Exception as e:  # noqa: BLE001
                        await self._handle_error(content, e)
            except aiohttp.ClientError as e:
                raise EcocitoError(
                    ECOCITO_ERROR_FETCHING.format(exc=e, type="collection types")
                ) from e

    async def get_collection_events(
        self, year: int
    ) -> dict[str, dict[str, CollectionEvent]]:
        """Return the list of the collection events for a type and a year."""
        async with aiohttp.ClientSession(cookie_jar=self._cookies) as session:
            try:
                while True:
                    async with session.get(
                        ECOCITO_COLLECTION_ENDPOINT.format(self._domain),
                        params={
                            "charger": "true",
                            "skip": "0",
                            "take": "1000",
                            "requireTotalCount": "true",
                            "idMatiere": str(-1),
                            "dateDebut": f"{year - 1}-01-01T00:00:00.000Z",
                            "dateFin": f"{year}-12-31T23:59:59.999Z",
                        },
                        raise_for_status=True,
                    ) as response:
                        content = await response.text()

                        try:
                            result = {}
                            for row in json.loads(content).get("data", []):
                                date = datetime.fromisoformat(row["DATE_DONNEE"])
                                y = "current" if date.year == year else "last"
                                matter = row["ID_MATIERE"]
                                if y not in result:
                                    result[y] = {}
                                if matter not in result[y]:
                                    result[y][matter] = []
                                result[y][matter].append(
                                    CollectionEvent(
                                        type=matter,
                                        date=date,
                                        location=row["LIBELLE_ADRESSE"],
                                        quantity=row["QUANTITE_NETTE"],
                                    )
                                )
                            return result
                        except Exception as e:  # noqa: BLE001
                            await self._handle_error(content, e)

            except aiohttp.ClientError as e:
                raise EcocitoError(
                    ECOCITO_ERROR_FETCHING.format(exc=e, type="collection events")
                ) from e

    async def get_waste_depot_visits(self, year: int) -> list[WasteDepotVisit]:
        """Return the list of the waste depot visits for a year."""
        async with aiohttp.ClientSession(cookie_jar=self._cookies) as session:
            try:
                while True:
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
                        except Exception as e:  # noqa: BLE001
                            await self._handle_error(content, e)

            except aiohttp.ClientError as e:
                raise EcocitoError(
                    ECOCITO_ERROR_FETCHING.format(exc=e, type="waste deposit events")
                ) from e

    async def _handle_error(self, content: str, e: Exception) -> None:
        """Handle request errors by checking for login form and re-auth if necessary."""
        html = bs(content, "html.parser")
        form = html.find("form", action=re.compile(f"{ECOCITO_LOGIN_URI}"))

        if form:
            LOGGER.debug("The session has expired, try to login again.")
            await self.authenticate()
        else:
            raise EcocitoError(ECOCITO_ERROR_UNHANDLED) from e
