"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, X, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Features", href: "#features" },
    { name: "Architecture", href: "#architecture" },
    { name: "Pricing", href: "#pricing" },
    { name: "Docs", href: "#docs" },
  ];

  return (
    <header
      className={cn(
        "fixed top-0 w-full z-50 transition-all duration-300 border-b-4 border-transparent",
        isScrolled ? "bg-background border-primary brutal-shadow-sm" : "bg-transparent"
      )}
    >
      <div className="container mx-auto px-4 h-20 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="bg-primary p-2 border-2 border-foreground group-hover:bg-accent transition-colors">
            <ShieldAlert className="w-6 h-6 text-foreground" strokeWidth={3} />
          </div>
          <span className="font-sans font-black text-xl tracking-tighter uppercase">DriftGuard</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-5 font-sans font-bold uppercase tracking-wider">
          {navLinks.map((link) => (
            <Link key={link.name} href={link.href} className="hover:text-primary transition-colors hover:underline decoration-4 underline-offset-4">
              {link.name}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-4 font-sans font-black">
          <Link href="/login" className="hover:text-primary transition-colors uppercase px-4 py-2">
            Sign In
          </Link>
          <Link
            href="/dashboard"
            className="bg-primary text-foreground px-6 py-2 border-2 border-foreground brutal-button uppercase tracking-wider"
          >
            Get Started
          </Link>
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden p-2 border-2 border-foreground bg-surface brutal-button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="text-primary" strokeWidth={3} /> : <Menu className="text-primary" strokeWidth={3} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-20 left-0 w-full bg-background border-b-4 border-primary brutal-shadow">
          <div className="flex flex-col p-4 font-sans font-black text-xl tracking-wider">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className="py-4 border-b-2 border-border hover:text-primary uppercase hover:pl-4 transition-all"
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.name}
              </Link>
            ))}
            <Link href="/login" className="py-4 border-b-2 border-border hover:text-primary uppercase hover:pl-4 transition-all">
              Sign In
            </Link>
            <Link href="/dashboard" className="py-4 text-primary uppercase hover:pl-4 transition-all">
              Get Started
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
