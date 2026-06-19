import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import FeedPage from "./pages/FeedPage";
import ProfilePage from "./pages/ProfilePage";
import ArtistPage from "./pages/ArtistPage";
import PredictPage from "./pages/PredictPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import CallbackPage from "./pages/CallbackPage";
import { AuthProvider } from "./context/AuthContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/callback" element={<CallbackPage />} />
          <Route element={<App />}>
            <Route index element={<Navigate to="/feed" replace />} />
            <Route path="/feed" element={<FeedPage />} />
            <Route path="/profile/:userId" element={<ProfilePage />} />
            <Route path="/artist" element={<ArtistPage />} />
            <Route path="/artist/:artistId" element={<ArtistPage />} />
            <Route path="/predict" element={<PredictPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
