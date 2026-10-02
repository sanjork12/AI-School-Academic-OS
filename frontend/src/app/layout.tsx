import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Academic OS | Internal Authoring Console",
  description:
    "Local deterministic Standard Deviation workflow and read-only curriculum evidence.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
