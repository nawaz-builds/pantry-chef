from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Literal 



class RecipeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingredients: list[str] = Field(min_length=1) 

    diet: Literal[
        "vegetarian",
        "non-vegetarian",
        "vegan"
    ]

    allergies: list[str] = []

    avoid: list[str] = []

    cuisine: str | None = None

    max_cooking_time: int | None = Field(
        default=None,
        gt=0
    )



class DetectedIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="Normalized name of the food ingredient"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence that the ingredient is clearly visible"
    )


class DetectedIngredients(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingredients: list[DetectedIngredient] 
        



class RecipeIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    quantity: str


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    cooking_time_minutes: int
    difficulty: Literal["easy", "medium", "hard"]

    available_ingredients: list[str]
    missing_ingredients: list[str]

    ingredients: list[RecipeIngredient]
    steps: list[str]


class RecipeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipes: list[Recipe] = Field(min_length=1,max_length=2)
    message: str | None

# AUTH SCHEMAS 

class UserRegister(BaseModel):
    email: EmailStr
    password: str    