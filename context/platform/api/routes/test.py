from fastapi import APIRouter

router = APIRouter()

# Define a test API endpoint
@router.get("/")
async def test_api():
    return {"message": "API is working"}