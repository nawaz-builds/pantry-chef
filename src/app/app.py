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
from app.prompts import SYSTEM_PROMPT, build_user_prompt, validate_recipes, parse_blocked

load_dotenv() 


client = Groq(api_key=os.getenv("groq_api_key"))



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



  user_prompt = build_user_prompt(
          ingredients=[item.name for item in detected.ingredients],
          diet=diet, allergies=allergies, avoid=avoid,
          cuisine=cuisine, max_cooking_time=max_cooking_time,
      )



  print("RECIPE USER PROMPT:")
  print(user_prompt)

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
        max_tokens=900,
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

  print("RAW RECIPE RESULT FROM GROQ:", result)

  result = validate_recipes(result, detected, blocked_terms=parse_blocked(allergies, avoid))

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