"""
Repositório base para repositórios de modelos.
"""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base) # type: ignore


class BaseRepository(Generic[ModelType]):
    """Fornece os métodos básicos reaproveitáveis para todos os repositórios."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get_by_id(self, db: Session, id: str) -> Optional[ModelType]:
        """Busca um registro específico pelo ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retorna uma listagem paginada dos registros"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in_data: dict) -> ModelType:
        """Cria um novo registro"""
        if hasattr(obj_in_data, "model_'dump"):
            obj_in_data = obj_in_data.model_dump()
        elif isinstance(obj_in_data, dict):
            obj_in_data = obj_in_data
        else:
            obj_in_data = dict(obj_in_data)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: ModelType, updates: dict) -> ModelType:
        """Atualiza um registro existente"""
        for field, value in updates.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, db_obj: ModelType) -> ModelType:
        """Remove um registro existente"""
        db.delete(db_obj)
        db.commit()
        return db_obj