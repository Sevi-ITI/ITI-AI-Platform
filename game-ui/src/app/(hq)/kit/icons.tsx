// Small line icons for the console (inline SVG, no icon package). Decorative: the text next to each
// icon (or the button's aria-label) carries the meaning.

type IconProps = { d: string; size?: number };

function Icon({ d, size = 18 }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

export const OverviewIcon = () => <Icon d="M4 4h7v7H4z M13 4h7v4h-7z M13 10h7v10h-7z M4 13h7v7H4z" />;
export const PerformanceIcon = () => <Icon d="M4 4v16h16 M7 15l4-5 3 3 5-6" />;
export const RequestLogIcon = () => <Icon d="M9 6h11 M9 12h11 M9 18h11 M4.5 6h.01 M4.5 12h.01 M4.5 18h.01" />;
export const UsersIcon = () => <Icon d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21c0-4 3-6 7-6s7 2 7 6 M16 3.5a4 4 0 0 1 0 7.5 M18 15c2.5.6 4 2.6 4 6" />;
export const DocumentsIcon = () => <Icon d="M14 3H6v18h12V7z M14 3v4h4 M9 12h6 M9 16h6" />;
export const KeysIcon = () => <Icon d="M8 19a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M11 12l9-9 M16 7l3 3" />;
export const ChatIcon = () => <Icon d="M4 5h16v11H9l-5 4z" />;
export const AccountsIcon = () => <Icon d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z M9 12l2 2 4-4" />;
export const ToolsIcon = () => <Icon d="M14.5 5.5a4 4 0 0 0-5 5L4 16l4 4 5.5-5.5a4 4 0 0 0 5-5l-2.5 2.5-2.5-.5-.5-2.5z" />;
export const SunIcon = () => (
  <Icon d="M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4" />
);
export const MoonIcon = () => <Icon d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />;
export const LogOutIcon = () => <Icon d="M15 4h4v16h-4 M10 8l-4 4 4 4 M6 12h10" />;
export const PlusIcon = () => <Icon d="M12 5v14 M5 12h14" />;
export const MenuIcon = () => <Icon d="M4 7h16 M4 12h16 M4 17h16" />;
export const SendIcon = () => <Icon d="M21 3L10 14 M21 3l-7 18-4-7-7-4z" />;
export const StopIcon = () => <Icon d="M7 7h10v10H7z" />;
export const CompaniesIcon = () => (
  <Icon d="M4 21V6l8-3 8 3v15 M2 21h20 M10 21v-4h4v4 M8 9h.01 M12 9h.01 M16 9h.01 M8 13h.01 M12 13h.01 M16 13h.01" />
);

// Status marks: a different SHAPE per state (check, triangle, cross), so color is never the only signal.
// Sized to sit inside a line of small text.
export const StatusOkIcon = () => <Icon size={14} d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M8 12.5l2.5 2.5L16 9.5" />;
export const StatusWarnIcon = () => <Icon size={14} d="M12 3.5l9.5 16.5h-19z M12 10v4 M12 17h.01" />;
export const StatusErrorIcon = () => <Icon size={14} d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M9 9l6 6 M15 9l-6 6" />;
export const CopyIcon = () => <Icon size={14} d="M9 9h11v11H9z M5 15H4V4h11v1" />;
// 8.6e-3: the security password gate (closed / open padlock)
export const LockIcon = () => <Icon size={14} d="M6 11h12v10H6z M8.5 11V7.5a3.5 3.5 0 0 1 7 0V11" />;
export const UnlockIcon = () => <Icon size={14} d="M6 11h12v10H6z M8.5 11V7.5a3.5 3.5 0 0 1 6.8-1.2" />;
