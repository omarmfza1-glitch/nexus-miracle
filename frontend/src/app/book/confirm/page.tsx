"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

interface BookingData {
    doctor: string;
    date: string;
    time: string;
    branch: string;
    address: string;
    reference: string;
}

export default function ConfirmationPage() {
    const [bookingData, setBookingData] = useState<BookingData | null>(null);
    const [showAnimation, setShowAnimation] = useState(true);

    useEffect(() => {
        // Get booking data from sessionStorage
        const stored = sessionStorage.getItem("bookingConfirmation");
        if (stored) {
            setBookingData(JSON.parse(stored));
        }

        // Hide animation after 2 seconds
        const timer = setTimeout(() => setShowAnimation(false), 2000);
        return () => clearTimeout(timer);
    }, []);

    // Format date for display
    const formatDate = (dateStr: string) => {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString("ar-SA", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    };

    return (
        <div className="confirmation-page">
            {/* Success Animation */}
            <div className={`success-animation ${showAnimation ? "show" : "hide"}`}>
                <div className="checkmark">
                    <svg viewBox="0 0 52 52">
                        <circle cx="26" cy="26" r="25" fill="none" />
                        <path fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
                    </svg>
                </div>
            </div>

            {/* Content */}
            <div className={`content ${showAnimation ? "hidden" : "visible"}`}>
                <header className="header">
                    <div className="success-icon">✓</div>
                    <h1>تم الحجز بنجاح!</h1>
                    <p>سيتم إرسال تأكيد عبر الواتساب</p>
                </header>

                {bookingData && (
                    <div className="booking-card">
                        <div className="reference">
                            <span className="label">رقم الحجز:</span>
                            <span className="value">{bookingData.reference}</span>
                        </div>

                        <div className="divider" />

                        <div className="details">
                            <div className="detail-row">
                                <span className="icon">👨‍⚕️</span>
                                <div>
                                    <span className="label">الطبيب</span>
                                    <span className="value">{bookingData.doctor}</span>
                                </div>
                            </div>

                            <div className="detail-row">
                                <span className="icon">📅</span>
                                <div>
                                    <span className="label">التاريخ</span>
                                    <span className="value">{formatDate(bookingData.date)}</span>
                                </div>
                            </div>

                            <div className="detail-row">
                                <span className="icon">🕐</span>
                                <div>
                                    <span className="label">الوقت</span>
                                    <span className="value">{bookingData.time}</span>
                                </div>
                            </div>

                            <div className="detail-row">
                                <span className="icon">📍</span>
                                <div>
                                    <span className="label">الفرع</span>
                                    <span className="value">{bookingData.branch}</span>
                                    <span className="address">{bookingData.address}</span>
                                </div>
                            </div>
                        </div>

                        <a
                            href="https://maps.google.com/?q=الرياض+حي+الملقا"
                            target="_blank"
                            className="map-link"
                        >
                            🗺️ عرض الموقع على الخريطة
                        </a>
                    </div>
                )}

                {/* WhatsApp Section */}
                <div className="whatsapp-section">
                    <div className="whatsapp-icon">📱</div>
                    <p>سيصلك تأكيد على واتساب خلال دقائق</p>
                    <a
                        href="https://wa.me/966920012345"
                        target="_blank"
                        className="whatsapp-btn"
                    >
                        <span className="wa-icon">💬</span>
                        تواصل معنا على واتساب
                    </a>
                </div>

                {/* Actions */}
                <div className="actions">
                    <Link href="/book" className="action-btn primary">
                        حجز موعد آخر
                    </Link>
                    <Link href="/" className="action-btn secondary">
                        العودة للرئيسية
                    </Link>
                </div>

                {/* Footer */}
                <footer className="footer">
                    <p>عيادات نِكسوس مراكل الطبية</p>
                    <p>📞 920012345</p>
                </footer>
            </div>

            <style jsx>{`
        .confirmation-page {
          min-height: 100vh;
          background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
          direction: rtl;
          font-family: "IBM Plex Sans Arabic", "Segoe UI", sans-serif;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 1rem;
        }

        /* Success Animation */
        .success-animation {
          position: fixed;
          inset: 0;
          background: #27AE60;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 100;
          transition: opacity 0.5s, transform 0.5s;
        }

        .success-animation.show {
          opacity: 1;
          transform: scale(1);
        }

        .success-animation.hide {
          opacity: 0;
          transform: scale(0.8);
          pointer-events: none;
        }

        .checkmark {
          width: 100px;
          height: 100px;
        }

        .checkmark svg {
          width: 100%;
          height: 100%;
        }

        .checkmark circle {
          stroke: white;
          stroke-width: 2;
          stroke-dasharray: 166;
          stroke-dashoffset: 166;
          animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
        }

        .checkmark path {
          stroke: white;
          stroke-width: 3;
          stroke-linecap: round;
          stroke-linejoin: round;
          stroke-dasharray: 48;
          stroke-dashoffset: 48;
          animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.6s forwards;
        }

        @keyframes stroke {
          100% {
            stroke-dashoffset: 0;
          }
        }

        /* Content */
        .content {
          width: 100%;
          max-width: 500px;
          transition: opacity 0.3s;
        }

        .content.hidden {
          opacity: 0;
        }

        .content.visible {
          opacity: 1;
        }

        /* Header */
        .header {
          text-align: center;
          margin-bottom: 1.5rem;
        }

        .success-icon {
          width: 60px;
          height: 60px;
          background: #27AE60;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 2rem;
          margin: 0 auto 1rem;
        }

        .header h1 {
          font-size: 1.75rem;
          color: #166534;
          margin: 0 0 0.5rem;
        }

        .header p {
          color: #16a34a;
          font-size: 1rem;
          margin: 0;
        }

        /* Booking Card */
        .booking-card {
          background: white;
          border-radius: 20px;
          padding: 1.5rem;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
          margin-bottom: 1.5rem;
        }

        .reference {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 1rem;
        }

        .reference .label {
          color: #64748b;
          font-size: 0.9rem;
        }

        .reference .value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #1B4F72;
          letter-spacing: 2px;
        }

        .divider {
          height: 1px;
          background: #e2e8f0;
          margin-bottom: 1rem;
        }

        .details {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .detail-row {
          display: flex;
          gap: 1rem;
          align-items: flex-start;
        }

        .detail-row .icon {
          font-size: 1.5rem;
          flex-shrink: 0;
        }

        .detail-row div {
          display: flex;
          flex-direction: column;
        }

        .detail-row .label {
          color: #64748b;
          font-size: 0.85rem;
        }

        .detail-row .value {
          color: #334155;
          font-weight: 500;
        }

        .detail-row .address {
          color: #94a3b8;
          font-size: 0.85rem;
          margin-top: 0.25rem;
        }

        .map-link {
          display: block;
          text-align: center;
          margin-top: 1rem;
          padding: 0.75rem;
          background: #f1f5f9;
          border-radius: 10px;
          color: #1B4F72;
          text-decoration: none;
          font-weight: 500;
        }

        .map-link:hover {
          background: #e2e8f0;
        }

        /* WhatsApp Section */
        .whatsapp-section {
          background: white;
          border-radius: 16px;
          padding: 1.5rem;
          text-align: center;
          margin-bottom: 1.5rem;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .whatsapp-icon {
          font-size: 2.5rem;
          margin-bottom: 0.5rem;
        }

        .whatsapp-section p {
          color: #64748b;
          margin: 0 0 1rem;
        }

        .whatsapp-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          background: #25D366;
          color: white;
          border-radius: 10px;
          text-decoration: none;
          font-weight: 500;
          transition: background 0.2s;
        }

        .whatsapp-btn:hover {
          background: #20bd5a;
        }

        /* Actions */
        .actions {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .action-btn {
          display: block;
          padding: 1rem;
          border-radius: 12px;
          text-align: center;
          text-decoration: none;
          font-weight: 600;
          font-size: 1rem;
          transition: all 0.2s;
        }

        .action-btn.primary {
          background: #1B4F72;
          color: white;
        }

        .action-btn.primary:hover {
          background: #154360;
        }

        .action-btn.secondary {
          background: white;
          color: #1B4F72;
          border: 2px solid #1B4F72;
        }

        .action-btn.secondary:hover {
          background: #f1f5f9;
        }

        /* Footer */
        .footer {
          text-align: center;
          margin-top: 2rem;
          color: #64748b;
        }

        .footer p {
          margin: 0.25rem 0;
        }
      `}</style>
        </div>
    );
}
