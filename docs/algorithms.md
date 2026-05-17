# Algorithms

## Adaptive Learning Recommendations
`learning-service` scores candidate lessons by novelty and weak-topic overlap. Weak topics boost ranking, while advanced lessons get a small penalty when learners still struggle with fundamentals.

## Essay Grading
`test-service` uses a lightweight keyword-coverage heuristic plus a structure bonus for longer answers. The output includes score, feedback, and matched concepts.

## Dropout Risk Prediction
`analytics-service` combines completion ratio, missed deadlines, and webinar attendance into a bounded risk score from `0.0` to `1.0`.

## Course Effectiveness
The course KPI blends completion ratio, quiz performance, and webinar attendance into a single score used in instructor dashboards.

## Webinar Balancing
`webinar-service` exposes a capacity estimator that converts active webinar count into balanced node allocation and viewers per node.
