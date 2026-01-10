"use client";

import { useState, useEffect } from "react";

// Mock appointments data (will be replaced with API call)
const mockAppointments = [
    {
        id: "NX961700",
        patientName: "عمر الغامدي",
        patientPhone: "+966512345678",
        doctorName: "دكتور فهد الغامدي",
        doctorId: "dr_001",
        specialty: "العظام",
        scheduledAt: "2025-01-10T08:00:00",
        branch: "الفرع الرئيسي",
        status: "confirmed",
        source: "website",
        notes: "",
    },
    {
        id: "NX961698",
        patientName: "محمد العتيبي",
        patientPhone: "+966551234567",
        doctorName: "دكتورة سارة العتيبي",
        doctorId: "dr_002",
        specialty: "العظام",
        scheduledAt: "2025-01-10T10:00:00",
        branch: "فرع النخيل",
        status: "confirmed",
        source: "phone",
        notes: "مريض يعاني من آلام الظهر",
    },
    {
        id: "NX961695",
        patientName: "فاطمة الشمري",
        patientPhone: "+966501234567",
        doctorName: "دكتور فهد الغامدي",
        doctorId: "dr_001",
        specialty: "العظام",
        scheduledAt: "2025-01-11T14:00:00",
        branch: "الفرع الرئيسي",
        status: "pending",
        source: "phone",
        notes: "",
    },
    {
        id: "NX961690",
        patientName: "أحمد المالكي",
        patientPhone: "+966559876543",
        doctorName: "دكتور محمد الشهري",
        doctorId: "dr_003",
        specialty: "الباطنية",
        scheduledAt: "2025-01-12T09:00:00",
        branch: "الفرع الرئيسي",
        status: "confirmed",
        source: "website",
        notes: "",
    },
];

type ViewMode = "calendar" | "list";

// Generate calendar days for a month
function generateCalendarDays(year: number, month: number) {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDayOfWeek = firstDay.getDay();

    const days: (number | null)[] = [];

    // Add empty slots for days before the first day
    for (let i = 0; i < startDayOfWeek; i++) {
        days.push(null);
    }

    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
        days.push(day);
    }

    return days;
}

const dayNames = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
const monthNames = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
];

const statusColors: Record<string, string> = {
    confirmed: "bg-green-100 text-green-800",
    pending: "bg-yellow-100 text-yellow-800",
    cancelled: "bg-red-100 text-red-800",
    completed: "bg-blue-100 text-blue-800",
};

const statusLabels: Record<string, string> = {
    confirmed: "مؤكد",
    pending: "بانتظار",
    cancelled: "ملغي",
    completed: "مكتمل",
};

const sourceLabels: Record<string, string> = {
    website: "🌐 الموقع",
    phone: "📞 الهاتف",
};

export default function AppointmentsPage() {
    const [viewMode, setViewMode] = useState<ViewMode>("calendar");
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState<Date | null>(null);
    const [appointments, setAppointments] = useState(mockAppointments);
    const [selectedAppointment, setSelectedAppointment] = useState<typeof mockAppointments[0] | null>(null);
    const [filterStatus, setFilterStatus] = useState("all");
    const [filterSource, setFilterSource] = useState("all");

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const calendarDays = generateCalendarDays(year, month);

    // Get appointments for a specific day
    function getAppointmentsForDay(day: number) {
        const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        return appointments.filter(apt => apt.scheduledAt.startsWith(dateStr));
    }

    // Get filtered appointments
    const filteredAppointments = appointments.filter(apt => {
        if (filterStatus !== "all" && apt.status !== filterStatus) return false;
        if (filterSource !== "all" && apt.source !== filterSource) return false;
        if (selectedDate) {
            const aptDate = new Date(apt.scheduledAt);
            if (aptDate.toDateString() !== selectedDate.toDateString()) return false;
        }
        return true;
    });

    // Navigate months
    const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
    const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
    const goToToday = () => {
        setCurrentDate(new Date());
        setSelectedDate(new Date());
    };

    return (
        <div className="space-y-6" dir="rtl">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold">📅 جدول المواعيد</h1>
                    <p className="text-muted-foreground">عرض وإدارة مواعيد المرضى</p>
                </div>

                <div className="flex items-center gap-3">
                    {/* View Toggle */}
                    <div className="flex bg-muted rounded-lg p-1">
                        <button
                            onClick={() => setViewMode("calendar")}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${viewMode === "calendar" ? "bg-background shadow" : ""
                                }`}
                        >
                            📆 التقويم
                        </button>
                        <button
                            onClick={() => setViewMode("list")}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${viewMode === "list" ? "bg-background shadow" : ""
                                }`}
                        >
                            📋 القائمة
                        </button>
                    </div>

                    <button
                        onClick={goToToday}
                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium"
                    >
                        اليوم
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3">
                <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 border rounded-lg bg-background"
                >
                    <option value="all">جميع الحالات</option>
                    <option value="confirmed">مؤكد</option>
                    <option value="pending">بانتظار</option>
                    <option value="cancelled">ملغي</option>
                    <option value="completed">مكتمل</option>
                </select>

                <select
                    value={filterSource}
                    onChange={(e) => setFilterSource(e.target.value)}
                    className="px-3 py-2 border rounded-lg bg-background"
                >
                    <option value="all">جميع المصادر</option>
                    <option value="website">الموقع</option>
                    <option value="phone">الهاتف</option>
                </select>

                {selectedDate && (
                    <button
                        onClick={() => setSelectedDate(null)}
                        className="px-3 py-2 bg-muted rounded-lg text-sm flex items-center gap-2"
                    >
                        ✕ إزالة فلتر التاريخ
                    </button>
                )}
            </div>

            {viewMode === "calendar" ? (
                /* Calendar View */
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Calendar */}
                    <div className="lg:col-span-2 bg-card border rounded-xl p-6">
                        {/* Month Navigation */}
                        <div className="flex items-center justify-between mb-6">
                            <button onClick={prevMonth} className="p-2 hover:bg-muted rounded-lg">
                                →
                            </button>
                            <h2 className="text-xl font-semibold">
                                {monthNames[month]} {year}
                            </h2>
                            <button onClick={nextMonth} className="p-2 hover:bg-muted rounded-lg">
                                ←
                            </button>
                        </div>

                        {/* Day Headers */}
                        <div className="grid grid-cols-7 gap-1 mb-2">
                            {dayNames.map(day => (
                                <div key={day} className="text-center text-sm font-medium text-muted-foreground py-2">
                                    {day}
                                </div>
                            ))}
                        </div>

                        {/* Calendar Grid */}
                        <div className="grid grid-cols-7 gap-1">
                            {calendarDays.map((day, index) => {
                                if (day === null) {
                                    return <div key={index} className="h-24" />;
                                }

                                const dayAppointments = getAppointmentsForDay(day);
                                const isToday =
                                    day === new Date().getDate() &&
                                    month === new Date().getMonth() &&
                                    year === new Date().getFullYear();
                                const isSelected = selectedDate &&
                                    day === selectedDate.getDate() &&
                                    month === selectedDate.getMonth();

                                return (
                                    <button
                                        key={index}
                                        onClick={() => setSelectedDate(new Date(year, month, day))}
                                        className={`h-24 p-2 border rounded-lg text-right hover:bg-muted/50 transition-colors ${isToday ? "border-primary bg-primary/5" : ""
                                            } ${isSelected ? "ring-2 ring-primary" : ""}`}
                                    >
                                        <span className={`text-sm font-medium ${isToday ? "text-primary" : ""}`}>
                                            {day}
                                        </span>

                                        {dayAppointments.length > 0 && (
                                            <div className="mt-1 space-y-1">
                                                {dayAppointments.slice(0, 2).map(apt => (
                                                    <div
                                                        key={apt.id}
                                                        className={`text-xs px-1 py-0.5 rounded truncate ${apt.source === "phone" ? "bg-purple-100 text-purple-800" : "bg-blue-100 text-blue-800"
                                                            }`}
                                                    >
                                                        {new Date(apt.scheduledAt).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" })}
                                                    </div>
                                                ))}
                                                {dayAppointments.length > 2 && (
                                                    <div className="text-xs text-muted-foreground">
                                                        +{dayAppointments.length - 2} المزيد
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Selected Day Appointments */}
                    <div className="bg-card border rounded-xl p-6">
                        <h3 className="text-lg font-semibold mb-4">
                            {selectedDate
                                ? `مواعيد ${selectedDate.toLocaleDateString("ar-SA", { weekday: "long", day: "numeric", month: "long" })}`
                                : "اختر يوماً لعرض المواعيد"
                            }
                        </h3>

                        {selectedDate && (
                            <div className="space-y-3">
                                {filteredAppointments.length === 0 ? (
                                    <p className="text-muted-foreground text-center py-8">
                                        لا توجد مواعيد في هذا اليوم
                                    </p>
                                ) : (
                                    filteredAppointments.map(apt => (
                                        <button
                                            key={apt.id}
                                            onClick={() => setSelectedAppointment(apt)}
                                            className="w-full text-right p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                                        >
                                            <div className="flex items-start justify-between">
                                                <span className={`text-xs px-2 py-1 rounded ${statusColors[apt.status]}`}>
                                                    {statusLabels[apt.status]}
                                                </span>
                                                <span className="font-medium text-lg">
                                                    {new Date(apt.scheduledAt).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" })}
                                                </span>
                                            </div>
                                            <p className="font-medium mt-2">{apt.patientName}</p>
                                            <p className="text-sm text-muted-foreground">{apt.doctorName}</p>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                {sourceLabels[apt.source]} • {apt.id}
                                            </p>
                                        </button>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                </div>
            ) : (
                /* List View */
                <div className="bg-card border rounded-xl overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-muted">
                            <tr>
                                <th className="px-4 py-3 text-right font-medium">رقم الحجز</th>
                                <th className="px-4 py-3 text-right font-medium">المريض</th>
                                <th className="px-4 py-3 text-right font-medium">الطبيب</th>
                                <th className="px-4 py-3 text-right font-medium">التاريخ والوقت</th>
                                <th className="px-4 py-3 text-right font-medium">المصدر</th>
                                <th className="px-4 py-3 text-right font-medium">الحالة</th>
                                <th className="px-4 py-3 text-right font-medium">إجراءات</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {filteredAppointments.map(apt => (
                                <tr key={apt.id} className="hover:bg-muted/50">
                                    <td className="px-4 py-3 font-mono text-sm">{apt.id}</td>
                                    <td className="px-4 py-3">
                                        <p className="font-medium">{apt.patientName}</p>
                                        <p className="text-sm text-muted-foreground">{apt.patientPhone}</p>
                                    </td>
                                    <td className="px-4 py-3">
                                        <p>{apt.doctorName}</p>
                                        <p className="text-sm text-muted-foreground">{apt.specialty}</p>
                                    </td>
                                    <td className="px-4 py-3">
                                        <p>{new Date(apt.scheduledAt).toLocaleDateString("ar-SA")}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {new Date(apt.scheduledAt).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" })}
                                        </p>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`text-sm ${apt.source === "phone" ? "text-purple-600" : "text-blue-600"}`}>
                                            {sourceLabels[apt.source]}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`text-xs px-2 py-1 rounded ${statusColors[apt.status]}`}>
                                            {statusLabels[apt.status]}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        <button
                                            onClick={() => setSelectedAppointment(apt)}
                                            className="text-primary hover:underline text-sm"
                                        >
                                            عرض
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Appointment Detail Modal */}
            {selectedAppointment && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedAppointment(null)}>
                    <div className="bg-background rounded-xl p-6 max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-semibold">تفاصيل الموعد</h3>
                            <button onClick={() => setSelectedAppointment(null)} className="text-muted-foreground hover:text-foreground">
                                ✕
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">رقم الحجز</span>
                                <span className="font-mono font-bold">{selectedAppointment.id}</span>
                            </div>

                            <hr />

                            <div>
                                <p className="text-sm text-muted-foreground">المريض</p>
                                <p className="font-medium">{selectedAppointment.patientName}</p>
                                <p className="text-sm">{selectedAppointment.patientPhone}</p>
                            </div>

                            <div>
                                <p className="text-sm text-muted-foreground">الطبيب</p>
                                <p className="font-medium">{selectedAppointment.doctorName}</p>
                                <p className="text-sm">{selectedAppointment.specialty} • {selectedAppointment.branch}</p>
                            </div>

                            <div>
                                <p className="text-sm text-muted-foreground">الموعد</p>
                                <p className="font-medium">
                                    {new Date(selectedAppointment.scheduledAt).toLocaleDateString("ar-SA", {
                                        weekday: "long",
                                        year: "numeric",
                                        month: "long",
                                        day: "numeric"
                                    })}
                                </p>
                                <p className="text-lg font-bold text-primary">
                                    {new Date(selectedAppointment.scheduledAt).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" })}
                                </p>
                            </div>

                            <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded text-sm ${statusColors[selectedAppointment.status]}`}>
                                    {statusLabels[selectedAppointment.status]}
                                </span>
                                <span className="text-sm text-muted-foreground">
                                    {sourceLabels[selectedAppointment.source]}
                                </span>
                            </div>

                            {selectedAppointment.notes && (
                                <div>
                                    <p className="text-sm text-muted-foreground">ملاحظات</p>
                                    <p className="bg-muted p-2 rounded text-sm">{selectedAppointment.notes}</p>
                                </div>
                            )}

                            <div className="flex gap-2 pt-4">
                                <button className="flex-1 py-2 bg-green-500 text-white rounded-lg font-medium">
                                    ✓ تأكيد
                                </button>
                                <button className="flex-1 py-2 bg-red-500 text-white rounded-lg font-medium">
                                    ✕ إلغاء
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
