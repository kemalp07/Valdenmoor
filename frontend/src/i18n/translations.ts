export type Language = 'tr' | 'en';

export const translations = {
  tr: {
    welcome: "Valdenmoor'a Hoş Geldin",
    noCharacter: 'Yeni bir hükümdar adı gir ve tahta geç',
    newCharacter: 'Krallığa Başla',
    addCharacter: '+ Yeni Oyun',
    houseNotSelected: 'Valdenmoor',
    deleteCharacter: 'Kayıtlı Oyunu Sil',
    deleteConfirm: (name: string) => `"${name}" ve tüm sohbet geçmişi silinecek. Emin misin?`,
    cancel: 'İptal',
    delete: 'Sil',
    namePlaceholder: 'Hükümdar adını gir...',
    inputPlaceholder: 'Emir ver veya konuş...',
    inputPlaceholderWeb: 'Mesaj yaz... ("devam et" = hikaye ilerler)',
    narratorSubtitle: 'Krallık Yönetimi',
    emptyStateSubtitle: 'Krallığın seni bekliyor...',
    errorMessage: 'Bir şeyler ters gitti, tekrar dener misin?',
    edit: 'Düzenle',
    save: 'Kaydet',
    narratorLabel: 'Anlatıcı',
    aiErrorFallback: '⏳ Valdenmoor yanıt verirken bir aksaklık yaşandı. Lütfen tekrar dene...',
  },
  en: {
    welcome: 'Welcome to Valdenmoor',
    noCharacter: 'Enter a new ruler\'s name and ascend the throne',
    newCharacter: 'Begin Your Reign',
    addCharacter: '+ New Game',
    houseNotSelected: 'Valdenmoor',
    deleteCharacter: 'Delete Saved Game',
    deleteConfirm: (name: string) => `"${name}" and all chat history will be deleted. Are you sure?`,
    cancel: 'Cancel',
    delete: 'Delete',
    namePlaceholder: 'Enter ruler name...',
    inputPlaceholder: 'Give an order or speak...',
    inputPlaceholderWeb: 'Write a message... (type "continue" to progress the story)',
    narratorSubtitle: 'Kingdom Management',
    emptyStateSubtitle: 'Your kingdom awaits...',
    errorMessage: 'Something went wrong. Would you like to try again?',
    edit: 'Edit',
    save: 'Save',
    narratorLabel: 'Narrator',
    aiErrorFallback: '⏳ A hiccup occurred while reaching Valdenmoor. Please try again...',
  },
} as const;

export type TranslationKey = keyof typeof translations['tr'];

export function t(lang: Language, key: TranslationKey, ...args: any[]): string {
  const val = (translations[lang] as any)[key];
  if (typeof val === 'function') return val(...args);
  return val ?? key;
}

export function getInputTips(lang: Language): string[] {
  if (lang === 'en') {
    return [
      '💬 Give an order: "Summon the chancellor"',
      '⚡ Action: *look out the window*',
      '👑 Make a decision: pay the army\'s wages',
      '📖 Direct the scene: I want to visit the market square',
      '🔮 Express emotion: I worry about public support',
      '📖 Type "continue" to progress the story',
    ];
  }
  return [
    '💬 Emir ver: "Veziri çağır"',
    '⚡ Eylem: *pencereden dışarı bakarım*',
    '👑 Karar al: Orduya maaş öde',
    '📖 Sahne yönlendir: Saray bahçesine çıkmak istiyorum',
    '🔮 Duygu belirt: Halkın desteğinden endişeliyim',
    '📖 Hikayeye devam için "devam et" yaz',
  ];
}

const CHARACTER_TAG_NAMES: Record<Language, Record<string, string>> = {
  tr: {
    NARRATOR: 'Anlatıcı',
    UNKNOWN: 'Bilinmeyen',
    DUKE_MALACHAR: 'Dük Malachar',
    GENERAL_HARKON: 'General Harkon',
    KING_EDWYN: 'Kral Edwyn',
    PRINCESS_ELOWEN: 'Prenses Elowen',
    PRINCE_ALDRIC_SELMARA: 'Prens Aldric',
    SULTAN_RASHID: 'Sultan Rashid',
    ENVOY_ZARA: 'Elçi Zara',
    LORD_ALDRIC_VANE: 'Lord Aldric Vane',
    LORD_HARWIN_SORN: 'Lord Harwin Sorn',
    LORD_CERIN_VANE: 'Lord Cerin Vane',
    PRIEST_EDRAN: 'Rahip Edran',
    MIRA: 'Mira',
    GENERAL_CAELAN_VOSS: 'General Caelan Voss',
    LORD_COMMANDER_DRAVEN: 'Lord Commander Draven',
    COMMANDER_SERA_ASHFORD: 'Komutan Sera Ashford',
    TOMAS: 'Tomas',
    LENA: 'Lena',
  },
  en: {
    NARRATOR: 'Narrator',
    UNKNOWN: 'Unknown',
    DUKE_MALACHAR: 'Duke Malachar',
    GENERAL_HARKON: 'General Harkon',
    KING_EDWYN: 'King Edwyn',
    PRINCESS_ELOWEN: 'Princess Elowen',
    PRINCE_ALDRIC_SELMARA: 'Prince Aldric',
    SULTAN_RASHID: 'Sultan Rashid',
    ENVOY_ZARA: 'Envoy Zara',
    LORD_ALDRIC_VANE: 'Lord Aldric Vane',
    LORD_HARWIN_SORN: 'Lord Harwin Sorn',
    LORD_CERIN_VANE: 'Lord Cerin Vane',
    PRIEST_EDRAN: 'Priest Edran',
    MIRA: 'Mira',
    GENERAL_CAELAN_VOSS: 'General Caelan Voss',
    LORD_COMMANDER_DRAVEN: 'Lord Commander Draven',
    COMMANDER_SERA_ASHFORD: 'Commander Sera Ashford',
    TOMAS: 'Tomas',
    LENA: 'Lena',
  },
};

export function getTagNames(lang: Language): Record<string, string> {
  return CHARACTER_TAG_NAMES[lang];
}
