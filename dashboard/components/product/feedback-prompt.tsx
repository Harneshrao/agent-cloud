"use client";

import { useState } from "react";
import { MessageSquare, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { submitProductFeedback } from "@/lib/analytics";

const DISMISS_KEY = "agent_cloud_feedback_dismissed";

export function FeedbackPrompt({
  context,
  title = "How was this step?",
}: {
  context: string;
  title?: string;
}) {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);

  if (typeof window !== "undefined" && localStorage.getItem(`${DISMISS_KEY}_${context}`)) {
    return null;
  }

  if (sent) {
    return (
      <p className="text-center text-sm text-neutral-400">Thanks — your feedback helps us improve.</p>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mx-auto flex items-center gap-2 text-sm text-neutral-500 hover:text-primary"
      >
        <MessageSquare className="h-4 w-4" />
        Share quick feedback
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <button
          type="button"
          className="text-neutral-500 hover:text-foreground"
          aria-label="Dismiss"
          onClick={() => {
            localStorage.setItem(`${DISMISS_KEY}_${context}`, "1");
            setOpen(false);
          }}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-3 flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => setRating(n)}
            className={`h-9 w-9 rounded-lg text-sm font-medium ${
              rating === n
                ? "bg-primary text-primary-foreground"
                : "bg-white/5 text-neutral-400 hover:bg-white/10"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <textarea
        className="mt-3 w-full rounded-lg border border-white/10 bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-neutral-500"
        rows={2}
        placeholder="Optional — what was confusing or painful?"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />
      <Button
        type="button"
        size="sm"
        className="mt-3"
        disabled={rating < 1}
        onClick={() => {
          submitProductFeedback(rating, comment, context);
          setSent(true);
          localStorage.setItem(`${DISMISS_KEY}_${context}`, "1");
        }}
      >
        Send feedback
      </Button>
    </div>
  );
}
