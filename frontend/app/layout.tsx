import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "canon",
  description: "Organizational memory for engineering teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <head>
        <meta name="apple-mobile-web-app-title" content="canon" />
      </head>
      <body className="h-full bg-canon-bg text-canon-text antialiased">{children}</body>
    </html>
  );
}
