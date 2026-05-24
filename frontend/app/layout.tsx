import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Canon",
  description: "Organizational memory for engineering teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-canon-bg text-canon-text antialiased">{children}</body>
    </html>
  );
}
