"""
Tests for character details generation via AI
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.character_service import CharacterService


@pytest.mark.asyncio
async def test_parse_character_details_with_json_response():
    """Test parsing when AI returns proper JSON"""
    service = CharacterService()
    
    # Simulate a proper JSON response from the AI
    ai_response = """```json
{
    "physical_description": "Tall woman in her seventies with sharp eyes and stern expression",
    "personality": "Strict but fair, deeply caring beneath a tough exterior",
    "character_arc": "Moves from authority figure to mentor and protector",
    "want": "To protect Hogwarts and its students",
    "need": "To trust others and show vulnerability",
    "lie": "That showing emotion is weakness",
    "ghost": "Witnessed too many student deaths in previous wars"
}
```"""
    
    result = service._parse_character_details_response(
        ai_response=ai_response,
        character_name="Professor McGonagall",
        role="supporting"
    )
    
    # Verify all fields are populated
    assert result["name"] == "Professor McGonagall"
    assert result["role"] == "supporting"
    assert result["physical_description"] != ""
    assert result["personality"] != ""
    assert result["character_arc"] != ""
    assert result["want"] != ""
    assert result["need"] != ""
    assert result["lie"] != ""
    assert result["ghost"] != ""
    
    # Verify specific content
    assert "seventies" in result["physical_description"].lower()
    assert "strict" in result["personality"].lower()


@pytest.mark.asyncio
async def test_parse_character_details_with_plain_json():
    """Test parsing when AI returns JSON without markdown"""
    service = CharacterService()
    
    ai_response = """{
    "physical_description": "Elderly wizard with half-moon spectacles",
    "personality": "Wise, powerful, yet kind and understanding",
    "character_arc": "From mysterious mentor to sacrificial hero",
    "want": "To defeat Voldemort and protect Harry",
    "need": "To atone for past mistakes",
    "lie": "That he can control everything",
    "ghost": "His sister's death and family tragedy"
}"""
    
    result = service._parse_character_details_response(
        ai_response=ai_response,
        character_name="Albus Dumbledore",
        role="mentor"
    )
    
    # Verify all fields populated
    assert all(result[field] != "" for field in [
        "physical_description", "personality", "character_arc",
        "want", "need", "lie", "ghost"
    ])


@pytest.mark.asyncio
async def test_parse_character_details_with_text_fallback():
    """Test text parsing fallback when JSON parsing fails"""
    service = CharacterService()
    
    # Simulate a text response (not JSON)
    ai_response = """
Physical Description: Young boy with messy black hair and green eyes, lightning bolt scar on forehead

Personality: Brave, loyal, sometimes impulsive but deeply caring

Character Arc: Orphan discovering his destiny to chosen one accepting sacrifice

Want: To belong and have a family

Need: To accept love and his own worth

Lie They Believe: That he doesn't deserve love or happiness

Ghost: Witnessed his parents' murder as a baby, carries survivor's guilt
"""
    
    result = service._parse_character_details_response(
        ai_response=ai_response,
        character_name="Harry Potter",
        role="protagonist"
    )
    
    # Verify fields are extracted from text
    assert result["name"] == "Harry Potter"
    assert result["role"] == "protagonist"
    assert "black hair" in result["physical_description"].lower()
    assert "brave" in result["personality"].lower()
    assert result["want"] != ""
    assert result["need"] != ""


@pytest.mark.asyncio
async def test_generate_character_details_from_book_integration():
    """Integration test for full character generation flow (mocked)"""
    
    # Mock the database and services
    mock_db = Mock()
    mock_db.table = Mock(return_value=Mock(
        select=Mock(return_value=Mock(
            eq=Mock(return_value=Mock(
                single=Mock(return_value=Mock(
                    execute=Mock(return_value=Mock(data={
                        'id': 'book-123',
                        'title': 'Test Book',
                        'author': 'Test Author',
                        'genre': 'Fantasy',
                        'description': 'A magical story'
                    }))
                ))
            ))
        ))
    ))
    
    service = CharacterService(supabase_client=mock_db)
    
    # Mock OpenRouter response
    mock_ai_response = {
        "status": "success",
        "result": """```json
{
    "physical_description": "Test description",
    "personality": "Test personality",
    "character_arc": "Test arc",
    "want": "Test want",
    "need": "Test need",
    "lie": "Test lie",
    "ghost": "Test ghost"
}
```"""
    }
    
    with patch.object(service.openrouter, 'analyze_content', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_ai_response
        
        with patch.object(service.subscription_manager, 'get_user_tier', new_callable=AsyncMock) as mock_tier:
            from app.services.subscription_manager import SubscriptionTier
            mock_tier.return_value = SubscriptionTier.FREE
            
            result = await service.generate_character_details_from_book(
                character_name="Test Character",
                book_id="book-123",
                user_id="user-123",
                role="supporting"
            )
    
    # Verify all fields are present and populated
    assert result["name"] == "Test Character"
    assert result["role"] == "supporting"
    assert result["physical_description"] == "Test description"
    assert result["personality"] == "Test personality"
    assert result["character_arc"] == "Test arc"
    assert result["want"] == "Test want"
    assert result["need"] == "Test need"
    assert result["lie"] == "Test lie"
    assert result["ghost"] == "Test ghost"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])