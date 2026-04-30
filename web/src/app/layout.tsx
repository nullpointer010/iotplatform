import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { TopNav } from "@/components/top-nav";

export const metadata: Metadata = {
  title: "CropDataSpace IoT",
  description: "Operator UI for the CropDataSpace IoT platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-screen bg-background">
        <Providers>
          <TopNav />
          <main className="container py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
