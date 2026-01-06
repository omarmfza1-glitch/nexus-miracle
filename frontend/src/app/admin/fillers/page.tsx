"use client";

import { useEffect, useState, useRef } from "react";
import { Trash2, Plus, Volume2, Loader2, Square } from "lucide-react";
import { getFillers, saveFiller, deleteFiller, type FillerPhrase } from "@/lib/api";

const categories = [
    { id: "search", label: "البحث" },
    { id: "empathy", label: "التعاطف" },
    { id: "delay", label: "التأخير" },
    { id: "dialog", label: "الحوار الثنائي" },
    { id: "silence", label: "الصمت" },
    { id: "goodbye", label: "الوداع" },
];

export default function FillersPage() {
    const [activeCategory, setActiveCategory] = useState("search");
    const [fillers, setFillers] = useState<FillerPhrase[]>([]);
    const [loading, setLoading] = useState(true);
    const [newText, setNewText] = useState("");
    const [newSpeaker, setNewSpeaker] = useState<"سارة" | "نِكسوس">("سارة");
    const [saving, setSaving] = useState(false);
    const [playingId, setPlayingId] = useState<number | null>(null);
    const [loadingId, setLoadingId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // Load fillers from API
    useEffect(() => {
        async function fetchFillers() {
            try {
                const data = await getFillers();
                setFillers(data);
            } catch (error) {
                console.error("Error fetching fillers:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchFillers();
    }, []);

    const filteredFillers = fillers.filter((f) => f.category === activeCategory);

    const handleAdd = async () => {
        if (!newText.trim()) return;
        setSaving(true);
        try {
            const newFiller = await saveFiller({
                text: newText,
                category: activeCategory,
                speaker: newSpeaker,
            });
            setFillers([...fillers, newFiller]);
            setNewText("");
        } catch (error) {
            console.error("Error adding filler:", error);
            alert("Error adding phrase");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        console.log("handleDelete called with id:", id);
        const confirmed = window.confirm("هل تريد حذف هذه العبارة؟ / Delete this phrase?");
        console.log("Confirmation result:", confirmed);
        if (!confirmed) return;

        try {
            console.log("Calling deleteFiller API...");
            await deleteFiller(id);
            console.log("Delete successful, updating state");
            setFillers(fillers.filter((f) => f.id !== id));
        } catch (error) {
            console.error("Error deleting filler:", error);
            alert("Error deleting phrase");
        }
    };

    const handlePlayAudio = async (id: number, text: string, speaker: string) => {
        // Stop any currently playing audio
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }

        if (playingId === id) {
            setPlayingId(null);
            return;
        }

        setError(null);
        setLoadingId(id);

        try {
            // Map Arabic speaker names to voice names
            const voiceName = speaker === "سارة" ? "sara" : "nexus";

            // Call ElevenLabs TTS API via backend
            const response = await fetch("/api/admin/voices/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: text,
                    voice: voiceName,
                    stability: 0.5,
                    similarity_boost: 0.75,
                    speed: 1.0,
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
                setPlayingId(null);
                URL.revokeObjectURL(audioUrl);
            };

            audio.onerror = () => {
                setPlayingId(null);
                setError("Failed to play audio");
                URL.revokeObjectURL(audioUrl);
            };

            setPlayingId(id);
            await audio.play();

        } catch (err) {
            console.error("TTS error:", err);
            setError(err instanceof Error ? err.message : "TTS failed");
            setPlayingId(null);
        } finally {
            setLoadingId(null);
        }
    };

    const handleStopAudio = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setPlayingId(null);
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
                    <h1 className="text-3xl font-bold">Filler Phrases</h1>
                    <p className="text-muted-foreground">Manage Arabic filler phrases</p>
                </div>
            </div>

            {error && (
                <div className="rounded-lg bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 p-4 text-red-700 dark:text-red-300">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Category tabs */}
            <div className="flex flex-wrap gap-2">
                {categories.map((cat) => (
                    <button
                        key={cat.id}
                        onClick={() => setActiveCategory(cat.id)}
                        className={`px-4 py-2 rounded-lg transition-colors ${activeCategory === cat.id
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted hover:bg-muted/80"
                            }`}
                        dir="rtl"
                    >
                        {cat.label}
                    </button>
                ))}
            </div>

            {/* Add new phrase */}
            <div className="rounded-xl bg-card border p-4">
                <h3 className="font-medium mb-4">Add New Phrase</h3>
                <div className="flex flex-col sm:flex-row gap-4">
                    <input
                        type="text"
                        value={newText}
                        onChange={(e) => setNewText(e.target.value)}
                        placeholder="أدخل العبارة..."
                        dir="rtl"
                        className="flex-1 px-3 py-2 rounded-lg border bg-background"
                    />
                    <select
                        value={newSpeaker}
                        onChange={(e) => setNewSpeaker(e.target.value as "سارة" | "نِكسوس")}
                        className="px-3 py-2 rounded-lg border bg-background"
                        dir="rtl"
                    >
                        <option value="سارة">سارة</option>
                        <option value="نِكسوس">نِكسوس</option>
                    </select>
                    <button
                        onClick={handleAdd}
                        disabled={saving || !newText.trim()}
                        className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 flex items-center gap-2 disabled:opacity-50"
                    >
                        {saving ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                        Add
                    </button>
                </div>
            </div>

            {/* Phrases list */}
            <div className="space-y-3">
                {filteredFillers.map((filler) => (
                    <div
                        key={filler.id}
                        className="rounded-xl bg-card border p-4 flex items-center gap-4"
                    >
                        <div className="flex-1" dir="rtl">
                            <p className="text-lg">{filler.text}</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                Speaker: {filler.speaker}
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => playingId === filler.id ? handleStopAudio() : handlePlayAudio(filler.id, filler.text, filler.speaker)}
                                disabled={loadingId === filler.id}
                                className={`p-2 rounded-lg transition-colors ${playingId === filler.id
                                    ? "bg-primary text-primary-foreground"
                                    : "hover:bg-muted"
                                    } disabled:opacity-50`}
                                title={playingId === filler.id ? "Stop" : "Play with ElevenLabs"}
                            >
                                {loadingId === filler.id ? (
                                    <Loader2 size={18} className="animate-spin" />
                                ) : playingId === filler.id ? (
                                    <Square size={18} />
                                ) : (
                                    <Volume2 size={18} />
                                )}
                            </button>
                            <button
                                onClick={() => handleDelete(filler.id)}
                                className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900 text-red-600 transition-colors"
                            >
                                <Trash2 size={18} />
                            </button>
                        </div>
                    </div>
                ))}

                {filteredFillers.length === 0 && (
                    <div className="text-center py-12 text-muted-foreground">
                        No phrases in this category
                    </div>
                )}
            </div>
        </div>
    );
}
