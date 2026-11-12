"""
Módulo de Repositório para Categorias.

Centraliza todas as operações diretas de banco de dados (SQLAlchemy)
relacionadas à tabela 'categories'.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.category import Category
from app.repositories.base import BaseRepository

class CategoryRepository(BaseRepository[Category]):
    """Repositório de Categorias."""
    def __init__(self):
        super().__init__(Category)

    def get_by_name(self, db: Session, name: str) -> Optional[Category]:
        """Busca uma categoria pelo nome exato."""
        return db.query(self.model).filter(self.model.name == name).first()


category_repository = CategoryRepository()