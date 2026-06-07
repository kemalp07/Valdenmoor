import React, { createContext, useContext, useEffect, useState, useMemo, ReactNode } from 'react';
import { API_BASE } from '../config/api';
import { Language } from '../i18n/translations';

export type Message = {
  id: string;
  role: 'user' | 'ai';
  text: string;
  characterName?: string;
  timestamp?: number;
};

export type Character = {
  id: string;
  name: string;
  gender: string;
  rulingStyle?: string;
  traits: string[];
  origin: string;
  height: string;
  hairColor: string;
  fear: string;
  hobby: string;
  secretTrait: string;
  house: string;
  sessionId: string;
  createdAt: string;
  attraction?: string;
};

export type AppContextType = {
  characters: Character[];
  setCharacters: (chars: Character[] | ((prev: Character[]) => Character[])) => void;
  activeCharacter: Character | null;
  setActiveCharacter: (char: Character | null) => void;
  sessionId: string;
  messages: Message[];
  setMessages: (msgs: Message[] | ((prev: Message[]) => Message[])) => void;
  isLoading: boolean;
  setIsLoading: (val: boolean) => void;
  language: Language;
  setLanguage: (lang: Language) => void;
};

const AppContext = createContext<AppContextType | undefined>(undefined);

export const CHARACTERS_STORAGE_KEY = 'valdenmoor_characters';
export const ACTIVE_CHARACTER_STORAGE_KEY = 'valdenmoor_active_character_id';
const KNOWN_SESSIONS_KEY = 'valdenmoor_known_session_ids';

const LEGACY_CHARACTERS_KEY = 'fantasy_characters';
const LEGACY_ACTIVE_CHARACTER_KEY = 'fantasy_active_character_id';
const LEGACY_KNOWN_SESSIONS_KEY = 'fantasy_known_session_ids';
const OLDEST_CHARACTERS_KEY = 'hp_characters';
const OLDEST_ACTIVE_CHARACTER_KEY = 'hp_active_character_id';
const OLDEST_KNOWN_SESSIONS_KEY = 'hp_known_session_ids';

function migrateStorageKey(newKey: string, ...legacyKeys: string[]): string | null {
  const current = localStorage.getItem(newKey);
  if (current !== null) return current;

  for (const oldKey of legacyKeys) {
    const legacy = localStorage.getItem(oldKey);
    if (legacy !== null) {
      localStorage.setItem(newKey, legacy);
      localStorage.removeItem(oldKey);
      return legacy;
    }
  }

  return null;
}

export function loadStoredCharacters(): Character[] {
  const saved = migrateStorageKey(CHARACTERS_STORAGE_KEY, LEGACY_CHARACTERS_KEY, OLDEST_CHARACTERS_KEY);
  if (!saved) return [];

  try {
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function loadStoredActiveCharacterId(): string | null {
  return migrateStorageKey(ACTIVE_CHARACTER_STORAGE_KEY, LEGACY_ACTIVE_CHARACTER_KEY, OLDEST_ACTIVE_CHARACTER_KEY);
}

function resolveActiveCharacter(chars: Character[]): Character | null {
  const activeId = loadStoredActiveCharacterId();
  if (!activeId) return null;

  const match = chars.find((c) => c.id === activeId);
  if (!match?.sessionId) return null;

  return match;
}

function trackKnownSessionId(sessionId: string) {
  migrateStorageKey(KNOWN_SESSIONS_KEY, LEGACY_KNOWN_SESSIONS_KEY, OLDEST_KNOWN_SESSIONS_KEY);
  const ids: string[] = JSON.parse(localStorage.getItem(KNOWN_SESSIONS_KEY) || '[]');
  if (!ids.includes(sessionId)) {
    localStorage.setItem(KNOWN_SESSIONS_KEY, JSON.stringify([...ids, sessionId]));
  }
}

export function mapDbCharacterToCharacter(row: Record<string, unknown>): Character {
  return {
    id: String(row.id || ''),
    name: String(row.name || ''),
    gender: String(row.gender || ''),
    rulingStyle: String(
      row.ruling_style ||
        row.rulingStyle ||
        (Array.isArray(row.traits) && row.traits[0] ? row.traits[0] : ''),
    ),
    traits: Array.isArray(row.traits) ? row.traits as string[] : [],
    origin: String(row.origin || ''),
    height: String(row.height || ''),
    hairColor: String(row.hair_color || row.hairColor || ''),
    fear: String(row.fear || ''),
    hobby: String(row.hobby || ''),
    secretTrait: String(row.secret_trait || row.secretTrait || ''),
    house: String(row.player_house || row.house || 'valdenmoor'),
    sessionId: String(row.session_id || row.sessionId || ''),
    createdAt: String(row.created_at || row.createdAt || new Date().toISOString()),
    attraction: row.attraction ? String(row.attraction) : undefined,
  };
}

export async function saveCharacterToDB(character: Character, sessionId: string) {
  try {
    await fetch(`${API_BASE}/save-character`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, character }),
    });
    trackKnownSessionId(sessionId);
  } catch (e) {
    console.error('saveCharacterToDB error:', e);
  }
}

export async function loadCharactersFromDB(sessionId: string): Promise<Character[]> {
  try {
    const res = await fetch(
      `${API_BASE}/load-characters?session_id=${encodeURIComponent(sessionId)}`,
    );
    if (!res.ok) return [];
    const data = await res.json();
    return (data.characters || []).map(mapDbCharacterToCharacter);
  } catch (e) {
    console.error('loadCharactersFromDB error:', e);
    return [];
  }
}

export async function loadAllCharactersFromDB(): Promise<Character[]> {
  migrateStorageKey(KNOWN_SESSIONS_KEY, LEGACY_KNOWN_SESSIONS_KEY, OLDEST_KNOWN_SESSIONS_KEY);
  const sessionIds: string[] = JSON.parse(localStorage.getItem(KNOWN_SESSIONS_KEY) || '[]');
  const merged = new Map<string, Character>();
  for (const sid of sessionIds) {
    const chars = await loadCharactersFromDB(sid);
    for (const c of chars) {
      merged.set(c.id, c);
    }
  }
  return [...merged.values()];
}

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const initialCharacters = loadStoredCharacters();

  const [characters, setCharacters] = useState<Character[]>(initialCharacters);
  const [activeCharacter, setActiveCharacter] = useState<Character | null>(() =>
    resolveActiveCharacter(initialCharacters),
  );
  const sessionId = useMemo(() => {
    return activeCharacter?.sessionId || '';
  }, [activeCharacter]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [language, setLanguage] = useState<Language>(() => {
    const current = localStorage.getItem('valdenmoor_language') as Language | null;
    if (current) return current;
    const legacy = localStorage.getItem('hp_language') as Language | null;
    if (legacy) {
      localStorage.setItem('valdenmoor_language', legacy);
      localStorage.removeItem('hp_language');
      return legacy;
    }
    return 'tr';
  });

  const handleSetLanguage = (lang: Language) => {
    localStorage.setItem('valdenmoor_language', lang);
    setLanguage(lang);
  };

  useEffect(() => {
    localStorage.setItem(CHARACTERS_STORAGE_KEY, JSON.stringify(characters));
  }, [characters]);

  useEffect(() => {
    const syncOnStartup = async () => {
      let chars = loadStoredCharacters();

      if (chars.length === 0) {
        const fromDb = await loadAllCharactersFromDB();
        if (fromDb.length > 0) {
          chars = fromDb;
          setCharacters(fromDb);
        }
      }

      const resolved = resolveActiveCharacter(chars);
      if (resolved) {
        setActiveCharacter(resolved);
      }
    };

    syncOnStartup();
  }, []);

  useEffect(() => {
    if (activeCharacter) {
      localStorage.setItem(ACTIVE_CHARACTER_STORAGE_KEY, activeCharacter.id);
    } else {
      localStorage.removeItem(ACTIVE_CHARACTER_STORAGE_KEY);
    }
  }, [activeCharacter]);

  return (
    <AppContext.Provider
      value={{
        characters,
        setCharacters,
        activeCharacter,
        setActiveCharacter,
        sessionId,
        messages,
        setMessages,
        isLoading,
        setIsLoading,
        language,
        setLanguage: handleSetLanguage,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
