const API_BASE = "/api";

// Generic fetch wrapper with error handling
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options?.headers,
        },
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(error.detail || "API Error");
    }

    return res.json();
}

// Settings
export async function getSettings() {
    return fetchApi("/admin/settings");
}

export async function saveSettings(settings: Record<string, unknown>) {
    return fetchApi("/admin/settings", {
        method: "PUT",
        body: JSON.stringify(settings),
    });
}

// Doctors
export interface Doctor {
    id: number;
    name: string;
    name_ar: string;
    specialty: string;
    specialty_ar: string;
    branch: string;
    status: string;
    rating: number;
}

export interface DoctorListResponse {
    items: Doctor[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
}

export async function getDoctors(params?: { specialty?: string; page?: number }): Promise<DoctorListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.specialty) searchParams.set("specialty", params.specialty);
    if (params?.page) searchParams.set("page", params.page.toString());
    const query = searchParams.toString();
    return fetchApi(`/doctors${query ? `?${query}` : ""}`);
}

export async function getDoctorSlots(doctorId: number, date: string) {
    return fetchApi(`/doctors/${doctorId}/slots?date=${date}`);
}

// Insurance
export interface InsuranceResponse {
    found: boolean;
    coverage?: {
        company_name: string;
        company_name_ar: string;
        coverage_percent: number;
        copay_sar: number;
        network: string;
    };
}

export async function getInsurance(company: string): Promise<InsuranceResponse> {
    return fetchApi(`/insurance/${encodeURIComponent(company)}`);
}

// Appointments
export interface Appointment {
    id: number;
    patient_name: string;
    patient_phone: string;
    doctor_name: string;
    scheduled_at: string;
    status: string;
    notes?: string;
}

export async function getAppointments(params?: { page?: number; status?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.status) searchParams.set("status", params.status);
    const query = searchParams.toString();
    return fetchApi(`/appointments${query ? `?${query}` : ""}`);
}

// Voice Settings
export interface VoiceSettings {
    voice_id: string;
    stability: number;
    similarity_boost: number;
    style: number;
    speed: number;
}

export async function getVoiceSettings() {
    return fetchApi<{ sara: VoiceSettings; nexus: VoiceSettings }>("/admin/voices");
}

export async function saveVoiceSettings(voices: { sara: VoiceSettings; nexus: VoiceSettings }) {
    return fetchApi("/admin/voices", {
        method: "PUT",
        body: JSON.stringify(voices),
    });
}

export async function testVoice(voiceId: string, text: string) {
    return fetchApi("/admin/voices/test", {
        method: "POST",
        body: JSON.stringify({ voice_id: voiceId, text }),
    });
}

// Filler Phrases
export interface FillerPhrase {
    id: number;
    text: string;
    category: string;
    speaker: string;
    audio_url?: string;
}

export async function getFillers(): Promise<FillerPhrase[]> {
    return fetchApi("/admin/fillers");
}

export async function saveFiller(filler: Omit<FillerPhrase, "id">) {
    return fetchApi("/admin/fillers", {
        method: "POST",
        body: JSON.stringify(filler),
    });
}

export async function deleteFiller(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/admin/fillers/${id}`, { method: "DELETE" });
    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(error.detail || "Delete failed");
    }
    // 204 No Content - don't try to parse JSON
}

// Call Logs
export interface CallLog {
    id: string;
    phone: string;
    start_time: string;
    end_time?: string;
    duration_seconds?: number;
    status: string;
    transcript?: string;
}

export async function getCallLogs(params?: { page?: number; phone?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.phone) searchParams.set("phone", params.phone);
    const query = searchParams.toString();
    return fetchApi(`/admin/calls${query ? `?${query}` : ""}`);
}

export async function getCallTranscript(callId: string) {
    return fetchApi<{ transcript: string }>(`/admin/calls/${callId}/transcript`);
}
