"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { submitUserResearchSession } from "@/lib/analytics";

const DISMISS_KEY = "agent_cloud_user_research_done";

/**
 * End-of-session PMF capture — shown after first API key (First 5 users flow).
 */
export function UserResearchPrompt() {
  const [clarity, setClarity] = useState(0);
  const [wouldUseAgain, setWouldUseAgain] = useState(0);
  const [neededHelp, setNeededHelp] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);

  if (typeof window !== "undefined" && localStorage.getItem(DISMISS_KEY)) {
    return null;
  }

  if (sent) {
    return (
      <p className="text-center text-sm text-neutral-400">
        Thanks — this directly shapes what we fix next.
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-6">
      <p className="text-sm font-medium text-foreground">Quick session feedback (~30 sec)</p>
      <p className="mt-1 text-xs text-neutral-500">
        You finished the core loop — help us know if it actually worked for you.
      </p>

      <div className="mt-4 space-y-4">
        <div>
          <p className="text-xs font-medium text-neutral-400">Was the flow clear?</p>
          <div className="mt-2 flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <RatingDot key={n} value={n} selected={clarity} onSelect={setClarity} />
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-neutral-400">Would you use Agent Cloud again?</p>
          <div className="mt-2 flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <RatingDot key={n} value={n} selected={wouldUseAgain} onSelect={setWouldUseAgain} />
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-neutral-400">Did you need help from us?</p>
          <div className="mt-2 flex gap-2">
            <Button
              type="button"
              size="sm"
              variant={neededHelp === false ? "default" : "outline"}
              onClick={() => setNeededHelp(false)}
            >
              No
            </Button>
            <Button
              type="button"
              size="sm"
              variant={neededHelp === true ? "default" : "outline"}
              onClick={() => setNeededHelp(true)}
            >
              Yes
            </Button>
          </div>
        </div>

        <textarea
          className="w-full rounded-lg border border-white/10 bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-neutral-500"
          rows={2}
          placeholder="Optional — what was confusing or broke trust?"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />

        <Button
          type="button"
          size="sm"
          disabled={clarity < 1 || wouldUseAgain < 1 || neededHelp === null}
          onClick={() => {
            submitUserResearchSession({
              clarity_rating: clarity,
              would_use_again: wouldUseAgain,
              needed_help: neededHelp,
              comment,
            });
            setSent(true);
            localStorage.setItem(DISMISS_KEY, "1");
          }}
        >
          Submit feedback
        </Button>
      </div>
    </div>
  );
}

function RatingDot({
  value,
  selected,
  onSelect,
}: {
  value: number;
  selected: number;
  onSelect: (n: number) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`h-9 w-9 rounded-lg text-sm font-medium ${
        selected === value
          ? "bg-primary text-primary-foreground"
          : "bg-white/5 text-neutral-400 hover:bg-white/10"
      }`}
    >
      {value}
    </button>
  );
}
