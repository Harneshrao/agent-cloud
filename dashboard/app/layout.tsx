import "./globals.css";
import Providers from "./providers";
import { ProductLayout } from "@/components/product/product-layout";
import { Plus_Jakarta_Sans } from "next/font/google";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${plusJakarta.className} min-h-screen bg-background text-foreground antialiased`}>
        <Providers>
          <ProductLayout>{children}</ProductLayout>
        </Providers>
      </body>
    </html>
  );
}

