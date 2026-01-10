"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
    LayoutDashboard,
    FileText,
    MessageSquare,
    Mic,
    Settings,
    Phone,
    Stethoscope,
    Users,
    Menu,
    X,
    Moon,
    Sun,
    CalendarDays,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { href: "/admin", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/admin/appointments", icon: CalendarDays, label: "Appointments" },
    { href: "/admin/calendar", icon: CalendarDays, label: "Calendar" },
    { href: "/admin/prompt", icon: FileText, label: "System Prompt" },
    { href: "/admin/fillers", icon: MessageSquare, label: "Filler Phrases" },
    { href: "/admin/voices", icon: Mic, label: "Voice Settings" },
    { href: "/admin/environment", icon: Settings, label: "Environment" },
    { href: "/admin/calls", icon: Phone, label: "Call Logs" },
    { href: "/admin/doctors", icon: Stethoscope, label: "Doctors" },
    { href: "/admin/patients", icon: Users, label: "Patients" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [darkMode, setDarkMode] = useState(false);

    useEffect(() => {
        const stored = localStorage.getItem("darkMode");
        if (stored === "true" || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
            setDarkMode(true);
            document.documentElement.classList.add("dark");
        }
    }, []);

    const toggleDarkMode = () => {
        const newValue = !darkMode;
        setDarkMode(newValue);
        localStorage.setItem("darkMode", String(newValue));
        document.documentElement.classList.toggle("dark", newValue);
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Mobile overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-black/50 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 w-64 transform bg-card border-r transition-transform duration-200 lg:translate-x-0",
                    sidebarOpen ? "translate-x-0" : "-translate-x-full"
                )}
            >
                <div className="flex h-16 items-center justify-between px-4 border-b">
                    <h1 className="text-lg font-bold text-primary">Nexus Miracle</h1>
                    <button onClick={() => setSidebarOpen(false)} className="lg:hidden p-2">
                        <X size={20} />
                    </button>
                </div>

                <nav className="p-4 space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href ||
                            (item.href !== "/admin" && pathname.startsWith(item.href));
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                onClick={() => setSidebarOpen(false)}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                                    isActive
                                        ? "bg-primary text-primary-foreground"
                                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <item.icon size={20} />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div className="absolute bottom-0 left-0 right-0 p-4 border-t">
                    <button
                        onClick={toggleDarkMode}
                        className="flex w-full items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                    >
                        {darkMode ? <Sun size={20} /> : <Moon size={20} />}
                        <span>{darkMode ? "Light Mode" : "Dark Mode"}</span>
                    </button>
                </div>
            </aside>

            {/* Main content */}
            <div className="lg:pl-64">
                {/* Top bar */}
                <header className="sticky top-0 z-30 h-16 bg-background/95 backdrop-blur border-b flex items-center px-4 lg:hidden">
                    <button onClick={() => setSidebarOpen(true)} className="p-2">
                        <Menu size={24} />
                    </button>
                    <h1 className="ml-4 text-lg font-bold">Nexus Miracle</h1>
                </header>

                <main className="p-4 lg:p-8">{children}</main>
            </div>
        </div>
    );
}
