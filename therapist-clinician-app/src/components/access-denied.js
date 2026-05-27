import { ACCESS_DENIED_MESSAGE } from "../services/auth-adapter.js";

export function renderAccessDenied(message = ACCESS_DENIED_MESSAGE) {
  return `
    <section class="panel" style="padding: 16px;">
      <div class="panel-title">
        <h3>Access denied</h3>
        <span>role-based access control</span>
      </div>
      <p class="empty-state">${message}</p>
    </section>
  `;
}
