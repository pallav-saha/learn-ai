import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Birthday Reminder Bot",
  description: "Never miss a birthday again! Upload your contacts and get email reminders.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        {children}
      </body>
    </html>
  );
}
