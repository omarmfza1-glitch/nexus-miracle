"use client";

import { useEffect, useState } from "react";
import { getDoctors, type Doctor } from "@/lib/api";

export default function AdminDashboard() {
    const [stats, setStats] = useState({
        doctors: 0,
        appointments: 0,
        calls: 0,
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchStats() {
            try {
                const doctorsRes = await getDoctors();
                setStats({
                    doctors: doctorsRes.total,
                    appointments: 0,
                    calls: 0,
                });
            } catch (error) {
                console.error("Error fetching stats:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchStats();
    }, []);

    const statCards = [
        { label: "Active Doctors", value: stats.doctors, color: "bg-blue-500" },
        { label: "Today's Appointments", value: stats.appointments, color: "bg-green-500" },
        { label: "Active Calls", value: stats.calls, color: "bg-purple-500" },
    ];

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold">Dashboard</h1>
                <p className="text-muted-foreground mt-1">Welcome to Nexus Miracle Admin</p>
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-32 rounded-xl bg-muted animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {statCards.map((card) => (
                        <div
                            key={card.label}
                            className="relative overflow-hidden rounded-xl bg-card border p-6"
                        >
                            <div className={`absolute top-0 right-0 w-24 h-24 rounded-bl-full ${card.color} opacity-10`} />
                            <p className="text-sm text-muted-foreground">{card.label}</p>
                            <p className="text-4xl font-bold mt-2">{card.value}</p>
                        </div>
                    ))}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="rounded-xl bg-card border p-6">
                    <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
                    <div className="space-y-3">
                        <a
                            href="/admin/prompt"
                            className="block p-4 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                        >
                            <p className="font-medium">Edit System Prompt</p>
                            <p className="text-sm text-muted-foreground">Customize AI behavior</p>
                        </a>
                        <a
                            href="/admin/voices"
                            className="block p-4 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                        >
                            <p className="font-medium">Voice Settings</p>
                            <p className="text-sm text-muted-foreground">Configure Sara & Nexus voices</p>
                        </a>
                        <a
                            href="/admin/doctors"
                            className="block p-4 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                        >
                            <p className="font-medium">Manage Doctors</p>
                            <p className="text-sm text-muted-foreground">View and edit doctor list</p>
                        </a>
                    </div>
                </div>

                <div className="rounded-xl bg-card border p-6">
                    <h2 className="text-xl font-semibold mb-4">System Status</h2>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <span>Backend API</span>
                            <span className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500" />
                                Online
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span>Database</span>
                            <span className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500" />
                                Connected
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span>Telephony</span>
                            <span className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-yellow-500" />
                                Standby
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
