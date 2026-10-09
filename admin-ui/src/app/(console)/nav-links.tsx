"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./console.module.css";
import {
  AccountsIcon,
  ChatIcon,
  DocumentsIcon,
  KeysIcon,
  OverviewIcon,
  PerformanceIcon,
  RequestLogIcon,
  UsersIcon,
} from "./icons";

const LINKS = [
  { href: "/", label: "Overview", Icon: OverviewIcon },
  { href: "/performance", label: "Performance", Icon: PerformanceIcon },
  { href: "/requests", label: "Request log", Icon: RequestLogIcon },
  { href: "/users", label: "Users & chats", Icon: UsersIcon },
  { href: "/documents", label: "Documents", Icon: DocumentsIcon },
  { href: "/apps", label: "Apps & keys", Icon: KeysIcon },
  { href: "/chat", label: "Chat", Icon: ChatIcon },
];

const ACCOUNTS = { href: "/accounts", label: "Accounts", Icon: AccountsIcon };

export default function NavLinks({ showAccounts }: { showAccounts: boolean }) {
  const pathname = usePathname();
  const links = showAccounts ? [...LINKS, ACCOUNTS] : LINKS;

  return (
    <ul className={styles.nav}>
      {links.map(({ href, label, Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <li key={href}>
            {/* title: the name on hover when the sidebar is collapsed to icons (narrow windows) */}
            <Link href={href} aria-current={active ? "page" : undefined} title={label}>
              <Icon />
              <span className={styles.label}>{label}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
