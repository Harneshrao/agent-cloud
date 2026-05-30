import { redirect } from "next/navigation";

/**
 * Home redirects to the primary wedge surface (projects).
 */
export default function HomePage() {
  redirect("/projects");
}
