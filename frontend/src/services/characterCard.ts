const OPENING_TR =
  'Taht odasının kapısı gıcırdayarak açılır. Lord Aldric Vane eşikte duruyor — elinde hazine raporu, yüzünde o tanıdık gülümseme.\n\n"Majesteleri. Kuzeyden haberler var. Ve hazinenin durumu... konuşmamız gerekiyor."';

const OPENING_EN =
  'The throne room door creaks open. Lord Aldric Vane stands at the threshold — treasury report in hand, that familiar smile on his face.\n\n"Your Majesty. News from the north. And the treasury... we must speak."';

export function getFirstMessage(_greetingIndex: number = 0, language: string = 'tr'): string {
  return language === 'en' ? OPENING_EN : OPENING_TR;
}

export function getAlternateGreetings(): string[] {
  return [];
}
