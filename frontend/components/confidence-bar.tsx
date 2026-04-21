import { cn } from "@/lib/utils";

type ConfidenceBarProps = {
  value: number;
};

export function ConfidenceBar({ value }: ConfidenceBarProps) {
  const percent = Math.round(value * 100);
  const tone =
    percent >= 85
      ? "bg-secondary"
      : percent >= 70
        ? "bg-accent"
        : "bg-destructive";

  return (
    <div className="flex min-w-28 items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${percent}%` }} />
      </div>
      <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">
        {percent}%
      </span>
    </div>
  );
}
