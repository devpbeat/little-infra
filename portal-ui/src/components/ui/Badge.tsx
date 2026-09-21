import type { HTMLAttributes } from "react";
import "./Badge.css";

export type BadgeTone = "accent" | "neutral" | "success";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ tone = "neutral", className, ...rest }: BadgeProps) {
  return <span className={["badge", `badge-${tone}`, className].filter(Boolean).join(" ")} {...rest} />;
}
