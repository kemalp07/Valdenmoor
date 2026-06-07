// Assembles final prompt and calls the AI API
import { API_BASE } from '../config/api';

export type Message = { id: string; role: 'user' | 'ai'; text: string; characterName?: string };

export type AIMessageResult = {
  text: string;
  characterName?: string;
  narratorInjection?: string;
  location?: string;
  userMessageId?: string;
  assistantMessageId?: string;
};

type ApiMessage = {
  role: 'user' | 'assistant';
  content: string;
};

type ChatApiResponse = {
  response?: string;
  text?: string;
  character_name?: string;
  location?: string;
};

const API_URL = `${API_BASE}/chat`;

export async function deleteMessage(
  sessionId: string,
  content: string,
  role: 'user' | 'assistant',
  messageId?: string,
): Promise<void> {
  try {
    await fetch(`${API_BASE}/delete-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        content,
        role,
        message_id: messageId,
      }),
    });
  } catch {
    // Best-effort server sync.
  }
}

export async function updateMessage(
  sessionId: string,
  oldContent: string,
  newContent: string,
  role: 'user' | 'assistant',
): Promise<void> {
  const trimmed = newContent.trim();
  if (!trimmed || trimmed === oldContent) return;

  try {
    await fetch(`${API_BASE}/edit-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        old_content: oldContent,
        new_content: trimmed,
        role,
      }),
    });
  } catch {
    // Best-effort server sync.
  }
}

export async function sendMessage(
  messages: Message[],
  userName: string,
  _house: string = '',
  sessionId: string = '',
  characterProfile: any = null,
  _playerAttraction: string = '',
  options?: { onChunk?: (text: string) => void },
): Promise<AIMessageResult> {
  try {
    const history: ApiMessage[] = messages
      .slice(-20)
      .map((m) => ({
        role: m.role === 'ai' ? 'assistant' : 'user',
        content: m.text,
      }));

    const payload = {
      message: messages.length === 0 ? '' : (history[history.length - 1]?.content || ''),
      user_name: userName,
      character_id: 'valdenmoor-narrator',
      location_id: 'ashenmoor-palace',
      history,
      session_id: sessionId,
      character_profile: characterProfile,
      language: localStorage.getItem('valdenmoor_language') || localStorage.getItem('hp_language') || 'tr',
    };

    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`AI API error: ${response.status}`);
    }

    const contentType = response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
      const data = (await response.json()) as ChatApiResponse;
      const text = data.response || data.text || '';
      if (!text) {
        throw new Error('Empty response from AI API');
      }
      return { text, characterName: data.character_name, location: data.location };
    }

    if (!response.body) {
      throw new Error('Streaming response body is empty');
    }

    // Gerçek SSE streaming — ReadableStream ile oku
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assembled = '';
    let characterName = '';
    let narratorInjection: string | undefined;
    let location: string | undefined;
    let userMessageId: string | undefined;
    let assistantMessageId: string | undefined;
    let buffer = '';

    const onChunk = options?.onChunk;

    const parseSseLine = (line: string) => {
      if (!line.startsWith('data: ')) return;
      const dataPart = line.slice(6).trim();
      if (!dataPart) return;

      try {
        const parsed = JSON.parse(dataPart) as {
          type?: string;
          text?: string;
          character_name?: string;
          narrator_injection?: string;
          location?: string;
          user_message_id?: string;
          assistant_message_id?: string;
        };
        if (parsed.type === 'meta') {
          narratorInjection = parsed.narrator_injection;
          if (parsed.location) location = parsed.location;
        } else if (parsed.type === 'chunk' && parsed.text) {
          assembled += parsed.text;
          if (onChunk) onChunk(assembled);
        } else if (parsed.type === 'done') {
          if (parsed.character_name) characterName = parsed.character_name;
          if (parsed.location) location = parsed.location;
          if (parsed.user_message_id) userMessageId = parsed.user_message_id;
          if (parsed.assistant_message_id) assistantMessageId = parsed.assistant_message_id;
        }
      } catch {
        // Ignore malformed SSE chunks.
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        parseSseLine(line);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      parseSseLine(buffer.trim());
    }

    if (!assembled) {
      throw new Error('Empty streaming response from AI API');
    }

    return {
      text: assembled,
      characterName: characterName || undefined,
      narratorInjection,
      location,
      userMessageId,
      assistantMessageId,
    };
  } catch (error) {
    console.error('sendMessage failed:', error);
    throw error;
  }
}
