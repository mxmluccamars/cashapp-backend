"""
Módulo de Repositório para Contas Recorrentes (Recurring Bills).

Centraliza todas as operações diretas de banco de dados (SQLAlchemy)
relacionadas à tabela 'recurring_bills'.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.recurring_bill import RecurringBill


class RecurringBillRepository(BaseRepository[RecurringBill]):
    """Repositório de Contas Recorrentes (Recurring Bills)."""
    
    def __init__(self):
        super().__init__(RecurringBill)

    def get_by_name(self, db: Session, name: str) -> Optional[RecurringBill]:
        """Busca uma conta recorrente pelo nome exato."""
        return db.query(self.model).filter(self.model.name == name).first()

    def get_active_bills(self, db: Session, skip: int = 0, limit: int = 100) -> List[RecurringBill]:
        """Retorna apenas as assinaturas que estão ativas no momento."""
        return (
            db.query(self.model)
            .filter(self.model.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )


# Instância única exportada para uso no Service
recurring_bill_repository = RecurringBillRepository()