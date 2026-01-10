"use client";

import Link from "next/link";

// Specialty data
const specialties = [
    {
        id: "orthopedics",
        name: "العظام",
        nameEn: "Orthopedics",
        icon: "🦴",
        doctorCount: 5,
        color: "#3498DB",
    },
    {
        id: "internal",
        name: "الباطنية",
        nameEn: "Internal Medicine",
        icon: "🩺",
        doctorCount: 8,
        color: "#27AE60",
    },
    {
        id: "dermatology",
        name: "الجلدية",
        nameEn: "Dermatology",
        icon: "✋",
        doctorCount: 4,
        color: "#9B59B6",
    },
    {
        id: "pediatrics",
        name: "الأطفال",
        nameEn: "Pediatrics",
        icon: "👶",
        doctorCount: 6,
        color: "#E74C3C",
    },
    {
        id: "cardiology",
        name: "القلب",
        nameEn: "Cardiology",
        icon: "❤️",
        doctorCount: 3,
        color: "#E91E63",
    },
    {
        id: "ophthalmology",
        name: "العيون",
        nameEn: "Ophthalmology",
        icon: "👁️",
        doctorCount: 4,
        color: "#00BCD4",
    },
];

function SpecialtyCard({
    specialty,
}: {
    specialty: (typeof specialties)[0];
}) {
    return (
        <Link
            href={`/book/${specialty.id}`}
            className="specialty-card"
            style={{ "--accent-color": specialty.color } as React.CSSProperties}
        >
            <div className="specialty-icon">{specialty.icon}</div>
            <h3 className="specialty-name">{specialty.name}</h3>
            <p className="specialty-name-en">{specialty.nameEn}</p>
            <p className="doctor-count">{specialty.doctorCount} أطباء</p>
        </Link>
    );
}

export default function BookingLandingPage() {
    return (
        <div className="booking-page">
            {/* Hero Section */}
            <header className="hero">
                <div className="hero-content">
                    <div className="clinic-logo">
                        <span className="logo-icon">🏥</span>
                        <span className="logo-text">نِكسوس مراكل</span>
                    </div>
                    <h1>احجز موعدك في عيادات نِكسوس</h1>
                    <p>اختر التخصص الطبي للبدء في حجز موعدك</p>
                </div>
            </header>

            {/* Specialty Selection */}
            <main className="main-content">
                <section className="specialties-section">
                    <h2>التخصصات الطبية</h2>
                    <div className="specialties-grid">
                        {specialties.map((specialty) => (
                            <SpecialtyCard key={specialty.id} specialty={specialty} />
                        ))}
                    </div>
                </section>

                {/* Info Section */}
                <section className="info-section">
                    <div className="info-cards">
                        <div className="info-card">
                            <span className="info-icon">⏰</span>
                            <h4>حجز سريع</h4>
                            <p>احجز موعدك في أقل من دقيقتين</p>
                        </div>
                        <div className="info-card">
                            <span className="info-icon">📱</span>
                            <h4>تأكيد واتساب</h4>
                            <p>ستصلك رسالة تأكيد فورية</p>
                        </div>
                        <div className="info-card">
                            <span className="info-icon">💳</span>
                            <h4>تأمين طبي</h4>
                            <p>نقبل جميع شركات التأمين</p>
                        </div>
                    </div>
                </section>
            </main>

            {/* Footer */}
            <footer className="booking-footer">
                <p>عيادات نِكسوس مراكل الطبية</p>
                <p>الرياض، المملكة العربية السعودية</p>
                <p className="phone">📞 920012345</p>
            </footer>

            <style jsx>{`
        .booking-page {
          min-height: 100vh;
          background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
          direction: rtl;
          font-family: "IBM Plex Sans Arabic", "Segoe UI", sans-serif;
        }

        /* Hero */
        .hero {
          background: linear-gradient(135deg, #1B4F72 0%, #21618C 100%);
          color: white;
          padding: 3rem 1.5rem;
          text-align: center;
        }

        .hero-content {
          max-width: 600px;
          margin: 0 auto;
        }

        .clinic-logo {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin-bottom: 1.5rem;
        }

        .logo-icon {
          font-size: 2rem;
        }

        .logo-text {
          font-size: 1.5rem;
          font-weight: 700;
        }

        .hero h1 {
          font-size: 2rem;
          font-weight: 700;
          margin: 0 0 0.75rem;
          line-height: 1.3;
        }

        .hero p {
          font-size: 1.1rem;
          opacity: 0.9;
          margin: 0;
        }

        /* Main Content */
        .main-content {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem 1.5rem;
        }

        .specialties-section h2 {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1B4F72;
          margin: 0 0 1.5rem;
          text-align: center;
        }

        /* Specialties Grid */
        .specialties-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
          gap: 1rem;
        }

        .specialty-card {
          background: white;
          border-radius: 16px;
          padding: 1.5rem 1rem;
          text-align: center;
          text-decoration: none;
          color: inherit;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
          transition: all 0.2s ease;
          border: 2px solid transparent;
          min-height: 180px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }

        .specialty-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
          border-color: var(--accent-color);
        }

        .specialty-card:active {
          transform: translateY(-2px);
        }

        .specialty-icon {
          font-size: 3rem;
          margin-bottom: 0.75rem;
        }

        .specialty-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1B4F72;
          margin: 0 0 0.25rem;
        }

        .specialty-name-en {
          font-size: 0.85rem;
          color: #64748b;
          margin: 0 0 0.5rem;
        }

        .doctor-count {
          font-size: 0.9rem;
          color: var(--accent-color);
          font-weight: 500;
          margin: 0;
          padding: 0.25rem 0.75rem;
          background: rgba(27, 79, 114, 0.08);
          border-radius: 12px;
        }

        /* Info Section */
        .info-section {
          margin-top: 3rem;
        }

        .info-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .info-card {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          text-align: center;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }

        .info-icon {
          font-size: 2rem;
          margin-bottom: 0.5rem;
          display: block;
        }

        .info-card h4 {
          font-size: 1.1rem;
          font-weight: 600;
          color: #1B4F72;
          margin: 0 0 0.5rem;
        }

        .info-card p {
          font-size: 0.9rem;
          color: #64748b;
          margin: 0;
        }

        /* Footer */
        .booking-footer {
          background: #1B4F72;
          color: white;
          text-align: center;
          padding: 2rem 1.5rem;
          margin-top: 3rem;
        }

        .booking-footer p {
          margin: 0.25rem 0;
          opacity: 0.9;
        }

        .booking-footer .phone {
          font-size: 1.2rem;
          font-weight: 600;
          margin-top: 0.75rem;
          opacity: 1;
        }

        /* Mobile Responsive */
        @media (max-width: 480px) {
          .hero h1 {
            font-size: 1.5rem;
          }

          .hero p {
            font-size: 1rem;
          }

          .specialties-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
          }

          .specialty-card {
            padding: 1rem;
            min-height: 150px;
          }

          .specialty-icon {
            font-size: 2.5rem;
          }

          .specialty-name {
            font-size: 1rem;
          }
        }
      `}</style>
        </div>
    );
}
