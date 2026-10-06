import React, { useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function AnalyticsDashboard() {
  // -----------------------------
  // FILTERS
  // -----------------------------

  const [dateFilter, setDateFilter] = useState("All Time");
  const [organizerFilter, setOrganizerFilter] =
    useState("All Organizers");
  const [technologyFilter, setTechnologyFilter] =
    useState("All Technologies");

  // -----------------------------
  // MOCK SUMMARY DATA
  // -----------------------------

  const organizerStats = {
    "All Organizers": {
      total: 128,
      upcoming: 42,
      predictions: 86,
      accuracy: "91%",
    },

    Microsoft: {
      total: 45,
      upcoming: 15,
      predictions: 30,
      accuracy: "93%",
    },

    Google: {
      total: 38,
      upcoming: 12,
      predictions: 25,
      accuracy: "90%",
    },

    Amazon: {
      total: 32,
      upcoming: 10,
      predictions: 22,
      accuracy: "92%",
    },
  };

  const selectedStats =
    organizerStats[organizerFilter];

  // -----------------------------
  // SUMMARY CARDS
  // -----------------------------

  const stats = [
    {
      title: "Total Hackathons",
      value: selectedStats.total,
    },
    {
      title: "Upcoming Hackathons",
      value: selectedStats.upcoming,
    },
    {
      title: "Predictions Generated",
      value: selectedStats.predictions,
    },
    {
      title: "Model Accuracy",
      value: selectedStats.accuracy,
    },
  ];

  // -----------------------------
  // HACKATHONS OVER TIME
  // -----------------------------

  const allHackathonData = [
    { month: "Jan", hackathons: 12 },
    { month: "Feb", hackathons: 18 },
    { month: "Mar", hackathons: 15 },
    { month: "Apr", hackathons: 25 },
    { month: "May", hackathons: 22 },
    { month: "Jun", hackathons: 30 },
  ];

  let hackathonData = allHackathonData;

  if (dateFilter === "Last 30 Days") {
    hackathonData = allHackathonData.slice(-1);
  }

  if (dateFilter === "Last 90 Days") {
    hackathonData = allHackathonData.slice(-3);
  }

  // -----------------------------
  // TECHNOLOGY DATA
  // -----------------------------

  const allTechnologyData = [
    { category: "AI/ML", count: 35 },
    { category: "Web", count: 28 },
    { category: "Cloud", count: 22 },
    { category: "Cyber", count: 18 },
    { category: "Other", count: 15 },
  ];

  let technologyData = allTechnologyData;

  if (technologyFilter === "AI/ML") {
    technologyData = [
      { category: "AI/ML", count: 35 },
    ];
  }

  if (technologyFilter === "Web Development") {
    technologyData = [
      { category: "Web", count: 28 },
    ];
  }

  if (technologyFilter === "Cloud") {
    technologyData = [
      { category: "Cloud", count: 22 },
    ];
  }

  if (technologyFilter === "Cybersecurity") {
    technologyData = [
      { category: "Cyber", count: 18 },
    ];
  }

  // -----------------------------
  // ORGANIZER DATA
  // -----------------------------

  const allOrganizerData = [
    { organizer: "Microsoft", count: 32 },
    { organizer: "Google", count: 28 },
    { organizer: "Amazon", count: 24 },
  ];

  let organizerData = allOrganizerData;

  if (organizerFilter !== "All Organizers") {
    organizerData = allOrganizerData.filter(
      (item) =>
        item.organizer === organizerFilter
    );
  }

  // -----------------------------
  // PAGE
  // -----------------------------

  return (
    <div className="page">

      {/* PAGE HEADER */}

      <div className="page-header">

        <p className="eyebrow">
          ANALYTICS
        </p>

        <h1>
          Analytics Dashboard
        </h1>

        <p>
          Overview of hackathons, predictions
          and platform activity.
        </p>

      </div>

      {/* SUMMARY CARDS */}

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
          gap: "20px",
          marginTop: "32px",
        }}
      >

        {stats.map((stat) => (

          <div
            key={stat.title}
            style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: "16px",
              padding: "24px",
              boxShadow:
                "0 4px 12px rgba(15, 23, 42, 0.06)",
            }}
          >

            <p
              style={{
                margin: 0,
                color: "#64748b",
                fontSize: "14px",
                fontWeight: "600",
              }}
            >
              {stat.title}
            </p>

            <h2
              style={{
                margin:
                  "10px 0 0 0",
                color: "#111827",
                fontSize: "32px",
                fontWeight: "700",
              }}
            >
              {stat.value}
            </h2>

          </div>

        ))}

      </div>

      {/* FILTERS */}

      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          marginTop: "28px",
          marginBottom: "28px",
          padding: "20px",
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: "16px",
        }}
      >

        {/* DATE */}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >

          <label
            htmlFor="date-filter"
            style={{
              fontSize: "13px",
              fontWeight: "600",
              color: "#374151",
            }}
          >
            Date Range
          </label>

          <select
            id="date-filter"
            value={dateFilter}
            onChange={(e) =>
              setDateFilter(e.target.value)
            }
            style={{
              padding: "10px 14px",
              borderRadius: "10px",
              border:
                "1px solid #d1d5db",
              background: "#ffffff",
              color: "#111827",
              minWidth: "160px",
            }}
          >

            <option>
              All Time
            </option>

            <option>
              Last 30 Days
            </option>

            <option>
              Last 90 Days
            </option>

            <option>
              This Year
            </option>

          </select>

        </div>

        {/* ORGANIZER */}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >

          <label
            htmlFor="organizer-filter"
            style={{
              fontSize: "13px",
              fontWeight: "600",
              color: "#374151",
            }}
          >
            Organizer
          </label>

          <select
            id="organizer-filter"
            value={organizerFilter}
            onChange={(e) =>
              setOrganizerFilter(
                e.target.value
              )
            }
            style={{
              padding: "10px 14px",
              borderRadius: "10px",
              border:
                "1px solid #d1d5db",
              background: "#ffffff",
              color: "#111827",
              minWidth: "160px",
            }}
          >

            <option>
              All Organizers
            </option>

            <option>
              Microsoft
            </option>

            <option>
              Google
            </option>

            <option>
              Amazon
            </option>

          </select>

        </div>

        {/* TECHNOLOGY */}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >

          <label
            htmlFor="technology-filter"
            style={{
              fontSize: "13px",
              fontWeight: "600",
              color: "#374151",
            }}
          >
            Technology
          </label>

          <select
            id="technology-filter"
            value={technologyFilter}
            onChange={(e) =>
              setTechnologyFilter(
                e.target.value
              )
            }
            style={{
              padding: "10px 14px",
              borderRadius: "10px",
              border:
                "1px solid #d1d5db",
              background: "#ffffff",
              color: "#111827",
              minWidth: "160px",
            }}
          >

            <option>
              All Technologies
            </option>

            <option>
              AI/ML
            </option>

            <option>
              Web Development
            </option>

            <option>
              Cloud
            </option>

            <option>
              Cybersecurity
            </option>

          </select>

        </div>

      </div>

      {/* CHARTS */}

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(2, minmax(0, 1fr))",
          gap: "20px",
        }}
      >

        {/* HACKATHONS OVER TIME */}

        <div
          style={{
            background: "#ffffff",
            border:
              "1px solid #e5e7eb",
            borderRadius: "16px",
            padding: "24px",
            boxShadow:
              "0 4px 12px rgba(15, 23, 42, 0.06)",
          }}
        >

          <h2
            style={{
              marginTop: 0,
              color: "#111827",
              fontSize: "20px",
            }}
          >
            Hackathons Over Time
          </h2>

          <p
            style={{
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Hackathon activity across
            the selected period.
          </p>

          <div
            style={{
              width: "100%",
              height: "300px",
              marginTop: "20px",
            }}
          >

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <LineChart
                data={hackathonData}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e5e7eb"
                />

                <XAxis
                  dataKey="month"
                  stroke="#64748b"
                />

                <YAxis
                  allowDecimals={false}
                  stroke="#64748b"
                />

                <Tooltip />

                <Line
                  type="monotone"
                  dataKey="hackathons"
                  stroke="#635bff"
                  strokeWidth={3}
                  dot={{
                    r: 4,
                    fill: "#635bff",
                  }}
                />

              </LineChart>

            </ResponsiveContainer>

          </div>

        </div>

        {/* TECHNOLOGY CHART */}

        <div
          style={{
            background: "#ffffff",
            border:
              "1px solid #e5e7eb",
            borderRadius: "16px",
            padding: "24px",
            boxShadow:
              "0 4px 12px rgba(15, 23, 42, 0.06)",
          }}
        >

          <h2
            style={{
              marginTop: 0,
              color: "#111827",
              fontSize: "20px",
            }}
          >
            Hackathon Categories
          </h2>

          <p
            style={{
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Hackathons grouped by
            technology.
          </p>

          <div
            style={{
              width: "100%",
              height: "300px",
              marginTop: "20px",
            }}
          >

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <BarChart
                data={technologyData}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e5e7eb"
                />

                <XAxis
                  dataKey="category"
                  stroke="#64748b"
                />

                <YAxis
                  allowDecimals={false}
                  stroke="#64748b"
                />

                <Tooltip />

                <Bar
                  dataKey="count"
                  fill="#635bff"
                  radius={[
                    6,
                    6,
                    0,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>

        {/* ORGANIZER CHART */}

        <div
          style={{
            background: "#ffffff",
            border:
              "1px solid #e5e7eb",
            borderRadius: "16px",
            padding: "24px",
            boxShadow:
              "0 4px 12px rgba(15, 23, 42, 0.06)",
            gridColumn:
              "1 / -1",
          }}
        >

          <h2
            style={{
              marginTop: 0,
              color: "#111827",
              fontSize: "20px",
            }}
          >
            Hackathon Organizers
          </h2>

          <p
            style={{
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Hackathon activity by
            organizer.
          </p>

          <div
            style={{
              width: "100%",
              height: "300px",
              marginTop: "20px",
            }}
          >

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <BarChart
                data={organizerData}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e5e7eb"
                />

                <XAxis
                  dataKey="organizer"
                  stroke="#64748b"
                />

                <YAxis
                  allowDecimals={false}
                  stroke="#64748b"
                />

                <Tooltip />

                <Bar
                  dataKey="count"
                  fill="#7c3aed"
                  radius={[
                    6,
                    6,
                    0,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>

      </div>

      {/* MOCK DATA MESSAGE */}

      <div
        style={{
          marginTop: "24px",
          padding: "16px 20px",
          background: "#f5f3ff",
          border:
            "1px solid #ddd6fe",
          borderRadius: "12px",
          color: "#3730a3",
        }}
      >

        <strong>
          Demo Dashboard
        </strong>

        <p
          style={{
            margin:
              "6px 0 0 0",
            fontSize: "14px",
          }}
        >
          This dashboard currently
          uses mock data. API integration
          will be added with the backend.
        </p>

      </div>

    </div>
  );
}

export default AnalyticsDashboard;