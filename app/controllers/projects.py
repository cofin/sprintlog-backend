# pyright: reportGeneralTypeIssues=false

from typing import TYPE_CHECKING
from uuid import UUID

from litestar import (
    Controller,
    delete,
    get,  # pylint: disable=unused-import
    post,
    put,
)
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.projects import Project as Model
from app.domain.projects import ReadDTO, Repository, Service, WriteDTO

if TYPE_CHECKING:
    from litestar.contrib.repository.abc import FilterTypes

__all__ = ["ApiController", "provides_service"]


def provides_service(db_session: AsyncSession) -> Service:
    """Constructs repository and service objects for the request."""
    return Service(Repository(session=db_session))


class ApiController(Controller):
    DETAIL_ROUTE = "/{col_id:uuid}"
    dto = WriteDTO
    return_dto = ReadDTO
    details = "/{col_id:uuid}"
    path = "/projects"
    dependencies = {"service": Provide(provides_service)}
    tags = ["Projects"]

    @get()
    async def filter(self, service: Service, filters: list["FilterTypes"]) -> list[Model]:
        """Get a list of templates."""
        return await service.list(*filters)

    @post()
    async def create(self, data: Model, service: Service) -> Model:
        """Create an `Model`."""
        return await service.create(data)

    @get(DETAIL_ROUTE)
    async def retrieve(self, service: Service, template_id: UUID) -> Model:
        """Get Model by ID."""
        return await service.get(template_id)

    @put(DETAIL_ROUTE)
    async def update(self, data: Model, service: Service, template_id: UUID) -> Model:
        """Update an template."""
        return await service.update(template_id, data)

    @delete(DETAIL_ROUTE, status_code=HTTP_200_OK)
    async def delete(self, service: Service, template_id: UUID) -> Model:
        """Delete Model by ID."""
        return await service.delete(template_id)