// MOCK_MODE=true
import { store } from "../store/state.js";
import { login, signUp } from "../services/auth-service.js";
import { AUTH_MODE, DATA_MODE, SAFETY_DISCLAIMER } from "../constants.js";
import { mockUsers } from "../store/mock-data.js";
import { iconSvg } from "../components/icons.js";

export function renderLogin() {
  const state = store.getState();
  const viewMode = state.authViewMode || "login";
  const authError = state.authError || "";
  
  const loginFormHtml = `
    <h4>Welcome Back</h4>
    <p class="login-subtitle">Please sign in to access your clinic workspace.</p>
    
    <p id="login-error" class="form-error" ${authError ? "" : "hidden"}>${authError || "Demo login failed. Check email or password."}</p>
    
    <form id="login-form" class="login-input-grid">
      <div class="input-field-group">
        <label for="login-email">Username / Email</label>
        <input type="email" id="login-email" class="glass-input" value="therapist@example.test" required placeholder="therapist@example.test">
      </div>
      <div class="input-field-group">
        <label for="login-password">Password</label>
        <input type="password" id="login-password" class="glass-input" value="demo-password" required placeholder="••••••••">
      </div>
      <button type="submit" class="btn-submit-primary">Sign In</button>
    </form>
    
    <div style="margin-top: 16px; text-align: center;">
      <a href="#" id="toggle-auth-view" style="color: var(--primary); font-size: 0.85rem; font-weight: 500; text-decoration: none;">Don't have an account? Register</a>
    </div>

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
  `;

  const registerFormHtml = `
    <h4>Create Workspace Account</h4>
    <p class="login-subtitle">Register a new speech therapist or clinician account.</p>
    
    <p id="login-error" class="form-error" ${authError ? "" : "hidden"}>${authError}</p>
    <p id="login-success" class="form-success" style="color: var(--success); font-weight: 600; font-size: 0.85rem;" hidden>Registration successful! You can now log in.</p>
    
    <form id="register-form" class="login-input-grid" style="display: flex; flex-direction: column; gap: 12px;">
      <div class="input-field-group">
        <label for="reg-name">Full Name</label>
        <input type="text" id="reg-name" class="glass-input" required placeholder="Therapist Name">
      </div>
      <div class="input-field-group">
        <label for="reg-email">Email Address</label>
        <input type="email" id="reg-email" class="glass-input" required placeholder="therapist@example.com">
      </div>
      <div class="input-field-group">
        <label for="reg-password">Password</label>
        <input type="password" id="reg-password" class="glass-input" required minlength="6" placeholder="••••••••">
      </div>
      <div class="input-field-group">
        <label for="reg-role">Clinical Role</label>
        <select id="reg-role" class="glass-input" required>
          <option value="therapist">Speech Therapist / Clinician</option>
          <option value="clinician">MD Clinician</option>
          <option value="admin">Administrator (Audit View)</option>
        </select>
      </div>
      <div class="input-field-group">
        <label for="reg-org">Organization / Clinic</label>
        <input type="text" id="reg-org" class="glass-input" required placeholder="Speech Therapy Lab">
      </div>
      <button type="submit" class="btn-submit-primary">Register Account</button>
    </form>
    
    <div style="margin-top: 16px; text-align: center;">
      <a href="#" id="toggle-auth-view" style="color: var(--primary); font-size: 0.85rem; font-weight: 500; text-decoration: none;">Already have an account? Sign In</a>
    </div>
  `;

  return `
    <div class="login-layout-wrapper">
      <div class="login-glass-container">
        <div class="login-brand-info">
          <h2>Clinical Workspace</h2>
          <p class="brand-sub">Secure clinical decision-support portal for speech therapists and session observations analysis.</p>
          <div class="safety-warning-badge">${iconSvg.shield || ""}<span>Clinical Decision-Support Only</span></div>
          <p class="safety-disclaimer-text">${SAFETY_DISCLAIMER}</p>
        </div>
        <div class="login-form-area">
          ${viewMode === "login" ? loginFormHtml : registerFormHtml}
        </div>
      </div>
    </div>
  `;
}

export function bindLogin(onSuccess) {
  const toggleLink = document.getElementById("toggle-auth-view");
  if (toggleLink) {
    toggleLink.addEventListener("click", (e) => {
      e.preventDefault();
      const currentMode = store.getState().authViewMode || "login";
      const nextMode = currentMode === "login" ? "register" : "login";
      store.setState({ authViewMode: nextMode, authError: "" });
      
      const root = document.getElementById("app");
      if (root) {
        root.innerHTML = renderLogin();
        bindLogin(onSuccess);
      }
    });
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
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
            err.textContent = store.getState().authError || "Demo login failed. Check email or use a sample account.";
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

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("reg-name").value;
      const email = document.getElementById("reg-email").value;
      const pass = document.getElementById("reg-password").value;
      const role = document.getElementById("reg-role").value;
      const org = document.getElementById("reg-org").value;

      try {
        const user = await signUp(email, pass, name, role, org);
        if (user) {
          const successEl = document.getElementById("login-success");
          if (successEl) successEl.removeAttribute("hidden");
          setTimeout(() => {
            store.setState({ authViewMode: "login", authError: "" });
            const root = document.getElementById("app");
            if (root) {
              root.innerHTML = renderLogin();
              bindLogin(onSuccess);
            }
          }, 1500);
        } else {
          const err = document.getElementById("login-error");
          if (err) {
            err.textContent = store.getState().authError || "Registration failed. Try a different email.";
            err.removeAttribute("hidden");
          }
        }
      } catch (err) {
        const errorEl = document.getElementById("login-error");
        if (errorEl) {
          errorEl.textContent = store.getState().authError || `Failed to register: ${err.message || err}`;
          errorEl.removeAttribute("hidden");
        }
      }
    });
  }

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
