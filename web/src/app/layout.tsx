import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { TopNav } from "@/components/top-nav";
import { getLocale, loadMessages } from "@/i18n";

export const metadata: Metadata = {
  title: "CropDataSpace IoT",
  description: "Operator UI for the CropDataSpace IoT platform.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = getLocale();
  const messages = await loadMessages(locale);
  return (
    <html lang={locale} className="h-full">
      <body className="min-h-screen bg-background">
        <Providers locale={locale} messages={messages}>
          <TopNav />
          <main className="container py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
