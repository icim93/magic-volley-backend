from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin, get_current_user
from app.core.push import send_push_to_all_guardians

router = APIRouter(prefix="/api/news", tags=["News"])


def _revision_out(db: Session, revision: models.NewsRevision) -> schemas.NewsRevisionOut:
    current = None
    if revision.news_id:
        news_item = db.query(models.News).filter(models.News.id == revision.news_id).first()
        if news_item:
            current = schemas.NewsOut.model_validate(news_item)
    submitter = revision.submitted_by or db.query(models.User).filter(models.User.id == revision.submitted_by_id).first()
    return schemas.NewsRevisionOut(
        id=revision.id,
        news_id=revision.news_id,
        title=revision.title,
        slug=revision.slug,
        summary=revision.summary,
        content=revision.content,
        cover_image_url=revision.cover_image_url,
        published=revision.published,
        status=revision.status,
        submitted_by_name=submitter.full_name if submitter else "—",
        current=current,
        reject_reason=revision.reject_reason,
        created_at=revision.created_at,
        reviewed_at=revision.reviewed_at,
    )


@router.get("", response_model=List[schemas.NewsOut])
def list_news(published_only: bool = True, db: Session = Depends(get_db)):
    """Elenco news, più recenti prima. Il sito pubblico chiama con published_only=true."""
    query = db.query(models.News)
    if published_only:
        query = query.filter(models.News.published == True)  # noqa: E712
    return query.order_by(models.News.created_at.desc()).all()


# --- Proposte in attesa di approvazione (staff) --------------------------
# Queste route devono restare PRIMA di GET /{slug}, altrimenti "revisions"
# verrebbe interpretato come uno slug e non raggiungerebbe mai questi handler.

@router.get("/revisions", response_model=List[schemas.NewsRevisionOut])
def list_pending_revisions(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    """Proposte in attesa di revisione — solo admin/superadmin."""
    revisions = (
        db.query(models.NewsRevision)
        .filter(models.NewsRevision.status == models.RevisionStatus.pending)
        .order_by(models.NewsRevision.created_at.desc())
        .all()
    )
    return [_revision_out(db, r) for r in revisions]


@router.get("/revisions/mine", response_model=List[schemas.NewsRevisionOut])
def list_my_revisions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Le proposte inviate dall'utente corrente, in ogni stato — per lo staff, per vedere l'esito."""
    revisions = (
        db.query(models.NewsRevision)
        .filter(models.NewsRevision.submitted_by_id == current_user.id)
        .order_by(models.NewsRevision.created_at.desc())
        .all()
    )
    return [_revision_out(db, r) for r in revisions]


@router.post("/revisions", response_model=schemas.NewsRevisionOut, status_code=201)
def submit_revision(
    data: schemas.NewsRevisionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Propone un articolo nuovo (news_id assente) o una modifica a uno esistente
    (news_id valorizzato). Non tocca mai la tabella News: resta in coda finché
    un admin/superadmin non approva o rifiuta.
    """
    if data.news_id:
        target = db.query(models.News).filter(models.News.id == data.news_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Articolo non trovato")

    revision = models.NewsRevision(
        news_id=data.news_id,
        title=data.title,
        slug=data.slug,
        summary=data.summary,
        content=data.content,
        cover_image_url=data.cover_image_url,
        published=data.published,
        submitted_by_id=current_user.id,
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return _revision_out(db, revision)


@router.post("/revisions/{revision_id}/approve", response_model=schemas.NewsOut)
def approve_revision(
    revision_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Applica la proposta: crea l'articolo se era nuovo, altrimenti aggiorna quello esistente."""
    revision = db.query(models.NewsRevision).filter(models.NewsRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Proposta non trovata")
    if revision.status != models.RevisionStatus.pending:
        raise HTTPException(status_code=400, detail="Questa proposta è già stata revisionata")

    fields = {
        "title": revision.title,
        "slug": revision.slug,
        "summary": revision.summary,
        "content": revision.content,
        "cover_image_url": revision.cover_image_url,
        "published": revision.published,
    }

    if revision.news_id:
        item = db.query(models.News).filter(models.News.id == revision.news_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="L'articolo collegato non esiste più")
        newly_published = fields["published"] and not item.published_at
        if newly_published:
            item.published_at = datetime.utcnow()
        for field, value in fields.items():
            setattr(item, field, value)
    else:
        existing = db.query(models.News).filter(models.News.slug == fields["slug"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Slug già in uso: chiedi allo staff di proporre uno slug diverso prima di approvare")
        newly_published = fields["published"]
        if newly_published:
            fields["published_at"] = datetime.utcnow()
        item = models.News(**fields, author_id=revision.submitted_by_id)
        db.add(item)

    revision.status = models.RevisionStatus.approved
    revision.reviewed_by_id = current_user.id
    revision.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    if newly_published:
        send_push_to_all_guardians(db, title="Nuova news", body=item.title, url=f"/news/{item.slug}", category="news")

    return item


@router.post("/revisions/{revision_id}/reject")
def reject_revision(
    revision_id: int,
    data: schemas.NewsRevisionReject,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    revision = db.query(models.NewsRevision).filter(models.NewsRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Proposta non trovata")
    if revision.status != models.RevisionStatus.pending:
        raise HTTPException(status_code=400, detail="Questa proposta è già stata revisionata")

    revision.status = models.RevisionStatus.rejected
    revision.reject_reason = data.reason
    revision.reviewed_by_id = current_user.id
    revision.reviewed_at = datetime.utcnow()
    db.commit()
    return {"message": "Proposta rifiutata."}


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
    current_user: models.User = Depends(require_admin),
):
    """Scrittura diretta, senza approvazione — riservata ad admin/superadmin.
    Lo staff usa POST /api/news/revisions per proporre."""
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
    if item.published:
        send_push_to_all_guardians(db, title="Nuova news", body=item.title, url=f"/news/{item.slug}", category="news")
    return item


@router.patch("/{news_id}", response_model=schemas.NewsOut)
def update_news(
    news_id: int,
    news_in: schemas.NewsUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """Scrittura diretta, senza approvazione — riservata ad admin/superadmin."""
    item = db.query(models.News).filter(models.News.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Articolo non trovato")

    data = news_in.model_dump(exclude_unset=True)
    newly_published = data.get("published") and not item.published_at
    if newly_published:
        item.published_at = datetime.utcnow()
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    if newly_published:
        send_push_to_all_guardians(db, title="Nuova news", body=item.title, url=f"/news/{item.slug}", category="news")
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
