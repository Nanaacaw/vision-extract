"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

type TabsProps = {
  tabs: string[];
  value: string;
  onValueChange: (value: string) => void;
};

export function Tabs({ tabs, value, onValueChange }: TabsProps) {
  return (
    <div className="inline-flex rounded-md border bg-muted p-1">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onValueChange(tab)}
          className={cn(
            "min-h-10 rounded-sm px-3 text-sm font-medium text-muted-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            value === tab && "bg-card text-foreground shadow-sm",
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
