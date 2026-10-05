const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function login(email, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    credentials: "include",
    body: new URLSearchParams({
      email,
      password,
    }),
  });

  return response.json();
}

export async function register(email, password) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      email,
      password,
    }),
  });

  return response.json();
}

export async function getCurrentUser() {
  const response = await fetch(`${API_URL}/auth/me`, {
    credentials: "include",
  });

  return response.json();
}

export async function logout() {
  const response = await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  return response.json();
}


export async function saveRecipe(recipe) {
  const response = await fetch("http://localhost:8000/recipes/save", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(recipe),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Failed to save recipe");
  }

  return data;
}



export async function getSavedRecipes() {
  const response = await fetch("http://localhost:8000/recipes/saved", {
    method: "GET",
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Failed to load saved recipes");
  }

  return data;
}



export async function deleteSavedRecipe(recipeId) {
  const response = await fetch(
    `http://localhost:8000/recipes/saved/${recipeId}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Failed to delete recipe");
  }

  return data;
}