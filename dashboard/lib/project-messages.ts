export const NO_PROJECT_MESSAGE =
  "Choose a project first — use the dropdown at the top of the page, or create one on Projects.";

export function isProjectContextError(message: string): boolean {
  const m = message.toLowerCase();
  return (
    m.includes("project context") ||
    m.includes("x-project-id") ||
    m.includes("select a project")
  );
}

export function friendlyApiError(message: string): string {
  if (isProjectContextError(message)) return NO_PROJECT_MESSAGE;
  return message;
}
