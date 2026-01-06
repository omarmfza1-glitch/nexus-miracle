"use client";

import { useEffect, useState } from "react";
import { Search, Loader2, Phone, User } from "lucide-react";

const API_BASE = "/api";

interface Patient {
    id: number;
    phone: string;
    name: string | null;
    name_ar: string | null;
    national_id_last4: string | null;
    gender: string | null;
    insurance_company: string | null;
    insurance_id: string | null;
    language: string;
}

interface PatientListResponse {
    items: Patient[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
}

export default function PatientsPage() {
    const [patients, setPatients] = useState<Patient[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        async function fetchPatients() {
            setLoading(true);
            try {
                const params = new URLSearchParams();
                params.set("page", currentPage.toString());
                if (search) params.set("search", search);

                const res = await fetch(`${API_BASE}/patients?${params}`);
                if (res.ok) {
                    const data: PatientListResponse = await res.json();
                    setPatients(data.items);
                    setTotalPages(data.pages);
                    setTotal(data.total);
                }
            } catch (error) {
                console.error("Error fetching patients:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchPatients();
    }, [currentPage, search]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setCurrentPage(1);
    };

    const genderLabel = (gender: string | null) => {
        if (gender === "male") return "ذكر";
        if (gender === "female") return "أنثى";
        return "-";
    };

    if (loading && patients.length === 0) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold">Patients</h1>
                    <p className="text-muted-foreground">
                        {total} registered patients
                    </p>
                </div>
            </div>

            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search by phone, name..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background"
                    />
                </div>
                <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                >
                    Search
                </button>
            </form>

            {/* Patients Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {patients.map((patient) => (
                    <div
                        key={patient.id}
                        className="rounded-xl bg-card border p-6 hover:shadow-lg transition-shadow"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-3 rounded-full bg-primary/10 text-primary">
                                <User size={24} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <h3 className="font-bold text-lg truncate" dir="rtl">
                                    {patient.name_ar || patient.name || "Unknown"}
                                </h3>
                                {patient.name && patient.name_ar && (
                                    <p className="text-sm text-muted-foreground truncate">
                                        {patient.name}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="mt-4 space-y-2">
                            <div className="flex items-center gap-2 text-sm">
                                <Phone size={14} className="text-muted-foreground" />
                                <span className="font-mono">{patient.phone}</span>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-sm">
                                <div>
                                    <span className="text-muted-foreground">Gender:</span>
                                    <span className="ml-1" dir="rtl">{genderLabel(patient.gender)}</span>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">Language:</span>
                                    <span className="ml-1">{patient.language === "ar" ? "العربية" : "English"}</span>
                                </div>
                            </div>

                            {patient.insurance_company && (
                                <div className="text-sm">
                                    <span className="text-muted-foreground">Insurance:</span>
                                    <span className="ml-1" dir="rtl">{patient.insurance_company}</span>
                                </div>
                            )}

                            {patient.national_id_last4 && (
                                <div className="text-sm">
                                    <span className="text-muted-foreground">ID (last 4):</span>
                                    <span className="ml-1 font-mono">****{patient.national_id_last4}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {patients.length === 0 && !loading && (
                <div className="text-center py-12 text-muted-foreground">
                    No patients found
                </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                    <button
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 rounded border disabled:opacity-50"
                    >
                        Previous
                    </button>
                    <span className="px-3 py-1">
                        Page {currentPage} of {totalPages}
                    </span>
                    <button
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 rounded border disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
