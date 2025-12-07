import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", className = "", ...rest }: Props) {
  const base = "rounded px-3 py-2 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed";
  const styles =
    variant === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-800"
      : "bg-white text-slate-800 border border-slate-300 hover:bg-slate-100";
  return <button className={`${base} ${styles} ${className}`} {...rest} />;
}
