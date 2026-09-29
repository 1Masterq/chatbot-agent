import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northstar Agent",
  description: "A focused workspace for thinking with an AI agent.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
