from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin, get_current_user

router = APIRouter(prefix="/api/news", tags=["News"])


@router.get("", response_model=List[schemas.NewsOut])
def list_news(published_only: bool = True, db: Session = Depends(get_db)):
    """Elenco news, più recenti prima. Il sito pubblico chiama con published_only=true."""
    query = db.query(models.News)
    if published_only:
        query = query.filter(models.News.published == True)  # noqa: E712
    return query.order_by(models.News.created_at.desc()).all()


@router.get("/{slug}", response_model=schemas.NewsOut)
def get_news_by_slug(slug: str, db: Session = Depends(get_db)):
    item = db.query(models.News).filter(models.News.slug == slug).first()
    if not item:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    return item


@router.post("", response_model=schemas.NewsOut, status_code=201)
def create_news(
    news_in: schemas.NewsCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing = db.query(models.News).filter(models.News.slug == news_in.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug già in uso, sceglierne un altro")

    data = news_in.model_dump()
    if data.get("published"):
        data["published_at"] = datetime.utcnow()
    item = models.News(**data, author_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{news_id}", response_model=schemas.NewsOut)
def update_news(
    news_id: int,
    news_in: schemas.NewsUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    item = db.query(models.News).filter(models.News.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Articolo non trovato")

    data = news_in.model_dump(exclude_unset=True)
    if data.get("published") and not item.published_at:
        item.published_at = datetime.utcnow()
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{news_id}", status_code=204)
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    item = db.query(models.News).filter(models.News.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    db.delete(item)
    db.commit()
