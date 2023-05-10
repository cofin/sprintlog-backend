# ruff: noqa: B008
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Controller, delete, get, post, put
from litestar.di import Provide
from litestar.params import Dependency
from litestar.status_codes import HTTP_200_OK

from app.domain.backlogs import Backlog as Model
from app.domain.backlogs import ReadDTO, Repository, Service, WriteDTO

if TYPE_CHECKING:
    from uuid import UUID

    from litestar.contrib.repository.abc import FilterTypes
    from sqlalchemy.ext.asyncio import AsyncSession


__all__ = [
    "ApiController",
]

DETAIL_ROUTE = "/{backlog_id:uuid}"


def provides_service(db_session: AsyncSession) -> Service:
    """Constructs repository and service objects for the request."""
    return Service(Repository(session=db_session))


class ApiController(Controller):
    dto = WriteDTO
    return_dto = ReadDTO
    path = "/backlogs"
    dependencies = {"service": Provide(provides_service)}
    tags = ["Backlogs"]

    @get()
    async def filter(
        self, service: Service, filters: list[FilterTypes] = Dependency(skip_validation=True)
    ) -> list[Model]:
        """Get a list of Models."""
        return await service.list(*filters)

    @post()
    async def create(self, data: Model, service: Service) -> Model:
        """Create an `Model`."""
        return await service.create(data)

    @get(DETAIL_ROUTE)
    async def retrieve(self, service: Service, col_id: UUID) -> Model:
        """Get Model by ID."""
        return await service.get(col_id)

    @put(DETAIL_ROUTE)
    async def update(self, data: Model, service: Service, col_id: UUID) -> Model:
        """Update an Model."""
        return await service.update(col_id, data)

    @delete(DETAIL_ROUTE, status_code=HTTP_200_OK)
    async def delete(self, service: Service, col_id: UUID) -> Model:
        """Delete Author by ID."""
        return await service.delete(col_id)
