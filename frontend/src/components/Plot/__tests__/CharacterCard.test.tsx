import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import CharacterCard from '../CharacterCard';

describe('CharacterCard - Add Archetype Modal', () => {
  const mockCharacter = {
    id: '1',
    name: 'Test Character',
    role: 'protagonist',
    physical_description: 'A brave hero',
    personality: 'Courageous and kind',
    character_arc: 'From zero to hero',
    archetypes: ['Hero'],
    want: 'To save the world',
    need: 'To believe in themselves',
    lie: 'They are not strong enough',
    ghost: 'Lost their mentor',
    image_url: undefined,
  };

  const mockProps = {
    character: mockCharacter,
    isGeneratingImage: false,
    isSelected: false,
    onToggleSelect: jest.fn(),
    onUpdate: jest.fn().mockResolvedValue(undefined),
    onDelete: jest.fn(),
    onGenerateImage: jest.fn(),
    onRegenerateImage: jest.fn(),
    onViewImage: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders character card with archetypes section when editing', () => {
    render(<CharacterCard {...mockProps} />);
    
    // Click edit button
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Check if archetypes section is visible
    expect(screen.getByText('Archetypes')).toBeInTheDocument();
    expect(screen.getByText('Hero')).toBeInTheDocument();
  });

  test('opens modal when clicking Add button in archetypes section', () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Click the Add button
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Modal should be visible
    expect(screen.getByText('Add Archetype')).toBeInTheDocument();
    expect(screen.getByLabelText(/enter archetype name/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  test('adds archetype when entering valid name and clicking Create', async () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Click Add button to open modal
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Enter archetype name
    const input = screen.getByLabelText(/enter archetype name/i);
    fireEvent.change(input, { target: { value: 'Warrior' } });
    
    // Click Create button
    const createButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(createButton);
    
    // Modal should close
    await waitFor(() => {
      expect(screen.queryByText('Add Archetype')).not.toBeInTheDocument();
    });
    
    // Archetype should be added to the list
    expect(screen.getByText('Warrior')).toBeInTheDocument();
  });

  test('shows validation error when trying to add empty archetype name', () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Open modal
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Click Create without entering a name
    const createButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(createButton);
    
    // Error message should appear
    expect(screen.getByText('Archetype name is required')).toBeInTheDocument();
    
    // Modal should still be open
    expect(screen.getByText('Add Archetype')).toBeInTheDocument();
  });

  test('shows error when trying to add duplicate archetype', () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Open modal
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Try to add existing archetype
    const input = screen.getByLabelText(/enter archetype name/i);
    fireEvent.change(input, { target: { value: 'Hero' } });
    
    const createButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(createButton);
    
    // Error message should appear
    expect(screen.getByText('This archetype already exists')).toBeInTheDocument();
    
    // Modal should still be open
    expect(screen.getByText('Add Archetype')).toBeInTheDocument();
  });

  test('closes modal when clicking Cancel button', async () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Open modal
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Enter some text
    const input = screen.getByLabelText(/enter archetype name/i);
    fireEvent.change(input, { target: { value: 'Warrior' } });
    
    // Click Cancel
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);
    
    // Modal should close and archetype not added
    await waitFor(() => {
      expect(screen.queryByText('Add Archetype')).not.toBeInTheDocument();
    });
    expect(screen.queryByText('Warrior')).not.toBeInTheDocument();
  });

  test('submits form when pressing Enter key', async () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Open modal
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Enter archetype name and press Enter
    const input = screen.getByLabelText(/enter archetype name/i);
    fireEvent.change(input, { target: { value: 'Mentor' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    
    // Modal should close and archetype added
    await waitFor(() => {
      expect(screen.queryByText('Add Archetype')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Mentor')).toBeInTheDocument();
  });

  test('closes modal when pressing Escape key', async () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Open modal
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    // Enter some text
    const input = screen.getByLabelText(/enter archetype name/i);
    fireEvent.change(input, { target: { value: 'Warrior' } });
    
    // Press Escape
    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
    
    // Modal should close and archetype not added
    await waitFor(() => {
      expect(screen.queryByText('Add Archetype')).not.toBeInTheDocument();
    });
    expect(screen.queryByText('Warrior')).not.toBeInTheDocument();
  });

  test('calls onUpdate with new archetype when saving character', async () => {
    render(<CharacterCard {...mockProps} />);
    
    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);
    
    // Add new archetype
    const addButton = screen.getByRole('button', { name: /add/i });
    fireEvent.click(addButton);
    
    const input = screen.getByLabelText(/enter archetype name/i);
    fireEvent.change(input, { target: { value: 'Trickster' } });
    
    const createButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(createButton);
    
    // Wait for modal to close
    await waitFor(() => {
      expect(screen.queryByText('Add Archetype')).not.toBeInTheDocument();
    });
    
    // Save character
    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);
    
    // onUpdate should be called with the new archetype
    await waitFor(() => {
      expect(mockProps.onUpdate).toHaveBeenCalledWith(
        '1',
        expect.objectContaining({
          archetypes: expect.arrayContaining(['Hero', 'Trickster'])
        })
      );
    });
  });
});