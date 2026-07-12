import { useRef, useState } from "react";
import { ask, extractArtifacts } from "./api";

interface Message {
  role: "user" | "assistant";
  text: string;
  artifacts?: string[];
}

const SUGGESTIONS = [
  "Show total spend by campaign last quarter",
  "Flag the 3 worst campaigns by ROAS",
  "Summarize the worst campaigns as a one-page PDF and a 5-slide deck",
];

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  // One stable session id per browser tab => multi-turn memory on the server.
  const sessionId = useRef(crypto.randomUUID()).current;

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const answer = await ask(question, sessionId);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: answer, artifacts: extractArtifacts(answer) },
      ]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${String(err)}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Atlas</h1>
        <span>MCP-native agentic workspace assistant</span>
      </header>

      <div className="transcript">
        {messages.length === 0 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <pre>{m.text}</pre>
            {m.artifacts && m.artifacts.length > 0 && (
              <div className="artifacts">
                {m.artifacts.map((a) => (
                  <a key={a} href={`file://${a}`} download>
                    ⬇ {a.split("/").pop()}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant">…</div>}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          placeholder="Ask about the marketing warehouse…"
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
        />
        <button type="submit" disabled={busy}>
          Send
        </button>
      </form>
    </div>
  );
}
