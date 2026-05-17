import React, { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { TaskBoard } from "../components/TaskBoard";

const gatewayUrl = import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:8380";

const emptyDashboard = {
  course: {
    title: "EduStream Demo Course",
    description: "Courses, webinars, testing, and learner analytics are loading.",
    difficulty: "intermediate",
    modules: [],
  },
  learning: {
    progress: { completion_ratio: 0 },
    recommendations: { recommended_lesson_ids: [] },
    dropout_risk: 0,
  },
  webinars: { items: [], count: 0 },
  leaderboard: { items: [] },
  profile: { items: [] },
  analytics: { completed_lessons: 0, dropout_risk: 0 },
  course_analytics: {
    course_effectiveness: 0,
    avg_completion_ratio: 0,
    avg_quiz_score: 0,
    avg_webinar_attendance: 0,
  },
  kpi: {
    video_load_seconds_estimate: 0,
    target_video_load_seconds: 3,
    recommendation_accuracy_pct: 0,
    target_recommendation_accuracy_pct: 80,
    capacity_target_viewers: 10000,
  },
  quizzes: { items: [] },
};

async function loadDashboard(courseId, userId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${courseId}/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard: ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const [courseId, setCourseId] = useState("COURSE-DEMO");
  const [userId, setUserId] = useState("STU-001");
  const [theme, setTheme] = useState("light");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(emptyDashboard);

  useEffect(() => {
    let active = true;

    loadDashboard(courseId, userId)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDashboard({ ...emptyDashboard, ...payload });
        setStatus("succeeded");
        setError(null);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setStatus("failed");
        setError(err.message);
      });

    return () => {
      active = false;
    };
  }, [courseId, userId]);

  const progressPct = Math.round((dashboard.learning?.progress?.completion_ratio || 0) * 100);
  const dropoutRisk = Number(dashboard.analytics?.dropout_risk || dashboard.learning?.dropout_risk || 0);
  const recommendationIds = dashboard.learning?.recommendations?.recommended_lesson_ids || [];
  const profileCard = dashboard.profile?.items?.[0];
  const modules = dashboard.course?.modules || [];
  const quizzes = dashboard.quizzes?.items || [];
  const webinars = dashboard.webinars?.items || [];
  const leaderboard = dashboard.leaderboard?.items || [];

  const statusLabel = useMemo(() => {
    if (status === "loading") {
      return "loading";
    }
    if (status === "failed") {
      return "fallback";
    }
    return "live";
  }, [status]);

  const refresh = async () => {
    try {
      setStatus("loading");
      const payload = await loadDashboard(courseId, userId);
      setDashboard({ ...emptyDashboard, ...payload });
      setStatus("succeeded");
      setError(null);
    } catch (err) {
      setStatus("failed");
      setError(err.message);
    }
  };

  return (
    <div className={`app theme-${theme}`}>
      <div className="background-orb orb-a" />
      <div className="background-orb orb-b" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">EduStream Ecosystem</p>
          <h1>Courses, webinars, testing, and learner momentum in one control room.</h1>
          <p className="sub">
            EduStream brings together adaptive recommendations, automated grading, live webinar orchestration, and
            certificate delivery for online education teams.
          </p>
          <div className="hero-badges">
            <span>Adaptive learning</span>
            <span>Essay grading</span>
            <span>Webinar balancing</span>
            <span>Zoom and YouTube sync</span>
          </div>
        </div>

        <div className="hero-panel">
          <label>
            Course ID
            <input value={courseId} onChange={(e) => setCourseId(e.target.value)} placeholder="COURSE-DEMO" />
          </label>
          <label>
            User ID
            <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="STU-001" />
          </label>
          <div className="hero-actions">
            <button onClick={refresh}>Refresh dashboard</button>
            <button className="ghost" onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}>
              Theme
            </button>
          </div>
          <p className="status-line">Status: {statusLabel}</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard
          title="Video Start"
          value={`${Number(dashboard.kpi?.video_load_seconds_estimate || 0).toFixed(1)} sec`}
          target={`Target < ${dashboard.kpi?.target_video_load_seconds || 3} sec`}
          ok={Number(dashboard.kpi?.video_load_seconds_estimate || 99) <= Number(dashboard.kpi?.target_video_load_seconds || 3)}
        />
        <KpiCard
          title="Recommendation Fit"
          value={`${Number(dashboard.kpi?.recommendation_accuracy_pct || 0).toFixed(1)}%`}
          target={`Target > ${dashboard.kpi?.target_recommendation_accuracy_pct || 80}%`}
          ok={
            Number(dashboard.kpi?.recommendation_accuracy_pct || 0) >=
            Number(dashboard.kpi?.target_recommendation_accuracy_pct || 80)
          }
        />
        <KpiCard title="Learner Progress" value={`${progressPct}%`} target="Keep momentum above 60%" ok={progressPct >= 60} />
        <KpiCard title="Dropout Risk" value={dropoutRisk.toFixed(2)} target="Keep under 0.35" ok={dropoutRisk < 0.35} />
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="content-grid">
        <article className="panel panel-featured">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Course Overview</p>
              <h2>{dashboard.course?.title || "EduStream Demo Course"}</h2>
            </div>
            <span className="pill">{dashboard.course?.difficulty || "intermediate"}</span>
          </div>
          <p className="panel-copy">{dashboard.course?.description}</p>
          <div className="metrics-row">
            <div>
              <strong>{modules.length}</strong>
              <span>modules</span>
            </div>
            <div>
              <strong>{quizzes.length}</strong>
              <span>quizzes</span>
            </div>
            <div>
              <strong>{dashboard.webinars?.count || webinars.length}</strong>
              <span>webinars</span>
            </div>
            <div>
              <strong>{profileCard?.total_points || 0}</strong>
              <span>points</span>
            </div>
          </div>
          <TaskBoard modules={modules} />
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Adaptive Path</p>
              <h2>Next lessons</h2>
            </div>
            <span className="pill accent">{recommendationIds.length} picks</span>
          </div>
          <div className="chip-list">
            {recommendationIds.length ? recommendationIds.map((item) => <span key={item}>{item}</span>) : <span>Waiting for activity</span>}
          </div>
          <div className="stack-list">
            {quizzes.map((quiz) => (
              <div className="stack-item" key={quiz.quiz_id}>
                <div>
                  <p className="stack-title">{quiz.title}</p>
                  <p className="stack-sub">Lesson {quiz.lesson_id}</p>
                </div>
                <span>{quiz.questions?.length || 0} questions</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Live Layer</p>
              <h2>Upcoming webinars</h2>
            </div>
            <span className="pill">Capacity {dashboard.kpi?.capacity_target_viewers || 10000}</span>
          </div>
          <div className="stack-list">
            {webinars.map((webinar) => (
              <div className="stack-item webinar-item" key={webinar.webinar_id}>
                <div>
                  <p className="stack-title">{webinar.title}</p>
                  <p className="stack-sub">{new Date(webinar.scheduled_at).toLocaleString()}</p>
                </div>
                <span>{webinar.provider}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Leaderboard</p>
              <h2>Student energy</h2>
            </div>
            <span className="pill">Tier {profileCard?.tier || "bronze"}</span>
          </div>
          <div className="stack-list">
            {leaderboard.map((item, index) => (
              <div className="stack-item" key={`${item.user_id}-${index}`}>
                <div>
                  <p className="stack-title">{item.user_id}</p>
                  <p className="stack-sub">{item.tier}</p>
                </div>
                <span>{item.total_points} pts</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel-analytics">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Instructor Analytics</p>
              <h2>Course efficiency snapshot</h2>
            </div>
            <span className="pill accent">{dashboard.course_analytics?.course_effectiveness || 0}</span>
          </div>
          <div className="analytics-grid">
            <div>
              <strong>{Math.round((dashboard.course_analytics?.avg_completion_ratio || 0) * 100)}%</strong>
              <span>avg completion</span>
            </div>
            <div>
              <strong>{Number(dashboard.course_analytics?.avg_quiz_score || 0).toFixed(1)}%</strong>
              <span>quiz score</span>
            </div>
            <div>
              <strong>{Math.round((dashboard.course_analytics?.avg_webinar_attendance || 0) * 100)}%</strong>
              <span>attendance</span>
            </div>
            <div>
              <strong>{dashboard.analytics?.completed_lessons || 0}</strong>
              <span>lessons completed</span>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
