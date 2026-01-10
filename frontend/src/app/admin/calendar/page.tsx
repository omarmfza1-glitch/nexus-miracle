"use client";

import { useState, useRef, useEffect } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import { EventClickArg, EventDropArg, DateSelectArg } from "@fullcalendar/core";

// Initial appointments data (will be replaced with API call)
const initialAppointments = [
    {
        id: "NX961700",
        patientName: "عمر الغامدي",
        patientPhone: "+966512345678",
        doctorId: "dr_001",
        doctorName: "دكتور فهد الغامدي",
        specialty: "العظام",
        branch: "الفرع الرئيسي",
        scheduledAt: "2026-01-10T08:00:00",
        endAt: "2026-01-10T08:30:00",
        status: "confirmed",
        source: "website",
        insurance: "بوبا",
        notes: "",
        createdAt: "2026-01-09T15:30:00",
        doctorColor: "#3498DB",
    },
    {
        id: "NX961698",
        patientName: "محمد العتيبي",
        patientPhone: "+966551234567",
        doctorId: "dr_002",
        doctorName: "دكتورة سارة العتيبي",
        specialty: "العظام",
        branch: "فرع النخيل",
        scheduledAt: "2026-01-10T10:00:00",
        endAt: "2026-01-10T10:30:00",
        status: "pending",
        source: "phone",
        insurance: "التعاونية",
        notes: "مريض يعاني من آلام الظهر",
        createdAt: "2026-01-09T16:45:00",
        doctorColor: "#9B59B6",
    },
    {
        id: "NX961695",
        patientName: "فاطمة الشمري",
        patientPhone: "+966501234567",
        doctorId: "dr_001",
        doctorName: "دكتور فهد الغامدي",
        specialty: "العظام",
        branch: "الفرع الرئيسي",
        scheduledAt: "2026-01-11T14:00:00",
        endAt: "2026-01-11T14:30:00",
        status: "pending",
        source: "phone",
        insurance: "",
        notes: "متابعة بعد العملية",
        createdAt: "2026-01-10T09:00:00",
        doctorColor: "#3498DB",
    },
    {
        id: "NX961690",
        patientName: "أحمد المالكي",
        patientPhone: "+966559876543",
        doctorId: "dr_003",
        doctorName: "دكتور محمد الشهري",
        specialty: "الباطنية",
        branch: "الفرع الرئيسي",
        scheduledAt: "2026-01-12T09:00:00",
        endAt: "2026-01-12T09:30:00",
        status: "confirmed",
        source: "website",
        insurance: "ميدغلف",
        notes: "",
        createdAt: "2026-01-10T11:30:00",
        doctorColor: "#27AE60",
    },
    {
        id: "NX961685",
        patientName: "نورة القحطاني",
        patientPhone: "+966543216789",
        doctorId: "dr_002",
        doctorName: "دكتورة سارة العتيبي",
        specialty: "العظام",
        branch: "فرع النخيل",
        scheduledAt: "2026-01-10T15:00:00",
        endAt: "2026-01-10T15:30:00",
        status: "cancelled",
        source: "website",
        insurance: "الراجحي",
        notes: "ألغت المريضة",
        createdAt: "2026-01-08T14:00:00",
        doctorColor: "#9B59B6",
    },
];

const doctors = [
    { id: "dr_001", name: "دكتور فهد الغامدي", color: "#3498DB" },
    { id: "dr_002", name: "دكتورة سارة العتيبي", color: "#9B59B6" },
    { id: "dr_003", name: "دكتور محمد الشهري", color: "#27AE60" },
];

const statusConfig = {
    pending: { label: "بانتظار التأكيد", color: "#F1C40F", bgColor: "rgba(241, 196, 15, 0.2)" },
    confirmed: { label: "مؤكد", color: "#27AE60", bgColor: "rgba(39, 174, 96, 0.2)" },
    cancelled: { label: "ملغي", color: "#E74C3C", bgColor: "rgba(231, 76, 60, 0.2)" },
};

const sourceLabels = {
    website: "🌐 الموقع",
    phone: "📞 مكالمة هاتفية",
};

type Appointment = typeof initialAppointments[0];

export default function CalendarPage() {
    const calendarRef = useRef<FullCalendar>(null);
    const [appointments, setAppointments] = useState(initialAppointments);
    const [selectedDoctors, setSelectedDoctors] = useState<string[]>(doctors.map(d => d.id));
    const [selectedStatuses, setSelectedStatuses] = useState<string[]>(["pending", "confirmed"]);
    const [selectedBranch, setSelectedBranch] = useState("all");
    const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
    const [showRescheduleModal, setShowRescheduleModal] = useState(false);
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [cancelReason, setCancelReason] = useState("");
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

    // Show toast notification
    const showToast = (message: string, type: "success" | "error" = "success") => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    // Filter appointments
    const filteredAppointments = appointments.filter(apt => {
        if (!selectedDoctors.includes(apt.doctorId)) return false;
        if (!selectedStatuses.includes(apt.status)) return false;
        if (selectedBranch !== "all" && apt.branch !== selectedBranch) return false;
        return true;
    });

    // Convert to FullCalendar events
    const events = filteredAppointments.map(apt => ({
        id: apt.id,
        title: apt.patientName,
        start: apt.scheduledAt,
        end: apt.endAt,
        backgroundColor: apt.status === "cancelled"
            ? statusConfig.cancelled.bgColor
            : apt.status === "confirmed"
                ? statusConfig.confirmed.color
                : apt.doctorColor,
        borderColor: apt.status === "cancelled"
            ? statusConfig.cancelled.color
            : apt.status === "confirmed"
                ? statusConfig.confirmed.color
                : apt.doctorColor,
        textColor: apt.status === "cancelled" ? "#999" : "#fff",
        extendedProps: { ...apt },
        classNames: apt.status === "cancelled" ? ["cancelled-event"] : [],
    }));

    // Handle event click
    const handleEventClick = (info: EventClickArg) => {
        const aptId = info.event.id;
        const apt = appointments.find(a => a.id === aptId);
        if (apt) {
            setSelectedAppointment(apt);
        }
    };

    // Handle event drop (drag-and-drop reschedule)
    const handleEventDrop = (info: EventDropArg) => {
        const aptId = info.event.id;
        const apt = appointments.find(a => a.id === aptId);
        const newStart = info.event.start;
        const newEnd = info.event.end;

        if (!apt || !newStart) {
            info.revert();
            return;
        }

        if (confirm(`نقل موعد ${apt.patientName} إلى ${newStart.toLocaleString("ar-SA")}؟`)) {
            // Update appointment in state
            setAppointments(prev => prev.map(a =>
                a.id === aptId
                    ? {
                        ...a,
                        scheduledAt: newStart.toISOString(),
                        endAt: newEnd?.toISOString() || new Date(newStart.getTime() + 30 * 60000).toISOString()
                    }
                    : a
            ));
            showToast(`✅ تم نقل موعد ${apt.patientName} بنجاح`);
        } else {
            info.revert();
        }
    };

    // Toggle doctor filter
    const toggleDoctor = (doctorId: string) => {
        setSelectedDoctors(prev =>
            prev.includes(doctorId)
                ? prev.filter(id => id !== doctorId)
                : [...prev, doctorId]
        );
    };

    // Toggle status filter
    const toggleStatus = (status: string) => {
        setSelectedStatuses(prev =>
            prev.includes(status)
                ? prev.filter(s => s !== status)
                : [...prev, status]
        );
    };

    // Confirm appointment
    const confirmAppointment = () => {
        if (selectedAppointment) {
            setAppointments(prev => prev.map(apt =>
                apt.id === selectedAppointment.id
                    ? { ...apt, status: "confirmed" }
                    : apt
            ));
            showToast(`✅ تم تأكيد موعد ${selectedAppointment.patientName}`);
            setSelectedAppointment(null);
            // TODO: API call + WhatsApp notification
        }
    };

    // Cancel appointment
    const cancelAppointment = () => {
        if (selectedAppointment && cancelReason) {
            setAppointments(prev => prev.map(apt =>
                apt.id === selectedAppointment.id
                    ? { ...apt, status: "cancelled", notes: cancelReason }
                    : apt
            ));
            showToast(`❌ تم إلغاء موعد ${selectedAppointment.patientName}`, "error");
            setShowCancelModal(false);
            setCancelReason("");
            setSelectedAppointment(null);
            // TODO: API call + notification
        }
    };

    // Navigate calendar
    const navigateToday = () => calendarRef.current?.getApi().today();

    return (
        <div className="h-[calc(100vh-6rem)]" dir="rtl">
            <div className="flex h-full gap-6">
                {/* Filters Sidebar */}
                <div className="w-64 flex-shrink-0 bg-card border rounded-xl p-4 overflow-y-auto">
                    <h2 className="text-lg font-semibold mb-4">🔍 الفلاتر</h2>

                    {/* Quick Filters */}
                    <div className="mb-6">
                        <button
                            onClick={navigateToday}
                            className="w-full py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium mb-2"
                        >
                            📅 اليوم
                        </button>
                    </div>

                    {/* Doctors Filter */}
                    <div className="mb-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">الأطباء</h3>
                        <div className="space-y-2">
                            {doctors.map(doctor => (
                                <label key={doctor.id} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={selectedDoctors.includes(doctor.id)}
                                        onChange={() => toggleDoctor(doctor.id)}
                                        className="rounded"
                                    />
                                    <span
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: doctor.color }}
                                    />
                                    <span className="text-sm">{doctor.name}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Status Filter */}
                    <div className="mb-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">الحالة</h3>
                        <div className="space-y-2">
                            {Object.entries(statusConfig).map(([status, config]) => (
                                <label key={status} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={selectedStatuses.includes(status)}
                                        onChange={() => toggleStatus(status)}
                                        className="rounded"
                                    />
                                    <span
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: config.color }}
                                    />
                                    <span className="text-sm">{config.label}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Branch Filter */}
                    <div className="mb-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">الفرع</h3>
                        <select
                            value={selectedBranch}
                            onChange={(e) => setSelectedBranch(e.target.value)}
                            className="w-full px-3 py-2 border rounded-lg bg-background text-sm"
                        >
                            <option value="all">جميع الفروع</option>
                            <option value="الفرع الرئيسي">الفرع الرئيسي</option>
                            <option value="فرع النخيل">فرع النخيل</option>
                        </select>
                    </div>

                    {/* Stats */}
                    <div className="pt-4 border-t">
                        <p className="text-sm text-muted-foreground">
                            إجمالي المواعيد: <span className="font-bold">{filteredAppointments.length}</span>
                        </p>
                    </div>
                </div>

                {/* Calendar */}
                <div className="flex-1 bg-card border rounded-xl p-4 overflow-hidden">
                    <style jsx global>{`
            .fc {
              font-family: inherit;
              direction: rtl;
            }
            .fc-toolbar-title {
              font-size: 1.25rem !important;
              font-weight: 600;
            }
            .fc-button {
              background: hsl(var(--primary)) !important;
              border: none !important;
              font-family: inherit !important;
            }
            .fc-button:hover {
              background: hsl(var(--primary) / 0.9) !important;
            }
            .fc-button-active {
              background: hsl(var(--primary) / 0.8) !important;
            }
            .fc-event {
              cursor: pointer;
              border-radius: 4px;
              font-size: 0.8rem;
              padding: 2px 4px;
            }
            .fc-event-title {
              font-weight: 500;
            }
            .cancelled-event {
              text-decoration: line-through;
              opacity: 0.7;
            }
            .fc-timegrid-slot {
              height: 40px;
            }
            .fc-day-today {
              background: hsl(var(--primary) / 0.05) !important;
            }
            .fc-col-header-cell {
              background: hsl(var(--muted));
              padding: 8px;
              font-weight: 600;
            }
            .fc-timegrid-now-indicator-line {
              border-color: #E74C3C;
              border-width: 2px;
            }
            .fc-timegrid-now-indicator-arrow {
              border-color: #E74C3C;
            }
          `}</style>

                    <FullCalendar
                        ref={calendarRef}
                        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                        initialView="timeGridWeek"
                        headerToolbar={{
                            right: "prev,next today",
                            center: "title",
                            left: "dayGridMonth,timeGridWeek,timeGridDay",
                        }}
                        buttonText={{
                            today: "اليوم",
                            month: "شهر",
                            week: "أسبوع",
                            day: "يوم",
                        }}
                        locale="ar-sa"
                        direction="rtl"
                        firstDay={6} // Saturday
                        slotMinTime="08:00:00"
                        slotMaxTime="22:00:00"
                        slotDuration="00:30:00"
                        allDaySlot={false}
                        nowIndicator={true}
                        editable={true}
                        selectable={true}
                        selectMirror={true}
                        events={events}
                        eventClick={handleEventClick}
                        eventDrop={handleEventDrop}
                        height="100%"
                        stickyHeaderDates={true}
                        dayHeaderFormat={{ weekday: "long" }}
                        slotLabelFormat={{
                            hour: "2-digit",
                            minute: "2-digit",
                            hour12: false,
                        }}
                        eventTimeFormat={{
                            hour: "2-digit",
                            minute: "2-digit",
                            hour12: false,
                        }}
                    />
                </div>
            </div>

            {/* Appointment Details Modal */}
            {selectedAppointment && !showCancelModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedAppointment(null)}>
                    <div className="bg-background rounded-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-semibold">📋 تفاصيل الموعد</h3>
                            <button onClick={() => setSelectedAppointment(null)} className="text-muted-foreground hover:text-foreground text-2xl">
                                ×
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Patient Info */}
                            <div className="bg-muted p-4 rounded-lg">
                                <p className="text-sm text-muted-foreground">المريض</p>
                                <p className="text-lg font-semibold">{selectedAppointment.patientName}</p>
                                <p className="text-sm">{selectedAppointment.patientPhone}</p>
                            </div>

                            {/* Doctor Info */}
                            <div className="flex items-center gap-3 p-4 border rounded-lg">
                                <div
                                    className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold"
                                    style={{ backgroundColor: selectedAppointment.doctorColor }}
                                >
                                    {selectedAppointment.doctorName.slice(6, 8)}
                                </div>
                                <div>
                                    <p className="font-medium">{selectedAppointment.doctorName}</p>
                                    <p className="text-sm text-muted-foreground">{selectedAppointment.specialty}</p>
                                </div>
                            </div>

                            {/* Date/Time */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-3 border rounded-lg">
                                    <p className="text-sm text-muted-foreground">📅 التاريخ</p>
                                    <p className="font-medium">
                                        {new Date(selectedAppointment.scheduledAt).toLocaleDateString("ar-SA", {
                                            weekday: "long",
                                            year: "numeric",
                                            month: "long",
                                            day: "numeric",
                                        })}
                                    </p>
                                </div>
                                <div className="p-3 border rounded-lg">
                                    <p className="text-sm text-muted-foreground">🕐 الوقت</p>
                                    <p className="font-medium text-xl">
                                        {new Date(selectedAppointment.scheduledAt).toLocaleTimeString("ar-SA", {
                                            hour: "2-digit",
                                            minute: "2-digit",
                                        })}
                                    </p>
                                </div>
                            </div>

                            {/* Branch */}
                            <div className="p-3 border rounded-lg">
                                <p className="text-sm text-muted-foreground">📍 الفرع</p>
                                <p className="font-medium">{selectedAppointment.branch}</p>
                            </div>

                            {/* Status */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-muted-foreground">الحالة:</span>
                                <span
                                    className="px-3 py-1 rounded-full text-sm font-medium"
                                    style={{
                                        backgroundColor: statusConfig[selectedAppointment.status as keyof typeof statusConfig].bgColor,
                                        color: statusConfig[selectedAppointment.status as keyof typeof statusConfig].color,
                                    }}
                                >
                                    {statusConfig[selectedAppointment.status as keyof typeof statusConfig].label}
                                </span>
                            </div>

                            {/* Insurance */}
                            {selectedAppointment.insurance && (
                                <div className="p-3 border rounded-lg">
                                    <p className="text-sm text-muted-foreground">💳 التأمين</p>
                                    <p className="font-medium">{selectedAppointment.insurance}</p>
                                </div>
                            )}

                            {/* Notes */}
                            {selectedAppointment.notes && (
                                <div className="p-3 border rounded-lg">
                                    <p className="text-sm text-muted-foreground">📝 ملاحظات</p>
                                    <p>{selectedAppointment.notes}</p>
                                </div>
                            )}

                            {/* Source & Created */}
                            <div className="pt-3 border-t text-sm text-muted-foreground">
                                <p>تم الحجز عن طريق: {sourceLabels[selectedAppointment.source as keyof typeof sourceLabels]}</p>
                                <p>وقت الحجز: {new Date(selectedAppointment.createdAt).toLocaleString("ar-SA")}</p>
                            </div>

                            {/* Actions */}
                            {selectedAppointment.status !== "cancelled" && (
                                <div className="flex gap-2 pt-4 border-t">
                                    {selectedAppointment.status === "pending" && (
                                        <button
                                            onClick={confirmAppointment}
                                            className="flex-1 py-3 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600"
                                        >
                                            ✓ تأكيد
                                        </button>
                                    )}
                                    <button
                                        onClick={() => setShowCancelModal(true)}
                                        className="flex-1 py-3 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600"
                                    >
                                        ✕ إلغاء
                                    </button>
                                    <button
                                        onClick={() => setShowRescheduleModal(true)}
                                        className="flex-1 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600"
                                    >
                                        📅 تغيير الموعد
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Cancel Modal */}
            {showCancelModal && selectedAppointment && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-background rounded-xl p-6 max-w-md w-full mx-4">
                        <h3 className="text-xl font-semibold mb-4">❌ إلغاء الموعد</h3>
                        <p className="text-muted-foreground mb-4">
                            سيتم إلغاء موعد <strong>{selectedAppointment.patientName}</strong> وإرسال إشعار للمريض.
                        </p>

                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">سبب الإلغاء</label>
                            <textarea
                                value={cancelReason}
                                onChange={(e) => setCancelReason(e.target.value)}
                                className="w-full px-3 py-2 border rounded-lg"
                                rows={3}
                                placeholder="أدخل سبب الإلغاء..."
                            />
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={() => { setShowCancelModal(false); setCancelReason(""); }}
                                className="flex-1 py-2 border rounded-lg"
                            >
                                رجوع
                            </button>
                            <button
                                onClick={cancelAppointment}
                                disabled={!cancelReason}
                                className="flex-1 py-2 bg-red-500 text-white rounded-lg disabled:opacity-50"
                            >
                                تأكيد الإلغاء
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast Notification */}
            {toast && (
                <div
                    className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-6 py-3 rounded-lg shadow-lg z-50 animate-pulse ${toast.type === "success" ? "bg-green-500" : "bg-red-500"
                        } text-white font-medium`}
                >
                    {toast.message}
                </div>
            )}
        </div>
    );
}
