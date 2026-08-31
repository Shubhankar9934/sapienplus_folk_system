import type { Metadata } from "next";
import { Inter, Anton } from "next/font/google";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
import { Providers } from "./providers";
import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const anton = Anton({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FOLK Cultural Intelligence",
  description:
    "Understand how cultures differ across the world. 197 countries, 4 dimensions — Identity, Expression, Structure, Drive — scored by a multi-LLM research council across 5 academic frameworks.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${anton.variable}`}>
        <Providers>
          <div className="flex min-h-screen flex-col">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
