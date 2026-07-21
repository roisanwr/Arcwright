import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import Landing from './pages/Landing'
import ChatPage from './pages/ChatPage'
import DevSudoPage from './pages/DevSudoPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<Landing />} />
        <Route path="/chat"      element={<ChatPage />} />
        <Route path="/dev/sudo"  element={<DevSudoPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
