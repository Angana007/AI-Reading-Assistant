import React, { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const [pdfFile, setPdfFile] = useState(null);
  const [voice, setVoice] = useState("ash");
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [jobId, setJobId] = useState(null);

  const voices = ["ash", "alloy", "verse", "sage"];

  const handleFileChange = (e) => setPdfFile(e.target.files[0]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pdfFile) return alert("Please select a PDF file");

    const formData = new FormData();
    formData.append("file", pdfFile);
    formData.append("voice", voice);

    try {
      setLoading(true);
      setProgress(0);
      setAudioUrl(null);

      const response = await axios.post("http://localhost:8000/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setJobId(response.data.job_id);
      setAudioUrl(`http://localhost:8000${response.data.audio_url}`);
    } catch (err) {
      console.error(err);
      alert("Error uploading PDF");
    }
  };

  // Poll backend for progress every 1s
  useEffect(() => {
    let interval;
    if (jobId) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`http://localhost:8000/progress/${jobId}`);
          setProgress(res.data.progress);
          if (res.data.progress >= 100 || res.data.progress === -1) {
            clearInterval(interval);
            setLoading(false);
          }
        } catch (err) {
          console.error(err);
          clearInterval(interval);
          setLoading(false);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div style={{ maxWidth: 600, margin: "50px auto", fontFamily: "sans-serif" }}>
      <h1>📖 AI PDF Reader</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label>Upload PDF: </label>
          <input type="file" accept=".pdf" onChange={handleFileChange} />
        </div>

        <div style={{ marginTop: 10 }}>
          <label>Select Voice: </label>
          <select value={voice} onChange={(e) => setVoice(e.target.value)}>
            {voices.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        <button style={{ marginTop: 20 }} type="submit" disabled={loading}>
          {loading ? "Generating..." : "Generate Audio"}
        </button>
      </form>

      {/* Real progress bar */}
      {loading && (
        <div style={{ marginTop: 20, width: "100%", background: "#eee", borderRadius: 5 }}>
          <div
            style={{
              width: `${progress}%`,
              height: 10,
              background: "#4caf50",
              borderRadius: 5,
              transition: "width 0.3s ease",
            }}
          />
          <div style={{ textAlign: "center", marginTop: 5 }}>{progress}%</div>
        </div>
      )}

      {audioUrl && !loading && (
        <div style={{ marginTop: 30 }}>
          <h3>🎧 Listen to your audiobook:</h3>
          <audio controls src={audioUrl} autoPlay />
          <a href={audioUrl} download style={{ display: "block", marginTop: 10 }}>
            ⬇️ Download Audio
          </a>
        </div>
      )}
    </div>
  );
}

export default App;
