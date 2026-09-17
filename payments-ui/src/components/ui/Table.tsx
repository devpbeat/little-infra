import type { PropsWithChildren } from "react";
import "./Table.css";

export function Table({ children }: PropsWithChildren) {
  return (
    <div className="table-wrap">
      <table className="table">{children}</table>
    </div>
  );
}
