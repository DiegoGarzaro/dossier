"""Custom field business logic: typed validation, ordering, pinning (Epic C)."""

import math
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import FieldType
from app.core.errors import InvalidInputError, NotFoundError
from app.models import PersonField
from app.repositories.field_repo import FieldRepository
from app.repositories.people_repo import PeopleRepository
from app.schemas.field import FieldCreate, FieldUpdate, ReorderRequest


def validate_value(field_type: FieldType, value: str | None) -> None:
    """Validate a field value against its declared type (FR-14).

    Args:
        field_type (FieldType): The field's type.
        value (str | None): The candidate value; empty values are always allowed.

    Returns:
        None

    Raises:
        InvalidInputError: If the value does not conform to the type.
    """
    if value is None or value == "":
        return
    if field_type is FieldType.number:
        try:
            parsed = float(value)
        except ValueError:
            raise InvalidInputError("Value must be a number") from None
        if not math.isfinite(parsed):
            raise InvalidInputError("Value must be a finite number")
    elif field_type is FieldType.date:
        try:
            date.fromisoformat(value)
        except ValueError:
            raise InvalidInputError("Value must be an ISO date (YYYY-MM-DD)") from None
    elif field_type is FieldType.boolean and value not in ("true", "false"):
        raise InvalidInputError("Value must be 'true' or 'false'")


class FieldService:
    """Orchestrates field operations on a person's record."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._fields = FieldRepository(session)
        self._people = PeopleRepository(session)

    async def add(self, person_id: int, data: FieldCreate) -> PersonField:
        """Add a field to a person at the end of the list (FR-11).

        Args:
            person_id (int): The owning person id.
            data (FieldCreate): Label, value, type, and pinned flag.

        Returns:
            PersonField: The created field.

        Raises:
            NotFoundError: If the person does not exist.
            InvalidInputError: If the value fails type validation.
        """
        if await self._people.get(person_id) is None:
            raise NotFoundError("Person not found")
        validate_value(data.type, data.value)
        return await self._fields.add(
            PersonField(
                person_id=person_id,
                label=data.label,
                value=data.value,
                type=data.type,
                is_pinned=data.is_pinned,
                position=await self._fields.next_position(person_id),
            )
        )

    async def update(self, field_id: int, data: FieldUpdate) -> PersonField:
        """Edit a field's label, value, type, or pinned flag (FR-15/16).

        Args:
            field_id (int): The field id.
            data (FieldUpdate): The partial update.

        Returns:
            PersonField: The updated field.

        Raises:
            NotFoundError: If the field does not exist.
            InvalidInputError: If the resulting value fails type validation.
        """
        field = await self._fields.get(field_id)
        if field is None:
            raise NotFoundError("Field not found")
        updates = data.model_dump(exclude_unset=True)
        new_type = updates.get("type", field.type)
        new_value = updates.get("value", field.value)
        validate_value(new_type, new_value)
        for key, value in updates.items():
            setattr(field, key, value)
        return field

    async def remove(self, field_id: int) -> None:
        """Remove a field (FR-15).

        Args:
            field_id (int): The field id.

        Returns:
            None

        Raises:
            NotFoundError: If the field does not exist.
        """
        field = await self._fields.get(field_id)
        if field is None:
            raise NotFoundError("Field not found")
        await self._fields.delete(field)

    async def reorder(self, person_id: int, data: ReorderRequest) -> list[PersonField]:
        """Apply new sort positions to a person's fields (FR-15).

        Args:
            person_id (int): The owning person id.
            data (ReorderRequest): The (id, position) pairs to apply.

        Returns:
            list[PersonField]: The person's fields in their new order.

        Raises:
            NotFoundError: If the person does not exist.
            InvalidInputError: If any field does not belong to the person.
        """
        if await self._people.get(person_id) is None:
            raise NotFoundError("Person not found")
        fields = {field.id: field for field in await self._fields.list_for_person(person_id)}
        for item in data.items:
            field = fields.get(item.id)
            if field is None:
                raise InvalidInputError(f"Field {item.id} does not belong to this person")
            field.position = item.position
        return sorted(fields.values(), key=lambda field: field.position)
