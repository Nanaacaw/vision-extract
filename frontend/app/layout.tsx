import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finance OCR",
  description: "Internal finance OCR review workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
