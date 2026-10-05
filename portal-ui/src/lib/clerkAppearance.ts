/**
 * Theming for Clerk's prebuilt components so they match the portal's
 * orange (#FF5A1F) / Plus Jakarta Sans / pill-button design system
 * (see src/index.css for the source tokens). Typed loosely because
 * `@clerk/react`'s `Appearance` type isn't re-exported as a standalone
 * import; the shape is still validated structurally by each component's
 * `appearance` prop at the call site.
 */
export const clerkAppearance = {
  variables: {
    colorPrimary: "#ff5a1f",
    colorText: "#1a1410",
    colorTextSecondary: "#6b6058",
    colorBackground: "#ffffff",
    colorInputBackground: "#ffffff",
    colorInputText: "#1a1410",
    fontFamily: '"Plus Jakarta Sans", "Segoe UI", system-ui, -apple-system, sans-serif',
    borderRadius: "999px",
  },
  elements: {
    card: {
      boxShadow: "none",
      border: "none",
      padding: 0,
    },
    headerTitle: {
      display: "none",
    },
    headerSubtitle: {
      display: "none",
    },
    formButtonPrimary: {
      borderRadius: "999px",
      textTransform: "none",
      fontSize: "15px",
      "&:hover": {
        backgroundColor: "#e64f19",
      },
    },
    socialButtonsBlockButton: {
      borderRadius: "999px",
      borderColor: "#ece2d8",
    },
    formFieldInput: {
      borderRadius: "12px",
      borderColor: "#ece2d8",
    },
    footerActionLink: {
      color: "#ff5a1f",
    },
  },
};
