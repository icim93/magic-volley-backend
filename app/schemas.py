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
    email: str  # username di accesso staff/admin: non deve necessariamente essere un'email valida
    full_name: str
    role: UserRole = UserRole.staff


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str


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
    height_cm: Optional[int] = None
    bio: Optional[str] = None
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
    height_cm: Optional[int] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None


class PlayerOut(PlayerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PlayerDetailOut(PlayerOut):
    """Scheda pubblica della giocatrice, con la squadra di appartenenza."""
    team: TeamOut


class TeamWithPlayersOut(TeamOut):
    players: List[PlayerOut] = []


# ---------- Staff ----------

class StaffBase(BaseModel):
    first_name: str
    last_name: str
    role: str
    area: str = "collaboratori"  # dirigenza | staff_tecnico | area_sanitaria | collaboratori
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
    area: Optional[str] = None
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
    birth_place: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    fiscal_code: Optional[str] = None
    parent_name: Optional[str] = None
    parent_birth_place: Optional[str] = None
    parent_address: Optional[str] = None
    parent_city: Optional[str] = None
    parent_postal_code: Optional[str] = None
    parent_fiscal_code: Optional[str] = None
    email: EmailStr
    phone: str
    requested_team_category: Optional[str] = None
    medical_certificate_url: Optional[str] = None
    id_document_url: Optional[str] = None
    documents_accepted: bool = False  # step 2 del form pubblico: non persistito così com'è, vedi documents_accepted_at


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
    player_id: Optional[int] = None
    guardian_id: Optional[int] = None
    documents_accepted_at: Optional[datetime] = None


class RegistrationApprove(BaseModel):
    """Dati per approvare un'iscrizione: crea la giocatrice e collega/crea il genitore."""
    team_id: int
    jersey_number: Optional[int] = None
    guardian_first_name: str
    guardian_last_name: str
    guardian_email: EmailStr


class RegistrationApproveOut(BaseModel):
    player: PlayerOut
    guardian_email: str
    email_sent: bool
    activation_link: str  # utile come fallback se l'email non è configurata/fallita


# ---------- Guardian (area riservata genitori) ----------

class GuardianPlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    jersey_number: Optional[int] = None
    role: Optional[str] = None
    team: TeamOut


class GuardianMeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    players: List[GuardianPlayerOut] = []


class GuardianAdminOut(BaseModel):
    """Vista genitore per il pannello (sezione Genitori): include is_active,
    a differenza di GuardianMeOut usata dal genitore stesso."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    players: List[GuardianPlayerOut] = []


class GuardianActivationLinkOut(BaseModel):
    activation_link: str
    email_sent: bool


class GuardianActivate(BaseModel):
    token: str
    password: str


class GuardianChangePassword(BaseModel):
    current_password: str
    new_password: str


class GuardianLoginOut(Token):
    pass


# ---------- Gallery ----------

class GalleryPhotoBase(BaseModel):
    image_url: str
    caption: Optional[str] = None
    category: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class GalleryPhotoCreate(GalleryPhotoBase):
    pass


class GalleryPhotoUpdate(BaseModel):
    image_url: Optional[str] = None
    caption: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class GalleryPhotoOut(GalleryPhotoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


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


# ---------- Document (pannello, non pubblico) ----------

class DocumentBase(BaseModel):
    title: str
    category: Optional[str] = None
    file_url: str
    file_name: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentOut(DocumentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    uploaded_by: Optional[UserOut] = None
