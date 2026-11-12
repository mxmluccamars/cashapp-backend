"""
Módulo de Repositório para Objetivos.

Centraliza todas as operações diretas de banco de dados (SQLAlchemy)
relacionadas à tabela 'goals'.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.goal import Goal
from app.repositories.base import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    """Repositório de Objetivos."""
    def __init__(self):
        super().__init__(Goal)

    def get_by_name(self, db: Session, name: str) -> Optional[Goal]:
        """Busca um objetivo pelo nome exato."""
        return db.query(self.model).filter(self.model.name == name).first()

goal_repository = GoalRepository()