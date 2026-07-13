import type { Metadata } from "next";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
import { Providers } from "./providers";
import { NavBar } from "@/components/NavBar";

export const metadata: Metadata = {
  title: "FOLK Cultural Intelligence",
  description:
    "Understand how cultures differ across the world. 197 countries, 4 dimensions, 5 cultural frameworks, a multi-LLM research council.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <NavBar />
          <main className="min-h-screen">{children}</main>
          <footer className="border-t border-line mt-20 py-10 text-center text-sm text-ink-dim">
            <p>
              FOLK Cultural Intelligence Platform &middot; Evidence-centric
              cultural scoring across 4 dimensions and 5 frameworks.
            </p>
            <p className="mt-1">
              Scores are calibrated against fixed global reference points and
              reviewed by a multi-LLM research council.
            </p>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
