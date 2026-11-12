"""
mÓdulo de Repositório para Contextos.

Centraliza todas as operações diretas de banco de dados (SQLAlchemy)
relacionadas à tabela 'contexts'.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.context import Context
from app.repositories.base import BaseRepository

class ContextRepository(BaseRepository[Context]):
    """Repositório de Contextos."""
    def __init__(self):
        super().__init__(Context)

    def get_by_name(self, db: Session, name: str) -> Optional[Context]:
        """Busca um contexto pelo nome exato."""
        return db.query(self.model).filter(self.model.name == name).first()


context_repository = ContextRepository()