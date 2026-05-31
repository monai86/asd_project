import { store } from "../store/state.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderAccessDenied } from "../components/access-denied.js";
import { canViewAuditLogs } from "../services/auth-service.js";

export function renderAuditLogs() {
  const { auditLogs, currentUser } = store.getState();

  if (!canViewAuditLogs(currentUser)) {
    return `
      ${renderSafetyBanner()}
      ${renderAccessDenied("Access denied: audit logs are available to admin users only.")}
    `;
  }
  const visibleLogs = currentUser?.role === "admin" ? auditLogs : [];

  return `
    ${renderSafetyBanner()}
    <section class="panel" style="padding: 16px;">
      <div class="panel-title">
        <h3>Audit Logs</h3>
        <span>security and data flow audits</span>
      </div>
      <div style="max-height: 500px; overflow-y: auto; display: grid; gap: 8px;">
        ${visibleLogs
          .map(
            log => `
          <div style="padding: 10px; border-bottom: 1px solid var(--line); font-size: 0.85rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <strong style="color: var(--violet);">${log.event_type}</strong>
              <span style="color: var(--muted);">${new Date(log.created_at).toLocaleString()}</span>
            </div>
            <div><strong>Actor:</strong> ${log.actor_user_id} · <strong>Target:</strong> ${log.target_type} (${log.target_id})</div>
            <div style="margin-top: 4px; color: var(--ink);">${log.message}</div>
          </div>
        `
          )
          .join("")}
        ${visibleLogs.length === 0 ? '<p class="empty-state">No audit logs recorded yet.</p>' : ""}
      </div>
    </section>
  `;
}

export function bindAuditLogs(navigate) {
  // No interactive bindings needed for read-only audit log view
}
