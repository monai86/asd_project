import { store } from "../store/state.js";
import { login } from "../services/auth-service.js";
import { SAFETY_DISCLAIMER } from "../constants.js";
import { mockUsers } from "../store/mock-data.js";

export function renderLogin() {
  return `
    <main class="login-layout">
      <section class="login-panel">
        <div class="product-mark">ap</div>
        <p class="eyebrow">MOCK_MODE=true</p>
        <h1>Speech Therapist Prototype</h1>
        <p class="lead">A focused workspace for therapists and clinicians to manage anonymized child cases, review speech sessions, and track progress with decision-support outputs.</p>
        <div class="safety-banner">${SAFETY_DISCLAIMER}</div>
        <form id="login-form" class="form-grid">
          <label>Email <input name="email" type="email" id="login-email" value="therapist@example.test" autocomplete="username" /></label>
          <label>Password <input name="password" type="password" id="login-password" value="demo-password" autocomplete="current-password" /></label>
          <button class="primary-action" type="submit">Log in</button>
        </form>
        <p id="login-error" class="form-error" hidden>Mock login failed. Use one of the sample accounts.</p>
      </section>
      <aside class="credential-panel">
        <h2>Sample Accounts</h2>
        ${mockUsers.map(user => `
          <button class="credential-row" data-email="${user.email}">
            <span>${user.role}</span>
            <strong>${user.email}</strong>
            <small>demo-password</small>
          </button>
        `).join("")}
      </aside>
    </main>
  `;
}

export function bindLogin(onSuccess) {
  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = document.getElementById("login-email").value;
      const pass = document.getElementById("login-password").value;
      const user = login(email, pass);
      if (user) {
        onSuccess();
      } else {
        const err = document.getElementById("login-error");
        if (err) err.removeAttribute("hidden");
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
