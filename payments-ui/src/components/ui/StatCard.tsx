import { Card } from "./Card";
import "./StatCard.css";

interface StatCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaTone?: "positive" | "neutral";
}

export function StatCard({ label, value, delta, deltaTone = "positive" }: StatCardProps) {
  return (
    <Card className="stat-card">
      <h3>{label}</h3>
      <div className="stat-card-value">{value}</div>
      {delta && <div className={`stat-card-delta stat-card-delta-${deltaTone}`}>{delta}</div>}
    </Card>
  );
}
