import { redirect } from "next/navigation";

/** Logs live on the execution trace — one list entry point via Runs. */
export default function LogsPage() {
  redirect("/runs");
}
