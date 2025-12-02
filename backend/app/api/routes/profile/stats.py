@router.get("/me/stats", response_model=dict)
async def get_user_stats(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user)
):
    """Get aggregated statistics for the current user."""
    user_id = current_user['id']
    
    books_progress_req = supabase_client.table('user_progress').select('completed_at, time_spent').eq('user_id', user_id).execute()
    badges_req = supabase_client.table('user_badges').select('badge_id', count='exact').eq('user_id', user_id).execute()
    quizzes_req = supabase_client.table('quiz_attempts').select('score').eq('user_id', user_id).execute()
    books_uploaded_req = supabase_client.table('books').select('id', count='exact').eq('user_id', user_id).execute()

    books_progress = books_progress_req.data
    badges_count = badges_req.count if badges_req.count is not None else 0
    quizzes = quizzes_req.data
    books_uploaded_count = books_uploaded_req.count if books_uploaded_req.count is not None else 0

    books_read = len([p for p in books_progress if p.get('completed_at')])
    total_time_minutes = sum(p.get('time_spent', 0) for p in books_progress)
    
    stats = {
        "books_read": books_read,
        "books_in_progress": len(books_progress) - books_read,
        "books_uploaded": books_uploaded_count,
        "total_time_hours": total_time_minutes // 60,
        "badges_earned": badges_count,
        "quizzes_taken": len(quizzes),
        "average_quiz_score": sum(q.get('score', 0) for q in quizzes) / len(quizzes) if quizzes else 0
    }
    
    return stats