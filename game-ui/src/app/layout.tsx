import type { Metadata } from "next";
import { cookies } from "next/headers";

import { comfortaa, comfortaaExt } from "@/app/fonts/comfortaa";
import { shownTheme } from "@/hq/theme";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ITI AI HQ", template: "%s – ITI AI HQ" },
  description: "The ITI AI Console as a game: one room per console page",
};

// The theme comes from the person's cookies (dark by default, or Manila's time of day when the PHT auto theme is
// on), so the first paint is already right.
export default async function RootLayout({ children }: LayoutProps<"/">) {
  const theme = shownTheme(await cookies());
  return (
    <html lang="en" data-theme={theme} className={`${comfortaa.variable} ${comfortaaExt.variable}`}>
      <body>{children}</body>
    </html>
  );
}
