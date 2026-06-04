// MOCK_MODE=true
import { store } from "../store/state.js";
import { login } from "../services/auth-service.js";
import { AUTH_MODE, DATA_MODE, SAFETY_DISCLAIMER } from "../constants.js";
import { mockUsers } from "../store/mock-data.js";
import { iconSvg } from "../components/icons.js";

export function renderLogin() {
  return `
    <div class="login-layout-wrapper">
      <div class="login-glass-container">
        <div class="login-brand-info">
          <h2>asd-Project</h2>
          <p class="brand-sub">Research prototype for extracting speech-language features to support ASD clinical assessment.</p>
          <div class="safety-warning-badge">${iconSvg.shield}<span>Clinical Decision-Support Only</span></div>
          <p class="safety-disclaimer-text">${SAFETY_DISCLAIMER}</p>
        </div>
        <div class="login-form-area">
          <h4>Welcome Back</h4>
          <p class="login-subtitle">Please sign in to access your clinic dashboard.</p>
          
          <p id="login-error" class="form-error" hidden>Demo login failed. Use one of the sample accounts.</p>
          
          <form id="login-form" class="login-input-grid">
            <div class="input-field-group">
              <label for="login-email">Username / Email</label>
              <input type="email" id="login-email" class="glass-input" value="therapist@example.test" required>
            </div>
            <div class="input-field-group">
              <label for="login-password">Password</label>
              <input type="password" id="login-password" class="glass-input" value="demo-password" required>
            </div>
            <button type="submit" class="btn-submit-primary">Sign In</button>
          </form>

          <div class="demo-accounts-section">
            <h5>Demo Accounts</h5>
            <div class="demo-accounts-grid">
              ${mockUsers.map(user => `
                <button type="button" class="credential-row" data-email="${user.email}">
                  <strong>${user.role}</strong>
                  <span>${user.email}</span>
                </button>
              `).join("")}
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function bindLogin(onSuccess) {
  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("login-email").value;
      const pass = document.getElementById("login-password").value;
      try {
        const user = await login(email, pass);
        if (user) {
          onSuccess();
        } else {
          const err = document.getElementById("login-error");
          if (err) {
            err.textContent = store.getState().authError || "Demo login failed. Use one of the sample accounts.";
            err.removeAttribute("hidden");
          }
        }
      } catch (err) {
        const errorEl = document.getElementById("login-error");
        if (errorEl) {
          errorEl.textContent = store.getState().authError || `Failed to sign in: ${err.message || err}`;
          errorEl.removeAttribute("hidden");
        }
      }
    });
  }

  // Credential autofill clicking
  const rows = document.querySelectorAll(".credential-row");
  rows.forEach(row => {
    row.addEventListener("click", () => {
      const email = row.getAttribute("data-email");
      const emailInput = document.getElementById("login-email");
      if (emailInput) {
        emailInput.value = email;
      }
    });
  });
}
