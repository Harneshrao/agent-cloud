"use client";

import { useState } from "react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RunAgentModal } from "@/components/run-agent-modal";
import type { AgentStoreItem } from "@/types";
import { Bot } from "lucide-react";

interface AgentCardProps {
  agent: AgentStoreItem;
}

export function AgentCard({ agent }: AgentCardProps) {
  const [modalOpen, setModalOpen] = useState(false);

  const capabilities = Array.isArray(agent.capabilities)
    ? agent.capabilities
    : [];

  return (
    <>
      <Card className="flex flex-col transition-all duration-300 hover:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.5)]">
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-accent/10 p-2.5 text-accent">
              <Bot className="h-5 w-5" />
            </span>
            <div>
              <h3 className="font-semibold text-foreground">{agent.name}</h3>
              <p className="text-xs text-neutral-500">v{agent.version}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex-1">
          <p className="text-sm text-neutral-400 line-clamp-2">
            {agent.description || "No description"}
          </p>
          {capabilities.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {capabilities.slice(0, 5).map((cap) => (
                <span
                  key={cap}
                  className="rounded-lg bg-white/5 px-2 py-0.5 text-xs text-neutral-400"
                >
                  {cap}
                </span>
              ))}
            </div>
          )}
        </CardContent>
        <CardFooter>
          <Button
            className="w-full"
            onClick={() => setModalOpen(true)}
          >
            Run agent
          </Button>
        </CardFooter>
      </Card>
      <RunAgentModal
        agent={agent}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </>
  );
}
