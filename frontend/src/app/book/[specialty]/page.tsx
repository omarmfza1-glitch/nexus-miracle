"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";

// Mock doctor data
const mockDoctors = [
    {
        id: "dr_001",
        name: "دكتور فهد الغامدي",
        nameEn: "Dr. Fahad Al-Ghamdi",
        title: "استشاري جراحة العظام",
        specialty: "orthopedics",
        rating: 4.9,
        reviewCount: 120,
        branch: "الفرع الرئيسي",
        nextAvailable: "الثلاثاء 24 ديسمبر",
        gender: "male",
        image: null,
    },
    {
        id: "dr_002",
        name: "دكتورة سارة العتيبي",
        nameEn: "Dr. Sara Al-Otaibi",
        title: "استشارية أمراض العظام",
        specialty: "orthopedics",
        rating: 4.8,
        reviewCount: 95,
        branch: "فرع النخيل",
        nextAvailable: "الأربعاء 25 ديسمبر",
        gender: "female",
        image: null,
    },
    {
        id: "dr_003",
        name: "دكتور محمد الشهري",
        nameEn: "Dr. Mohammed Al-Shehri",
        title: "أخصائي جراحة العظام",
        specialty: "orthopedics",
        rating: 4.7,
        reviewCount: 78,
        branch: "الفرع الرئيسي",
        nextAvailable: "الخميس 26 ديسمبر",
        gender: "male",
        image: null,
    },
];

const specialtyNames: Record<string, string> = {
    orthopedics: "العظام",
    internal: "الباطنية",
    dermatology: "الجلدية",
    pediatrics: "الأطفال",
    cardiology: "القلب",
    ophthalmology: "العيون",
};

function DoctorCard({ doctor, specialty }: { doctor: typeof mockDoctors[0]; specialty: string }) {
    const initials = doctor.name.split(" ").slice(1, 3).map(n => n[0]).join("");

    return (
        <Link href={`/book/${specialty}/${doctor.id}`} className="doctor-card">
            <div className="doctor-avatar">
                {doctor.image ? (
                    <img src={doctor.image} alt={doctor.name} />
                ) : (
                    <div className="avatar-placeholder">
                        <span>{initials || "د"}</span>
                    </div>
                )}
            </div>

            <div className="doctor-info">
                <h3 className="doctor-name">{doctor.name}</h3>
                <p className="doctor-title">{doctor.title}</p>

                <div className="doctor-meta">
                    <span className="rating">
                        ⭐ {doctor.rating} ({doctor.reviewCount} تقييم)
                    </span>
                    <span className="branch">📍 {doctor.branch}</span>
                </div>

                <div className="next-available">
                    <span className="label">أقرب موعد:</span>
                    <span className="date">{doctor.nextAvailable}</span>
                </div>
            </div>

            <button className="book-btn">احجز الآن</button>

            <style jsx>{`
        .doctor-card {
          background: white;
          border-radius: 16px;
          padding: 1.25rem;
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          text-decoration: none;
          color: inherit;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
          transition: all 0.2s ease;
          position: relative;
        }

        .doctor-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        }

        .doctor-avatar {
          flex-shrink: 0;
        }

        .avatar-placeholder {
          width: 70px;
          height: 70px;
          border-radius: 50%;
          background: linear-gradient(135deg, #1B4F72, #21618C);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 1.5rem;
          font-weight: 600;
        }

        .doctor-info {
          flex: 1;
          min-width: 0;
        }

        .doctor-name {
          font-size: 1.1rem;
          font-weight: 600;
          color: #1B4F72;
          margin: 0 0 0.25rem;
        }

        .doctor-title {
          font-size: 0.9rem;
          color: #64748b;
          margin: 0 0 0.5rem;
        }

        .doctor-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          margin-bottom: 0.5rem;
          font-size: 0.85rem;
        }

        .rating {
          color: #f59e0b;
        }

        .branch {
          color: #64748b;
        }

        .next-available {
          display: flex;
          gap: 0.5rem;
          font-size: 0.9rem;
        }

        .next-available .label {
          color: #64748b;
        }

        .next-available .date {
          color: #27AE60;
          font-weight: 500;
        }

        .book-btn {
          position: absolute;
          top: 1.25rem;
          left: 1.25rem;
          background: #27AE60;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s;
          font-family: inherit;
        }

        .book-btn:hover {
          background: #219653;
        }

        @media (max-width: 480px) {
          .doctor-card {
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding-top: 3.5rem;
          }

          .book-btn {
            position: relative;
            top: 0;
            left: 0;
            width: 100%;
            margin-top: 1rem;
            padding: 0.75rem;
          }

          .doctor-meta {
            justify-content: center;
          }

          .next-available {
            justify-content: center;
          }
        }
      `}</style>
        </Link>
    );
}

export default function DoctorListPage() {
    const params = useParams();
    const router = useRouter();
    const specialty = params.specialty as string;

    const [doctors, setDoctors] = useState(mockDoctors);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState({
        branch: "all",
        gender: "all",
        rating: "all",
    });

    const specialtyName = specialtyNames[specialty] || specialty;

    // Filter doctors
    const filteredDoctors = doctors.filter(doc => {
        if (filters.branch !== "all" && doc.branch !== filters.branch) return false;
        if (filters.gender !== "all" && doc.gender !== filters.gender) return false;
        if (filters.rating !== "all" && doc.rating < parseFloat(filters.rating)) return false;
        return true;
    });

    return (
        <div className="doctor-list-page">
            {/* Header */}
            <header className="page-header">
                <button className="back-btn" onClick={() => router.push("/book")}>
                    → العودة
                </button>
                <h1>أطباء {specialtyName}</h1>
                <p>{filteredDoctors.length} طبيب متاح</p>
            </header>

            {/* Filters */}
            <div className="filters-bar">
                <select
                    value={filters.branch}
                    onChange={(e) => setFilters({ ...filters, branch: e.target.value })}
                >
                    <option value="all">جميع الفروع</option>
                    <option value="الفرع الرئيسي">الفرع الرئيسي</option>
                    <option value="فرع النخيل">فرع النخيل</option>
                </select>

                <select
                    value={filters.gender}
                    onChange={(e) => setFilters({ ...filters, gender: e.target.value })}
                >
                    <option value="all">الجنس</option>
                    <option value="male">ذكر</option>
                    <option value="female">أنثى</option>
                </select>

                <select
                    value={filters.rating}
                    onChange={(e) => setFilters({ ...filters, rating: e.target.value })}
                >
                    <option value="all">التقييم</option>
                    <option value="4.5">4.5+ ⭐</option>
                    <option value="4.0">4.0+ ⭐</option>
                </select>
            </div>

            {/* Doctor List */}
            <main className="doctors-list">
                {loading ? (
                    <div className="loading">جاري التحميل...</div>
                ) : filteredDoctors.length === 0 ? (
                    <div className="empty">لا يوجد أطباء مطابقين للبحث</div>
                ) : (
                    filteredDoctors.map((doctor) => (
                        <DoctorCard key={doctor.id} doctor={doctor} specialty={specialty} />
                    ))
                )}
            </main>

            <style jsx>{`
        .doctor-list-page {
          min-height: 100vh;
          background: #f8fafc;
          direction: rtl;
          font-family: "IBM Plex Sans Arabic", "Segoe UI", sans-serif;
        }

        .page-header {
          background: linear-gradient(135deg, #1B4F72 0%, #21618C 100%);
          color: white;
          padding: 1.5rem;
          text-align: center;
        }

        .back-btn {
          position: absolute;
          right: 1rem;
          top: 1rem;
          background: rgba(255,255,255,0.2);
          border: none;
          color: white;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          font-family: inherit;
          font-size: 0.9rem;
        }

        .back-btn:hover {
          background: rgba(255,255,255,0.3);
        }

        .page-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 0.25rem;
        }

        .page-header p {
          font-size: 0.95rem;
          opacity: 0.9;
          margin: 0;
        }

        .filters-bar {
          display: flex;
          gap: 0.75rem;
          padding: 1rem 1.5rem;
          background: white;
          border-bottom: 1px solid #e2e8f0;
          overflow-x: auto;
        }

        .filters-bar select {
          padding: 0.5rem 1rem;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          background: white;
          font-family: inherit;
          font-size: 0.9rem;
          color: #334155;
          cursor: pointer;
          min-width: 120px;
        }

        .filters-bar select:focus {
          outline: none;
          border-color: #1B4F72;
        }

        .doctors-list {
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          max-width: 800px;
          margin: 0 auto;
        }

        .loading, .empty {
          text-align: center;
          padding: 3rem 1rem;
          color: #64748b;
          font-size: 1.1rem;
        }

        @media (max-width: 480px) {
          .filters-bar {
            padding: 0.75rem 1rem;
          }

          .filters-bar select {
            min-width: 100px;
            font-size: 0.85rem;
          }

          .doctors-list {
            padding: 1rem;
          }
        }
      `}</style>
        </div>
    );
}
