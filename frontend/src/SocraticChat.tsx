import { FormEvent, useEffect, useState } from "react";
import { useSocraticChat } from "./useSocraticChat";

interface SocraticChatProps {
  studentId: string;
  skillContext: string;
}

export default function SocraticChat({ studentId, skillContext }: SocraticChatProps) {
  const { messages, sending, drillDownNotice, start, send, clearNotice } = useSocraticChat(studentId, skillContext);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    start();
  }, [start]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!draft.trim()) {
      return;
    }
    send(draft.trim());
    setDraft("");
  }

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-800 bg-slate-950">
      <div className="border-b border-slate-800 px-4 py-3">
        <p className="text-sm font-medium text-slate-200">Juthoor Tutor</p>
      </div>

      {drillDownNotice && (
        <div className="mx-4 mt-3 rounded-lg border border-amber-700 bg-amber-950 px-3 py-2 text-sm text-amber-200">
          <span>{drillDownNotice}</span>
          <button className="ms-3 underline" onClick={clearNotice} type="button">
            حسناً
          </button>
        </div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "student" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                m.role === "student" ? "bg-emerald-700 text-white" : "bg-slate-800 text-slate-100"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && <div className="text-xs text-slate-500">...</div>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-slate-800 p-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="اكتب سؤالك هنا"
          className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-600"
        />
        <button
          type="submit"
          disabled={sending}
          className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          إرسال
        </button>
      </form>
    </div>
  );
}
