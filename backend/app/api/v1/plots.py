from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import Optional

from app.schemas.plot import (
    PlotGenerationRequest,
    PlotGenerationResponse,
    PlotOverviewResponse,
    PlotOverviewUpdate
)
from app.services.plot_service import PlotService
from app.core.database import get_supabase
from app.core.auth import get_current_active_user
from app.services.subscription_manager import SubscriptionManager

router = APIRouter()


@router.post("/books/{book_id}/generate", response_model=PlotGenerationResponse)
async def generate_plot_overview(
    book_id: str,
    request: PlotGenerationRequest,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Generate comprehensive plot overview with characters for a book.

    - **book_id**: ID of the book to generate plot for
    - **request**: Plot generation parameters including custom prompt, genre, tone, audience
    """
    try:
        # Validate book ownership
        book_response = supabase_client.table('books').select('user_id').eq('id', book_id).single().execute()
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found")

        if book_response.data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this book")

        # Check subscription limits
        subscription_manager = SubscriptionManager(supabase_client)
        usage_check = await subscription_manager.check_usage_limits(current_user['id'], "plot")

        if not usage_check["can_generate"]:
            raise HTTPException(
                status_code=402,
                detail=f"Plot generation limit exceeded. You have used {usage_check['plots_used']} out of {usage_check['plots_limit']} plots. Please upgrade your subscription."
            )

        # Generate plot overview
        plot_service = PlotService(supabase_client)
        result = await plot_service.generate_plot_overview(
            user_id=current_user['id'],
            book_id=book_id,
            request=request
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plot overview: {str(e)}")


@router.get("/books/{book_id}", response_model=PlotOverviewResponse)
async def get_plot_overview(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Retrieve existing plot overview for a book.

    - **book_id**: ID of the book
    """
    try:
        # Validate book ownership
        book_response = supabase_client.table('books').select('user_id').eq('id', book_id).single().execute()
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found")

        if book_response.data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this book")

        # Get plot overview
        plot_service = PlotService(supabase_client)
        plot_overview = await plot_service.get_plot_overview(
            user_id=current_user['id'],
            book_id=book_id
        )

        if not plot_overview:
            raise HTTPException(status_code=404, detail="No plot overview found for this book")

        return plot_overview

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve plot overview: {str(e)}")


@router.get("/books/{book_id}/overview", response_model=PlotOverviewResponse)
async def get_plot_overview_overview(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Retrieve existing plot overview for a book.

    - **book_id**: ID of the book
    """
    try:
        # Validate book ownership
        book_response = supabase_client.table('books').select('user_id').eq('id', book_id).single().execute()
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found")

        if book_response.data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this book")

        # Get plot overview
        plot_service = PlotService(supabase_client)
        plot_overview = await plot_service.get_plot_overview(
            user_id=current_user['id'],
            book_id=book_id
        )

        if not plot_overview:
            raise HTTPException(status_code=404, detail="No plot overview found for this book")

        return plot_overview

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve plot overview: {str(e)}")


@router.put("/{plot_id}", response_model=PlotOverviewResponse)
async def update_plot_overview(
    plot_id: str,
    updates: PlotOverviewUpdate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update existing plot overview.

    - **plot_id**: ID of the plot overview to update
    - **updates**: Fields to update
    """
    try:
        # Update plot overview
        plot_service = PlotService(supabase_client)
        updated_plot = await plot_service.update_plot_overview(
            user_id=current_user['id'],
            plot_id=plot_id,
            updates=updates
        )

        return updated_plot

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update plot overview: {str(e)}")


@router.delete("/{plot_id}")
async def delete_plot_overview(
    plot_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Delete plot overview (soft delete).

    - **plot_id**: ID of the plot overview to delete
    """
    try:
        # Validate ownership and soft delete
        plot_response = supabase_client.table('plot_overviews').select('user_id').eq('id', plot_id).single().execute()
        if not plot_response.data:
            raise HTTPException(status_code=404, detail="Plot overview not found")

        if plot_response.data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this plot overview")

        # Soft delete by updating status
        supabase_client.table('plot_overviews').update({
            'status': 'deleted',
            'updated_at': 'now()'
        }).eq('id', plot_id).execute()

        # Also soft delete associated characters
        supabase_client.table('characters').update({
            'status': 'deleted',
            'updated_at': 'now()'
        }).eq('plot_overview_id', plot_id).execute()

        return {"message": "Plot overview deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete plot overview: {str(e)}")