from fastapi import APIRouter, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os

router = APIRouter()

# Configure CrateDB connection
CRATEDB_URL = os.getenv("CRATEDB_URL", "crate://cratedb:4200")
engine = create_engine(CRATEDB_URL)

def get_db():
    db = engine.connect()
    try:
        yield db
    finally:
        db.close()

# Get data from CrateDB table mtiot.ettemperaturesensor
@router.get("/")
async def get_dummy_data(db: Session = Depends(get_db)):
    query = text("SELECT * FROM mtiot.ettemperaturesensor LIMIT 10")
    result = db.execute(query)
    
    data = []
    for row in result:
        data.append(dict(row._mapping))
    
    return {"data": data}