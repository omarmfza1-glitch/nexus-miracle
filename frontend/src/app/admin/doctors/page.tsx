"use client";

import { useEffect, useState } from "react";
import { getDoctors, type Doctor } from "@/lib/api";

export default function DoctorsPage() {
    const [doctors, setDoctors] = useState<Doctor[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("");

    useEffect(() => {
        async function fetchDoctors() {
            try {
                const res = await getDoctors(filter ? { specialty: filter } : undefined);
                setDoctors(res.items);
            } catch (error) {
                console.error("Error fetching doctors:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchDoctors();
    }, [filter]);

    const specialties = ["عظام", "باطنية", "جلدية", "أطفال"];

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold">Doctors</h1>
                    <p className="text-muted-foreground">Manage clinic doctors</p>
                </div>

                <div className="flex gap-2">
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="px-3 py-2 rounded-lg border bg-background"
                    >
                        <option value="">All Specialties</option>
                        {specialties.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <div key={i} className="h-48 rounded-xl bg-muted animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {doctors.map((doctor) => (
                        <div
                            key={doctor.id}
                            className="rounded-xl bg-card border p-6 hover:shadow-lg transition-shadow"
                        >
                            <div className="flex items-start justify-between">
                                <div>
                                    <h3 className="font-bold text-lg" dir="rtl">{doctor.name_ar}</h3>
                                    <p className="text-muted-foreground">{doctor.name}</p>
                                </div>
                                <span className={`px-2 py-1 rounded-full text-xs ${doctor.status === "active"
                                        ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                                        : "bg-gray-100 text-gray-800"
                                    }`}>
                                    {doctor.status}
                                </span>
                            </div>

                            <div className="mt-4 space-y-2">
                                <div className="flex items-center gap-2 text-sm">
                                    <span className="text-muted-foreground">Specialty:</span>
                                    <span dir="rtl">{doctor.specialty_ar}</span>
                                </div>
                                <div className="flex items-center gap-2 text-sm">
                                    <span className="text-muted-foreground">Branch:</span>
                                    <span dir="rtl">{doctor.branch}</span>
                                </div>
                                <div className="flex items-center gap-2 text-sm">
                                    <span className="text-muted-foreground">Rating:</span>
                                    <span>{"⭐".repeat(Math.round(doctor.rating))}</span>
                                    <span className="text-muted-foreground">({doctor.rating})</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!loading && doctors.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                    No doctors found
                </div>
            )}
        </div>
    );
}
