from fastapi import APIRouter, Depends
from app.core.security import verify_token
from app.api.v1.endpoints import auth, categories, transactions, contexts, locations, goals, payment_methods, recurring_bills

api_router = APIRouter()

# Rota pública (para validar o PIN e gerar o token)
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])

protected = [Depends(verify_token)]


api_router.include_router(categories.router, prefix="/categories", tags=["Categorias"], dependencies=protected)
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transações"], dependencies=protected)
api_router.include_router(contexts.router, prefix="/contexts", tags=["Contextos"], dependencies=protected)
api_router.include_router(locations.router, prefix="/locations", tags=["Locais"], dependencies=protected)
api_router.include_router(goals.router, prefix="/goals", tags=["Objetivos"], dependencies=protected)
api_router.include_router(payment_methods.router, prefix="/payment_methods", tags=["Métodos de Pagamento"], dependencies=protected)
api_router.include_router(recurring_bills.router, prefix="/recurring_bills", tags=["Contas Recorrentes"], dependencies=protected)