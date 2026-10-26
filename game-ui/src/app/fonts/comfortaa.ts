import localFont from "next/font/local";

// Comfortaa (variable, weights 300-700), served from files inside the app: no Google Fonts requests.
// Source: @fontsource-variable/comfortaa 5.3.0 (Google Fonts v47), SIL Open Font License 1.1 (OFL.txt).
// Two files, split by character range like Google Fonts does: Latin (English, Filipino incl. ñ) and
// Latin Extended (e.g. the peso sign ₱), which the browser downloads only when a page needs it.

export const comfortaa = localFont({
  src: "./comfortaa-latin-wght-normal.woff2",
  weight: "300 700",
  display: "swap",
  // No generated Arial fallback here: it covers every character and would sit before the Latin Extended
  // file in the font stack, so ₱ would be drawn in Arial. The Extended font keeps its fallback.
  adjustFontFallback: false,
  variable: "--font-comfortaa",
  declarations: [
    {
      prop: "unicode-range",
      // One literal: next/font only accepts values written out, no string concatenation.
      value:
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
    },
  ],
});

export const comfortaaExt = localFont({
  src: "./comfortaa-latin-ext-wght-normal.woff2",
  weight: "300 700",
  display: "swap",
  preload: false,
  variable: "--font-comfortaa-ext",
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
    },
  ],
});
