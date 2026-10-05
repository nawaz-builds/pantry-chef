import { useState } from "react";
import { login, register, getCurrentUser } from "./api";

function Login({ onLogin }) {
  const [mode, setMode] = useState("login");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    setSuccess("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (mode === "register") {
        if (password !== confirmPassword) {
          setError("Passwords do not match.");
          return;
        }

        const data = await register(email, password);

        if (data.error) {
          setError(data.error);
          return;
        }

        setSuccess("Account created successfully. You can now log in.");

        setMode("login");
        setPassword("");
        setConfirmPassword("");

        return;
      }

      const data = await login(email, password);

      if (data.error) {
        setError(data.error);
        return;
      }

      const user = await getCurrentUser();

      if (user.email) {
        onLogin(user);
      } else {
        setError("Login succeeded, but user verification failed.");
      }
    } catch (error) {
      console.error(error);
      setError("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <div className="auth-page">

      {/* Left branding section */}
      <section className="auth-showcase">
        <div className="auth-brand">
          <div className="auth-brand-icon">🍳</div>
          <span>PantryChef</span>
        </div>

        <div className="showcase-content">
          <span className="showcase-label">YOUR PERSONAL AI CHEF</span>

          <h1>
            Cook with
            <br />
            what you
            <br />
            <span>already have.</span>
          </h1>

          <p>
            Turn the ingredients sitting in your kitchen into
            delicious recipes with the help of AI.
          </p>

          <div className="feature-list">
            <div className="feature-item">
              <div className="feature-icon">📷</div>
              <div>
                <strong>Scan ingredients</strong>
                <span>Let AI identify what's in your kitchen.</span>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon">✨</div>
              <div>
                <strong>Get AI recipes</strong>
                <span>Recipes built around what you already have.</span>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon">🥕</div>
              <div>
                <strong>Waste less food</strong>
                <span>Make better use of the ingredients you buy.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="showcase-footer">
          Powered by AI • Built for everyday cooking
        </div>
      </section>


      {/* Login/Register section */}
      <section className="auth-section">
        <div className="auth-card">

          <div className="mobile-brand">
            <div className="auth-brand-icon">🍳</div>
            <span>PantryChef</span>
          </div>

          <div className="auth-heading">
            <h2>
              {isRegister ? "Create your account" : "Welcome back"}
            </h2>

            <p>
              {isRegister
                ? "Start turning your ingredients into recipes."
                : "Log in to continue cooking smarter."}
            </p>
          </div>

          <form onSubmit={handleSubmit}>

            <div className="input-group">
              <label htmlFor="email">Email</label>

              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>


            <div className="input-group">
              <label htmlFor="password">Password</label>

              <input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>


            {isRegister && (
              <div className="input-group">
                <label htmlFor="confirm-password">
                  Confirm password
                </label>

                <input
                  id="confirm-password"
                  type="password"
                  placeholder="Enter your password again"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            )}


            {error && (
              <div className="auth-message error-message">
                {error}
              </div>
            )}

            {success && (
              <div className="auth-message success-message">
                {success}
              </div>
            )}


            <button
              className="auth-submit"
              type="submit"
              disabled={loading}
            >
              {loading
                ? isRegister
                  ? "Creating account..."
                  : "Logging in..."
                : isRegister
                  ? "Create account"
                  : "Log in"}
            </button>

          </form>


          <div className="auth-divider">
            <span>OR</span>
          </div>


          <div className="auth-switch">
            {isRegister ? (
              <>
                Already have an account?
                <button
                  type="button"
                  onClick={() => switchMode("login")}
                >
                  Log in
                </button>
              </>
            ) : (
              <>
                Don't have an account?
                <button
                  type="button"
                  onClick={() => switchMode("register")}
                >
                  Create one
                </button>
              </>
            )}
          </div>

        </div>
      </section>

    </div>
  );
}

export default Login;