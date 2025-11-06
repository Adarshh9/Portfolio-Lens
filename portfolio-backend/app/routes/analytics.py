import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models.database import db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/analytics/popular-queries")
async def get_popular_queries(limit: int = 10, mode: Optional[str] = None):
    """Get most popular questions asked"""
    try:
        queries = await db.get_popular_queries(limit=limit, mode=mode)
        
        return {
            "status": "success",
            "mode_filter": mode,
            "limit": limit,
            "queries": [
                {"query": q, "count": count} 
                for q, count in queries
            ]
        }
    except Exception as e:
        logger.error(f"Error getting popular queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/quality-metrics")
async def get_quality_metrics(hours: int = 24):
    """Get response quality metrics"""
    try:
        metrics = await db.get_quality_metrics(hours=hours)
        
        return {
            "status": "success",
            "period_hours": hours,
            "average_quality_score": metrics.get("average_quality", 0),
            "by_mode": metrics.get("by_mode", {}),
            "total_queries": metrics.get("total_queries", 0)
        }
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/mode-distribution")
async def get_mode_distribution():
    """Get distribution of queries by mode"""
    try:
        distribution = await db.get_mode_distribution()
        
        total = sum(distribution.values())
        percentages = {
            mode: (count / total * 100) if total > 0 else 0
            for mode, count in distribution.items()
        }
        
        return {
            "status": "success",
            "distribution": distribution,
            "percentages": percentages,
            "total_queries": total
        }
    except Exception as e:
        logger.error(f"Error getting mode distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/dashboard")
async def get_dashboard():
    """Complete analytics dashboard"""
    try:
        popular = await db.get_popular_queries(limit=10)
        metrics = await db.get_quality_metrics()
        distribution = await db.get_mode_distribution()
        
        total = sum(distribution.values())
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_queries": metrics.get("total_queries", 0),
                "average_quality": metrics.get("average_quality", 0),
                "popular_queries": len(popular),
                "modes_used": len(distribution)
            },
            "popular_questions": [
                {"query": q, "count": count}
                for q, count in popular
            ],
            "quality_by_mode": metrics.get("by_mode", {}),
            "mode_distribution": {
                "counts": distribution,
                "percentages": {
                    mode: (count / total * 100) if total > 0 else 0
                    for mode, count in distribution.items()
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))