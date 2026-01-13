import React, { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import axios from "axios";
import "./App.css";
import { ThemeToggle } from "./components/ThemeToggle";
import { ResizableLayout } from "./components/ResizableLayout";
import { EditorView } from "./components/EditorView";
import faviconPng from "./logo.jpg";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:7777";
console.log("Using backend URL:", BACKEND_URL);

function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [responseData, setResponseData] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [status, setStatus] = useState("Agents ready");
  const [expandedReasoning, setExpandedReasoning] = useState(new Set());
  const messagesEndRef = useRef(null);
  
  // Editor/Viewer State
  const [activeFile, setActiveFile] = useState(null);
  const [viewMode, setViewMode] = useState("browser"); // "browser" or "editor"
  const fileInputRef = useRef(null);

  const fetchLatestAnswer = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/latest_answer`);
      const data = res.data;

      updateData(data);
      if (!data.answer || data.answer.trim() === "") {
        return;
      }
      const normalizedNewAnswer = normalizeAnswer(data.answer);
      const answerExists = messages.some(
        (msg) => normalizeAnswer(msg.content) === normalizedNewAnswer
      );
      if (!answerExists) {
        setMessages((prev) => [
          ...prev,
          {
            type: "agent",
            content: data.answer,
            reasoning: data.reasoning,
            agentName: data.agent_name,
            status: data.status,
            uid: data.uid,
          },
        ]);
        setStatus(data.status);
        scrollToBottom();
      } else {
        console.log("Duplicate answer detected, skipping:", data.answer);
      }
    } catch (error) {
      console.error("Error fetching latest answer:", error);
    }
  }, [messages]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      checkHealth();
      fetchLatestAnswer();
      fetchScreenshot();
    }, 3000);
    return () => clearInterval(intervalId);
  }, [fetchLatestAnswer]);

  const checkHealth = async () => {
    try {
      await axios.get(`${BACKEND_URL}/health`);
      setIsOnline(true);
      console.log("System is online");
    } catch {
      setIsOnline(false);
      console.log("System is offline");
    }
  };

  const fetchScreenshot = async () => {
    try {
      const timestamp = new Date().getTime();
      const res = await axios.get(
        `${BACKEND_URL}/screenshots/updated_screen.png?timestamp=${timestamp}`,
        {
          responseType: "blob",
        }
      );
      console.log("Screenshot fetched successfully");
      const imageUrl = URL.createObjectURL(res.data);
      setResponseData((prev) => {
        if (prev?.screenshot && prev.screenshot !== "placeholder.png") {
          URL.revokeObjectURL(prev.screenshot);
        }
        return {
          ...prev,
          screenshot: imageUrl,
          screenshotTimestamp: new Date().getTime(),
        };
      });
    } catch (err) {
      console.error("Error fetching screenshot:", err);
      setResponseData((prev) => ({
        ...prev,
        screenshot: "placeholder.png",
        screenshotTimestamp: new Date().getTime(),
      }));
    }
  };

  const normalizeAnswer = (answer) => {
    return answer
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/[.,!?]/g, "");
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const toggleReasoning = (messageIndex) => {
    setExpandedReasoning((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(messageIndex)) {
        newSet.delete(messageIndex);
      } else {
        newSet.add(messageIndex);
      }
      return newSet;
    });
  };

  const updateData = (data) => {
    setResponseData((prev) => ({
      ...prev,
      blocks: data.blocks || prev.blocks || null,
      done: data.done,
      answer: data.answer,
      agent_name: data.agent_name,
      status: data.status,
      uid: data.uid,
    }));
  };

  const processQuery = async (text) => {
    if (!text.trim()) return;
    
    checkHealth();
    setMessages((prev) => [...prev, { type: "user", content: text }]);
    setIsLoading(true);
    setError(null);

    try {
      console.log("Sending query:", text);
      const res = await axios.post(`${BACKEND_URL}/query`, {
        query: text,
        tts_enabled: false,
      });
      console.log("Response:", res.data);
      const data = res.data;
      updateData(data);
    } catch (err) {
      console.error("Error:", err);
      const responseData = err?.response?.data;
      const statusCode = err?.response?.status;
      const serverMessage =
        (typeof responseData?.reasoning === "string" && responseData.reasoning.trim()
          ? responseData.reasoning
          : null) ||
        (typeof responseData?.error === "string" && responseData.error.trim()
          ? responseData.error
          : null);
      const errorContent =
        statusCode === 429
          ? "Error: Il sistema sta ancora elaborando una richiesta. Aspetta qualche secondo o premi Stop."
          : serverMessage
        ? serverMessage.startsWith("Error:")
          ? serverMessage
          : `Error: ${serverMessage}`
        : "Error: Unable to get a response.";
      setError("Failed to process query.");
      setMessages((prev) => [
        ...prev,
        { type: "error", content: errorContent },
      ]);
    } finally {
      console.log("Query completed");
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await axios.post(`${BACKEND_URL}/upload`, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        });
        const uploadedFilename = res.data.filename || file.name;
        setActiveFile(uploadedFilename);
        setViewMode("editor");
        
        await processQuery(`I uploaded file: ${uploadedFilename}. Please analyze/edit it.`);
    } catch (err) {
        console.error("Error uploading file:", err);
        setError("Failed to upload file");
    }
  };

  const handleStop = async (e) => {
    e.preventDefault();
    checkHealth();
    setIsLoading(false);
    setError(null);
    try {
      await axios.get(`${BACKEND_URL}/stop`);
      setStatus("Requesting stop...");
    } catch (err) {
      console.error("Error stopping the agent:", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      console.log("Empty query");
      return;
    }
    let textToSend = query;
    // Add context about the active file if available
    if (activeFile && viewMode === "editor") {
        textToSend += `\n[System Context: User is viewing file '${activeFile}']`;
    }

    setQuery("");
    await processQuery(textToSend);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-brand">
          <div className="logo-container">
            <img src={faviconPng} alt="Agentic Local" className="logo-icon" />
          </div>
          <div className="brand-text">
            <h1>Agentic Local</h1>
          </div>
        </div>
        <div className="header-status">
          <div
            className={`status-indicator ${isOnline ? "online" : "offline"}`}
          >
            <div className="status-dot"></div>
            <span className="status-text">
              {isOnline ? "Online" : "Offline"}
            </span>
          </div>
        </div>
        <div className="header-actions">
          <div className="view-toggle">
            <button 
                className={`toggle-btn ${viewMode === "browser" ? "active" : ""}`}
                onClick={() => setViewMode("browser")}
            >
                Browser
            </button>
            <button 
                className={`toggle-btn ${viewMode === "editor" ? "active" : ""}`}
                onClick={() => setViewMode("editor")}
            >
                Editor
            </button>
          </div>
          <div>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="main">
        <ResizableLayout initialLeftWidth={50}>
          <div className="chat-section">
            <h2>Chat Interface</h2>
            <div className="messages">
              {messages.length === 0 ? (
                <p className="placeholder">
                  No messages yet. Type below to start!
                </p>
              ) : (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`message ${
                      msg.type === "user"
                        ? "user-message"
                        : msg.type === "agent"
                        ? "agent-message"
                        : "error-message"
                    }`}
                  >
                    <div className="message-header">
                      {msg.type === "agent" && (
                        <span className="agent-name">{msg.agentName}</span>
                      )}
                      {msg.type === "agent" &&
                        msg.reasoning &&
                        expandedReasoning.has(index) && (
                          <div className="reasoning-content">
                            <ReactMarkdown>{msg.reasoning}</ReactMarkdown>
                          </div>
                        )}
                      {msg.type === "agent" && (
                        <button
                          className="reasoning-toggle"
                          onClick={() => toggleReasoning(index)}
                          title={
                            expandedReasoning.has(index)
                              ? "Hide reasoning"
                              : "Show reasoning"
                          }
                        >
                          {expandedReasoning.has(index) ? "▼" : "▶"} Reasoning
                        </button>
                      )}
                    </div>
                    <div className="message-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
            {isOnline && <div className="loading-animation">{status}</div>}
            {!isLoading && !isOnline && (
              <p className="loading-animation">
                System offline. Deploy backend first.
              </p>
            )}
            <form onSubmit={handleSubmit} className="input-area">
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                onChange={handleFileUpload}
              />
              <button
                type="button"
                className="upload-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Upload File"
              >
                📎
              </button>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your query..."
                disabled={isLoading}
              />
              <div className="action-buttons">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="icon-button"
                  aria-label="Send message"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={handleStop}
                  className="icon-button stop-button"
                  aria-label="Stop processing"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect
                      x="6"
                      y="6"
                      width="12"
                      height="12"
                      fill="currentColor"
                      rx="2"
                      stroke="none"
                    />
                  </svg>
                </button>
              </div>
            </form>
          </div>

          {viewMode === "editor" ? (
            <EditorView activeFile={activeFile} onFileChange={setActiveFile} />
          ) : (
            <div className="computer-section">
              <h2>Computer View</h2>
              <div className="content">
                {error && <p className="error">{error}</p>}
                <div className="screenshot">
                    {responseData?.screenshot &&
                    responseData.screenshot !== "placeholder.png" ? (
                      <img
                        src={responseData?.screenshot}
                        alt="Screenshot"
                        onError={(e) => {
                          e.target.src = "placeholder.png";
                          console.error("Failed to load screenshot");
                        }}
                        key={responseData?.screenshotTimestamp || "default"}
                      />
                    ) : (
                      <div className="block">
                        <p className="block-tool">Browser non disponibile</p>
                        <pre>
                          Nessuno screenshot. Le azioni di ricerca appaiono in Editor
                          View come tool web_search.
                        </pre>
                      </div>
                    )}
                </div>
              </div>
            </div>
          )}
        </ResizableLayout>
      </main>
    </div>
  );
}

export default App;
