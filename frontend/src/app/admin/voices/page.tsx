"use client";

import { useEffect, useState, useRef } from "react";
import { Loader2, Volume2, Square } from "lucide-react";
import { getVoiceSettings, saveVoiceSettings } from "@/lib/api";

interface VoiceConfig {
    voice_id: string;
    stability: number;
    similarity_boost: number;
    style: number;
    speed: number;
}

export default function VoicesPage() {
    const [sara, setSara] = useState<VoiceConfig>({
        voice_id: "",
        stability: 0.5,
        similarity_boost: 0.75,
        style: 0.0,
        speed: 1.0,
    });

    const [nexus, setNexus] = useState<VoiceConfig>({
        voice_id: "",
        stability: 0.6,
        similarity_boost: 0.8,
        style: 0.0,
        speed: 1.0,
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testText, setTestText] = useState("مرحباً، كيف يمكنني مساعدتك اليوم؟");
    const [playingVoice, setPlayingVoice] = useState<string | null>(null);
    const [loadingVoice, setLoadingVoice] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        async function fetchSettings() {
            try {
                const data = await getVoiceSettings();
                if (data.sara) setSara(data.sara);
                if (data.nexus) setNexus(data.nexus);
            } catch (error) {
                console.error("Error fetching voice settings:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchSettings();
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            await saveVoiceSettings({ sara, nexus });
            alert("Settings saved!");
        } catch (error) {
            console.error("Error saving settings:", error);
            alert("Error saving settings");
        } finally {
            setSaving(false);
        }
    };

    const handleTestVoice = async (voiceName: string, config: VoiceConfig) => {
        // Stop any currently playing audio
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }

        if (playingVoice === voiceName) {
            setPlayingVoice(null);
            return;
        }

        if (!testText.trim()) {
            alert("Please enter test text");
            return;
        }

        setError(null);
        setLoadingVoice(voiceName);

        try {
            // Call ElevenLabs TTS API via backend
            const response = await fetch("/api/admin/voices/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: testText,
                    voice: voiceName.toLowerCase(),
                    stability: config.stability,
                    similarity_boost: config.similarity_boost,
                    speed: config.speed,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `TTS Error: ${response.status}`);
            }

            // Get audio blob and play it
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            const audio = new Audio(audioUrl);
            audioRef.current = audio;

            audio.onended = () => {
                setPlayingVoice(null);
                URL.revokeObjectURL(audioUrl);
            };

            audio.onerror = () => {
                setPlayingVoice(null);
                setError("Failed to play audio");
                URL.revokeObjectURL(audioUrl);
            };

            setPlayingVoice(voiceName);
            await audio.play();

        } catch (err) {
            console.error("TTS error:", err);
            setError(err instanceof Error ? err.message : "TTS failed");
            setPlayingVoice(null);
        } finally {
            setLoadingVoice(null);
        }
    };

    const handleStopVoice = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setPlayingVoice(null);
    };

    const VoiceCard = ({
        name,
        nameAr,
        config,
        setConfig,
    }: {
        name: string;
        nameAr: string;
        config: VoiceConfig;
        setConfig: (c: VoiceConfig) => void;
    }) => (
        <div className="rounded-xl bg-card border p-6">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-xl font-bold">{name}</h2>
                    <p className="text-muted-foreground" dir="rtl">{nameAr}</p>
                </div>
            </div>

            <div className="space-y-6">
                <div>
                    <label className="block text-sm font-medium mb-2">Voice ID</label>
                    <input
                        type="text"
                        value={config.voice_id}
                        onChange={(e) => setConfig({ ...config, voice_id: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border bg-background font-mono text-sm"
                        placeholder="Enter ElevenLabs Voice ID"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">
                        Stability: {config.stability.toFixed(2)}
                    </label>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={config.stability}
                        onChange={(e) => setConfig({ ...config, stability: parseFloat(e.target.value) })}
                        className="w-full accent-primary"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">
                        Similarity: {config.similarity_boost.toFixed(2)}
                    </label>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={config.similarity_boost}
                        onChange={(e) => setConfig({ ...config, similarity_boost: parseFloat(e.target.value) })}
                        className="w-full accent-primary"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">
                        Style: {config.style.toFixed(2)}
                    </label>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={config.style}
                        onChange={(e) => setConfig({ ...config, style: parseFloat(e.target.value) })}
                        className="w-full accent-primary"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">
                        Speed: {config.speed.toFixed(2)}x
                    </label>
                    <input
                        type="range"
                        min="0.7"
                        max="1.2"
                        step="0.05"
                        value={config.speed}
                        onChange={(e) => setConfig({ ...config, speed: parseFloat(e.target.value) })}
                        className="w-full accent-primary"
                    />
                    <p className="text-xs text-muted-foreground mt-1">ElevenLabs supports 0.7x - 1.2x</p>
                </div>

                <button
                    onClick={() => playingVoice === name ? handleStopVoice() : handleTestVoice(name, config)}
                    disabled={loadingVoice === name}
                    className={`w-full px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors ${playingVoice === name
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary hover:bg-secondary/80"
                        } disabled:opacity-50`}
                >
                    {loadingVoice === name ? (
                        <>
                            <Loader2 size={18} className="animate-spin" />
                            Loading...
                        </>
                    ) : playingVoice === name ? (
                        <>
                            <Square size={18} />
                            Stop
                        </>
                    ) : (
                        <>
                            <Volume2 size={18} />
                            Test Voice (ElevenLabs)
                        </>
                    )}
                </button>
            </div>
        </div>
    );

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
                    <h1 className="text-3xl font-bold">Voice Settings</h1>
                    <p className="text-muted-foreground">Configure ElevenLabs voice parameters</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                    {saving ? "Saving..." : "Save All"}
                </button>
            </div>

            {error && (
                <div className="rounded-lg bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 p-4 text-red-700 dark:text-red-300">
                    <strong>Error:</strong> {error}
                </div>
            )}

            <div className="rounded-xl bg-muted p-4">
                <label className="block text-sm font-medium mb-2">Test Text</label>
                <textarea
                    value={testText}
                    onChange={(e) => setTestText(e.target.value)}
                    dir="rtl"
                    className="w-full px-3 py-2 rounded-lg border bg-background resize-none"
                    rows={2}
                    placeholder="أدخل النص للاختبار..."
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <VoiceCard name="Sara" nameAr="سارة" config={sara} setConfig={setSara} />
                <VoiceCard name="Nexus" nameAr="نِكسوس" config={nexus} setConfig={setNexus} />
            </div>
        </div>
    );
}
