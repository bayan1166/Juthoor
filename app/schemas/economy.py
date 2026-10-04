from pydantic import BaseModel, Field


class AvatarConfigIn(BaseModel):
    gender: str = Field(max_length=10)
    skin: str = Field(max_length=20)
    clothing: str = Field(max_length=40)
    top: str = Field(max_length=40)
    neck: str = Field(max_length=40)
    accessories: str = Field(max_length=40)
    hair: str = Field(max_length=20)
    hair_color: str = Field(max_length=20)
