import type { Metadata } from "next";
import { cookies } from "next/headers";

import { comfortaa, comfortaaExt } from "@/app/fonts/comfortaa";
import { THEME_COOKIE, themeFrom } from "@/lib/theme";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ITI AI Console", template: "%s – ITI AI Console" },
  description: "Monitoring and control for the ITI AI Platform",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const theme = themeFrom((await cookies()).get(THEME_COOKIE)?.value);

  return (
    // data-scroll-behavior: Next.js turns smooth scrolling off while it switches pages (no slow scroll-to-top)
    <html
      lang="en"
      data-theme={theme}
      data-scroll-behavior="smooth"
      className={`${comfortaa.variable} ${comfortaaExt.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
