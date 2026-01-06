"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

const API_BASE = "/api";

interface PromptVariable {
    name: string;
    description: string;
}

export default function PromptPage() {
    const [prompt, setPrompt] = useState("");
    const [variables, setVariables] = useState<PromptVariable[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        async function fetchPrompt() {
            try {
                const res = await fetch(`${API_BASE}/admin/prompt`);
                if (res.ok) {
                    const data = await res.json();
                    setPrompt(data.prompt || "");
                    setVariables(data.variables || []);
                }
            } catch (error) {
                console.error("Error fetching prompt:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchPrompt();
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/admin/prompt`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt }),
            });
            if (res.ok) {
                alert("Prompt saved!");
            } else {
                throw new Error("Save failed");
            }
        } catch {
            alert("Error saving prompt");
        } finally {
            setSaving(false);
        }
    };

    const handleReset = async () => {
        if (!confirm("Reset to default prompt?")) return;
        try {
            const res = await fetch(`${API_BASE}/admin/prompt`);
            if (res.ok) {
                const data = await res.json();
                setPrompt(data.prompt || "");
            }
        } catch {
            alert("Error resetting prompt");
        }
    };

    const insertVariable = (varName: string) => {
        setPrompt((prev) => prev + "\n" + varName);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">System Prompt</h1>
                    <p className="text-muted-foreground">Configure AI assistant behavior</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleReset}
                        className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
                    >
                        Reset
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                        {saving ? "Saving..." : "Save"}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Variables panel */}
                <div className="lg:col-span-1">
                    <div className="rounded-xl bg-card border p-4 sticky top-4">
                        <h3 className="font-semibold mb-4">Variables</h3>
                        <div className="space-y-3">
                            {variables.map((v) => (
                                <button
                                    key={v.name}
                                    onClick={() => insertVariable(v.name)}
                                    className="w-full text-left p-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                                >
                                    <code className="text-xs text-primary">{v.name}</code>
                                    <p className="text-xs text-muted-foreground mt-1" dir="rtl">{v.description}</p>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Editor */}
                <div className="lg:col-span-3">
                    <div className="rounded-xl bg-card border overflow-hidden">
                        <div className="bg-muted px-4 py-2 border-b flex items-center justify-between">
                            <span className="text-sm font-medium">Prompt Editor</span>
                            <span className="text-xs text-muted-foreground">
                                {prompt.length} characters
                            </span>
                        </div>
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            dir="rtl"
                            className="w-full h-[500px] p-4 bg-background font-mono text-sm resize-none focus:outline-none"
                            placeholder="Enter system prompt..."
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
