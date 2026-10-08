import re

# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------
# Design notes:
#  - States the positive goal first (produce 1-2 recipes).
#  - Empty list is a narrow last resort, and the empty JSON is NOT shown as an
#    example (models copy examples).
#  - One section per topic; no duplicated rules.
#  - One filled-in example so the model copies a *non-empty* output shape.

SYSTEM_PROMPT = """
You are PantryChef, a practical "cook with what you have" recipe assistant.
 
YOUR GOAL
Create 2 simple, recognizable recipes built around the ingredients the user
already has. Always return at least one recipe: some dish can always be made
from a few ingredients plus basic pantry items.
 
INGREDIENT TIERS
1. HAVE (the heart of the dish): ingredients from the detected list.
   Plurals and obvious variants count as the same food (tomato / tomatoes).
   Every recipe must be built around at least 2 of these (or the only one or
   two available).
2. PANTRY (assumed, never listed as missing): water, salt, pepper, cooking oil,
   sugar, onion, garlic, ginger, and common dried spices and seasonings
   (turmeric, cumin, paprika, chili powder, oregano, garam masala, etc.).
3. NEED (optional extras): at most 2 cheap, common items the user does NOT have
   that noticeably improve the dish (for example a lemon, flour, rice, an egg,
   fresh coriander). Put them in "missing_ingredients". Prefer recipes that
   need 0 or 1; use 2 only when it makes the dish clearly better.
Never invent a dish that depends mostly on missing items. The user's own
ingredients stay the star.
 
HOW TO BUILD A RECIPE
1. Look at the detected ingredients and pick the 2-4 that go well together.
   You do not have to use all of them, and you may ignore ones that do not fit.
2. Choose a simple, well-known dish those ingredients can make
   (stir-fry, curry, omelette, soup, salad, roast, fritters, scramble, etc.).
   Staples and spices are there to season and cook the dish, so use them freely.
3. Give realistic quantities and clear, realistic steps for a home kitchen.
4. Make the second recipe clearly different from the first (different dish
   type or cooking method), not a variation of it.
 
USER CONSTRAINTS
The ingredient list you receive has already been filtered for the user's diet,
allergies and foods to avoid. Do not second-guess it: every listed ingredient
is allowed. Do not add anything that is not listed (apart from the staples).
- Maximum cooking time: if given, every recipe must realistically fit in it.
- Cuisine: follow it when the ingredients allow. If they do not, make a
  practical dish instead of forcing the cuisine.
- If a Note says to keep food mild, use no chili or hot spices.
 
NEVER REFUSE
Do not say there are no recipes, not enough ingredients, or that nothing can be
made, in any field. If the list is small, make something simple: a stir-fry, a
salad, a soup, a scramble, a roast, a curry, a fritter. Use tier 2 and tier 3
to fill the gaps.
 
OUTPUT FORMAT
Return only valid JSON matching the provided schema.
- "recipes": list of 2 recipes (1 only if a second would be a near-duplicate). "message": null.
- Each recipe has:
  name (string), cooking_time_minutes (integer),
  difficulty ("easy", "medium" or "hard"),
  available_ingredients (detected ingredients actually used),
  missing_ingredients (0-2 items from tier 3, [] if none),
  ingredients (list of objects with "name" and "quantity", never plain strings),
  steps (list of clear instructions).
- Use "name" for the recipe title. Do not add a "title" or "description" field.
- "ingredients" lists everything the recipe uses: HAVE, PANTRY and NEED items.
  Every NEED item must also appear in missing_ingredients.
 
FORMAT EXAMPLE (shows the shape only; choose dishes that fit the actual list)
Detected: ["potato", "onion", "green chili"]
{
  "recipes": [
    {
      "name": "Spiced Potato Fry",
      "cooking_time_minutes": 25,
      "difficulty": "easy",
      "available_ingredients": ["potato", "onion", "green chili"],
      "missing_ingredients": ["lemon"],
      "ingredients": [
        {"name": "potato", "quantity": "3 medium, diced"},
        {"name": "onion", "quantity": "1, sliced"},
        {"name": "green chili", "quantity": "2, slit"},
        {"name": "cooking oil", "quantity": "2 tbsp"},
        {"name": "turmeric", "quantity": "1/2 tsp"},
        {"name": "salt", "quantity": "to taste"},
        {"name": "lemon", "quantity": "1/2, juiced (optional finish)"}
      ],
      "steps": [
        "Heat the oil in a pan over medium heat.",
        "Fry the onion and green chili for 3 minutes until soft.",
        "Add the potato, turmeric and salt, and stir to coat.",
        "Cover and cook for 12-15 minutes, stirring now and then, until tender and lightly browned.",
        "Finish with a squeeze of lemon juice."
      ]
    }
  ],
  "message": null
}
""".strip()

# ---------------------------------------------------------------------------
# USER PROMPT
# ---------------------------------------------------------------------------

def build_user_prompt(
    ingredients: list[str],
    diet: str,
    allergies: str = "",
    avoid: str = "",
    cuisine: str = "",
    max_cooking_time: int | None = None,
) -> str:
    """Short, data-only user message. Rules live in the system prompt."""
    lines = [
        "Create 1-2 practical recipes from these detected ingredients.",
        "",
        f"Detected ingredients: {', '.join(ingredients) if ingredients else '(none)'}",
        f"Diet: {diet or 'no restriction'}",
        f"Allergies: {allergies.strip() or 'none'}",
        f"Foods to avoid: {avoid.strip() or 'none'}",
        f"Cuisine: {cuisine or 'any'}",
    ]
    if max_cooking_time is not None:
        lines.append(f"Maximum cooking time: {max_cooking_time} minutes")
    else:
        lines.append("Maximum cooking time: no limit")

    lines += [
        "",
        "Pick the detected ingredients that go well together; you don't need to use all of them.",
        "Return the JSON response only.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------

_DESCRIPTORS = {
    "fresh", "ripe", "large", "small", "medium", "big", "chopped", "diced",
    "sliced", "minced", "grated", "crushed", "ground", "dried", "raw", "whole",
    "peeled", "boiled", "cooked", "finely", "roughly", "thinly",
}

_STAPLE_SPICES = {
    "turmeric", "cumin", "paprika", "oregano", "thyme", "rosemary", "cinnamon",
    "cardamom", "coriander", "masala", "garam masala", "curry powder",
    "chili powder", "chilli powder", "chili flakes", "chilli flakes",
    "red chili powder", "mustard seeds", "cumin seeds", "spice", "spices",
    "seasoning", "seasonings", "herbs", "mixed herbs", "italian seasoning",
    "bay leaf", "bay leaves", "cloves", "nutmeg", "garlic powder", "onion powder",
}

_PEPPER_STAPLES = {
    "pepper", "black pepper", "white pepper", "ground pepper",
    "ground black pepper", "peppercorn", "peppercorns",
}

_STAPLE_EXACT = {"water", "salt", "sea salt", "ice"}


def normalize_ingredient(name: str) -> str:
    """Lowercase, drop parentheticals/descriptors/commas, singularize."""
    name = name.lower().strip()
    name = re.sub(r"\(.*?\)", " ", name)       # "tomato (diced)" -> "tomato"
    name = name.split(",")[0]                  # "tomatoes, diced" -> "tomatoes"
    words = [w for w in re.findall(r"[a-z]+", name) if w not in _DESCRIPTORS]
    return " ".join(_singular(w) for w in words)


def _singular(word: str) -> str:
    if word.endswith("oes"):          # tomatoes, potatoes
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:   # berries -> berry
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _tokens(name: str) -> set[str]:
    return set(name.split())


def is_staple(name: str) -> bool:
    """name must already be normalized."""
    if name in _STAPLE_EXACT or name in _PEPPER_STAPLES:
        return True
    if name in {normalize_ingredient(s) for s in _STAPLE_SPICES}:
        return True
    # any kind of cooking oil: "olive oil", "mustard oil", "vegetable oil"
    if name == "oil" or name.endswith(" oil"):
        return True
    return False


def matches_detected(name: str, detected_names: set[str]) -> bool:
    """
    Whole-word match in either direction:
      "red onion" ~ "onion", "cheddar cheese" ~ "cheese", "bell pepper" ~ "red bell pepper".
    Trade-off: "coconut milk" would also match a detected "milk".
    """
    t = _tokens(name)
    for d in detected_names:
        dt = _tokens(d)
        if name == d or (dt and dt <= t) or (t and t <= dt):
            return True
    return False


def parse_blocked(allergies: str, avoid: str) -> set[str]:
    """Turn the free-text allergy / avoid fields into normalized terms."""
    terms = set()
    for field in (allergies, avoid):
        for part in re.split(r"[,;/\n]| and ", field or ""):
            n = normalize_ingredient(part)
            if n and n not in {"none", "no", "nil", "na"}:
                terms.add(n)
    return terms


def validate_recipes(result, detected, blocked_terms: set[str] | None = None):
    """
    Safety-net validation.
      1. Every ingredient must be a staple or match a detected ingredient.
      2. No ingredient may contain an allergy / avoid term (hard backstop,
         since the prompt itself no longer repeats these rules at length).
    Rejections are logged with the reason. The model's own message is kept when
    it gave one; otherwise a generic message is used.
    """
    detected_names = {normalize_ingredient(i.name) for i in detected.ingredients}
    blocked_terms = blocked_terms or set()

    valid_recipes = []
    had_recipes = bool(result.recipes)

    for recipe in result.recipes:
        reason = None

        for ing in recipe.ingredients:
            name = normalize_ingredient(ing.name)
            if not name:
                continue

            if any(b in _tokens(name) or b == name or b in name for b in blocked_terms):
                reason = f"'{ing.name}' conflicts with allergies/avoid list"
                break

            if is_staple(name) or matches_detected(name, detected_names):
                continue

            reason = f"'{ing.name}' is not detected and not a staple"
            break

        if reason:
            print(f"REJECTED RECIPE '{recipe.name}': {reason}")
        else:
            valid_recipes.append(recipe)

    result.recipes = valid_recipes

    if not result.recipes:
        if had_recipes:
            print("VALIDATOR removed every recipe the model returned.")
            result.message = (
                "I couldn't put together a recipe that fits your ingredients "
                "and preferences. Try a clearer photo or relax a filter."
            )
        elif not result.message:
            result.message = (
                "There are not enough compatible ingredients to make a practical recipe."
            )
    else:
        result.message = None

    return result