import type { Metadata } from "next";

import { comfortaa, comfortaaExt } from "@/app/fonts/comfortaa";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ITI AI HQ", template: "%s – ITI AI HQ" },
  description: "The ITI AI Console as a game: one room per console page",
};

// Dark only for now: the light theme (and its toggle) comes with the HQ scene in G2.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" data-theme="dark" className={`${comfortaa.variable} ${comfortaaExt.variable}`}>
      <body>{children}</body>
    </html>
  );
}
