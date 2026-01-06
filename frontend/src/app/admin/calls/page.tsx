"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getCallLogs, getCallTranscript } from "@/lib/api";

interface CallLog {
    id: number;
    phone: string;
    start_time: string;
    end_time?: string;
    duration_seconds?: number;
    status: string;
}

interface CallListResponse {
    items: CallLog[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
}

export default function CallsPage() {
    const [calls, setCalls] = useState<CallLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const [expandedTranscript, setExpandedTranscript] = useState<string | null>(null);
    const [filter, setFilter] = useState("");
    const [statusFilter, setStatusFilter] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    useEffect(() => {
        async function fetchCalls() {
            setLoading(true);
            try {
                const params: { page?: number; phone?: string; status?: string } = {
                    page: currentPage,
                };
                if (filter) params.phone = filter;
                if (statusFilter) params.status = statusFilter;

                const data = await getCallLogs(params) as CallListResponse;
                setCalls(data.items);
                setTotalPages(data.pages);
            } catch (error) {
                console.error("Error fetching calls:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchCalls();
    }, [currentPage, filter, statusFilter]);

    const handleRowClick = async (callId: number) => {
        if (expandedId === callId) {
            setExpandedId(null);
            setExpandedTranscript(null);
            return;
        }

        setExpandedId(callId);
        try {
            const data = await getCallTranscript(callId.toString());
            setExpandedTranscript(
                Array.isArray(data.transcript)
                    ? data.transcript.map((t: { content: string }) => t.content).join("\n")
                    : data.transcript || "No transcript available"
            );
        } catch {
            setExpandedTranscript("Error loading transcript");
        }
    };

    const formatDuration = (seconds?: number) => {
        if (!seconds) return "0:00";
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    };

    const formatTime = (isoString: string) => {
        return new Date(isoString).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    const statusColors: Record<string, string> = {
        completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
        missed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
        ongoing: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
        failed: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100",
    };

    if (loading && calls.length === 0) {
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
                    <h1 className="text-3xl font-bold">Call Logs</h1>
                    <p className="text-muted-foreground">View call history and transcripts</p>
                </div>
                <button className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80">
                    Export CSV
                </button>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
                <input
                    type="text"
                    placeholder="Search by phone..."
                    value={filter}
                    onChange={(e) => {
                        setFilter(e.target.value);
                        setCurrentPage(1);
                    }}
                    className="flex-1 px-3 py-2 rounded-lg border bg-background"
                />
                <select
                    value={statusFilter}
                    onChange={(e) => {
                        setStatusFilter(e.target.value);
                        setCurrentPage(1);
                    }}
                    className="px-3 py-2 rounded-lg border bg-background"
                >
                    <option value="">All Status</option>
                    <option value="completed">Completed</option>
                    <option value="missed">Missed</option>
                    <option value="ongoing">Ongoing</option>
                </select>
            </div>

            <div className="rounded-xl bg-card border overflow-hidden">
                <table className="w-full">
                    <thead className="bg-muted">
                        <tr>
                            <th className="px-4 py-3 text-left text-sm font-medium">Time</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Phone</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Duration</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {calls.map((call) => (
                            <>
                                <tr
                                    key={call.id}
                                    onClick={() => handleRowClick(call.id)}
                                    className="border-t cursor-pointer hover:bg-muted/50 transition-colors"
                                >
                                    <td className="px-4 py-3">{formatTime(call.start_time)}</td>
                                    <td className="px-4 py-3 font-mono">{call.phone}</td>
                                    <td className="px-4 py-3">{formatDuration(call.duration_seconds)}</td>
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 rounded-full text-xs ${statusColors[call.status] || statusColors.failed}`}>
                                            {call.status}
                                        </span>
                                    </td>
                                </tr>
                                {expandedId === call.id && (
                                    <tr key={`${call.id}-expanded`}>
                                        <td colSpan={4} className="px-4 py-4 bg-muted/30">
                                            <div className="space-y-4">
                                                <div>
                                                    <h4 className="text-sm font-medium mb-2">Transcript</h4>
                                                    <p className="text-sm text-muted-foreground whitespace-pre-wrap" dir="rtl">
                                                        {expandedTranscript || "Loading..."}
                                                    </p>
                                                </div>
                                                {call.status === "completed" && (
                                                    <button className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm">
                                                        Play Recording
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </>
                        ))}
                    </tbody>
                </table>

                {calls.length === 0 && !loading && (
                    <div className="text-center py-12 text-muted-foreground">
                        No calls found
                    </div>
                )}
            </div>

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
