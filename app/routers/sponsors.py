from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin

router = APIRouter(prefix="/api/sponsors", tags=["Sponsor"])


@router.get("", response_model=List[schemas.SponsorOut])
def list_sponsors(active_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(models.Sponsor)
    if active_only:
        query = query.filter(models.Sponsor.is_active == True)  # noqa: E712
    return query.order_by(models.Sponsor.display_order.asc()).all()


@router.post("", response_model=schemas.SponsorOut, status_code=201)
def create_sponsor(
    sponsor_in: schemas.SponsorCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    sponsor = models.Sponsor(**sponsor_in.model_dump())
    db.add(sponsor)
    db.commit()
    db.refresh(sponsor)
    return sponsor


@router.patch("/{sponsor_id}", response_model=schemas.SponsorOut)
def update_sponsor(
    sponsor_id: int,
    sponsor_in: schemas.SponsorUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    sponsor = db.query(models.Sponsor).filter(models.Sponsor.id == sponsor_id).first()
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor non trovato")
    for field, value in sponsor_in.model_dump(exclude_unset=True).items():
        setattr(sponsor, field, value)
    db.commit()
    db.refresh(sponsor)
    return sponsor


@router.delete("/{sponsor_id}", status_code=204)
def delete_sponsor(
    sponsor_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    sponsor = db.query(models.Sponsor).filter(models.Sponsor.id == sponsor_id).first()
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor non trovato")
    db.delete(sponsor)
    db.commit()
