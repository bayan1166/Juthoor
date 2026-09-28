import { useCallback, useState } from "react";
import { chatApi } from "./apiClient";

export interface ChatBubble {
  role: "student" | "tutor";
  text: string;
}

export function useSocraticChat(studentId: string, skillContext: string) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [sending, setSending] = useState(false);
  const [drillDownNotice, setDrillDownNotice] = useState<string | null>(null);

  const start = useCallback(async () => {
    const res = await chatApi.start(studentId, skillContext);
    setSessionId(res.session_id);
    setMessages([{ role: "tutor", text: res.opening_message }]);
  }, [studentId, skillContext]);

  const send = useCallback(
    async (text: string) => {
      if (!sessionId || sending) {
        return;
      }
      setSending(true);
      setMessages((prev) => [...prev, { role: "student", text }]);
      try {
        const res = await chatApi.send(studentId, sessionId, text);
        setMessages((prev) => [...prev, { role: "tutor", text: res.reply }]);
        if (res.drill_down_triggered && res.breadcrumb) {
          setDrillDownNotice(res.breadcrumb);
        }
      } finally {
        setSending(false);
      }
    },
    [studentId, sessionId, sending],
  );

  return { sessionId, messages, sending, drillDownNotice, start, send, clearNotice: () => setDrillDownNotice(null) };
}
