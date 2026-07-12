// Thin typed client for the orchestrator HTTP API (orchestrator/serve.py).

export interface AskResponse {
  answer: string;
}

export async function ask(question: string, sessionId: string): Promise<string> {
  const res = await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`request failed: ${res.status}`);
  const data: AskResponse = await res.json();
  return data.answer;
}

// Pull any absolute file paths the agent reports (generated PDF/PPTX) so the
// UI can surface them as download links.
export function extractArtifacts(answer: string): string[] {
  const matches = answer.match(/\/\S+\.(pdf|pptx)/gi);
  return matches ? Array.from(new Set(matches)) : [];
}
