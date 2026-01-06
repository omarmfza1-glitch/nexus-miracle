import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Nexus Miracle Admin",
    description: "Admin dashboard for AI contact center",
};

// Script to apply dark mode before hydration to prevent flash
const darkModeScript = `
  (function() {
    try {
      var stored = localStorage.getItem('darkMode');
      if (stored === 'true' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      }
    } catch (e) {}
  })();
`;

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <script dangerouslySetInnerHTML={{ __html: darkModeScript }} />
            </head>
            <body className={inter.className}>{children}</body>
        </html>
    );
}
