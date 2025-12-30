from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class OnboardingData(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    username: Optional[str] = None
    securityQuestion: Optional[str] = None
    securityAnswer: Optional[str] = None
    primaryRole: Optional[str] = None
    professionalRole: Optional[str] = None
    teamSize: Optional[str] = None
    discoverySource: Optional[str] = None
    interests: Optional[List[str]] = None
