import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";
import { Link, type LinkProps } from "react-router-dom";
import "./Button.css";

interface ButtonOwnProps {
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "sm";
  /** Renders as a react-router <Link> instead of a <button>. Accepts the same `state` prop as Link. */
  to?: LinkProps["to"];
  state?: LinkProps["state"];
  /** Renders as a plain <a> instead of a <button>. */
  href?: string;
}

type ButtonAsButtonProps = ButtonOwnProps & ButtonHTMLAttributes<HTMLButtonElement>;
type ButtonAsAnchorProps = ButtonOwnProps & AnchorHTMLAttributes<HTMLAnchorElement>;

type ButtonProps = ButtonAsButtonProps | ButtonAsAnchorProps;

export function Button({ variant = "primary", size = "md", className, to, state, href, ...rest }: ButtonProps) {
  const classes = ["btn", `btn-${variant}`, `btn-${size}`, className].filter(Boolean).join(" ");

  if (to !== undefined) {
    return <Link to={to} state={state} className={classes} {...(rest as AnchorHTMLAttributes<HTMLAnchorElement>)} />;
  }

  if (href !== undefined) {
    return <a href={href} className={classes} {...(rest as AnchorHTMLAttributes<HTMLAnchorElement>)} />;
  }

  return <button className={classes} {...(rest as ButtonHTMLAttributes<HTMLButtonElement>)} />;
}
