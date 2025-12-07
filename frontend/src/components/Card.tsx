import type { PropsWithChildren } from "react";

export function Card({ title, children }: PropsWithChildren<{ title?: string }>) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      {title && <div className="mb-2 text-sm font-semibold text-slate-700">{title}</div>}
      <div>{children}</div>
    </div>
  );
}
