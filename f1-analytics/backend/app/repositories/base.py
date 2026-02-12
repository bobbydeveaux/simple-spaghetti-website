"""
Base repository pattern for F1 Analytics.

This module provides a generic base repository with common CRUD operations
that can be extended by specific model repositories.
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any, Union
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.exc import IntegrityError, NoResultFound

from ..database import Base

logger = logging.getLogger(__name__)

# Generic type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing common CRUD operations.

    This class implements the repository pattern for database operations,
    providing a consistent interface for data access across all models.
    """

    def __init__(self, model: Type[ModelType], db_session: Session):
        """
        Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class
            db_session: Database session
        """
        self.model = model
        self.db = db_session

    def get_by_id(self, id: Union[int, str]) -> Optional[ModelType]:
        """
        Retrieve a record by its primary key.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        try:
            return self.db.query(self.model).filter(
                self.model.id == id
            ).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {id}: {e}")
            return None

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Retrieve all records with optional pagination and ordering.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            order_by: Column name to order by
            order_desc: Whether to order in descending order

        Returns:
            List of model instances
        """
        try:
            query = self.db.query(self.model)

            # Apply ordering if specified
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))

            return query.offset(skip).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            return []

    def get_by_fields(self, **filters) -> List[ModelType]:
        """
        Retrieve records by specified field values.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            List of matching model instances

        Example:
            repository.get_by_fields(status="active", role="admin")
        """
        try:
            query = self.db.query(self.model)

            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            return query.all()

        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by fields {filters}: {e}")
            return []

    def get_one_by_fields(self, **filters) -> Optional[ModelType]:
        """
        Retrieve a single record by specified field values.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            Single model instance or None if not found

        Example:
            user = repository.get_one_by_fields(email="user@example.com")
        """
        try:
            query = self.db.query(self.model)

            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            return query.first()

        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by fields {filters}: {e}")
            return None

    def create(self, obj_data: Union[ModelType, Dict[str, Any]]) -> Optional[ModelType]:
        """
        Create a new record.

        Args:
            obj_data: Model instance or dictionary of field values

        Returns:
            Created model instance or None if creation failed

        Example:
            user = repository.create({
                "email": "user@example.com",
                "password_hash": "hashed_password"
            })
        """
        try:
            if isinstance(obj_data, dict):
                obj = self.model(**obj_data)
            else:
                obj = obj_data

            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)

            logger.debug(f"Created {self.model.__name__} with id {getattr(obj, 'id', 'unknown')}")
            return obj

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            return None

    def update(self, id: Union[int, str], updates: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update a record by ID.

        Args:
            id: Primary key of record to update
            updates: Dictionary of field updates

        Returns:
            Updated model instance or None if update failed

        Example:
            user = repository.update(123, {"last_login": datetime.now()})
        """
        try:
            # Add timestamp if model supports it
            if hasattr(self.model, 'updated_at'):
                updates['updated_at'] = datetime.utcnow()

            obj = self.get_by_id(id)
            if not obj:
                logger.warning(f"{self.model.__name__} with id {id} not found for update")
                return None

            for field, value in updates.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)

            self.db.commit()
            self.db.refresh(obj)

            logger.debug(f"Updated {self.model.__name__} with id {id}")
            return obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} with id {id}: {e}")
            return None

    def delete(self, id: Union[int, str]) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Primary key of record to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            obj = self.get_by_id(id)
            if not obj:
                logger.warning(f"{self.model.__name__} with id {id} not found for deletion")
                return False

            self.db.delete(obj)
            self.db.commit()

            logger.debug(f"Deleted {self.model.__name__} with id {id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            return False

    def soft_delete(self, id: Union[int, str]) -> bool:
        """
        Soft delete a record (mark as inactive/deleted).

        This method only works if the model has an 'is_active' or 'deleted' field.

        Args:
            id: Primary key of record to soft delete

        Returns:
            True if soft deletion was successful, False otherwise
        """
        try:
            if hasattr(self.model, 'is_active'):
                return self.update(id, {'is_active': False}) is not None
            elif hasattr(self.model, 'deleted'):
                return self.update(id, {'deleted': True}) is not None
            else:
                logger.warning(f"{self.model.__name__} does not support soft delete")
                return False

        except Exception as e:
            logger.error(f"Error soft deleting {self.model.__name__} with id {id}: {e}")
            return False

    def count(self, **filters) -> int:
        """
        Count records matching the given filters.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            Number of matching records
        """
        try:
            query = self.db.query(func.count(self.model.id))

            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            return query.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model.__name__} with filters {filters}: {e}")
            return 0

    def exists(self, id: Union[int, str]) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Primary key to check

        Returns:
            True if record exists, False otherwise
        """
        try:
            return self.db.query(
                self.db.query(self.model).filter(self.model.id == id).exists()
            ).scalar()

        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {id}: {e}")
            return False

    def bulk_create(self, objects_data: List[Union[ModelType, Dict[str, Any]]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.

        Args:
            objects_data: List of model instances or dictionaries

        Returns:
            List of created model instances
        """
        try:
            objects = []
            for obj_data in objects_data:
                if isinstance(obj_data, dict):
                    obj = self.model(**obj_data)
                else:
                    obj = obj_data
                objects.append(obj)

            self.db.add_all(objects)
            self.db.commit()

            # Refresh all objects to get generated IDs
            for obj in objects:
                self.db.refresh(obj)

            logger.debug(f"Bulk created {len(objects)} {self.model.__name__} records")
            return objects

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error in bulk create of {self.model.__name__}: {e}")
            return []
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in bulk create of {self.model.__name__}: {e}")
            return []

    def bulk_update(self, updates_list: List[Dict[str, Any]], id_field: str = 'id') -> int:
        """
        Update multiple records in a single transaction.

        Args:
            updates_list: List of dictionaries containing id and update fields
            id_field: Name of the ID field (default: 'id')

        Returns:
            Number of records updated

        Example:
            updated_count = repository.bulk_update([
                {"id": 1, "status": "active"},
                {"id": 2, "status": "inactive"}
            ])
        """
        try:
            if not updates_list:
                return 0

            # Add timestamp if model supports it
            if hasattr(self.model, 'updated_at'):
                for update_data in updates_list:
                    update_data['updated_at'] = datetime.utcnow()

            # Perform bulk update using SQLAlchemy Core
            stmt = update(self.model)
            result = self.db.execute(stmt, updates_list)
            self.db.commit()

            updated_count = result.rowcount
            logger.debug(f"Bulk updated {updated_count} {self.model.__name__} records")
            return updated_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in bulk update of {self.model.__name__}: {e}")
            return 0

    def get_page(self, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """
        Get paginated results with metadata.

        Args:
            page: Page number (1-based)
            per_page: Records per page
            **filters: Optional filters

        Returns:
            Dictionary containing items, pagination metadata
        """
        try:
            query = self.db.query(self.model)

            # Apply filters
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            # Get total count
            total = query.count()

            # Calculate pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()

            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page,
                "has_next": page * per_page < total,
                "has_prev": page > 1,
            }

        except Exception as e:
            logger.error(f"Error getting page {page} of {self.model.__name__}: {e}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "pages": 0,
                "has_next": False,
                "has_prev": False,
            }


class AsyncBaseRepository(Generic[ModelType]):
    """
    Async base repository class providing common async CRUD operations.

    This class implements the repository pattern for async database operations.
    """

    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        """
        Initialize async repository with model class and database session.

        Args:
            model: SQLAlchemy model class
            db_session: Async database session
        """
        self.model = model
        self.db = db_session

    async def get_by_id(self, id: Union[int, str]) -> Optional[ModelType]:
        """
        Retrieve a record by its primary key asynchronously.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {id}: {e}")
            return None

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Retrieve all records with optional pagination and ordering asynchronously.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Column name to order by
            order_desc: Whether to order in descending order

        Returns:
            List of model instances
        """
        try:
            stmt = select(self.model)

            # Apply ordering if specified
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    stmt = stmt.order_by(desc(order_column))
                else:
                    stmt = stmt.order_by(asc(order_column))

            stmt = stmt.offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            return []

    async def create(self, obj_data: Union[ModelType, Dict[str, Any]]) -> Optional[ModelType]:
        """
        Create a new record asynchronously.

        Args:
            obj_data: Model instance or dictionary of field values

        Returns:
            Created model instance or None if creation failed
        """
        try:
            if isinstance(obj_data, dict):
                obj = self.model(**obj_data)
            else:
                obj = obj_data

            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)

            logger.debug(f"Created {self.model.__name__} with id {getattr(obj, 'id', 'unknown')}")
            return obj

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            return None

    async def count(self, **filters) -> int:
        """
        Count records matching the given filters asynchronously.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            Number of matching records
        """
        try:
            stmt = select(func.count(self.model.id))

            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model.__name__} with filters {filters}: {e}")
            return 0