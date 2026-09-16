import type { HTMLAttributes } from "react";
import "./Card.css";

type CardProps = HTMLAttributes<HTMLDivElement>;

export function Card({ children, className, ...rest }: CardProps) {
  return (
    <div className={["card", className].filter(Boolean).join(" ")} {...rest}>
      {children}
    </div>
  );
}
