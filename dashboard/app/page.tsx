import { redirect } from "next/navigation";

/**
 * Home redirects to the main product surface (dashboard).
 * The landing-page analyzer has been removed in favor of the agent marketplace.
 */
export default function HomePage() {
  redirect("/dashboard");
}
