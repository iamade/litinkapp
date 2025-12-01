from datetime import date
from pydantic_extra_types.country import CountryShortName
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic import field_validator
from app.user_profile.utils import validate_id_dates


class SalutationSchema(str,Enum):
    Mr = "Mr"
    Mrs = "Mrs"
    Miss = "Miss"
    
class GenderSchema(str, Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"
    # add other gender options

class ProfileBaseSchema(SQLModel):

class ProfileUpdateSchema(ProfileBaseSchema):