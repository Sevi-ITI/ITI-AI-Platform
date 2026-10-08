"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./console.module.css";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/performance", label: "Performance" },
  { href: "/requests", label: "Request log" },
  { href: "/users", label: "Users & chats" },
  { href: "/documents", label: "Documents" },
  { href: "/apps", label: "Apps & keys" },
  { href: "/chat", label: "Chat" },
];

export default function NavLinks({ showAccounts }: { showAccounts: boolean }) {
  const pathname = usePathname();
  const links = showAccounts ? [...LINKS, { href: "/accounts", label: "Accounts" }] : LINKS;

  return (
    <ul className={styles.nav}>
      {links.map(({ href, label }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <li key={href}>
            <Link href={href} aria-current={active ? "page" : undefined}>
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
