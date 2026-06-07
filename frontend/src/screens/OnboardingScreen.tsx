import React, { useEffect, useRef, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  Image,
  ImageBackground,
  Pressable,
  SafeAreaView,
  Platform,
  TouchableOpacity,
  TextInput,
  Animated,
} from 'react-native';
import {
  useAppContext,
  Character,
  CHARACTERS_STORAGE_KEY,
  ACTIVE_CHARACTER_STORAGE_KEY,
  loadStoredCharacters,
  loadAllCharactersFromDB,
  saveCharacterToDB,
} from '../context/AppContext';
import { API_BASE } from '../config/api';
import { t } from '../i18n/translations';

type OnboardingScreenProps = {
  navigation: any;
};

type RulerGender = 'king' | 'queen';
type RulingStyle = 'harsh' | 'diplomatic' | 'cunning';
type RulerOrigin = 'warrior' | 'merchant' | 'noble';

const STYLE_OPTIONS: { key: RulingStyle; labelKey: 'styleHarsh' | 'styleDiplomatic' | 'styleCunning'; descKey: 'styleHarshDesc' | 'styleDiplomaticDesc' | 'styleCunningDesc' }[] = [
  { key: 'harsh', labelKey: 'styleHarsh', descKey: 'styleHarshDesc' },
  { key: 'diplomatic', labelKey: 'styleDiplomatic', descKey: 'styleDiplomaticDesc' },
  { key: 'cunning', labelKey: 'styleCunning', descKey: 'styleCunningDesc' },
];

const ORIGIN_OPTIONS: { key: RulerOrigin; labelKey: 'originWarrior' | 'originMerchant' | 'originNoble'; descKey: 'originWarriorDesc' | 'originMerchantDesc' | 'originNobleDesc' }[] = [
  { key: 'warrior', labelKey: 'originWarrior', descKey: 'originWarriorDesc' },
  { key: 'merchant', labelKey: 'originMerchant', descKey: 'originMerchantDesc' },
  { key: 'noble', labelKey: 'originNoble', descKey: 'originNobleDesc' },
];

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ navigation }) => {
  const { characters, setCharacters, setActiveCharacter, language, setLanguage } = useAppContext();
  const [step, setStep] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<any>(null);
  const [rulerName, setRulerName] = useState('');
  const [rulerGender, setRulerGender] = useState<RulerGender | null>(null);
  const [rulingStyle, setRulingStyle] = useState<RulingStyle | null>(null);
  const [rulerOrigin, setRulerOrigin] = useState<RulerOrigin | null>(null);

  const fadeAnim = useRef(new Animated.Value(1)).current;
  const slideAnim = useRef(new Animated.Value(0)).current;

  const hasSavedCharacters = characters.length > 0;
  const nameFilled = !!rulerName.trim();
  const canAscend = rulerOrigin === 'warrior' || rulerOrigin === 'merchant' || rulerOrigin === 'noble';

  useEffect(() => {
    if (Platform.OS === 'web') {
      const link = document.createElement('link');
      link.href = 'https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&display=swap';
      link.rel = 'stylesheet';
      document.head.appendChild(link);
    }
  }, []);

  useEffect(() => {
    const loadFromDb = async () => {
      if (loadStoredCharacters().length > 0) return;
      const fromDb = await loadAllCharactersFromDB();
      if (fromDb.length > 0) {
        setCharacters(fromDb);
      }
    };
    loadFromDb();
  }, [setCharacters]);

  const resetCreationForm = () => {
    setRulerName('');
    setRulerGender(null);
    setRulingStyle(null);
    setRulerOrigin(null);
  };

  const animateStepTransition = (direction: 'forward' | 'back', onMid: () => void) => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 0, duration: 140, useNativeDriver: true }),
      Animated.timing(slideAnim, {
        toValue: direction === 'forward' ? -24 : 24,
        duration: 140,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onMid();
      slideAnim.setValue(direction === 'forward' ? 24 : -24);
      Animated.parallel([
        Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
        Animated.timing(slideAnim, { toValue: 0, duration: 200, useNativeDriver: true }),
      ]).start();
    });
  };

  const goToStep = (next: number) => {
    if (next === step) return;
    animateStepTransition(next > step ? 'forward' : 'back', () => setStep(next));
  };

  const getGenderLabel = (gender: string) => {
    if (gender === 'queen') return t(language, 'genderQueen');
    if (gender === 'king') return t(language, 'genderKing');
    return '';
  };

  const handleSelectCharacter = (character: Character) => {
    setActiveCharacter(character);
    navigation.navigate('Chat');
  };

  const handleBeginCreation = () => {
    resetCreationForm();
    goToStep(1);
  };

  const handleSelectGender = (gender: RulerGender) => {
    setRulerGender(gender);
    setTimeout(() => goToStep(3), 220);
  };

  const handleSelectStyle = (style: RulingStyle) => {
    setRulingStyle(style);
    setTimeout(() => goToStep(4), 220);
  };

  const handleSelectOrigin = (origin: RulerOrigin) => {
    setRulerOrigin(origin);
  };

  const handleBack = () => {
    if (step === 2) goToStep(1);
    else if (step === 3) goToStep(2);
    else if (step === 4) goToStep(3);
  };

  const handleAscendThrone = async () => {
    const name = rulerName.trim();
    if (!name || !rulerGender || !rulingStyle || !rulerOrigin) return;

    const newCharacter: Character = {
      id: crypto.randomUUID(),
      name,
      gender: rulerGender,
      rulingStyle,
      traits: [rulingStyle],
      origin: rulerOrigin,
      height: '',
      hairColor: '',
      fear: '',
      hobby: '',
      secretTrait: '',
      house: 'valdenmoor',
      sessionId: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
    };

    setCharacters([...characters, newCharacter]);
    setActiveCharacter(newCharacter);
    await saveCharacterToDB(newCharacter, newCharacter.sessionId);
    resetCreationForm();
    setStep(0);
    navigation.navigate('Chat');
  };

  const handleDeleteCharacter = (character: any) => {
    setDeleteTarget(character);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await fetch(`${API_BASE}/messages?session_id=${encodeURIComponent(deleteTarget.sessionId)}`, {
        method: 'DELETE',
      });
      const updated = characters.filter((c: any) => c.id !== deleteTarget.id);
      setCharacters(updated);
      localStorage.setItem(CHARACTERS_STORAGE_KEY, JSON.stringify(updated));
      const activeId = localStorage.getItem(ACTIVE_CHARACTER_STORAGE_KEY);
      if (activeId === deleteTarget.id) {
        localStorage.removeItem(ACTIVE_CHARACTER_STORAGE_KEY);
        setActiveCharacter(null);
      }
    } catch (e) {
      console.error(e);
    }
    setDeleteTarget(null);
  };

  const renderWizardStep = () => {
    switch (step) {
      case 1:
        return (
          <>
            <Text style={styles.stepTitle}>{t(language, 'stepNameTitle')}</Text>
            <TextInput
              value={rulerName}
              onChangeText={setRulerName}
              placeholder={t(language, 'namePlaceholder')}
              placeholderTextColor="rgba(245, 220, 180, 0.4)"
              style={styles.nameInput}
              maxLength={30}
              autoFocus
            />
          </>
        );
      case 2:
        return (
          <>
            <Text style={styles.stepTitle}>{t(language, 'stepGenderTitle')}</Text>
            <View style={styles.genderRow}>
              <Pressable
                style={[styles.genderCard, rulerGender === 'king' && styles.cardActive]}
                onPress={() => handleSelectGender('king')}
              >
                <Text style={styles.genderCardIcon}>👑</Text>
                <Text style={[styles.genderCardLabel, rulerGender === 'king' && styles.cardLabelActive]}>
                  {t(language, 'genderKing')}
                </Text>
              </Pressable>
              <Pressable
                style={[styles.genderCard, rulerGender === 'queen' && styles.cardActive]}
                onPress={() => handleSelectGender('queen')}
              >
                <Text style={styles.genderCardIcon}>👑</Text>
                <Text style={[styles.genderCardLabel, rulerGender === 'queen' && styles.cardLabelActive]}>
                  {t(language, 'genderQueen')}
                </Text>
              </Pressable>
            </View>
          </>
        );
      case 3:
        return (
          <>
            <Text style={styles.stepTitle}>{t(language, 'stepStyleTitle')}</Text>
            <View style={styles.optionColumn}>
              {STYLE_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.key}
                  style={[styles.choiceCard, rulingStyle === opt.key && styles.cardActive]}
                  onPress={() => handleSelectStyle(opt.key)}
                >
                  <Text style={styles.choiceCardLabel}>{t(language, opt.labelKey)}</Text>
                  <Text style={styles.choiceCardDesc}>{t(language, opt.descKey)}</Text>
                </Pressable>
              ))}
            </View>
          </>
        );
      case 4:
        return (
          <>
            <Text style={styles.stepTitle}>{t(language, 'stepOriginTitle')}</Text>
            <View style={styles.optionColumn}>
              {ORIGIN_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.key}
                  style={[styles.choiceCard, rulerOrigin === opt.key && styles.cardActive]}
                  onPress={() => handleSelectOrigin(opt.key)}
                >
                  <Text style={styles.choiceCardLabel}>{t(language, opt.labelKey)}</Text>
                  <Text style={styles.choiceCardDesc}>{t(language, opt.descKey)}</Text>
                </Pressable>
              ))}
            </View>
          </>
        );
      default:
        return null;
    }
  };

  const showFooterNext = step === 1;
  const showFooterAscend = step === 4;

  return (
    <SafeAreaView style={styles.container}>
      <ImageBackground
        source={require('../../assets/backgrounds/onboarding_bg.png')}
        style={styles.backgroundImage}
        resizeMode="cover"
      >
        <View style={styles.languageToggle}>
          <Pressable
            style={[styles.langBtn, language === 'tr' && styles.langBtnActive]}
            onPress={() => setLanguage('tr')}
          >
            <Text style={[styles.langBtnText, language === 'tr' && styles.langBtnTextActive]}>TR</Text>
          </Pressable>
          <Pressable
            style={[styles.langBtn, language === 'en' && styles.langBtnActive]}
            onPress={() => setLanguage('en')}
          >
            <Text style={[styles.langBtnText, language === 'en' && styles.langBtnTextActive]}>EN</Text>
          </Pressable>
        </View>

        {step === 0 ? (
          <View style={styles.content}>
            <Image
              source={require('../../assets/valdenmoor_crest.png')}
              style={styles.crestImage}
              resizeMode="contain"
            />
            <Text style={styles.title}>{t(language, 'welcome')}</Text>

            {hasSavedCharacters && (
              <View style={styles.characterList}>
                {characters.map((character) => (
                  <View key={character.id} style={styles.characterCard}>
                    <Pressable
                      style={styles.characterCardContent}
                      onPress={() => handleSelectCharacter(character)}
                    >
                      <Text style={styles.characterName}>{character.name}</Text>
                      {!!getGenderLabel(character.gender) && (
                        <Text style={styles.characterGender}>{getGenderLabel(character.gender)}</Text>
                      )}
                    </Pressable>
                    <Pressable
                      style={styles.deleteButton}
                      onPress={() => handleDeleteCharacter(character)}
                    >
                      <Text style={styles.deleteButtonText}>✕</Text>
                    </Pressable>
                  </View>
                ))}
              </View>
            )}

            <Pressable style={[styles.primaryButton, styles.homeStartButton]} onPress={handleBeginCreation}>
              <Text style={styles.primaryButtonText}>{t(language, 'newCharacter')}</Text>
            </Pressable>
          </View>
        ) : (
          <View style={styles.wizardContainer}>
            <View style={styles.wizardHeader}>
              {step > 1 ? (
                <Pressable style={styles.backButton} onPress={handleBack}>
                  <Text style={styles.backButtonText}>← {t(language, 'back')}</Text>
                </Pressable>
              ) : (
                <View style={styles.backButtonPlaceholder} />
              )}
              <Text style={styles.progressText}>{step}/4</Text>
              <View style={styles.backButtonPlaceholder} />
            </View>

            <View style={styles.stepContainer}>
              <Animated.View
                style={[
                  styles.stepContent,
                  { opacity: fadeAnim, transform: [{ translateX: slideAnim }] },
                ]}
              >
                {renderWizardStep()}
                {showFooterNext && (
                  <Pressable
                    style={[
                      styles.primaryButton,
                      styles.wizardActionButton,
                      !nameFilled && styles.primaryButtonDisabled,
                    ]}
                    onPress={() => goToStep(2)}
                    disabled={!nameFilled}
                  >
                    <Text style={styles.primaryButtonText}>{t(language, 'next')}</Text>
                  </Pressable>
                )}
                {showFooterAscend && (
                  <Pressable
                    style={[
                      styles.primaryButton,
                      styles.wizardActionButton,
                      !canAscend && styles.primaryButtonDisabled,
                    ]}
                    onPress={handleAscendThrone}
                    disabled={!canAscend}
                  >
                    <Text style={styles.primaryButtonText}>{t(language, 'ascendThrone')}</Text>
                  </Pressable>
                )}
              </Animated.View>
            </View>
          </View>
        )}
      </ImageBackground>

      {deleteTarget && (
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>{t(language, 'deleteCharacter')}</Text>
            <Text style={styles.modalText}>
              {t(language, 'deleteConfirm', deleteTarget.name)}
            </Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.modalCancel} onPress={() => setDeleteTarget(null)}>
                <Text style={styles.modalCancelText}>{t(language, 'cancel')}</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalDelete} onPress={confirmDelete}>
                <Text style={styles.modalDeleteText}>{t(language, 'delete')}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    minHeight: '100vh' as any,
    backgroundColor: 'transparent',
  },
  backgroundImage: {
    width: '100%',
    height: '100vh' as any,
    minHeight: '100vh' as any,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
    paddingHorizontal: 24,
    paddingVertical: 40,
    backgroundColor: 'transparent',
  },
  wizardContainer: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 56,
    paddingBottom: 32,
    backgroundColor: 'transparent',
  },
  wizardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 32,
    backgroundColor: 'transparent',
  },
  stepContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  stepContent: {
    width: '100%',
    maxWidth: 400,
    alignSelf: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  wizardActionButton: {
    marginTop: 32,
    maxWidth: 400,
    alignSelf: 'center',
  },
  progressText: {
    color: 'rgba(212, 175, 55, 0.6)',
    fontSize: 13,
    fontFamily: 'Cinzel, serif',
    letterSpacing: 2,
  },
  backButton: {
    paddingVertical: 4,
    minWidth: 72,
  },
  backButtonPlaceholder: {
    minWidth: 72,
    backgroundColor: 'transparent',
  },
  backButtonText: {
    color: 'rgba(245, 220, 180, 0.65)',
    fontSize: 14,
    fontFamily: 'Cinzel, serif',
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: '600',
    textAlign: 'center',
    color: '#F5E6C8',
    fontFamily: 'Cinzel, serif',
    letterSpacing: 1.5,
    marginBottom: 28,
    width: '100%',
  },
  crestImage: {
    width: 240,
    height: 240,
    marginBottom: 24,
  },
  nameInput: {
    width: '100%',
    maxWidth: 400,
    alignSelf: 'center',
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.35)',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: '#F5E6C8',
    fontSize: 18,
    backgroundColor: 'rgba(10, 6, 4, 0.6)',
    textAlign: 'center',
  },
  genderRow: {
    flexDirection: 'row',
    gap: 14,
    width: '100%',
    backgroundColor: 'transparent',
  },
  genderCard: {
    flex: 1,
    minHeight: 140,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.25)',
    backgroundColor: 'rgba(10, 6, 4, 0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 20,
  },
  genderCardIcon: {
    fontSize: 36,
    marginBottom: 12,
  },
  genderCardLabel: {
    color: 'rgba(245, 220, 180, 0.75)',
    fontSize: 18,
    fontWeight: '600',
    fontFamily: 'Cinzel, serif',
  },
  optionColumn: {
    gap: 12,
    width: '100%',
    backgroundColor: 'transparent',
  },
  choiceCard: {
    width: '100%',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.25)',
    backgroundColor: 'rgba(10, 6, 4, 0.65)',
    paddingHorizontal: 18,
    paddingVertical: 16,
  },
  cardActive: {
    borderWidth: 2,
    borderColor: '#D4AF37',
    backgroundColor: 'rgba(120, 50, 8, 0.5)',
  },
  cardLabelActive: {
    color: '#F5E6C8',
  },
  choiceCardLabel: {
    color: 'rgba(245, 220, 180, 0.85)',
    fontSize: 17,
    fontWeight: '600',
    fontFamily: 'Cinzel, serif',
    marginBottom: 6,
  },
  choiceCardDesc: {
    color: 'rgba(245, 220, 180, 0.45)',
    fontSize: 13,
    lineHeight: 18,
  },
  languageToggle: {
    position: 'absolute',
    top: 16,
    right: 24,
    flexDirection: 'row',
    gap: 8,
    zIndex: 10,
    backgroundColor: 'transparent',
  },
  langBtn: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.3)',
  },
  langBtnActive: {
    backgroundColor: 'rgba(120, 50, 8, 0.9)',
    borderColor: 'rgba(245, 220, 180, 0.6)',
  },
  langBtnText: {
    color: 'rgba(245, 220, 180, 0.5)',
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 1,
  },
  langBtnTextActive: {
    color: '#F5E6C8',
  },
  title: {
    fontSize: 32,
    fontWeight: '600',
    textAlign: 'center',
    color: '#F5E6C8',
    fontFamily: 'Cinzel, serif',
    letterSpacing: 3,
    width: '100%',
    maxWidth: 400,
  },
  characterList: {
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  characterCard: {
    width: '100%',
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.25)',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  characterCardContent: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  characterName: {
    fontSize: 22,
    fontWeight: '600',
    color: '#D4AF37',
    fontFamily: 'Cinzel, serif',
    marginBottom: 2,
  },
  characterGender: {
    fontSize: 13,
    color: 'rgba(212, 175, 55, 0.55)',
    fontStyle: 'italic',
  },
  deleteButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(200, 30, 30, 0.35)',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 12,
  },
  deleteButtonText: {
    color: '#FF4444',
    fontSize: 18,
    fontWeight: 'bold',
  },
  homeStartButton: {
    maxWidth: 320,
    alignSelf: 'center',
  },
  primaryButton: {
    width: '100%',
    maxWidth: 400,
    alignSelf: 'center',
    height: 52,
    backgroundColor: 'rgba(120, 50, 8, 0.95)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(245, 220, 180, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryButtonDisabled: {
    opacity: 0.45,
  },
  primaryButtonText: {
    color: '#F5E6C8',
    fontSize: 16,
    fontWeight: '600',
    letterSpacing: 1,
    fontFamily: 'Cinzel, serif',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
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
    fontFamily: 'Cinzel, serif',
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
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
});
