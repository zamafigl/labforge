import { useState } from "react";
import axios from "axios";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [form, setForm] = useState({
    subject: "cpp",
    lab: "lab_1",
    variant: 13,
    student: {
      name: "Иванов И.И.",
      group: "4131",
    },
  });

  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [error, setError] = useState("");

  function updateField(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  function updateStudent(field, value) {
    setForm((prev) => ({
      ...prev,
      student: {
        ...prev.student,
        [field]: value,
      },
    }));
  }

  async function generateLab() {
    setLoading(true);
    setError("");
    setDownloadUrl("");

    try {
      const response = await axios.post(`${API_URL}/generate-ai`, form);
      setDownloadUrl(`${API_URL}${response.data.download_url}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка генерации");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="card">
        <h1>LabForge</h1>
        <p className="subtitle">
          Генератор лабораторных работ по варианту
        </p>

        <div className="form">
          <label>
            Предмет
            <input
              value={form.subject}
              onChange={(e) => updateField("subject", e.target.value)}
            />
          </label>

          <label>
            Лаба
            <input
              value={form.lab}
              onChange={(e) => updateField("lab", e.target.value)}
            />
          </label>

          <label>
            Вариант
            <input
              type="number"
              value={form.variant}
              onChange={(e) => updateField("variant", Number(e.target.value))}
            />
          </label>

          <label>
            ФИО
            <input
              value={form.student.name}
              onChange={(e) => updateStudent("name", e.target.value)}
            />
          </label>

          <label>
            Группа
            <input
              value={form.student.group}
              onChange={(e) => updateStudent("group", e.target.value)}
            />
          </label>

          <button onClick={generateLab} disabled={loading}>
            {loading ? "Генерация..." : "Сгенерировать"}
          </button>

          {downloadUrl && (
            <a className="download" href={downloadUrl}>
              Скачать ZIP
            </a>
          )}

          {error && <div className="error">{error}</div>}
        </div>
      </section>
    </main>
  );
}

export default App;
