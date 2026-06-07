// Assembles final prompt and calls the AI API
import { API_BASE } from '../config/api';

export type Message = { id: string; role: 'user' | 'ai'; text: string; characterName?: string };

export type ActionButton = { action: string; label: string };

export type AIMessageResult = {
  text: string;
  characterName?: string;
  narratorInjection?: string;
  location?: string;
  gameStats?: Record<string, number>;
  suggestedButtons?: ActionButton[];
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
): Promise<void> {
  try {
    await fetch(`${API_BASE}/delete-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, content, role }),
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

    const raw = await response.text();
    let assembled = '';
    let characterName = '';
    let narratorInjection: string | undefined;
    let location: string | undefined;
    let gameStats: Record<string, number> | undefined;
    let suggestedButtons: ActionButton[] | undefined;

    for (const line of raw.split('\n')) {
      if (!line.startsWith('data: ')) {
        continue;
      }

      const dataPart = line.slice(6).trim();
      if (!dataPart) {
        continue;
      }

      try {
        const parsed = JSON.parse(dataPart) as {
          type?: string;
          text?: string;
          character_name?: string;
          narrator_injection?: string;
          location?: string;
          game_stats?: Record<string, number>;
          suggested_buttons?: ActionButton[];
        };
        if (parsed.type === 'meta') {
          narratorInjection = parsed.narrator_injection;
          if (parsed.location) {
            location = parsed.location;
          }
          if (parsed.suggested_buttons && parsed.suggested_buttons.length > 0) {
            suggestedButtons = parsed.suggested_buttons;
          }
        } else if (parsed.type === 'chunk' && parsed.text) {
          assembled += parsed.text;
        } else if (parsed.type === 'done') {
          if (parsed.character_name) {
            characterName = parsed.character_name;
          }
          if (parsed.location) {
            location = parsed.location;
          }
          if (parsed.game_stats) {
            gameStats = parsed.game_stats;
          }
          if (parsed.suggested_buttons && parsed.suggested_buttons.length > 0) {
            suggestedButtons = parsed.suggested_buttons;
          }
        }
      } catch {
        // Ignore malformed SSE chunks.
      }
    }

    if (!assembled) {
      throw new Error('Empty streaming response from AI API');
    }

    return {
      text: assembled,
      characterName: characterName || undefined,
      narratorInjection,
      location,
      gameStats,
      suggestedButtons,
    };
  } catch (error) {
    console.error('sendMessage failed:', error);
    throw error;
  }
}
