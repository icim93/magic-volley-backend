"""
Schemi Pydantic: definiscono la forma dei dati che entrano/escono dalle API.
Convenzione: <Entita>Base (campi comuni) -> <Entita>Create (input creazione)
-> <Entita>Update (input update, tutto opzionale) -> <Entita>Out (output, con id).
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

from app.models import UserRole, RegistrationStatus, MatchStatus


# ---------- User / Auth ----------

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.staff


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Team ----------

class TeamBase(BaseModel):
    name: str
    category: str
    season: str
    description: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool = True


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    season: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None


class TeamOut(TeamBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Player ----------

class PlayerBase(BaseModel):
    team_id: int
    first_name: str
    last_name: str
    jersey_number: Optional[int] = None
    role: Optional[str] = None
    birth_date: Optional[date] = None
    photo_url: Optional[str] = None
    is_active: bool = True


class PlayerCreate(PlayerBase):
    pass


class PlayerUpdate(BaseModel):
    team_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    jersey_number: Optional[int] = None
    role: Optional[str] = None
    birth_date: Optional[date] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None


class PlayerOut(PlayerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TeamWithPlayersOut(TeamOut):
    players: List[PlayerOut] = []


# ---------- Staff ----------

class StaffBase(BaseModel):
    first_name: str
    last_name: str
    role: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class StaffCreate(StaffBase):
    team_ids: List[int] = []


class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    team_ids: Optional[List[int]] = None


class StaffOut(StaffBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teams: List[TeamOut] = []


# ---------- Match ----------

class MatchBase(BaseModel):
    home_team_id: int
    home_team_name: str
    away_team_name: str
    is_home: bool = True
    match_date: datetime
    location: Optional[str] = None
    status: MatchStatus = MatchStatus.scheduled
    home_sets: Optional[int] = None
    away_sets: Optional[int] = None
    set_scores: Optional[str] = None
    notes: Optional[str] = None


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    home_team_id: Optional[int] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    is_home: Optional[bool] = None
    match_date: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[MatchStatus] = None
    home_sets: Optional[int] = None
    away_sets: Optional[int] = None
    set_scores: Optional[str] = None
    notes: Optional[str] = None


class MatchOut(MatchBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- News ----------

class NewsBase(BaseModel):
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    cover_image_url: Optional[str] = None
    published: bool = False


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[str] = None
    published: Optional[bool] = None


class NewsOut(NewsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    published_at: Optional[datetime] = None
    created_at: datetime


# ---------- Registration ----------

class RegistrationCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    parent_name: Optional[str] = None
    email: EmailStr
    phone: str
    requested_team_category: Optional[str] = None
    medical_certificate_url: Optional[str] = None
    id_document_url: Optional[str] = None


class RegistrationUpdate(BaseModel):
    status: Optional[RegistrationStatus] = None
    notes: Optional[str] = None


class RegistrationOut(RegistrationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: RegistrationStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------- Sponsor ----------

class SponsorBase(BaseModel):
    name: str
    logo_url: str
    website_url: Optional[str] = None
    tier: str = "standard"
    display_order: int = 0
    is_active: bool = True


class SponsorCreate(SponsorBase):
    pass


class SponsorUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    tier: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class SponsorOut(SponsorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
