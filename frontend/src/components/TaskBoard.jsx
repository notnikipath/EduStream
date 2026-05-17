import React from "react";

export function TaskBoard({ modules }) {
  if (!modules?.length) {
    return <div className="empty-board">No modules yet. Add lessons to see the learning path.</div>;
  }

  return (
    <section className="learning-map">
      {modules.map((module) => (
        <div className="module-card" key={module.module_id}>
          <div className="module-head">
            <p className="module-kicker">Module</p>
            <h3>{module.title}</h3>
            <p>{module.summary}</p>
          </div>
          <div className="lesson-list">
            {(module.lessons || []).map((lesson) => (
              <article className="lesson-card" key={lesson.lesson_id}>
                <div>
                  <p className="lesson-type">{lesson.format.replaceAll("_", " ")}</p>
                  <h4>{lesson.title}</h4>
                </div>
                <div className="lesson-meta">
                  <span>{lesson.duration_minutes} min</span>
                  <span>{lesson.difficulty}</span>
                </div>
              </article>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
