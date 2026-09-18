import { describe, expect, it } from 'vitest';
import { applyGeneratedCharacterDetails } from './characterDetails';

interface NewCharacterForm {
  name: string;
  role: string;
  physical_description: string;
  personality: string;
  character_arc: string;
  want: string;
  need: string;
  lie: string;
  ghost: string;
  accent: string;
  voice_characteristics: string;
  voice_gender: string;
  entity_type: 'character' | 'object' | 'location';
}

const prevForm: NewCharacterForm = {
  name: 'Ada',
  role: 'protagonist',
  physical_description: '',
  personality: '',
  character_arc: '',
  want: '',
  need: '',
  lie: '',
  ghost: '',
  accent: 'american',
  voice_characteristics: '',
  voice_gender: 'auto',
  entity_type: 'character',
};

describe('applyGeneratedCharacterDetails', () => {
  it('populates role, accent, voice_gender and voice_characteristics on clean data', () => {
    const result = applyGeneratedCharacterDetails(prevForm, {
      role: 'mentor',
      accent: 'british',
      voice_gender: 'female',
      voice_characteristics: 'Deep, raspy, warm',
    });

    expect(result.role).toBe('mentor');
    expect(result.accent).toBe('british');
    expect(result.voice_gender).toBe('female');
    expect(result.voice_characteristics).toBe('Deep, raspy, warm');
  });

  it('keeps prev role when the response role is not a UI Role select option', () => {
    const villain = applyGeneratedCharacterDetails(prevForm, { role: 'villain' });
    expect(villain.role).toBe('protagonist');

    const empty = applyGeneratedCharacterDetails(prevForm, { role: '' });
    expect(empty.role).toBe('protagonist');
  });

  it('normalizes accent casing: "British" matches the "british" option', () => {
    const result = applyGeneratedCharacterDetails(prevForm, { accent: 'British' });
    expect(result.accent).toBe('british');
  });

  it('keeps prev accent when the normalized accent is unknown', () => {
    const result = applyGeneratedCharacterDetails(prevForm, { accent: '  Korean  ' });
    expect(result.accent).toBe('american');
  });

  it('keeps prev voice_gender when the value is not male or female', () => {
    const robot = applyGeneratedCharacterDetails(prevForm, { voice_gender: 'robot' });
    expect(robot.voice_gender).toBe('auto');

    // 'auto' is a UI default, not an AI-prefillable value
    const auto = applyGeneratedCharacterDetails(
      { ...prevForm, voice_gender: 'male' },
      { voice_gender: 'auto' }
    );
    expect(auto.voice_gender).toBe('male');
  });

  it('keeps prev voice_characteristics when the response value is empty', () => {
    const result = applyGeneratedCharacterDetails(
      { ...prevForm, voice_characteristics: 'Cheerful' },
      { voice_characteristics: '' }
    );
    expect(result.voice_characteristics).toBe('Cheerful');
  });

  it('still maps the original seven detail fields', () => {
    const result = applyGeneratedCharacterDetails(prevForm, {
      physical_description: 'Tall and scarred',
      personality: 'Stoic',
      character_arc: 'Guilt to redemption',
      want: 'To win the war',
      need: 'To forgive himself',
      lie: 'He is beyond redemption',
      ghost: 'The brother he lost',
    });

    expect(result.physical_description).toBe('Tall and scarred');
    expect(result.personality).toBe('Stoic');
    expect(result.character_arc).toBe('Guilt to redemption');
    expect(result.want).toBe('To win the war');
    expect(result.need).toBe('To forgive himself');
    expect(result.lie).toBe('He is beyond redemption');
    expect(result.ghost).toBe('The brother he lost');
  });

  it('preserves all prev values (and non-detail fields) when the response omits keys', () => {
    const result = applyGeneratedCharacterDetails(prevForm, {});

    expect(result).toEqual(prevForm);
    expect(result.name).toBe('Ada');
    expect(result.entity_type).toBe('character');
  });
});
