"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./console.module.css";
import {
  AccountsIcon,
  ChatIcon,
  CompaniesIcon,
  DocumentsIcon,
  KeysIcon,
  OverviewIcon,
  PerformanceIcon,
  RequestLogIcon,
  ToolsIcon,
  UsersIcon,
} from "./icons";

// Grouped by what the person is doing; Admin (Accounts, Tools & MCP) only for super admins; testers see only Chat.
const GROUPS = [
  {
    title: "Monitor",
    links: [
      { href: "/", label: "Overview", Icon: OverviewIcon },
      { href: "/performance", label: "Performance", Icon: PerformanceIcon },
      { href: "/requests", label: "Request log", Icon: RequestLogIcon },
    ],
  },
  {
    title: "Knowledge",
    links: [
      { href: "/documents", label: "Documents", Icon: DocumentsIcon },
      { href: "/chat", label: "Chat", Icon: ChatIcon },
    ],
  },
  {
    title: "Clients",
    links: [
      { href: "/companies", label: "Companies", Icon: CompaniesIcon },
      { href: "/apps", label: "Apps & keys", Icon: KeysIcon },
      { href: "/users", label: "Users & chats", Icon: UsersIcon },
    ],
  },
  {
    title: "Admin",
    superAdminOnly: true,
    links: [
      { href: "/accounts", label: "Accounts", Icon: AccountsIcon },
      { href: "/tools", label: "Tools & MCP", Icon: ToolsIcon },
    ],
  },
];

export default function NavLinks({ role }: { role: "super_admin" | "supervisor" | "tester" }) {
  const pathname = usePathname();

  return (
    <div className={styles.navGroups}>
      {GROUPS.filter((g) => role === "super_admin" || !g.superAdminOnly)
        .map((g) => (role === "tester" ? { ...g, links: g.links.filter((l) => l.href === "/chat") } : g))
        .filter((g) => g.links.length > 0)
        .map((group) => (
        // a <p>, not a heading: the sidebar comes before the page's h1
        <div key={group.title}>
          <p id={`nav-${group.title}`} className={styles.navGroup}>
            {group.title}
          </p>
          <ul className={styles.nav} aria-labelledby={`nav-${group.title}`}>
            {group.links.map(({ href, label, Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <li key={href}>
                  {/* title: the name on hover when the sidebar is collapsed to icons (narrow windows) */}
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    title={label}
                    // phones: close the menu once a page is picked (no-op when the menu isn't open)
                    onClick={(e) => e.currentTarget.closest<HTMLElement>(":popover-open")?.hidePopover()}
                  >
                    <Icon />
                    <span className={styles.label}>{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
