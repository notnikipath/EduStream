import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

const gatewayUrl = import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:8380";

export const fetchDashboard = createAsyncThunk("app/fetchDashboard", async ({ courseId, userId }) => {
  const response = await fetch(`${gatewayUrl}/dashboard/${courseId}/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard: ${response.status}`);
  }
  return response.json();
});

const initialState = {
  courseId: "COURSE-DEMO",
  userId: "STU-001",
  theme: "light",
  status: "idle",
  course: null,
  learning: null,
  webinars: { items: [] },
  leaderboard: { items: [] },
  profile: { items: [] },
  analytics: null,
  courseAnalytics: null,
  kpi: null,
  quizzes: { items: [] },
  error: null,
};

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setCourseId(state, action) {
      state.courseId = action.payload;
    },
    setUserId(state, action) {
      state.userId = action.payload;
    },
    toggleTheme(state) {
      state.theme = state.theme === "light" ? "dark" : "light";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboard.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.course = action.payload.course;
        state.learning = action.payload.learning;
        state.webinars = action.payload.webinars;
        state.leaderboard = action.payload.leaderboard;
        state.profile = action.payload.profile;
        state.analytics = action.payload.analytics;
        state.courseAnalytics = action.payload.course_analytics;
        state.kpi = action.payload.kpi;
        state.quizzes = action.payload.quizzes;
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message;
      });
  },
});

export const { setCourseId, setUserId, toggleTheme } = appSlice.actions;
export const appReducer = appSlice.reducer;
