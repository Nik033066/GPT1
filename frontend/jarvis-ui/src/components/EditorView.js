
import React, { useState, useEffect } from "react";
import axios from "axios";
import "./EditorView.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:7777";

export const EditorView = ({ activeFile, onFileChange }) => {
  const [content, setContent] = useState("");
  const [fileList, setFileList] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchFileList();
    if (activeFile) {
      loadFileContent(activeFile);
    }
  }, [activeFile]);

  const fetchFileList = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/files`);
      setFileList(res.data.files || []);
    } catch (err) {
      console.error("Error fetching file list:", err);
    }
  };

  const loadFileContent = async (filename) => {
    if (!filename) return;
    setLoading(true);
    try {
        // For PDFs, we don't fetch text content, we just set the URL
        if (filename.toLowerCase().endsWith(".pdf")) {
            setContent(null); 
        } else {
            const res = await axios.get(`${BACKEND_URL}/files/${filename}`, {
                responseType: 'text'
            });
            setContent(res.data);
        }
    } catch (err) {
      console.error("Error loading file content:", err);
      setContent("Error loading file content.");
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async () => {
    if (!activeFile) return;
    if (!window.confirm(`Are you sure you want to delete ${activeFile}?`)) return;
    try {
      await axios.delete(`${BACKEND_URL}/files/${activeFile}`);
      onFileChange(""); // clear active file
      fetchFileList();
    } catch (err) {
      console.error("Error deleting file:", err);
      alert("Failed to delete file");
    }
  };

  const isPdf = activeFile?.toLowerCase().endsWith(".pdf");
  const fileUrl = activeFile ? `${BACKEND_URL}/files/${activeFile}` : null;

  return (
    <div className="editor-view">
      <div className="editor-header">
        <h3>Editor / Viewer {activeFile && ` - ${activeFile}`}</h3>
        <div style={{display: 'flex', gap: '10px'}}>
            {activeFile && (
                <button onClick={deleteFile} className="delete-btn" title="Delete File">🗑️</button>
            )}
        </div>
      </div>
      
      <div className="editor-content">
        {!activeFile ? (
            <div className="placeholder-text">Select a file to view or edit</div>
        ) : loading ? (
            <div className="loading-text">Loading...</div>
        ) : isPdf ? (
            <iframe 
                src={fileUrl} 
                title="PDF Viewer"
                className="pdf-viewer" 
            />
        ) : (
            <textarea 
                className="code-editor"
                value={content} 
                onChange={(e) => setContent(e.target.value)}
                readOnly={true} // For now read-only until save implemented
            />
        )}
      </div>
    </div>
  );
};
