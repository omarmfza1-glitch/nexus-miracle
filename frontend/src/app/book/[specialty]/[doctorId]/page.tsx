"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";

// Mock data
const mockDoctor = {
    id: "dr_001",
    name: "دكتور فهد الغامدي",
    title: "استشاري جراحة العظام",
    rating: 4.9,
    reviewCount: 120,
    branch: "الفرع الرئيسي",
    branchAddress: "الرياض، حي الملقا، شارع الأمير محمد بن عبدالعزيز",
};

// Generate next 30 days
function generateDates() {
    const dates = [];
    const today = new Date();

    for (let i = 0; i < 30; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);

        // Random availability (for demo)
        const isAvailable = Math.random() > 0.3;

        dates.push({
            date,
            day: date.getDate(),
            dayName: date.toLocaleDateString("ar-SA", { weekday: "short" }),
            monthName: date.toLocaleDateString("ar-SA", { month: "long" }),
            isAvailable,
            isToday: i === 0,
        });
    }

    return dates;
}

// Time slots
const timeSlots = {
    morning: ["08:00", "09:00", "10:00", "11:00"],
    afternoon: ["14:00", "15:00", "16:00"],
    evening: ["17:00", "18:00", "19:00"],
};

// Generate random availability for slots
function generateSlotAvailability() {
    const availability: Record<string, boolean> = {};
    Object.values(timeSlots).flat().forEach(slot => {
        availability[slot] = Math.random() > 0.3;
    });
    return availability;
}

export default function BookingCalendarPage() {
    const params = useParams();
    const router = useRouter();
    const specialty = params.specialty as string;
    const doctorId = params.doctorId as string;

    const [dates] = useState(generateDates);
    const [selectedDate, setSelectedDate] = useState<typeof dates[0] | null>(null);
    const [selectedTime, setSelectedTime] = useState<string | null>(null);
    const [slotAvailability, setSlotAvailability] = useState<Record<string, boolean>>({});
    const [showForm, setShowForm] = useState(false);
    const [loading, setLoading] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        fullName: "",
        phone: "",
        idLast4: "",
        insurance: "",
        notes: "",
    });
    const [formErrors, setFormErrors] = useState<Record<string, string>>({});

    // Get current month display
    const currentMonth = selectedDate?.monthName || dates[0]?.monthName;

    // Update slot availability when date changes
    useEffect(() => {
        if (selectedDate) {
            setSlotAvailability(generateSlotAvailability());
            setSelectedTime(null);
        }
    }, [selectedDate]);

    // Validate Saudi phone number
    const validatePhone = (phone: string) => {
        const cleaned = phone.replace(/\D/g, "");
        return /^(5|05|966|9665)\d{8}$/.test(cleaned);
    };

    // Handle form submission
    const handleSubmit = async () => {
        const errors: Record<string, string> = {};

        if (!formData.fullName.trim()) {
            errors.fullName = "الاسم مطلوب";
        }

        if (!formData.phone.trim()) {
            errors.phone = "رقم الجوال مطلوب";
        } else if (!validatePhone(formData.phone)) {
            errors.phone = "رقم جوال غير صحيح";
        }

        if (!formData.idLast4.trim() || formData.idLast4.length !== 4) {
            errors.idLast4 = "أدخل آخر 4 أرقام من الهوية";
        }

        setFormErrors(errors);

        if (Object.keys(errors).length > 0) return;

        setLoading(true);

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Navigate to confirmation
        const bookingData = {
            doctor: mockDoctor.name,
            date: selectedDate?.date.toISOString(),
            time: selectedTime,
            branch: mockDoctor.branch,
            address: mockDoctor.branchAddress,
            reference: `NX${Date.now().toString().slice(-6)}`,
        };

        // Store in sessionStorage for confirmation page
        sessionStorage.setItem("bookingConfirmation", JSON.stringify(bookingData));

        router.push("/book/confirm");
    };

    return (
        <div className="booking-page">
            {/* Header */}
            <header className="page-header">
                <button className="back-btn" onClick={() => router.back()}>
                    → العودة
                </button>
                <h1>حجز موعد</h1>
            </header>

            {/* Doctor Info Card */}
            <div className="doctor-card">
                <div className="avatar">
                    <span>دغ</span>
                </div>
                <div className="info">
                    <h2>{mockDoctor.name}</h2>
                    <p className="title">{mockDoctor.title}</p>
                    <p className="rating">⭐ {mockDoctor.rating} ({mockDoctor.reviewCount} تقييم)</p>
                    <p className="branch">📍 {mockDoctor.branch}</p>
                </div>
            </div>

            {/* Calendar */}
            <section className="calendar-section">
                <h3>اختر التاريخ</h3>
                <div className="month-header">
                    <span>{currentMonth} 2025</span>
                </div>

                <div className="dates-scroll">
                    {dates.map((d, i) => (
                        <button
                            key={i}
                            className={`date-btn ${d.isAvailable ? "available" : "unavailable"} ${selectedDate === d ? "selected" : ""} ${d.isToday ? "today" : ""}`}
                            disabled={!d.isAvailable}
                            onClick={() => setSelectedDate(d)}
                        >
                            <span className="day-name">{d.dayName}</span>
                            <span className="day-number">{d.day}</span>
                        </button>
                    ))}
                </div>
            </section>

            {/* Time Slots */}
            {selectedDate && (
                <section className="slots-section">
                    <h3>اختر الوقت</h3>

                    <div className="slot-group">
                        <h4>🌅 صباحاً</h4>
                        <div className="slots">
                            {timeSlots.morning.map(time => (
                                <button
                                    key={time}
                                    className={`slot-btn ${slotAvailability[time] ? "available" : "booked"} ${selectedTime === time ? "selected" : ""}`}
                                    disabled={!slotAvailability[time]}
                                    onClick={() => setSelectedTime(time)}
                                >
                                    {time}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="slot-group">
                        <h4>🌤️ ظهراً</h4>
                        <div className="slots">
                            {timeSlots.afternoon.map(time => (
                                <button
                                    key={time}
                                    className={`slot-btn ${slotAvailability[time] ? "available" : "booked"} ${selectedTime === time ? "selected" : ""}`}
                                    disabled={!slotAvailability[time]}
                                    onClick={() => setSelectedTime(time)}
                                >
                                    {time}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="slot-group">
                        <h4>🌙 مساءً</h4>
                        <div className="slots">
                            {timeSlots.evening.map(time => (
                                <button
                                    key={time}
                                    className={`slot-btn ${slotAvailability[time] ? "available" : "booked"} ${selectedTime === time ? "selected" : ""}`}
                                    disabled={!slotAvailability[time]}
                                    onClick={() => setSelectedTime(time)}
                                >
                                    {time}
                                </button>
                            ))}
                        </div>
                    </div>
                </section>
            )}

            {/* Booking Summary */}
            {selectedDate && selectedTime && (
                <section className="summary-section">
                    <h3>ملخص الحجز</h3>
                    <div className="summary-card">
                        <div className="summary-row">
                            <span>الطبيب:</span>
                            <span>{mockDoctor.name}</span>
                        </div>
                        <div className="summary-row">
                            <span>التاريخ:</span>
                            <span>{selectedDate.dayName} {selectedDate.day} {selectedDate.monthName}</span>
                        </div>
                        <div className="summary-row">
                            <span>الوقت:</span>
                            <span>{selectedTime}</span>
                        </div>
                        <div className="summary-row">
                            <span>الفرع:</span>
                            <span>{mockDoctor.branch}</span>
                        </div>
                    </div>

                    <button className="next-btn" onClick={() => setShowForm(true)}>
                        التالي ←
                    </button>
                </section>
            )}

            {/* Patient Form Modal */}
            {showForm && (
                <div className="modal-overlay" onClick={() => setShowForm(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <h3>بيانات المريض</h3>

                        <div className="form-group">
                            <label>الاسم الكامل *</label>
                            <input
                                type="text"
                                value={formData.fullName}
                                onChange={e => setFormData({ ...formData, fullName: e.target.value })}
                                placeholder="أدخل اسمك الكامل"
                            />
                            {formErrors.fullName && <span className="error">{formErrors.fullName}</span>}
                        </div>

                        <div className="form-group">
                            <label>رقم الجوال *</label>
                            <div className="phone-input">
                                <span className="prefix">+966</span>
                                <input
                                    type="tel"
                                    value={formData.phone}
                                    onChange={e => setFormData({ ...formData, phone: e.target.value })}
                                    placeholder="5XXXXXXXX"
                                />
                            </div>
                            {formErrors.phone && <span className="error">{formErrors.phone}</span>}
                        </div>

                        <div className="form-group">
                            <label>آخر 4 أرقام من الهوية *</label>
                            <input
                                type="text"
                                maxLength={4}
                                value={formData.idLast4}
                                onChange={e => setFormData({ ...formData, idLast4: e.target.value.replace(/\D/g, "") })}
                                placeholder="XXXX"
                            />
                            {formErrors.idLast4 && <span className="error">{formErrors.idLast4}</span>}
                        </div>

                        <div className="form-group">
                            <label>شركة التأمين</label>
                            <select
                                value={formData.insurance}
                                onChange={e => setFormData({ ...formData, insurance: e.target.value })}
                            >
                                <option value="">بدون تأمين</option>
                                <option value="bupa">بوبا</option>
                                <option value="tawuniya">التعاونية</option>
                                <option value="medgulf">ميدغلف</option>
                                <option value="alrajhi">الراجحي</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>ملاحظات</label>
                            <textarea
                                value={formData.notes}
                                onChange={e => setFormData({ ...formData, notes: e.target.value })}
                                placeholder="أي ملاحظات إضافية..."
                                rows={3}
                            />
                        </div>

                        <button
                            className="submit-btn"
                            onClick={handleSubmit}
                            disabled={loading}
                        >
                            {loading ? "جاري الحجز..." : "تأكيد الحجز"}
                        </button>
                    </div>
                </div>
            )}

            <style jsx>{`
        .booking-page {
          min-height: 100vh;
          background: #f8fafc;
          direction: rtl;
          font-family: "IBM Plex Sans Arabic", "Segoe UI", sans-serif;
          padding-bottom: 2rem;
        }

        .page-header {
          background: linear-gradient(135deg, #1B4F72 0%, #21618C 100%);
          color: white;
          padding: 1.25rem 1.5rem;
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .back-btn {
          background: rgba(255,255,255,0.2);
          border: none;
          color: white;
          padding: 0.5rem 0.75rem;
          border-radius: 8px;
          cursor: pointer;
          font-family: inherit;
        }

        .page-header h1 {
          font-size: 1.25rem;
          margin: 0;
          font-weight: 600;
        }

        /* Doctor Card */
        .doctor-card {
          background: white;
          margin: 1rem;
          border-radius: 16px;
          padding: 1.25rem;
          display: flex;
          gap: 1rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .doctor-card .avatar {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: linear-gradient(135deg, #1B4F72, #21618C);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 1.25rem;
          font-weight: 600;
        }

        .doctor-card .info h2 {
          font-size: 1.1rem;
          margin: 0 0 0.25rem;
          color: #1B4F72;
        }

        .doctor-card .title {
          font-size: 0.9rem;
          color: #64748b;
          margin: 0 0 0.25rem;
        }

        .doctor-card .rating, .doctor-card .branch {
          font-size: 0.85rem;
          margin: 0.25rem 0 0;
          color: #64748b;
        }

        /* Calendar */
        .calendar-section {
          padding: 1rem;
        }

        .calendar-section h3 {
          font-size: 1.1rem;
          color: #1B4F72;
          margin: 0 0 1rem;
        }

        .month-header {
          text-align: center;
          font-size: 1rem;
          font-weight: 600;
          color: #334155;
          margin-bottom: 1rem;
        }

        .dates-scroll {
          display: flex;
          gap: 0.5rem;
          overflow-x: auto;
          padding: 0.5rem 0;
          scrollbar-width: none;
        }

        .dates-scroll::-webkit-scrollbar {
          display: none;
        }

        .date-btn {
          flex-shrink: 0;
          width: 60px;
          padding: 0.75rem 0.5rem;
          border-radius: 12px;
          border: 2px solid transparent;
          background: white;
          cursor: pointer;
          text-align: center;
          font-family: inherit;
          transition: all 0.2s;
        }

        .date-btn .day-name {
          display: block;
          font-size: 0.75rem;
          color: #64748b;
          margin-bottom: 0.25rem;
        }

        .date-btn .day-number {
          display: block;
          font-size: 1.1rem;
          font-weight: 600;
          color: #334155;
        }

        .date-btn.available:hover {
          border-color: #27AE60;
        }

        .date-btn.unavailable {
          opacity: 0.4;
          cursor: not-allowed;
        }

        .date-btn.selected {
          background: #1B4F72;
          border-color: #1B4F72;
        }

        .date-btn.selected .day-name,
        .date-btn.selected .day-number {
          color: white;
        }

        .date-btn.today {
          border-color: #27AE60;
        }

        /* Time Slots */
        .slots-section {
          padding: 1rem;
        }

        .slots-section h3 {
          font-size: 1.1rem;
          color: #1B4F72;
          margin: 0 0 1rem;
        }

        .slot-group {
          margin-bottom: 1.25rem;
        }

        .slot-group h4 {
          font-size: 0.95rem;
          color: #64748b;
          margin: 0 0 0.75rem;
          font-weight: 500;
        }

        .slots {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .slot-btn {
          padding: 0.6rem 1rem;
          border-radius: 8px;
          border: 2px solid #27AE60;
          background: white;
          color: #27AE60;
          font-family: inherit;
          font-size: 0.95rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          min-width: 70px;
        }

        .slot-btn.available:hover {
          background: rgba(39,174,96,0.1);
        }

        .slot-btn.booked {
          border-color: #e2e8f0;
          color: #94a3b8;
          cursor: not-allowed;
        }

        .slot-btn.selected {
          background: #27AE60;
          color: white;
        }

        /* Summary */
        .summary-section {
          padding: 1rem;
        }

        .summary-section h3 {
          font-size: 1.1rem;
          color: #1B4F72;
          margin: 0 0 1rem;
        }

        .summary-card {
          background: white;
          border-radius: 12px;
          padding: 1rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .summary-row {
          display: flex;
          justify-content: space-between;
          padding: 0.5rem 0;
          border-bottom: 1px solid #f1f5f9;
        }

        .summary-row:last-child {
          border-bottom: none;
        }

        .summary-row span:first-child {
          color: #64748b;
        }

        .summary-row span:last-child {
          color: #334155;
          font-weight: 500;
        }

        .next-btn {
          width: 100%;
          margin-top: 1rem;
          padding: 1rem;
          background: #27AE60;
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 1.1rem;
          font-weight: 600;
          cursor: pointer;
          font-family: inherit;
          transition: background 0.2s;
        }

        .next-btn:hover {
          background: #219653;
        }

        /* Modal */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: flex-end;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: white;
          border-radius: 24px 24px 0 0;
          padding: 1.5rem;
          width: 100%;
          max-width: 500px;
          max-height: 90vh;
          overflow-y: auto;
        }

        .modal h3 {
          font-size: 1.25rem;
          color: #1B4F72;
          margin: 0 0 1.5rem;
          text-align: center;
        }

        .form-group {
          margin-bottom: 1.25rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          color: #334155;
          font-weight: 500;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          width: 100%;
          padding: 0.75rem 1rem;
          border: 2px solid #e2e8f0;
          border-radius: 10px;
          font-family: inherit;
          font-size: 1rem;
          transition: border-color 0.2s;
        }

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
          outline: none;
          border-color: #1B4F72;
        }

        .phone-input {
          display: flex;
          align-items: stretch;
        }

        .phone-input .prefix {
          background: #f1f5f9;
          padding: 0.75rem;
          border: 2px solid #e2e8f0;
          border-left: none;
          border-radius: 0 10px 10px 0;
          color: #64748b;
        }

        .phone-input input {
          border-radius: 10px 0 0 10px;
        }

        .error {
          color: #dc2626;
          font-size: 0.85rem;
          margin-top: 0.25rem;
          display: block;
        }

        .submit-btn {
          width: 100%;
          padding: 1rem;
          background: #1B4F72;
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 1.1rem;
          font-weight: 600;
          cursor: pointer;
          font-family: inherit;
        }

        .submit-btn:disabled {
          background: #94a3b8;
          cursor: not-allowed;
        }

        @media (min-width: 768px) {
          .modal {
            border-radius: 24px;
            margin: 2rem;
          }
        }
      `}</style>
        </div>
    );
}
