import type { Message } from "./types";

export function messageTime(message: Message): Date {
  return new Date(
    message.role === "assistant" && message.visible_at
      ? message.visible_at
      : message.created_at,
  );
}

export function shouldShowTime(
  messages: Message[],
  index: number,
  thresholdSeconds = 300,
): boolean {
  if (index === 0) return true;
  const current = messageTime(messages[index]);
  const previous = messageTime(messages[index - 1]);
  if (current.toDateString() !== previous.toDateString()) return true;
  return current.getTime() - previous.getTime() >= thresholdSeconds * 1000;
}

export function formatMessageTime(message: Message, now = new Date()): string {
  const value = messageTime(message);
  const time = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
  const days = Math.floor(
    (startOfDay(now).getTime() - startOfDay(value).getTime()) / 86_400_000,
  );
  if (days === 0) return time;
  if (days === 1) return `Yesterday ${time}`;
  if (days < 7)
    return `${new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(value)} ${time}`;
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
  };
  if (value.getFullYear() !== now.getFullYear()) options.year = "numeric";
  return `${new Intl.DateTimeFormat(undefined, options).format(value)} ${time}`;
}

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}
