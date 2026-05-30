/**
 * Parse FastAPI error bodies into actionable messages for the UI.
 */

export function parseApiError(
  body: unknown,
  fallback = "Request failed"
): string {
  if (body == null) return fallback;
  if (typeof body === "string") return body;

  const record = body as Record<string, unknown>;
  const detail = record.detail;

  if (typeof detail === "string") return detail;

  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    const message = String(d.message ?? d.error ?? fallback);
    const hint = d.hint ? String(d.hint) : "";
    return hint ? `${message} — ${hint}` : message;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    return first?.msg ?? fallback;
  }

  if (typeof record.message === "string") return record.message;
  return fallback;
}
