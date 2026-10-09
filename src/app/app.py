from fastapi import FastAPI , HTTPException, Depends
from fastapi import File, UploadFile, Form 
from src.app.schemas import( RecipeRequest,
                             RecipeIngredient,
                             Recipe,
                             RecipeResponse ,
                             DetectedIngredients,
                             UserRegister,
                             UserLogin  )
from dotenv import load_dotenv 
import os 
from groq import Groq, APIError, RateLimitError
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
from sqlalchemy.exc import IntegrityError
from app.prompts import SYSTEM_PROMPT, build_user_prompt, validate_recipes, parse_blocked
import logging

load_dotenv() 

logger = logging.getLogger(__name__) 


client = Groq(api_key=os.getenv("GROQ_API_KEY"))



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
    session_id: str | None = Cookie(default=None)) -> User:
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with SessionLocal() as db:
        session = (await db.execute(
            select(Session).where(Session.id == session_id)
        )).scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        if session.expires_at <= datetime.now(timezone.utc):
            await db.delete(session)          # clean up the dead row
            await db.commit()
            raise HTTPException(status_code=401, detail="Session expired")

        user = (await db.execute(
            select(User).where(User.id == session.user_id)
        )).scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")

        return user




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
      raise HTTPException(
          status_code=401,
          detail="unauthorized"
      )

 
        
    #Read Uploaded image
  image_bytes = await image.read() 
  base64_image = base64.b64encode(image_bytes).decode("utf-8")
 
  try:   
    vision_response = await asyncio.to_thread( client.chat.completions.create,
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
  except RateLimitError :
      raise HTTPException(
          status_code=502,
          detail="AI service is busy , Please try again"
      )
  except APIError :
      logger.exception("Groq request failed")
      raise HTTPException(status_code=502, detail="AI service unavailable")
    
  detected = DetectedIngredients.model_validate(
    json.loads(vision_response.choices[0].message.content)
)



  user_prompt = build_user_prompt(
          ingredients=[item.name for item in detected.ingredients],
          diet=diet, allergies=allergies, avoid=avoid,
          cuisine=cuisine, max_cooking_time=max_cooking_time,
      )



  try:
    response = await asyncio.to_thread( client.chat.completions.create,
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
  except RateLimitError :
      raise HTTPException(
          status_code=502,
          detail="AI service is busy , Please try again"
      )
  except APIError :
      logger.exception("Groq request failed")
      raise HTTPException(status_code=502, detail="AI service unavailable")
    

  result = RecipeResponse.model_validate(
    json.loads(response.choices[0].message.content)
)


  result = validate_recipes(result, detected, blocked_terms=parse_blocked(allergies, avoid))


  return result



@app.post("/auth/register", status_code=201)
async def register(data: UserRegister):
    email = str(data.email).lower()

    if len(data.password) < 8:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 8 characters"
        )

    async with SessionLocal() as db:
        existing = (
            await db.execute(
                select(User).where(User.email == email)
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        user = User(
            email=email,
            password_hash=hash_password(data.password)
        )

        db.add(user)

        try:
            await db.commit()

        except IntegrityError:
            await db.rollback()

            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        await db.refresh(user)

        return {
            "message": "User registered successfully",
            "user_id": user.id
        }



@app.post("/auth/login")
async def login(response: Response,
                data: UserLogin
                ):

    email = str(data.email).lower()
    password = str(data.password)

    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == email)
        )

        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Invalid email or password"
            )

        if not verify_password(password, user.password_hash):
            raise HTTPException (
                status_code=401,
                detail="Invalid email or password"
            )

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
        raise HTTPException (
            status_code=401,
            detail="Not authenticated"
        )

    async with SessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )

        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=401,
                detail="Invalid session"
            )

        if session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=401,
                detail="Invalid session"
            )

        result = await db.execute(
            select(User).where(User.id == session.user_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Not found"
            )

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
async def save_recipe(recipe_data: dict, user: User = Depends(get_authenticated_user)): 
    async with SessionLocal() as db:
        new_recipe = SavedRecipe(user_id=user.id, recipe_data=recipe_data)
        db.add(new_recipe)
        await db.commit()
        await db.refresh(new_recipe)
        return {"message": "Recipe saved successfully", "recipe_id": new_recipe.id}



@app.get("/recipes/saved")
async def get_saved_recipes(
    user : User = Depends(get_authenticated_user)
):

    async with SessionLocal() as db:

        result = await db.execute(
            select(SavedRecipe)
            .where(SavedRecipe.user_id == user.id)
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
    user : User = Depends(get_authenticated_user)
):
    

    async with SessionLocal() as db:


        result = await db.execute(
            select(SavedRecipe)
            .where(
                SavedRecipe.id == recipe_id,
                SavedRecipe.user_id == user.id
            )
        )
        saved_recipe = result.scalar_one_or_none()

        if not saved_recipe:
            raise HTTPException(
                status_code=404,
                detail="Recipe Not found"
            )

        await db.delete(saved_recipe)
        await db.commit()

        return {
            "message": "Recipe deleted successfully"
        }



@app.get("/health")
async def health():
    return {"status": "ok"}    