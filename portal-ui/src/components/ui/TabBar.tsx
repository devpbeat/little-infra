import "./TabBar.css";

export interface TabBarItem {
  label: string;
  icon: string;
  active?: boolean;
  onSelect?: () => void;
}

interface TabBarProps {
  items: TabBarItem[];
}

export function TabBar({ items }: TabBarProps) {
  return (
    <nav className="tab-bar" aria-label="Primary">
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          className={["tab-bar-item", item.active ? "active" : ""].filter(Boolean).join(" ")}
          onClick={item.onSelect}
        >
          <span className="tab-bar-icon" aria-hidden="true">
            {item.icon}
          </span>
          <span className="tab-bar-label">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
