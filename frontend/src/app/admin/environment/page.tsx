"use client";

import { useEffect, useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";

const API_BASE = "/api";

interface EnvSection {
    title: string;
    fields: {
        key: string;
        label: string;
        type: "text" | "password" | "number" | "toggle";
    }[];
}

export default function EnvironmentPage() {
    const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const [config, setConfig] = useState<Record<string, string | number | boolean>>({
        telnyx_api_key: "",
        telnyx_connection_id: "",
        telnyx_phone_number: "",
        elevenlabs_api_key: "",
        elevenlabs_voice_sara: "",
        elevenlabs_voice_nexus: "",
        google_api_key: "",
        vad_silence_threshold: 500,
        filler_delay: 300,
        max_conversation_turns: 50,
        barge_in_enabled: true,
        debug_mode: false,
        call_recording: false,
    });

    const sections: EnvSection[] = [
        {
            title: "Telephony (Telnyx)",
            fields: [
                { key: "telnyx_api_key", label: "API Key", type: "password" },
                { key: "telnyx_connection_id", label: "Connection ID", type: "text" },
                { key: "telnyx_phone_number", label: "Phone Number", type: "text" },
            ],
        },
        {
            title: "AI Services",
            fields: [
                { key: "elevenlabs_api_key", label: "ElevenLabs API Key", type: "password" },
                { key: "elevenlabs_voice_sara", label: "Sara Voice ID", type: "text" },
                { key: "elevenlabs_voice_nexus", label: "Nexus Voice ID", type: "text" },
                { key: "google_api_key", label: "Google API Key", type: "password" },
            ],
        },
        {
            title: "Performance",
            fields: [
                { key: "vad_silence_threshold", label: "VAD Silence Threshold (ms)", type: "number" },
                { key: "filler_delay", label: "Filler Phrase Delay (ms)", type: "number" },
                { key: "max_conversation_turns", label: "Max Conversation Turns", type: "number" },
            ],
        },
        {
            title: "Feature Flags",
            fields: [
                { key: "barge_in_enabled", label: "Barge-in Enabled", type: "toggle" },
                { key: "debug_mode", label: "Debug Mode", type: "toggle" },
                { key: "call_recording", label: "Call Recording", type: "toggle" },
            ],
        },
    ];

    useEffect(() => {
        async function fetchEnvironment() {
            try {
                const res = await fetch(`${API_BASE}/admin/environment`);
                if (res.ok) {
                    const data = await res.json();
                    setConfig((prev) => ({ ...prev, ...data }));
                }
            } catch (error) {
                console.error("Error fetching environment:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchEnvironment();
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/admin/environment`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config),
            });
            if (res.ok) {
                alert("Settings saved!");
            } else {
                throw new Error("Save failed");
            }
        } catch {
            alert("Error saving settings");
        } finally {
            setSaving(false);
        }
    };

    const togglePassword = (key: string) => {
        setShowPasswords((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    const updateConfig = (key: string, value: string | number | boolean) => {
        setConfig((prev) => ({ ...prev, [key]: value }));
    };

    const maskValue = (value: string) => {
        if (!value || value.length < 8) return "••••••••";
        return value.slice(0, 4) + "••••" + value.slice(-4);
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
                    <h1 className="text-3xl font-bold">Environment</h1>
                    <p className="text-muted-foreground">Configure system settings and API keys</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                    {saving ? "Saving..." : "Save All"}
                </button>
            </div>

            <div className="space-y-6">
                {sections.map((section) => (
                    <div key={section.title} className="rounded-xl bg-card border p-6">
                        <h2 className="text-lg font-semibold mb-4">{section.title}</h2>
                        <div className="space-y-4">
                            {section.fields.map((field) => (
                                <div key={field.key}>
                                    <label className="block text-sm font-medium mb-2">{field.label}</label>
                                    {field.type === "toggle" ? (
                                        <button
                                            onClick={() => updateConfig(field.key, !config[field.key])}
                                            className={`relative w-12 h-6 rounded-full transition-colors ${config[field.key] ? "bg-primary" : "bg-muted"
                                                }`}
                                        >
                                            <span
                                                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${config[field.key] ? "left-7" : "left-1"
                                                    }`}
                                            />
                                        </button>
                                    ) : field.type === "password" ? (
                                        <div className="relative">
                                            <input
                                                type={showPasswords[field.key] ? "text" : "password"}
                                                value={showPasswords[field.key] ? (config[field.key] as string) : maskValue(config[field.key] as string)}
                                                onChange={(e) => updateConfig(field.key, e.target.value)}
                                                placeholder="••••••••••••••••"
                                                className="w-full px-3 py-2 pr-10 rounded-lg border bg-background font-mono"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => togglePassword(field.key)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                                title={showPasswords[field.key] ? "Hide" : "Show"}
                                            >
                                                {showPasswords[field.key] ? <EyeOff size={18} /> : <Eye size={18} />}
                                            </button>
                                        </div>
                                    ) : (
                                        <input
                                            type={field.type}
                                            value={config[field.key] as string | number}
                                            onChange={(e) => updateConfig(field.key, field.type === "number" ? parseInt(e.target.value) || 0 : e.target.value)}
                                            className="w-full px-3 py-2 rounded-lg border bg-background"
                                        />
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
