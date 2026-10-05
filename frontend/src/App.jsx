import { useState, useEffect } from "react";
import "./index.css";
import { login, getCurrentUser, logout, saveRecipe, getSavedRecipes, deleteSavedRecipe  } from "./api";
import Login from "./login";


const API_URL = "http://localhost:8000/recipe"; 

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [savedRecipes, setSavedRecipes] = useState([]);
  const [showSaved, setShowSaved] = useState(false);

  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);

  const [diet, setDiet] = useState("vegetarian");
  const [allergies, setAllergies] = useState("");
  const [avoid, setAvoid] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [maxCookingTime, setMaxCookingTime] = useState("");

  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function checkAuth() {
      try {
        const data = await getCurrentUser();

        if (data.email) {
          setUser(data);

          const savedData = await getSavedRecipes();
          setSavedRecipes(savedData.recipes || []);
        }
      } catch (error) {
        console.error("Auth check failed:", error);
      } finally {
        setAuthLoading(false);
      }
    }

    checkAuth();
  }, []);

  function handleImageChange(event) {
    const selectedImage = event.target.files[0];

    if (!selectedImage) return;

    setImage(selectedImage);
    setPreview(URL.createObjectURL(selectedImage));
    setError("");
  }

  async function generateRecipes() {
    if (!image) {
      setError("Please upload an image of your ingredients.");
      return;
    }

    setLoading(true);
    setError("");
    setRecipes([]);

    try {
      const formData = new FormData();

      formData.append("image", image);
      formData.append("diet", diet);
      formData.append("allergies", allergies);
      formData.append("avoid", avoid);
      formData.append("cuisine", cuisine);

      if (maxCookingTime) {
        formData.append("max_cooking_time", maxCookingTime);
      }

      const response = await fetch(API_URL, {
        method: "POST",
        credentials : "include", 
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        throw new Error(
          errorData?.detail || `Server error: ${response.status}`
        );
      }

      const data = await response.json();
      console.log("RECIPE RESPONSE:", data);

      setRecipes(data.recipes || []);
    } catch (err) {
      console.error(err);
      setError(
        err.message ||
          "Something went wrong while generating your recipes."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(userData) {
  setUser(userData);

  try {
    const savedData = await getSavedRecipes();
    setSavedRecipes(savedData.recipes || []);
  } catch (error) {
    console.error("Failed to load saved recipes:", error);
    setSavedRecipes([]);
  }
  }

  async function handleLogout() {
  try {
    await logout();
    setUser(null);
    setSavedRecipes([]);
    setShowSaved(false);
  } catch (error) {
    console.error("Logout failed:", error);
  }
  }
   
  async function handleSaveRecipe(recipe) {
  try {
    const result = await saveRecipe(recipe);
    console.log("Recipe saved:", result);

    const savedData = await getSavedRecipes();
    setSavedRecipes(savedData.recipes || []);

    return result;
  } catch (error) {
    console.error("Save recipe failed:", error);
    throw error;
  }
  }

  async function handleDeleteRecipe(recipeId) {
  try {
    await deleteSavedRecipe(recipeId);

    setSavedRecipes((current) =>
      current.filter((recipe) => recipe.id !== recipeId)
    );
  } catch (error) {
    console.error("Delete recipe failed:", error);
  }
  }


  if (authLoading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }


  return (
    <div className="app">
    <header className="navbar">
      <div className="logo">
        <span className="logo-icon">🍳</span>
        PantryChef
      </div>

      <div className="navbar-tag">
        AI-powered cooking
      </div>

      <div className="user-email">
        {user.email}
      </div>

      <button className="saved-nav-button" onClick={() => setShowSaved(true)}>
        ♡ Saved Recipes
      </button>

      <button className="logout-button" onClick={handleLogout}>
      <span>↪</span>
      Logout
    </button>
    </header>

      <main className="container">
        {showSaved ? (
      <section className="saved-recipes-section">
    <div className="saved-recipes-header">
      <div>
        <p className="eyebrow">YOUR COLLECTION</p>
        <h2>Saved Recipes</h2>
      </div>

      <button
        className="back-to-cooking-button"
        onClick={() => setShowSaved(false)}
      >
        ← Back to cooking
      </button>
    </div>
          
    {savedRecipes.length === 0 ? (
      <div className="empty-saved-recipes">
        <div>♡</div>
        <h3>No saved recipes yet</h3>
        <p>Recipes you save will appear here.</p>
      </div>
    ) : (
      <div className="recipe-grid">
        {savedRecipes.map((saved) => {
          console.log("SAVED RECIPE OBJECT:", saved);

          return (
            <RecipeCard
              key={saved.id}
              recipe={saved.recipe}
              index={savedRecipes.indexOf(saved)}
              onSave={handleSaveRecipe}
              onDelete={() => handleDeleteRecipe(saved.id)}
              isSaved={true}
            />
          );
        })}
      </div>
    )}
  </section>
  ) : (
    <>
        <section className="hero">
          <p className="eyebrow">YOUR PERSONAL AI CHEF</p>

          <h1>
            Cook with what
            <br />
            <span>you already have.</span>
          </h1>

          <p className="hero-description">
            Upload a photo of your ingredients and PantryChef
            will turn them into practical recipes.
          </p>
        </section>

        <section className="workspace">
          <div className="panel">
            <div className="section-heading">
              <div>
                <p className="section-label">01</p>
                <h2>Your ingredients</h2>
              </div>
            </div>

            <label className="camera-button">
              📷 Take a Photo
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleImageChange}
                hidden
              />
            </label>

            <label className="upload-area">
              {preview ? (
                <div className="image-preview-wrapper">
                  <img
                    src={preview}
                    alt="Uploaded ingredients"
                    className="image-preview"
                  />

                  <div className="change-image">
                    Change image
                  </div>
                </div>
              ) : (
                <div className="upload-content">
                  <div className="upload-icon">📷</div>

                  <h3>Upload your ingredients</h3>

                  <p>
                    Take a clear photo of your fridge,
                    pantry, or ingredients.
                  </p>

                  <span className="upload-button">
                    Choose image
                  </span>
                </div>
              )}

              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                hidden
              />
            </label>
          </div>

          <div className="panel">
            <div className="section-heading">
              <div>
                <p className="section-label">02</p>
                <h2>Your preferences</h2>
              </div>
            </div>

            <div className="form-grid">
              <div className="field">
                <label>Diet</label>

                <select
                  value={diet}
                  onChange={(e) => setDiet(e.target.value)}
                >
                  <option value="vegetarian">
                    Vegetarian
                  </option>

                  <option value="non-vegetarian">
                    Non-vegetarian
                  </option>

                  <option value="vegan">
                    Vegan
                  </option>
                </select>
              </div>

              <div className="field">
                <label>Maximum cooking time</label>

                <div className="input-with-unit">
                  <input
                    type="number"
                    min="1"
                    placeholder="25"
                    value={maxCookingTime}
                    onChange={(e) =>
                      setMaxCookingTime(e.target.value)
                    }
                  />

                  <span>min</span>
                </div>
              </div>

              <div className="field">
                <label>Allergies</label>

                <input
                  type="text"
                  placeholder="e.g. peanuts, paneer"
                  value={allergies}
                  onChange={(e) =>
                    setAllergies(e.target.value)
                  }
                />
              </div>

              <div className="field">
                <label>Foods to avoid</label>

                <input
                  type="text"
                  placeholder="e.g. very spicy"
                  value={avoid}
                  onChange={(e) =>
                    setAvoid(e.target.value)
                  }
                />
              </div>

              <div className="field full-width">
                <label>Cuisine</label>

                <input
                  type="text"
                  placeholder="e.g. Indian, Italian, Mexican"
                  value={cuisine}
                  onChange={(e) =>
                    setCuisine(e.target.value)
                  }
                />
              </div>
            </div>

            {error && (
              <div className="error">
                <span>⚠</span>
                {error}
              </div>
            )}

            <button
              className="generate-button"
              onClick={generateRecipes}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Creating recipes...
                </>
              ) : (
                <>
                  ✨ Generate Recipes
                </>
              )}
            </button>
          </div>
        </section>

        {recipes.length > 0 && (
          <section className="results">
            <div className="results-heading">
              <div>
                <p className="section-label">03</p>

                <h2>Your recipes</h2>

                <p>
                  PantryChef found {recipes.length} recipe
                  {recipes.length !== 1 ? "s" : ""} for you.
                </p>
              </div>
            </div>

            <div className="recipe-grid">
              {recipes.map((recipe, index) => (
                <RecipeCard
                  key={`${recipe.name}-${index}`}
                  recipe={recipe}
                  index={index}
                  onSave={handleSaveRecipe}
                />
              ))}
            </div>
          </section>
        )}
        </> 
        )}        
      </main>

      <footer>
        <span>PantryChef</span>
        <span>Powered by AI</span>
      </footer>
    </div>
    
  );
}

function RecipeCard({ recipe, index, onSave, onDelete, isSaved = false }) {
  const [saved, setSaved] = useState(isSaved);

  async function handleSave() {
    try {
      await onSave(recipe);
      setSaved(true);
    } catch (error) {
      console.error("Save failed:", error);
    }
    }
  return (
    <article className="recipe-card">
      <div className="recipe-number">
        0{index + 1}
      </div>

      <div className="recipe-top">
        <h3>{recipe.name}</h3>

        <div className="recipe-meta">
          <span>⏱ {recipe.cooking_time_minutes} min</span>
          <span>{recipe.difficulty}</span>
        </div>
      </div>

      <div className="recipe-section">
        <h4>✓ You have</h4>

        <div className="ingredient-list">
          {recipe.available_ingredients?.map(
            (ingredient, index) => (
              <span key={index} className="ingredient available">
                {ingredient}
              </span>
            )
          )}
        </div>
      </div>

      {recipe.missing_ingredients?.length > 0 && (
        <div className="recipe-section">
          <h4>＋ You'll need</h4>

          <div className="ingredient-list">
            {recipe.missing_ingredients.map(
              (ingredient, index) => (
                <span
                  key={index}
                  className="ingredient missing"
                >
                  {ingredient}
                </span>
              )
            )}
          </div>
        </div>
      )}

      <div className="recipe-section">
        <h4>Ingredients</h4>

        <ul className="quantity-list">
          {recipe.ingredients?.map((ingredient, index) => (
            <li key={index}>
              <span>{ingredient.name}</span>
              <strong>{ingredient.quantity}</strong>
            </li>
          ))}
        </ul>
      </div>

      <div className="recipe-section">
        <h4>Method</h4>

        <ol className="steps">
          {recipe.steps?.map((step, index) => (
            <li key={index}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
      </div>
        <button
          className={`save-recipe-button ${saved ? "saved" : ""}`}
          onClick={handleSave}
          disabled={saved}
        >
          {saved ? "♥ Saved" : "♡ Save Recipe"}
        </button>
      {isSaved && (
        <button
          className="delete-recipe-button"
          onClick={() => onDelete()}
        >
          Delete Recipe
        </button>
      )}
    </article>
  );
}

export default App;