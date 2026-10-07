from fastapi import FastAPI 
from fastapi import File, UploadFile, Form 
from src.app.schemas import RecipeRequest, RecipeIngredient, Recipe, RecipeResponse , DetectedIngredients
from dotenv import load_dotenv 
import os 
from groq import Groq 
from fastapi.middleware.cors import CORSMiddleware
import asyncio  
import json
import base64
from sqlalchemy import select
from app.database import SessionLocal, User, Session, SavedRecipe 
from app.security import hash_password
from app.security import verify_password
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Response
from fastapi import Cookie 

load_dotenv() 


client = Groq(api_key=os.getenv("groq_api_key"))

SYSTEM_PROMPT = """
You are PantryChef, a practical recipe assistant.

Your job is to determine what food can genuinely be prepared using the
ingredients the user currently has.

The detected ingredient list represents the user's actual available food.

CORE PRODUCT RULE:
PantryChef is a "cook with what you have" assistant.

Do NOT behave like a normal recipe search engine.

Do NOT design a recipe first and then add ingredients that the user does
not have.

A recipe is valid only when its core ingredients are available in the
detected ingredient list.

--------------------------------------------------
1. AVAILABLE INGREDIENTS
--------------------------------------------------

The detected ingredient list is the user's actual food inventory.

You MUST NOT assume that the user has an ingredient simply because it is
common in a recipe.

For example, if the detected ingredients are:

["egg", "tomato", "onion"]

you may use:

- egg
- tomato
- onion

You may NOT assume:

- cheese
- bread
- rice
- flour
- chicken
- potato
- cream
- butter

unless they are explicitly detected.

Ingredient synonyms are allowed only when they clearly refer to the same
food.

Examples:

- tomato = tomatoes
- potato = potatoes
- egg = eggs
- onion = onions

Do not treat unrelated ingredients as synonyms.

--------------------------------------------------
2. BASIC PANTRY STAPLES
--------------------------------------------------

You may assume access to only these basic cooking staples:

- water
- salt
- cooking oil
- pepper
- basic spices and seasonings

These staples do NOT count as core ingredients.

Do NOT assume access to:

- flour
- bread
- rice
- pasta
- butter
- cheese
- milk
- cream
- sauces
- vegetables
- meat
- eggs

unless they are detected.

Do not use pantry staples to construct an otherwise impossible recipe.

--------------------------------------------------
3. RECIPE FEASIBILITY
--------------------------------------------------

Before generating a recipe, determine whether the dish is genuinely
practical using the available ingredients.

A valid recipe must:

- make culinary sense
- use the available ingredients meaningfully
- produce a recognizable and coherent dish
- have realistic quantities
- have realistic cooking steps
- be practical for a normal home kitchen
- not depend on unavailable core ingredients

Do NOT generate bizarre combinations simply because the ingredients can
technically be cooked together.

Do NOT dump unrelated ingredients into one recipe.

QUALITY IS MORE IMPORTANT THAN THE NUMBER OF RECIPES.

One excellent recipe is better than two mediocre recipes.

--------------------------------------------------
4. ZERO-RECIPE CONDITION
--------------------------------------------------

If no genuinely practical recipe can be made using the available
ingredients, return an empty recipes list.

Example:

{
  "recipes": [],
  "message": "There are not enough compatible ingredients to make a practical recipe."
}

An empty recipes list is a VALID and SUCCESSFUL response.

NEVER invent a recipe simply to avoid returning an empty list.

NEVER add unavailable core ingredients just to make a recipe possible.

--------------------------------------------------
5. NUMBER OF RECIPES
--------------------------------------------------

Return a maximum of 2 recipes.

Generate 2 recipes only when there are genuinely different and practical
recipes.

If only 1 good recipe exists, return 1 recipe.

If no good recipe exists, return an empty recipes list.

Never create a second recipe just to reach a target number.

--------------------------------------------------
6. INGREDIENT VALIDATION
--------------------------------------------------

Every ingredient in the recipe's ingredients array must be either:

1. Present in the detected ingredient list
OR
2. One of the allowed basic pantry staples.

Do not include unavailable ingredients.

The recipe must be possible to cook NOW using what the user has.

--------------------------------------------------
7. AVAILABLE AND MISSING INGREDIENTS
--------------------------------------------------

available_ingredients must contain only ingredients detected in the image.

missing_ingredients must normally be an empty list.

Do NOT use missing_ingredients to introduce core ingredients.

For example:

Detected:
["egg", "tomato", "onion"]

Good:

available_ingredients:
["egg", "tomato", "onion"]

missing_ingredients:
[]

Bad:

missing_ingredients:
["bread", "cheese", "butter"]

--------------------------------------------------
8. DIET
--------------------------------------------------

The user's diet is a strict constraint.

Respect it at all times.

For vegan:

- no meat
- no fish
- no eggs
- no milk
- no cheese
- no other animal-derived ingredients

For vegetarian:

- no meat
- no fish

Never sacrifice dietary compliance for recipe quality.

--------------------------------------------------
9. ALLERGIES
--------------------------------------------------

Allergies are absolute constraints.

Never use an ingredient listed in the user's allergies.

If there is uncertainty about whether an ingredient conflicts with an allergy,
do not use it.

Allergy safety takes priority over every other instruction.

--------------------------------------------------
10. FOODS TO AVOID
--------------------------------------------------

Never intentionally use ingredients listed in the user's foods-to-avoid
list.

--------------------------------------------------
11. COOKING TIME
--------------------------------------------------

If the user provides a maximum cooking time, every recipe must realistically
be achievable within that time.

Do not artificially reduce the cooking time just to satisfy the constraint.

--------------------------------------------------
12. CUISINE
--------------------------------------------------

Try to respect the requested cuisine when practical.

However, cuisine preference must NEVER override:

1. allergies
2. diet
3. available ingredients
4. recipe feasibility
5. cooking-time limits

If the requested cuisine cannot reasonably be achieved with the available
ingredients, prefer a practical recipe over a forced cuisine match.

--------------------------------------------------
13. NO RECIPE DESIGN AROUND MISSING INGREDIENTS
--------------------------------------------------

Do NOT create recipes that require a collection of missing ingredients.

Do NOT say:

"Make pizza, but you need flour, cheese, tomato sauce and yeast."

That violates the PantryChef concept.

PantryChef exists to discover what the user can make NOW.

--------------------------------------------------
14. OUTPUT
--------------------------------------------------

Return ONLY valid JSON matching the provided response schema.

Do not return markdown.

Do not return explanations outside the JSON.

Do not return comments.

Be honest.

If a good recipe exists, return it.

If no good recipe exists, return an empty recipes list.
"""


app = FastAPI()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




async def get_authenticated_user(
    session_id: str | None = Cookie(default=None)
):
    if not session_id:
        return None

    async with SessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )

        session = result.scalar_one_or_none()

        if not session:
            return None

        if session.expires_at <= datetime.now(timezone.utc):
            return None

        result = await db.execute(
            select(User).where(User.id == session.user_id)
        )

        return result.scalar_one_or_none()



ALLOWED_PANTRY_STAPLES = {
    "water",
    "salt",
    "oil",
    "cooking oil",
    "pepper",
}


def normalize_ingredient(name: str) -> str:
    name = name.lower().strip()

    aliases = {
        "tomatoes": "tomato",
        "potatoes": "potato",
        "eggs": "egg",
        "onions": "onion",
        "carrots": "carrot",
        "garlic cloves": "garlic",
        "ginger root": "ginger",
    }

    return aliases.get(name, name)




def validate_recipes(result: RecipeResponse, detected: DetectedIngredients):
    detected_names = {
        normalize_ingredient(item.name)
        for item in detected.ingredients
    }

    valid_recipes = []

    for recipe in result.recipes:
        valid = True

        for ingredient in recipe.ingredients:
            ingredient_name = normalize_ingredient(ingredient.name)

            if ingredient_name in ALLOWED_PANTRY_STAPLES:
                continue

            if ingredient_name not in detected_names:
                print(
                    f"REJECTED RECIPE '{recipe.name}': "
                    f"unavailable ingredient '{ingredient.name}'"
                )

                valid = False
                break

        if valid:
            valid_recipes.append(recipe)

    result.recipes = valid_recipes

    if not result.recipes:
        result.message = (
            "There are not enough compatible ingredients "
            "to make a practical recipe."
        )

    return result




@app.post("/recipe")
async def generate_recipe(
    image: UploadFile= File(...),
   diet:str = Form(...),
   allergies: str = Form(""),
   avoid:str = Form(""),
   cuisine:str = Form(...),
   max_cooking_time: int | None = Form(None),
   session_id: str | None = Cookie(default=None) 
   ):

  user = await get_authenticated_user(session_id) 

  if not user :
      return {"error" : "Not authenticated "} 

 
  VISION_PROMPT = """
    You are an ingredient detection system.

    Analyze the uploaded image and identify only food ingredients
    that are clearly visible.

    Return ONLY valid json.

    The json must have exactly this structure:

    {
    "ingredients": [
        {
        "name": "ingredient name",
        "confidence": 0.95
        }
    ]
    }

    Do not generate recipes.
    Do not infer ingredients.
    Do not guess based only on color.
    Prefer false negatives over false positives.
    Ignore containers, packaging, labels and text.
    Do not add ingredients that are not visibly present.
    Each ingredient should appear only once.
    """
        
    #Read Uploaded image
  image_bytes = await image.read() 
  base64_image = base64.b64encode(image_bytes).decode("utf-8")
 
    
  vision_response = client.chat.completions.create(
    model="qwen/qwen3.8-27b",
    messages=[
        {
            "role": "system",
            "content": """
    You are an ingredient detection system.

    You MUST return the answer as valid json.

    The json must have exactly this structure:

    {
        "ingredients": [
            {
                "name": "ingredient name",
                "confidence": 0.95
            }
        ]
    }

    Identify ONLY food ingredients that are clearly visible in the image.

    Do not generate recipes.
    Do not infer ingredients.
    Do not guess based only on color.
    Prefer false negatives over false positives.
    Ignore containers, packaging, labels and text.
    Do not add ingredients that are not visibly present.
    Each ingredient should appear only once.
    """
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Analyze this image and return the detected ingredients as json."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image.content_type};base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    temperature=0,
    response_format={"type": "json_object"}
)
    
  detected = DetectedIngredients.model_validate(
    json.loads(vision_response.choices[0].message.content)
)
  print("DETECTED INGREDIENTS:", detected)



  user_prompt = f"""
    Determine what practical recipes can genuinely be made from the following
    available ingredients.

    AVAILABLE INGREDIENTS:
    {[item.name for item in detected.ingredients]}

    USER PREFERENCES:

    Diet:
    {diet}

    Allergies:
    {allergies}

    Foods to avoid:
    {avoid}

    Cuisine:
    {cuisine}

    Maximum cooking time:
    {max_cooking_time} minutes

    IMPORTANT:

    The available ingredient list is the user's actual food inventory.

    Use the available ingredients as the foundation of the recipe.

    Only water, salt, cooking oil, pepper, and basic seasonings may be assumed
    as pantry staples.

    Do NOT assume the user has other ingredients.

    Do NOT add unavailable core ingredients.

    Before generating each recipe, verify that it is genuinely practical and
    recognizable using the available ingredients.

    If no practical recipe can be made, return:

    {{
    "recipes": [],
    "message": "There are not enough compatible ingredients to make a practical recipe."
    }}

    Do NOT invent a recipe just to avoid an empty response.

    Generate at most 2 recipes.

    Return only the JSON response matching the schema.
    """



  response = client.chat.completions.create(
      model="qwen/qwen3.8-27b",
      messages=[ 
          {
              "role": "system",
              "content": SYSTEM_PROMPT,
          },
          {
              "role": "user",
              "content": user_prompt,
          },
      ],
      temperature=0.2,
      max_tokens = 900, 
      response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "recipe_response",
        "strict": True,
        "schema": RecipeResponse.model_json_schema()
    }
  },
  )
 

  result = RecipeResponse.model_validate(
    json.loads(response.choices[0].message.content)
)

  result = validate_recipes(result, detected)

  print("FINAL RECIPE RESULT:", result)

  return result



@app.post("/auth/register")
async def register(email: str = Form(...),
                    password: str = Form(...)
                    ):
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == email)
        )

        existing_user = result.scalar_one_or_none()

        if existing_user:
            return {"error": "Email already registered"}

        user = User(
            email=email,
            password_hash=hash_password(password)
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return {
            "message": "User registered successfully",
            "user_id": user.id
        }



@app.post("/auth/login")
async def login(response: Response,
                email: str = Form(...),
                password : str = Form(...)
                ):
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == email)
        )

        user = result.scalar_one_or_none()

        if not user:
            return {"error": "Invalid email or password"}

        if not verify_password(password, user.password_hash):
            return {"error": "Invalid email or password"}

        session_id = secrets.token_urlsafe(32)

        session = Session(
            id=session_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.add(session)
        await db.commit()

        is_production = os.getenv("ENVIRONMENT") == "production"

        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=is_production,
            samesite="none" if is_production else "lax",
            max_age=7 * 24 * 60 * 60,
            path="/",
        )   

        return {
            "message": "Login successful"
        }



@app.get("/auth/me")
async def get_current_user(session_id: str | None = Cookie(default=None)):
    if not session_id:
        return {"error": "Not authenticated"}

    async with SessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )

        session = result.scalar_one_or_none()

        if not session:
            return {"error": "Invalid session"}

        if session.expires_at <= datetime.now(timezone.utc):
            return {"error": "Session expired"}

        result = await db.execute(
            select(User).where(User.id == session.user_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            return {"error": "User not found"}

        return {
            "id": user.id,
            "email": user.email
        }



@app.post("/auth/logout")
async def logout(
    response: Response,
    session_id: str | None = Cookie(default=None)
):
    if session_id:
        async with SessionLocal() as db:
            result = await db.execute(
                select(Session).where(Session.id == session_id)
            )

            session = result.scalar_one_or_none()

            if session:
                await db.delete(session)
                await db.commit()

    response.delete_cookie(
        key="session_id",
        path="/"
    )

    return {
        "message": "Logged out successfully"
    }



@app.post("/recipes/save")
async def save_recipe(
    recipe_data: dict,
    session_id: str | None = Cookie(default=None)
):
    if not session_id:
        return {"error": "Not authenticated"}

    async with SessionLocal() as db:

        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )

        session = result.scalar_one_or_none()

        if not session:
            return {"error": "Invalid session"}

        new_recipe = SavedRecipe(
            user_id=session.user_id,
            recipe_data=recipe_data
        )

        db.add(new_recipe)

        await db.commit()
        await db.refresh(new_recipe)

        return {
            "message": "Recipe saved successfully",
            "recipe_id": new_recipe.id
        }



@app.get("/recipes/saved")
async def get_saved_recipes(
    session_id: str | None = Cookie(default=None)
):
    if not session_id:
        return {"error": "Not authenticated"}

    async with SessionLocal() as db:

        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )

        session = result.scalar_one_or_none()

        if not session:
            return {"error": "Invalid session"}

        result = await db.execute(
            select(SavedRecipe)
            .where(SavedRecipe.user_id == session.user_id)
            .order_by(SavedRecipe.created_at.desc())
        )

        saved_recipes = result.scalars().all()

        return {
            "recipes": [
                {
                    "id": recipe.id,
                    "recipe": recipe.recipe_data,
                    "created_at": recipe.created_at
                }
                for recipe in saved_recipes
            ]
        }




@app.delete("/recipes/saved/{recipe_id}")
async def delete_saved_recipe(
    recipe_id: int,
    session_id: str | None = Cookie(default=None)
):
    if not session_id:
        return {"error": "Not authenticated"}

    async with SessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            return {"error": "Invalid session"}

        result = await db.execute(
            select(SavedRecipe)
            .where(
                SavedRecipe.id == recipe_id,
                SavedRecipe.user_id == session.user_id
            )
        )
        saved_recipe = result.scalar_one_or_none()

        if not saved_recipe:
            return {"error": "Saved recipe not found"}

        await db.delete(saved_recipe)
        await db.commit()

        return {
            "message": "Recipe deleted successfully"
        }



@app.get("/health")
async def health():
    return {"status": "ok"}    