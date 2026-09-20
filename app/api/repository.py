from pathlib import Path

from fastapi import APIRouter

from app.services.analyzer import RepositoryAnalyzer
from app.services.repository import RepositoryService


router = APIRouter(prefix="/repository", tags=["repository"])


@router.get("/analyze")
def analyze_repository():
    repository = RepositoryService(root_path=Path.cwd())
    analyzer = RepositoryAnalyzer(repository)

    return analyzer.analyze()