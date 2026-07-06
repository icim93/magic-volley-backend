from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin

router = APIRouter(prefix="/api/gallery", tags=["Fotogallery"])


@router.get("", response_model=List[schemas.GalleryPhotoOut])
def list_photos(
    category: Optional[str] = None,
    include_hidden: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(models.GalleryPhoto)
    if not include_hidden:
        query = query.filter(models.GalleryPhoto.is_active == True)  # noqa: E712
    if category:
        query = query.filter(models.GalleryPhoto.category == category)
    return query.order_by(
        models.GalleryPhoto.display_order,
        models.GalleryPhoto.created_at.desc(),
    ).all()


@router.post("", response_model=schemas.GalleryPhotoOut, status_code=201)
def create_photo(
    photo_in: schemas.GalleryPhotoCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    photo = models.GalleryPhoto(**photo_in.model_dump())
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.patch("/{photo_id}", response_model=schemas.GalleryPhotoOut)
def update_photo(
    photo_id: int,
    photo_in: schemas.GalleryPhotoUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    photo = db.query(models.GalleryPhoto).filter(models.GalleryPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto non trovata")
    for field, value in photo_in.model_dump(exclude_unset=True).items():
        setattr(photo, field, value)
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/{photo_id}", status_code=204)
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    photo = db.query(models.GalleryPhoto).filter(models.GalleryPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto non trovata")
    db.delete(photo)
    db.commit()
