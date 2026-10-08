# 🍳 PantryChef

### Cook with what you already have.

PantryChef is an AI-powered cooking app built around a simple idea:

> **Don't search for a recipe. Start with what's already in your kitchen.**

Upload a photo of your ingredients, choose your preferences, and PantryChef tries to turn that inventory into practical recipes — while respecting dietary preferences, allergies, ingredients you want to avoid, cuisine, and cooking time.

It also has user accounts and saved recipes, so this isn't just an AI demo. It's a full-stack application with a real backend, database, authentication, API, and deployed frontend.

---

## 🌐 Try it

**Live app:**  
https://pentry-ch.netlify.app/

The backend is deployed separately and serves the application's API.

---

## 🧠 What makes PantryChef different?

Most AI recipe generators work roughly like this:

```text
"Give me a recipe for chicken pasta"
              ↓
          AI generates
              ↓
          Recipe

PantryChef starts from the opposite direction:

             Your kitchen
                  │
                  ▼
          📷 Ingredient photo
                  │
                  ▼
        Ingredient detection
                  │
                  ▼
       Available food inventory
                  │
          ┌───────┴────────┐
          ▼                ▼
     User preferences   Restrictions
     • cuisine          • allergies
     • time             • avoid
     • diet
          └───────┬────────┘
                  ▼
             AI recipe
                  │
                  ▼
       Server-side validation
                  │
                  ▼
          🍳 Practical recipe

The important part is that the AI is not supposed to freely invent a recipe and then pretend the ingredients exist.

The available ingredients are treated as the user's actual inventory.

✨ Features
📷 Ingredient-based cooking

Upload an image of your fridge, pantry, or ingredients.

PantryChef uses the detected ingredients as the starting point for recipe generation.

🤖 AI recipe generation

Recipes are generated based on the ingredients actually available rather than simply searching for a generic recipe.

🥗 Dietary preferences

Recipes can take dietary preferences into account.

⚠️ Allergies

Users can specify ingredients they are allergic to.

🚫 Ingredients to avoid

Users can explicitly tell PantryChef what they don't want included.

⏱️ Cooking time

Recipes can be constrained by the amount of time the user wants to spend cooking.

🌎 Cuisine preferences

Users can choose the type of cuisine they want.

🔐 Authentication

PantryChef has user registration and login with session-based authentication.

Authentication uses HTTP cookies rather than storing authentication tokens in browser JavaScript.

💾 Saved recipes

Users can save generated recipes and access them later.

📱 Responsive UI

The frontend is designed to work on both desktop and mobile screens.

🏗️ Tech Stack
Frontend
React
Vite
CSS
Backend
Python
FastAPI
Pydantic
SQLAlchemy
PostgreSQL
AI
Groq API
Qwen model
Deployment
Netlify — frontend
Render — backend
Python tooling
uv
🔥 Architecture
                    ┌──────────────────────┐
                    │       Browser        │
                    │   React + Vite UI    │
                    └──────────┬───────────┘
                               │
                               │ HTTP / JSON
                               │
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │      Backend         │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        Authentication      Recipe API      Saved Recipes
              │                │                │
              │                ▼                │
              │           Groq / Qwen           │
              │                │                │
              │                ▼                │
              │        Pydantic validation      │
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                         PostgreSQL
🔐 A small security challenge

This project is also being used as a playground for learning web security.

If you're learning:

Web security
Pentesting
API security
Authentication
Authorization
Burp Suite
OWASP Top 10
IDOR / access-control testing

You're welcome to test PantryChef.

I'm especially interested in finding things I missed.

Things worth looking at
Authentication
     │
     ├── Registration
     ├── Login
     ├── Logout
     └── Session cookies

Authorization
     │
     ├── User → own recipes
     ├── Saved recipes
     └── Resource access

API
     │
     ├── Input validation
     ├── Request manipulation
     ├── Unexpected payloads
     └── Error handling

File uploads
     │
     └── Image upload handling

Database
     │
     └── User / recipe isolation
Testing rules

You have permission to test the PantryChef application itself.

Please don't:

DDoS or intentionally overload the service
Destroy the application
Delete or modify another user's data
Access another user's private information
Attack Render, Netlify, PostgreSQL infrastructure, or other third-party infrastructure

If you find something interesting, send me:

What you found
↓
How you reproduced it
↓
What you expected to happen
↓
What actually happened
↓
Why you think it matters

Screenshots, requests/responses, or a short PoC are useful.

This is a personal project, not a paid bug bounty program.

🚀 Running PantryChef locally
Requirements

You'll need:

Python
uv
Node.js
PostgreSQL
A Groq API key
1. Clone the repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git

cd pentry-chef
2. Install backend dependencies
uv sync
3. Configure environment variables

Create a .env file in the project root.

Example:

DATABASE_URL=your_database_url
GROQ_API_KEY=your_groq_api_key
FRONTEND_URL=http://localhost:5173

Never commit your real .env file.

Use .env.example for values that other developers need to configure.

4. Start the backend
uv run python main.py

The API will be available locally through FastAPI.

You can also open:

/docs

to explore the API through Swagger UI.

5. Start the frontend

Open another terminal:

cd frontend
npm install
npm run dev

Then open the local Vite URL shown in your terminal.

📁 Project structure
pentry-chef/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── index.css
│   │   ├── login.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── ...
│
├── src/
│   └── app/
│       ├── __init__.py
│       ├── app.py
│       ├── database.py
│       ├── schemas.py
│       └── security.py
│
├── main.py
├── pyproject.toml
├── uv.lock
├── .env.example
└── .gitignore
🧩 API

The backend exposes endpoints for things such as:

/auth/register
/auth/login
/auth/logout
/auth/me

/recipe

/saved-recipes

The exact API contract can be explored through the FastAPI Swagger documentation at:

/docs

when running the backend.

🛡️ Security-minded design

One of the things I'm intentionally experimenting with in this project is the difference between:

"The AI said this is okay."

and

"The server verified that this is okay."

For example, recipe generation is followed by server-side validation of the generated recipe against the detected ingredient inventory.

That means the application doesn't have to blindly trust the model's output.

This project is still evolving, so the security model should not be considered production-grade.

That's partly why I'm opening it up for testing.

📌 Current status

PantryChef is an active personal project.

The core application is working and deployed, but there are still things I want to improve:

Recipe generation quality
Ingredient detection accuracy
Security hardening
API validation
UI/UX
Error handling
Overall reliability

If you find something broken, weird, insecure, or just badly designed, I'd rather know about it.

🧪 Why I built this

This started as a simple idea:

What can I actually cook with the stuff sitting in my kitchen?

It turned into a much bigger experiment involving:

AI APIs
Computer vision / ingredient detection
Prompt engineering
Structured AI output
Pydantic validation
FastAPI
Async database operations
Session authentication
React
API integration
Deployment
Web security

So PantryChef ended up being less about recipes and more about building an actual AI-powered full-stack application from scratch.

👨‍💻 Built by

Nawaz

Personal project • Full-stack • AI • Web Security

