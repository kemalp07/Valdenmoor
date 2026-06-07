import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  Image,
  ImageBackground,
  FlatList,
  KeyboardAvoidingView,
  NativeSyntheticEvent,
  Platform,
  Pressable,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TextInputContentSizeChangeEventData,
  TextInputKeyPressEventData,
  View,
} from 'react-native';
import { API_BASE } from '../config/api';
import { useAppContext, Message } from '../context/AppContext';
import { getFirstMessage } from '../services/characterCard';
import { deleteMessage, sendMessage as sendAiMessage, updateMessage } from '../services/aiService';
import { getInputTips, getTagNames, t, Language } from '../i18n/translations';

const NARRATOR_NAME = 'Valdenmoor';
const NARRATOR_CREST = require('../../assets/valdenmoor_crest.png');
const USER_BUBBLE_COLOR = 'rgba(120, 50, 8, 0.95)';
const LOCATION_BACKGROUNDS: Record<string, any> = {
  throne_room: require('../../assets/backgrounds/throne_room.png'),
  great_hall: require('../../assets/backgrounds/great_hall.png'),
  war_room: require('../../assets/backgrounds/war_room.png'),
  castle_corridor: require('../../assets/backgrounds/castle_corridor.png'),
  castle_exterior: require('../../assets/backgrounds/castle_exterior.png'),
  ashenmoor_market: require('../../assets/backgrounds/ashenmoor_market.png'),
  ashenmoor_streets: require('../../assets/backgrounds/ashenmoor_streets.png'),
  dawnhold_fortress: require('../../assets/backgrounds/dawnhold_fortress.png'),
  varethis_harbor: require('../../assets/backgrounds/varethis_harbor.png'),
  varethis_sea: require('../../assets/backgrounds/varethis_sea.png'),
  throne_antechamber: require('../../assets/backgrounds/throne_antechamber.png'),
  castle_dungeon: require('../../assets/backgrounds/castle_dungeon.png'),
  castle_battlements: require('../../assets/backgrounds/castle_battlements.png'),
  royal_chambers: require('../../assets/backgrounds/royal_chambers.png'),
  forest_path: require('../../assets/backgrounds/forest_path.png'),
  selmara_palace: require('../../assets/backgrounds/selmara_palace.png'),
  kadir_bazaar: require('../../assets/backgrounds/kadir_bazaar.png'),
  battlefield: require('../../assets/backgrounds/battlefield.png'),
  council_chamber: require('../../assets/backgrounds/council_chamber.png'),
  chapel: require('../../assets/backgrounds/chapel.png'),
};
const MIN_INPUT_HEIGHT = 36;
const MAX_INPUT_HEIGHT = 100;

const WEB_INPUT_RESET =
  Platform.OS === 'web'
    ? ({ outlineWidth: 0, outlineStyle: 'none', boxShadow: 'none' } as any)
    : undefined;

const CHARACTER_AVATARS: Record<string, any> = {
  NARRATOR: NARRATOR_CREST,
  'Dük Malachar': require('../../assets/characters/duke_malachar.jpg'),
  'General Harkon': require('../../assets/characters/general_harkon.jpg'),
  'Kral Edwyn': require('../../assets/characters/king_edwyn.jpg'),
  'Prenses Elowen': require('../../assets/characters/princess_elowen.jpg'),
  'Prens Aldric': require('../../assets/characters/prince_aldric_selmara.jpg'),
  'Sultan Rashid': require('../../assets/characters/sultan_rashid.jpg'),
  'Elçi Zara': require('../../assets/characters/envoy_zara.jpg'),
  'Lord Aldric Vane': require('../../assets/characters/aldric_vane.jpg'),
  'Lord Harwin Sorn': require('../../assets/characters/harwin_sorn.jpg'),
  'Lord Cerin Vane': require('../../assets/characters/cerin_vane.jpg'),
  'Rahip Edran': require('../../assets/characters/rahip_edran.jpg'),
  Mira: require('../../assets/characters/mira.jpg'),
  'General Caelan Voss': require('../../assets/characters/caelan_voss.jpg'),
  'Lord Commander Draven': require('../../assets/characters/draven.jpg'),
  'Komutan Sera Ashford': require('../../assets/characters/sera_ashford.jpg'),
  Tomas: require('../../assets/characters/tomas.jpg'),
  Lena: require('../../assets/characters/lena.jpg'),
};

const TAG_AVATARS: Record<string, any> = {
  NARRATOR: NARRATOR_CREST,
  UNKNOWN: NARRATOR_CREST,
  DUKE_MALACHAR: require('../../assets/characters/duke_malachar.jpg'),
  GENERAL_HARKON: require('../../assets/characters/general_harkon.jpg'),
  KING_EDWYN: require('../../assets/characters/king_edwyn.jpg'),
  PRINCESS_ELOWEN: require('../../assets/characters/princess_elowen.jpg'),
  PRINCE_ALDRIC_SELMARA: require('../../assets/characters/prince_aldric_selmara.jpg'),
  SULTAN_RASHID: require('../../assets/characters/sultan_rashid.jpg'),
  ENVOY_ZARA: require('../../assets/characters/envoy_zara.jpg'),
  LORD_ALDRIC_VANE: require('../../assets/characters/aldric_vane.jpg'),
  LORD_HARWIN_SORN: require('../../assets/characters/harwin_sorn.jpg'),
  LORD_CERIN_VANE: require('../../assets/characters/cerin_vane.jpg'),
  PRIEST_EDRAN: require('../../assets/characters/rahip_edran.jpg'),
  MIRA: require('../../assets/characters/mira.jpg'),
  GENERAL_CAELAN_VOSS: require('../../assets/characters/caelan_voss.jpg'),
  LORD_COMMANDER_DRAVEN: require('../../assets/characters/draven.jpg'),
  COMMANDER_SERA_ASHFORD: require('../../assets/characters/sera_ashford.jpg'),
  TOMAS: require('../../assets/characters/tomas.jpg'),
  LENA: require('../../assets/characters/lena.jpg'),
};

function cleanAiDisplayText(text: string): string {
  return text.replace(/\s*\[LOCATION:[^\]]+\]/gi, '').trim();
}

function createMessage(role: 'user' | 'ai', text: string, characterName?: string): Message {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    role,
    text,
    characterName,
    timestamp: Date.now(),
  };
}

function isEmptyUserMessage(item: Message): boolean {
  return item.role === 'user' && (!item.text || item.text.trim() === '');
}

const TypingIndicator = () => {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const bounce = (dot: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, {
            toValue: -6,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.delay(600),
        ])
      ).start();

    bounce(dot1, 0);
    bounce(dot2, 150);
    bounce(dot3, 300);
  }, []);

  return (
    <View style={styles.typingIndicator}>
      <Animated.View style={[styles.typingDot, { transform: [{ translateY: dot1 }] }]} />
      <Animated.View style={[styles.typingDot, { transform: [{ translateY: dot2 }] }]} />
      <Animated.View style={[styles.typingDot, { transform: [{ translateY: dot3 }] }]} />
    </View>
  );
};

function TypingBubble({ language }: { language: Language }) {
  return (
    <View style={styles.typingBubbleSimple}>
      <TypingIndicator />
    </View>
  );
}

type DeleteConfirmState = {
  title: string;
  message: string;
  onConfirm: () => void | Promise<void>;
};

type MessageEditProps = {
  item: Message;
  sessionId: string;
  editingId: string | null;
  editText: string;
  setEditText: (text: string) => void;
  setEditingId: (id: string | null) => void;
  setMessages: (msgs: Message[] | ((prev: Message[]) => Message[])) => void;
  onRequestDelete: (opts: DeleteConfirmState) => void;
};

type MessageBubbleProps = MessageEditProps;

function applyAiResponseToMessages(
  prev: Message[],
  displayText: string,
  aiResponse: { characterName?: string; userMessageId?: string; assistantMessageId?: string },
): Message[] {
  const updated = [...prev];
  if (aiResponse.userMessageId) {
    const userIdx = updated.findLastIndex((m) => m.role === 'user');
    if (userIdx !== -1) {
      updated[userIdx] = { ...updated[userIdx], id: aiResponse.userMessageId };
    }
  }
  const aiMsg = createMessage('ai', displayText, aiResponse.characterName);
  if (aiResponse.assistantMessageId) {
    aiMsg.id = aiResponse.assistantMessageId;
  }
  return [...updated.filter((m) => m.id !== 'streaming'), aiMsg];
}

const STREAM_TICK_MS = 32;

function nextStreamRevealStep(remaining: number): number {
  if (remaining <= 0) return 0;
  if (remaining > 120) return 3;
  if (remaining > 60) return 2;
  return 1;
}

async function deleteMessageItem(
  sessionId: string,
  item: Message,
  role: 'user' | 'assistant',
  setMessages: MessageEditProps['setMessages'],
) {
  setMessages((prev) => prev.filter((m) => m.id !== item.id));
  await deleteMessage(sessionId, item.text, role, item.id);
}

async function deleteAiBlockItem(
  sessionId: string,
  item: Message,
  blockIndex: number,
  language: Language,
  setMessages: MessageEditProps['setMessages'],
) {
  const mergedBlocks = mergeTaggedBlocks(parseTaggedResponse(item.text, getTagNames(language)));

  if (blockIndex < 0 || blockIndex >= mergedBlocks.length) {
    return;
  }

  if (mergedBlocks.length === 1) {
    await deleteMessageItem(sessionId, item, 'assistant', setMessages);
    return;
  }

  mergedBlocks.splice(blockIndex, 1);
  const newText = rebuildTaggedText(mergedBlocks);

  setMessages((prev) =>
    prev.map((m) => (m.id === item.id ? { ...m, text: newText } : m)),
  );
  await updateMessage(sessionId, item.text, newText, 'assistant', item.id);
}

async function saveMessageEdit(
  sessionId: string,
  item: Message,
  newText: string,
  role: 'user' | 'assistant',
  setMessages: MessageEditProps['setMessages'],
  setEditingId: (id: string | null) => void,
) {
  const trimmed = newText.trim();
  if (!trimmed) {
    setEditingId(null);
    return;
  }

  setMessages((prev) =>
    prev.map((m) => (m.id === item.id ? { ...m, text: trimmed } : m)),
  );
  setEditingId(null);

  if (trimmed !== item.text) {
    await updateMessage(sessionId, item.text, trimmed, role, item.id);
  }
}

function DeleteConfirmModal({
  confirm,
  language,
  onCancel,
  onConfirm,
}: {
  confirm: DeleteConfirmState | null;
  language: Language;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!confirm) return null;

  return (
    <View style={styles.modalOverlay}>
      <View style={styles.modalBox}>
        <Text style={styles.modalTitle}>{confirm.title}</Text>
        <Text style={styles.modalText}>{confirm.message}</Text>
        <View style={styles.modalButtons}>
          <TouchableOpacity style={styles.modalCancel} onPress={onCancel}>
            <Text style={styles.modalCancelText}>{t(language, 'cancel')}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.modalDelete} onPress={onConfirm}>
            <Text style={styles.modalDeleteText}>{t(language, 'delete')}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

function BubbleInlineActions({
  onEdit,
  onDelete,
  variant = 'ai',
}: {
  onEdit: () => void;
  onDelete: () => void;
  variant?: 'user' | 'ai';
}) {
  const { language } = useAppContext();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const handler = () => setOpen(false);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, [open]);

  return (
    <View
      style={[
        styles.bubbleActionsAnchor,
        variant === 'user' ? styles.userBubbleActionsAnchor : styles.aiBubbleActionsAnchor,
      ]}
    >
      <Pressable onPress={() => setOpen((o) => !o)}>
        <Text style={{ color: 'rgba(255,255,255,0.3)', fontSize: 16, lineHeight: 16 }}>⋮</Text>
      </Pressable>

      {open && (
        <>
          <Pressable
            onPress={() => setOpen(false)}
            style={{
              position: 'fixed' as any,
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 25,
            }}
          />
          <View style={{
            position: 'absolute',
            bottom: 24,
            right: 0,
            backgroundColor: 'rgba(15,10,3,0.97)',
            borderRadius: 8,
            borderWidth: 1,
            borderColor: 'rgba(201,168,76,0.2)',
            flexDirection: 'row',
            overflow: 'hidden',
            zIndex: 30,
          }}>
            <Pressable
              onPress={() => {
                setOpen(false);
                onEdit();
              }}
              style={{ paddingHorizontal: 14, paddingVertical: 8 }}
            >
              <Text style={{ color: '#c9a84c', fontSize: 12 }}>{t(language, 'edit')}</Text>
            </Pressable>
            <View style={{ width: 1, backgroundColor: 'rgba(255,255,255,0.06)' }} />
            <Pressable
              onPress={() => {
                setOpen(false);
                onDelete();
              }}
              style={{ paddingHorizontal: 14, paddingVertical: 8 }}
            >
              <Text style={{ color: '#e87a7a', fontSize: 12 }}>{t(language, 'delete')}</Text>
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}

function EditMessageActions({
  onSave,
  onCancel,
}: {
  onSave: () => void;
  onCancel: () => void;
}) {
  const { language } = useAppContext();

  return (
    <View style={styles.userMessageActions}>
      <Pressable onPress={onSave}>
        <Text style={styles.userActionSave}>{t(language, 'save')}</Text>
      </Pressable>
      <Pressable onPress={onCancel}>
        <Text style={styles.userActionCancel}>{t(language, 'cancel')}</Text>
      </Pressable>
    </View>
  );
}

function getCharacterAvatarSource(characterName?: string) {
  if (!characterName) {
    return null;
  }

  return CHARACTER_AVATARS[characterName] || null;
}

type TaggedBlock = {
  tag: string;
  rawTag: string;
  name: string;
  content: string;
};

function mergeTaggedBlocks(blocks: TaggedBlock[]): TaggedBlock[] {
  return blocks.reduce((acc: TaggedBlock[], block) => {
    const last = acc[acc.length - 1];
    if (last && last.tag === block.tag && last.rawTag === block.rawTag) {
      last.content = `${last.content}\n${cleanContent(block.content)}`;
      return acc;
    }
    acc.push({ ...block, content: cleanContent(block.content) });
    return acc;
  }, []);
}

function rebuildTaggedText(blocks: TaggedBlock[]): string {
  return blocks
    .map((block) => `[${block.rawTag}]\n${block.content.trim()}`)
    .join('\n\n')
    .trim();
}

function parseTaggedResponse(text: string, tagNames: Record<string, string>): TaggedBlock[] {
  const lines = text.split('\n');
  const blocks: TaggedBlock[] = [];
  let currentTag = 'NARRATOR';
  let currentRawTag = 'NARRATOR';
  let currentLines: string[] = [];

  const pushBlock = () => {
    const content = currentLines.join('\n').trim();
    if (content) {
      let resolvedTag = currentTag;
      let resolvedName = tagNames[currentTag] || currentTag;

      if (currentRawTag.startsWith('CHARACTER:')) {
        resolvedName = currentRawTag.slice(10).trim();
        const idTag = resolvedName.toUpperCase().replace(/\s+/g, '_');
        if (TAG_AVATARS[idTag]) {
          resolvedTag = idTag;
        } else if (CHARACTER_AVATARS[resolvedName]) {
          resolvedTag = 'UNKNOWN';
        } else {
          const upperName = resolvedName.toUpperCase().split(' ')[0];
          resolvedTag = TAG_AVATARS[upperName] ? upperName : 'UNKNOWN';
        }
      }

      blocks.push({
        tag: resolvedTag,
        rawTag: currentRawTag,
        name: resolvedName,
        content,
      });
    }
  };

  for (const line of lines) {
    if (/^\[TIME:[^\]]+\]/i.test(line.trim())) {
      continue;
    }
    const tagMatch = line.match(/^\[([^\]]+)\]\s*(.*)/);
    if (tagMatch) {
      pushBlock();
      currentRawTag = tagMatch[1].trim();
      currentTag = currentRawTag;
      currentLines = tagMatch[2] ? [tagMatch[2]] : [];
    } else {
      currentLines.push(line);
    }
  }

  pushBlock();
  return blocks;
}

const cleanContent = (text: string) =>
  text.replace(/\[TIME:[^\]]+\]/gi, '').replace(/<[^>]*>/g, '').trim();

function parseAIMessage(text: string): React.ReactNode {
  const cleanedText = cleanContent(text);
  const paragraphs = cleanedText.split(/\n\n+/).filter((paragraph) => paragraph.trim() !== '');

  return (
    <>
      {paragraphs.map((paragraph, pi) => {
        const lines = paragraph.split('\n').filter((line) => line.trim() !== '');

        return (
          <View key={pi} style={styles.aiParagraph}>
            {lines.map((line, li) => {
              const dialogueMatch = line.match(/^([A-ZÇĞİÖŞÜa-zçğışöü\s]+):\s*"(.+)"$/);
              if (dialogueMatch) {
                return (
                  <Text key={`${pi}-${li}`} style={styles.aiLine}>
                    <Text style={styles.aiSpeakerText}>{dialogueMatch[1]}: </Text>
                    <Text style={styles.aiDialogueText}>"{dialogueMatch[2]}"</Text>
                  </Text>
                );
              }

              const quoteOnlyMatch = line.match(/^"(.+)"$/);
              if (quoteOnlyMatch) {
                return (
                  <Text key={`${pi}-${li}`} style={styles.aiLine}>
                    <Text style={styles.aiDialogueText}>"{quoteOnlyMatch[1]}"</Text>
                  </Text>
                );
              }

              if (line.indexOf('"') !== -1) {
                const pieces = line.split(/("[^"]*")/g);
                return (
                  <Text key={`${pi}-${li}`} style={styles.aiLine}>
                    {pieces.map((piece, j) => {
                      if (!piece) return null;
                      if (piece.startsWith('"') && piece.endsWith('"')) {
                        return (
                          <Text key={`${pi}-${li}-${j}`} style={styles.aiDialogueText}>
                            {piece}
                          </Text>
                        );
                      }

                      const parts = piece.split(/(\*[^*]+\*)/g);
                      return parts.map((part, k) =>
                        part.startsWith('*') && part.endsWith('*') ? (
                          <Text key={`${pi}-${li}-${j}-${k}`} style={styles.aiItalicText}>
                            {part.slice(1, -1)}
                          </Text>
                        ) : (
                          <Text key={`${pi}-${li}-${j}-${k}`} style={styles.aiPlainText}>
                            {part}
                          </Text>
                        ),
                      );
                    })}
                  </Text>
                );
              }

              const parts = line.split(/(\*[^*]+\*)/g);
              return (
                <Text key={`${pi}-${li}`} style={styles.aiLine}>
                  {parts.map((part, j) =>
                    part.startsWith('*') && part.endsWith('*') ? (
                      <Text key={`${pi}-${li}-${j}`} style={styles.aiItalicText}>
                        {part.slice(1, -1)}
                      </Text>
                    ) : (
                      <Text key={`${pi}-${li}-${j}`} style={styles.aiPlainText}>
                        {part}
                      </Text>
                    ),
                  )}
                </Text>
              );
            })}
          </View>
        );
      })}
    </>
  );
}

const isErrorMessage = (text: string) =>
  text.includes('Vertex AI HTTP 429') ||
  text.includes('RESOURCE_EXHAUSTED') ||
  text.includes('Resource exhausted') ||
  text.includes('Failed to fetch');

function AIMessageBubble({
  item,
  sessionId,
  editingId,
  editText,
  setEditText,
  setEditingId,
  setMessages,
  onRequestDelete,
  language,
}: MessageEditProps & { language: Language }) {
  if (isErrorMessage(item.text)) {
    return (
      <View style={styles.aiBlockRow}>
        <Text style={styles.aiErrorFallback}>
          {t(language, 'aiErrorFallback')}
        </Text>
      </View>
    );
  }

  if (editingId === item.id) {
    return (
      <View style={styles.aiBlockRow}>
        <View style={styles.aiBlockBody}>
          <TextInput
            value={editText}
            onChangeText={setEditText}
            style={[styles.aiBubble, styles.aiEditInput]}
            autoFocus
            multiline
          />
          <EditMessageActions
            onSave={() => saveMessageEdit(sessionId, item, editText, 'assistant', setMessages, setEditingId)}
            onCancel={() => setEditingId(null)}
          />
        </View>
      </View>
    );
  }

  const taggedBlocks = parseTaggedResponse(item.text, getTagNames(language));
  const mergedBlocks = mergeTaggedBlocks(taggedBlocks);

  const startEdit = () => {
    setEditText(item.text);
    setEditingId(item.id);
  };

  const handleDeleteBlock = (blockIndex: number) => {
    const block = mergedBlocks[blockIndex];
    const isLastBlock = mergedBlocks.length === 1;
    onRequestDelete({
      title: t(language, 'deleteMessageTitle'),
      message: isLastBlock
        ? t(language, 'deleteAiMessageConfirm')
        : t(language, 'deleteAiBlockConfirm', block?.name || ''),
      onConfirm: () => deleteAiBlockItem(sessionId, item, blockIndex, language, setMessages),
    });
  };

  return (
    <>
      {mergedBlocks.map((block, index) => {
        const avatarSource =
          TAG_AVATARS[block.tag] ?? getCharacterAvatarSource(block.name) ?? TAG_AVATARS['UNKNOWN'];
        return (
          <View key={`${item.id}-${index}`} style={styles.aiBlockRow}>
            <Image source={avatarSource} style={styles.aiBlockAvatarImage} resizeMode="contain" />
            <View style={styles.aiBlockBody}>
              <Text style={styles.aiBlockName}>{block.name}</Text>
              <View style={styles.aiBubble}>
                <BubbleInlineActions
                  onEdit={startEdit}
                  onDelete={() => handleDeleteBlock(index)}
                />
                <View style={styles.aiMessageRoot}>
                  {parseAIMessage(cleanContent(block.content))}
                </View>
              </View>
            </View>
          </View>
        );
      })}
    </>
  );
}

function MessageBubble({
  item,
  sessionId,
  editingId,
  editText,
  setEditText,
  setEditingId,
  setMessages,
  onRequestDelete,
}: MessageBubbleProps) {
  const { language } = useAppContext();
  const bubbleColor = USER_BUBBLE_COLOR;

  const startEdit = () => {
    setEditText(item.text);
    setEditingId(item.id);
  };

  const handleDelete = () =>
    onRequestDelete({
      title: t(language, 'deleteMessageTitle'),
      message: t(language, 'deleteUserMessageConfirm'),
      onConfirm: () => deleteMessageItem(sessionId, item, 'user', setMessages),
    });

  if (isEmptyUserMessage(item)) {
    return null;
  }

  if (editingId === item.id) {
    return (
      <View style={styles.userRow}>
        <TextInput
          value={editText}
          onChangeText={setEditText}
          style={[styles.userBubble, styles.userEditInput, { backgroundColor: bubbleColor, color: '#fff' }]}
          autoFocus
          multiline
        />
        <EditMessageActions
          onSave={() => saveMessageEdit(sessionId, item, editText, 'user', setMessages, setEditingId)}
          onCancel={() => setEditingId(null)}
        />
      </View>
    );
  }

  return (
    <View style={styles.userRow}>
      <View style={[styles.userBubble, { backgroundColor: bubbleColor }]}>
        <BubbleInlineActions variant="user" onEdit={startEdit} onDelete={handleDelete} />
        <Text style={[styles.messageText, styles.userMessageText]}>
          {item.text}
        </Text>
      </View>
    </View>
  );
}

export const ChatScreen = ({ navigation }: any) => {
  const {
    activeCharacter,
    sessionId,
    messages,
    setMessages,
    isLoading,
    setIsLoading,
    language,
  } = useAppContext();

  const inputTips = useMemo(() => getInputTips(language), [language]);
  const userName = activeCharacter?.name || '';
  const characterProfile = activeCharacter
    ? {
        gender: activeCharacter.gender,
        rulingStyle: activeCharacter.rulingStyle,
        traits: activeCharacter.traits,
        origin: activeCharacter.origin,
        height: activeCharacter.height,
        hairColor: activeCharacter.hairColor,
        fear: activeCharacter.fear,
        hobby: activeCharacter.hobby,
        secretTrait: activeCharacter.secretTrait,
      }
    : null;

  // Redirect to onboarding if no active character
  useEffect(() => {
    if (!activeCharacter) {
      navigation.navigate('Onboarding');
    }
  }, [activeCharacter, navigation]);

  useEffect(() => {
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
  }, []);

  const isWeb = Platform.OS === 'web';
  const flatListRef = useRef<FlatList<Message>>(null);
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const streamTargetRef = useRef('');
  const streamDisplayLenRef = useRef(0);
  const streamTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pushStreamingMessage = useCallback((rawText: string) => {
    const displayText = cleanAiDisplayText(rawText);
    setMessages((prev) => {
      const withoutStreaming = prev.filter((m) => m.id !== 'streaming');
      return [
        ...withoutStreaming,
        {
          id: 'streaming',
          role: 'ai' as const,
          text: displayText,
          characterName: NARRATOR_NAME,
        },
      ];
    });
  }, [setMessages]);

  const stopStreamReveal = useCallback(() => {
    if (streamTimerRef.current) {
      clearInterval(streamTimerRef.current);
      streamTimerRef.current = null;
    }
  }, []);

  const resetStreamReveal = useCallback(() => {
    stopStreamReveal();
    streamTargetRef.current = '';
    streamDisplayLenRef.current = 0;
  }, [stopStreamReveal]);

  const flushStreamReveal = useCallback(() => {
    stopStreamReveal();
    const target = streamTargetRef.current;
    streamDisplayLenRef.current = target.length;
    if (target) {
      pushStreamingMessage(target);
    }
  }, [pushStreamingMessage, stopStreamReveal]);

  const ensureStreamReveal = useCallback(() => {
    if (streamTimerRef.current) return;
    streamTimerRef.current = setInterval(() => {
      const target = streamTargetRef.current;
      const displayedLen = streamDisplayLenRef.current;
      if (displayedLen >= target.length) return;

      const step = nextStreamRevealStep(target.length - displayedLen);
      const nextLen = Math.min(target.length, displayedLen + step);
      streamDisplayLenRef.current = nextLen;
      pushStreamingMessage(target.slice(0, nextLen));
    }, STREAM_TICK_MS);
  }, [pushStreamingMessage]);

  const setStreamTarget = useCallback((text: string) => {
    streamTargetRef.current = text;
    ensureStreamReveal();
  }, [ensureStreamReveal]);

  useEffect(() => () => stopStreamReveal(), [stopStreamReveal]);

  const [inputText, setInputText] = useState('');
  const [inputHeight, setInputHeight] = useState(MIN_INPUT_HEIGHT);
  const [currentLocation, setCurrentLocation] = useState('castle_exterior');
  const [tipIndex, setTipIndex] = useState(0);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState | null>(null);

  const onRequestDelete = useCallback((opts: DeleteConfirmState) => {
    setDeleteConfirm(opts);
  }, []);

  const handleConfirmDelete = async () => {
    if (!deleteConfirm) return;
    await deleteConfirm.onConfirm();
    setDeleteConfirm(null);
  };

  const canSend = useMemo(() => !isLoading, [isLoading]);

  const applyLocationFromAi = (location: string | undefined) => {
    if (!location || location === 'unknown') return;
    const key = location.replace(/-/g, '_');
    if (LOCATION_BACKGROUNDS[key]) {
      setCurrentLocation(key);
    }
  };

  const openingRequested = useRef(false);

  useEffect(() => {
    setHistoryLoaded(false);
    openingRequested.current = false;
    setMessages([]);
  }, [sessionId, setMessages]);

  useEffect(() => {
    if (!activeCharacter || !historyLoaded || openingRequested.current) return;
    if (messages.length > 0) return;

    openingRequested.current = true;

    const loadOpening = async () => {
      setIsLoading(true);
      try {
        const aiResponse = await sendAiMessage(
          [],
          userName,
          '',
          sessionId,
          characterProfile,
        );
        applyLocationFromAi(aiResponse.location);
        const displayText = cleanAiDisplayText(aiResponse.text);
        const aiMsg = createMessage('ai', displayText, aiResponse.characterName || NARRATOR_NAME);
        if (aiResponse.assistantMessageId) {
          aiMsg.id = aiResponse.assistantMessageId;
        }
        setMessages([aiMsg]);
      } catch {
        const intro = getFirstMessage(0, language);
        setMessages([createMessage('ai', intro, NARRATOR_NAME)]);
      } finally {
        setIsLoading(false);
      }
    };

    loadOpening();
  }, [activeCharacter, historyLoaded, messages.length, userName, sessionId, language]);

  useEffect(() => {
    setTipIndex(0);
  }, [language]);

  useEffect(() => {
    const interval = setInterval(() => {
      setTipIndex(i => (i + 1) % inputTips.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [inputTips.length]);

  useEffect(() => {
    if (!sessionId) return;
    if (historyLoaded) return;

    const loadHistory = async () => {
      try {
        const res = await fetch(`${API_BASE}/history?session_id=${encodeURIComponent(sessionId)}`);
        if (!res.ok) return;
        const data = await res.json();
        const msgs: any[] = data.messages || [];

        setHistoryLoaded(true);

        if (msgs.length === 0) {
          return;
        }

        const loaded: Message[] = msgs
          .map((m: any) => ({
            id: m.id || `${m.role}-${Math.random().toString(36).slice(2)}`,
            role: m.role === 'user' ? 'user' : 'ai',
            text: m.role === 'assistant' ? cleanAiDisplayText(m.content) : m.content,
            characterName: m.character_name || undefined,
            timestamp: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
          }))
          .filter((m) => !isEmptyUserMessage(m));

        setMessages(loaded);
      } catch (e) {
        console.error('History load error:', e);
      }
    };

    loadHistory();
  }, [sessionId, historyLoaded]);

  useEffect(() => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    const frame = requestAnimationFrame(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [messages, isLoading]);

  const handleSend = async (overrideText?: string) => {
    const trimmed = (overrideText ?? inputText).trim();

    if (isLoading) {
      return;
    }

    const nextMessages = trimmed
      ? [...messages, createMessage('user', trimmed)]
      : [...messages];

    setMessages(nextMessages);
    setInputText('');
    setInputHeight(MIN_INPUT_HEIGHT);
    setIsLoading(true);
    resetStreamReveal();

    try {
      const aiResponse = await sendAiMessage(
        nextMessages,
        userName,
        '',
        sessionId,
        characterProfile,
        '',
        {
          onChunk: setStreamTarget,
        },
      );
      flushStreamReveal();
      applyLocationFromAi(aiResponse.location);
      const displayText = cleanAiDisplayText(aiResponse.text);
      if (aiResponse.narratorInjection) {
        const injectionMsg: Message = {
          id: `narrator-${Date.now()}`,
          role: 'ai',
          text: aiResponse.narratorInjection,
          characterName: 'Valdenmoor',
        };
        setMessages((prev) => applyAiResponseToMessages(
          [injectionMsg, ...prev],
          displayText,
          aiResponse,
        ));
      } else {
        setMessages((prev) => applyAiResponseToMessages(prev, displayText, aiResponse));
      }
    } catch (error) {
      console.error('AI Error:', error);
      setMessages([
        ...nextMessages,
        createMessage('ai', t(language, 'errorMessage')),
      ]);
    } finally {
      stopStreamReveal();
      setIsLoading(false);
    }
  };

  const handleContentSizeChange = (
    event: NativeSyntheticEvent<TextInputContentSizeChangeEventData>,
  ) => {
    const nextHeight = Math.min(MAX_INPUT_HEIGHT, Math.max(MIN_INPUT_HEIGHT, event.nativeEvent.contentSize.height));
    setInputHeight(nextHeight);
  };

  const handleKeyPress = (event: NativeSyntheticEvent<TextInputKeyPressEventData>) => {
    const webEvent = event as any;
    const shiftPressed = !!webEvent?.nativeEvent?.shiftKey;

    if (event.nativeEvent.key === 'Enter' && !shiftPressed) {
      webEvent?.preventDefault?.();
      handleSend();
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ImageBackground
        source={LOCATION_BACKGROUNDS[currentLocation] || LOCATION_BACKGROUNDS.castle_exterior}
        resizeMode="cover"
        style={styles.overlay}
      >
        <View style={styles.backgroundDarkOverlay} />
        <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
        <KeyboardAvoidingView
          style={styles.keyboardAvoidingView}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={[styles.screen, { position: 'relative' }]}>
            <View style={styles.header}>
              <Image source={NARRATOR_CREST} style={styles.headerCrest} resizeMode="contain" />
              <View style={styles.headerTextBlock}>
                <Text style={styles.headerTitle}>{NARRATOR_NAME.toUpperCase()}</Text>
                <Text style={styles.headerSubtitle}>{t(language, 'narratorSubtitle')}</Text>
              </View>
            </View>

            <FlatList
              ref={flatListRef}
              data={messages}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => {
                if (isEmptyUserMessage(item)) {
                  return null;
                }
                return item.role === 'ai' ? (
                  <AIMessageBubble
                    item={item}
                    sessionId={sessionId}
                    editingId={editingId}
                    editText={editText}
                    setEditText={setEditText}
                    setEditingId={setEditingId}
                    setMessages={setMessages}
                    onRequestDelete={onRequestDelete}
                    language={language}
                  />
                ) : (
                  <MessageBubble
                    item={item}
                    sessionId={sessionId}
                    editingId={editingId}
                    editText={editText}
                    setEditText={setEditText}
                    setEditingId={setEditingId}
                    setMessages={setMessages}
                    onRequestDelete={onRequestDelete}
                  />
                );
              }}
              onContentSizeChange={() => {
                flatListRef.current?.scrollToEnd({ animated: true });
              }}
              maintainVisibleContentPosition={null}
              style={styles.list}
              contentContainerStyle={styles.listContent}
              ItemSeparatorComponent={() => <View style={styles.messageSeparator} />}
              keyboardShouldPersistTaps="handled"
              inverted={false}
              showsVerticalScrollIndicator={false}
              ListFooterComponent={
                isLoading && !messages.some((m) => m.id === 'streaming')
                  ? <TypingBubble language={language} />
                  : null
              }
              ListEmptyComponent={
                <View style={styles.emptyStateWrap}>
                  <Image source={NARRATOR_CREST} style={styles.emptyStateCrest} resizeMode="contain" />
                  <Text style={styles.emptyStateTitle}>{NARRATOR_NAME}</Text>
                  <Text style={styles.emptyStateSubtitle}>{t(language, 'emptyStateSubtitle')}</Text>
                </View>
              }
            />

            <View style={styles.inputArea}>
              <Text style={styles.inputTip}>{inputTips[tipIndex]}</Text>
              <View style={[styles.inputBox, styles.inputBoxSpacing]}>
                <TextInput
                  value={inputText}
                  onChangeText={setInputText}
                  onSubmitEditing={isWeb ? undefined : handleSend}
                  onKeyPress={isWeb ? handleKeyPress : undefined}
                  onContentSizeChange={handleContentSizeChange}
                  placeholder={t(language, 'inputPlaceholderWeb')}
                  placeholderTextColor="#8B7355"
                  multiline={!isWeb}
                  blurOnSubmit={false}
                  returnKeyType="send"
                  underlineColorAndroid="transparent"
                  textAlignVertical="center"
                  scrollEnabled={inputHeight >= MAX_INPUT_HEIGHT}
                  style={[styles.textInput, { height: inputHeight }, WEB_INPUT_RESET]}
                />
                <Pressable
                  onPress={handleSend}
                  disabled={!canSend || isLoading}
                  style={({ pressed }) => [
                    styles.sendButton,
                    canSend && !isLoading ? styles.sendButtonActive : styles.sendButtonDisabled,
                    pressed && canSend && !isLoading ? styles.sendButtonPressed : null,
                  ]}
                >
                  <Text style={styles.sendButtonText}>↑</Text>
                </Pressable>
              </View>
            </View>
          </View>
        </KeyboardAvoidingView>
      </ImageBackground>

      <DeleteConfirmModal
        confirm={deleteConfirm}
        language={language}
        onCancel={() => setDeleteConfirm(null)}
        onConfirm={handleConfirmDelete}
      />
    </SafeAreaView>
  );
};

export default ChatScreen;

const styles = StyleSheet.create({
  safeArea: {
    width: '100vw' as any,
    height: '100vh' as any,
    overflow: 'hidden' as any,
    backgroundColor: 'transparent',
  },
  kingdomBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#0a0604',
  },
  overlay: {
    width: '100%',
    height: '100%',
    flex: 1,
    backgroundColor: 'transparent',
  },
  backgroundVideoWrap: {
    ...StyleSheet.absoluteFillObject,
  },
  backgroundVideoIgnorePointer: {
    pointerEvents: 'none',
  },
  backgroundVideo: {
    ...StyleSheet.absoluteFillObject,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    filter: 'saturate(1.14) contrast(1.08) brightness(1.04)',
  },
  backgroundVideoLayer: {
    // No transition: instant swap for seamless illusion
    transitionProperty: 'opacity',
    transitionDuration: `0ms`,
    transitionTimingFunction: 'linear',
  },

  backgroundColorFill: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'transparent',
  },
  backgroundDarkOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
  },
  keyboardAvoidingView: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  screen: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  header: {
    height: 64,
    backgroundColor: 'rgba(5, 3, 1, 0.88)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCrest: {
    width: 48,
    height: 48,
    marginRight: 10,
  },
  headerTextBlock: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    fontFamily: 'Cinzel, serif',
    letterSpacing: 3,
  },
  headerSubtitle: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.45)',
    letterSpacing: 2,
    marginTop: 1,
    fontFamily: 'Cinzel, serif',
  },
  list: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  listContent: {
    paddingHorizontal: 80,
    paddingTop: 16,
    paddingBottom: 16,
    flexGrow: 1,
    alignItems: 'stretch',
    maxWidth: 900,
    alignSelf: 'center',
    width: '100%',
  },
  messageSeparator: {
    height: 14,
  },
  userRow: {
    width: '100%',
    alignItems: 'flex-end',
  },
  bubbleActionsAnchor: {
    position: 'absolute',
    zIndex: 20,
  },
  userBubbleActionsAnchor: {
    top: 4,
    right: 4,
    bottom: 'auto' as any,
  },
  aiBubbleActionsAnchor: {
    top: 2,
    right: 12,
  },
  userBubble: {
    borderTopLeftRadius: 14,
    borderTopRightRadius: 4,
    borderBottomRightRadius: 14,
    borderBottomLeftRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    flexShrink: 1,
    maxWidth: '72%',
    alignSelf: 'flex-end',
    marginRight: 16,
    position: 'relative',
  },
  userEditInput: {
    minWidth: 120,
    textAlignVertical: 'top',
  },
  userMessageActions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
    marginRight: 16,
    alignSelf: 'flex-end',
  },
  userActionSave: {
    color: '#c9a84c',
    fontSize: 13,
  },
  userActionCancel: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 13,
  },
  aiRow: {
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  aiAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#D97706',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
    backgroundColor: 'rgba(12, 7, 2, 0.92)',
    flexShrink: 0,
  },
  aiBlockRow: {
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  aiErrorFallback: {
    color: 'rgba(255,255,255,0.3)',
    fontStyle: 'italic',
    fontSize: 12,
    padding: 8,
  },
  aiBlockAvatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(12, 7, 2, 0.92)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    flexShrink: 0,
  },
  aiBlockAvatarImage: {
    width: 40,
    height: 40,
    borderRadius: 20,
    overflow: 'hidden',
    marginRight: 8,
    flexShrink: 0,
  },
  aiBlockBody: {
    flex: 1,
    maxWidth: '88%',
  },
  aiBlockName: {
    fontSize: 11,
    fontWeight: '600',
    color: '#F59E0B',
    marginBottom: 4,
    letterSpacing: 0.5,
  },
  aiAvatarImage: {
    width: 36,
    height: 36,
    borderRadius: 18,
    overflow: 'hidden',
    marginRight: 8,
    flexShrink: 0,
  },
  aiAvatarText: {
    marginBottom: 0,
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  aiBubble: {
    backgroundColor: 'rgba(20, 12, 4, 0.82)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(120, 53, 15, 0.6)',
    borderTopLeftRadius: 4,
    borderTopRightRadius: 14,
    borderBottomRightRadius: 14,
    borderBottomLeftRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    maxWidth: '100%',
    flex: 1,
    position: 'relative',
  },
  aiEditInput: {
    color: '#fff',
    minHeight: 80,
    textAlignVertical: 'top',
    width: '100%',
  },
  messageText: {
    fontSize: 14,
    paddingTop: 12,
    paddingBottom: 12,
    flexShrink: 1,
    flexWrap: 'wrap',
  },
  userMessageText: {
    color: '#FFFFFF',
  },
  aiMessageRoot: {
    flexShrink: 1,
  },
  aiParagraph: {
    marginBottom: 12,
  },
  aiLine: {
    marginBottom: 4,
    fontSize: 14,
    lineHeight: 22,
  },
  aiSpeakerText: {
    fontWeight: '700',
    color: 'rgba(255,255,255,0.85)',
    lineHeight: 22,
  },
  aiDialogueText: {
    color: '#e8b86d',
    fontStyle: 'italic',
    lineHeight: 22,
  },
  aiPlainText: {
    color: 'rgba(255,255,255,0.85)',
    lineHeight: 22,
  },
  aiItalicText: {
    fontStyle: 'italic',
    color: 'rgba(255,255,255,0.85)',
    lineHeight: 22,
  },
  houseSelectionArea: {
    backgroundColor: 'transparent',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(245, 230, 200, 0.12)',
    paddingBottom: Platform.OS === 'ios' ? 24 : 12,
  },
  houseButtonsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    padding: 16,
    maxWidth: 760,
    alignSelf: 'center',
    width: '100%',
  },
  houseButton: {
    flexGrow: 1,
    flexBasis: '45%',
    minWidth: '45%',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  houseButtonDisabled: {
    opacity: 0.6,
  },
  houseButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  inputArea: {
    backgroundColor: 'transparent',
    paddingHorizontal: 80,
    paddingTop: 12,
    paddingBottom: 24,
    alignItems: 'center',
  },
  inputTip: {
    fontSize: 11,
    color: 'rgba(245, 220, 180, 0.45)',
    textAlign: 'center',
    marginBottom: 6,
    fontStyle: 'italic',
  },
  inputBoxSpacing: {
    marginBottom: 0,
  },
  inputBox: {
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 12,
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    maxWidth: 720,
  },
  textInput: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#F5E6C8',
    borderWidth: 0,
    paddingTop: 0,
    paddingBottom: 0,
    paddingHorizontal: 0,
    marginRight: 10,
    textAlignVertical: 'center',
    includeFontPadding: false,
    backgroundColor: 'transparent',
    alignSelf: 'center',
  },
  sendButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    alignSelf: 'center',
  },
  sendButtonActive: {
    backgroundColor: '#D97706',
  },
  sendButtonDisabled: {
    backgroundColor: 'transparent',
  },
  sendButtonPressed: {
    opacity: 0.9,
  },
  sendIcon: {
    fontSize: 16,
    fontWeight: '700',
    lineHeight: 16,
  },
  sendIconActive: {
    color: '#FFFFFF',
  },
  sendIconDisabled: {
    color: '#8C8C8C',
  },
  sendButtonText: {
    fontSize: 18,
    color: '#F5E6C8',
    fontWeight: '700',
  },
  emptyStateWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingVertical: 24,
  },
  emptyStateCrest: {
    width: 80,
    height: 80,
    marginBottom: 12,
  },
  emptyStateTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#F5E6C8',
    textAlign: 'center',
    marginBottom: 6,
  },
  emptyStateSubtitle: {
    fontSize: 14,
    color: '#CBB38C',
    textAlign: 'center',
    lineHeight: 20,
  },
  typingBubbleSimple: {
    alignSelf: 'flex-start',
    marginLeft: 16,
    marginVertical: 8,
    backgroundColor: 'rgba(10, 6, 4, 0.75)',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  typingDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: 'rgba(201, 168, 76, 0.7)',
    marginHorizontal: 2,
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 200,
  },
  modalBox: {
    backgroundColor: 'rgba(15, 10, 5, 0.98)',
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.2)',
    borderRadius: 16,
    padding: 28,
    width: '85%',
    maxWidth: 380,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#F5E6C8',
    fontFamily: Platform.OS === 'web' ? 'Cinzel, serif' : undefined,
    marginBottom: 12,
    textAlign: 'center',
  },
  modalText: {
    fontSize: 14,
    color: 'rgba(245, 220, 180, 0.7)',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
    backgroundColor: 'transparent',
  },
  modalCancel: {
    flex: 1,
    height: 44,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalCancelText: {
    color: 'rgba(245, 220, 180, 0.6)',
    fontSize: 15,
  },
  modalDelete: {
    flex: 1,
    height: 44,
    borderRadius: 10,
    backgroundColor: 'rgba(150, 20, 20, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalDeleteText: {
    color: '#F5E6C8',
    fontSize: 15,
    fontWeight: '600',
  },
});
