interface FlameLogoProps {
  size?: number;
  withWordmark?: boolean;
}

/**
 * Ignite Solutions brand mark: a stylized flame in a rounded orange tile.
 * `withWordmark` also renders the "Ignite Solutions" text next to it.
 */
export function FlameLogo({ size = 36, withWordmark = true }: FlameLogoProps) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <svg width={size} height={size} viewBox="0 0 36 36" fill="none" aria-hidden="true">
        <rect width="36" height="36" rx="10" fill="#FF5A1F" />
        <path
          d="M18 5c2.2 4.5-3 6.8-3 11.2 0 3 2.2 4.5 4.5 4.5 3 0 5.2-2.2 5.2-5.2 0-2.2-1.5-3.7-1.5-3.7.7 3.7-.7 6-3 6-1.1 0-2.2-1.1-2.2-2.2 0-3 3.7-4.5 3.7-9-2.2 0-3 1.1-3.7 -1.6z"
          fill="#FFFFFF"
        />
        <path
          d="M15 22c0 3 1.5 5.2 4.5 5.2S24 25 24 22.7c0-1.5-.7-2.2-.7-2.2 0 1.5-.7 3-2.2 3-1.1 0-1.9-.7-1.9-1.9 0-1.5 1.5-2.2 1.5-4.5-2.2.7-5.7 2.2-5.7 4.9z"
          fill="#FFE3D3"
        />
      </svg>
      {withWordmark && (
        <span style={{ fontWeight: 800, fontSize: 17, letterSpacing: "-0.01em" }}>Ignite Solutions</span>
      )}
    </span>
  );
}
