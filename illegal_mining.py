from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2 import pool
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import List
from pydantic import BaseModel

app = FastAPI(debug=True)

# Database connection parameters
db_name = "Illegal_Mining"
db_user = "postgres"
db_pswd = "csmpl@123"
db_host = "192.168.25.102"
db_port = "5432"

# Create a connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20, dbname=db_name, user=db_user, password=db_pswd, host=db_host, port=db_port
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/getJodaGeoJSON")
async def get_joda_geojson():
    try:
        # Get a connection from the pool
        connection = db_pool.getconn()
        cursor = connection.cursor()

        # Query to get the geometry as GeoJSON
        query = """
        SELECT ST_AsGeoJSON(geom) AS geojson
        FROM joda_valid
        WHERE gid = 1;
        """
        cursor.execute(query)
        result = cursor.fetchone()

        # Check if result exists
        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Polygon not found")

        # Parse the GeoJSON string into a proper JSON object
        geojson = json.loads(result[0])

        # Return GeoJSON polygon
        return {"geometry": geojson}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Release the connection back to the pool
        if connection:
            cursor.close()
            db_pool.putconn(connection)

# Pydantic Model for KML Data
class KMLData(BaseModel):
    gid: int
    layer: str

# Get getAllLessees Data
@app.get("/getAllLessees")
async def getAllLessees():
    """Fetches gid, layer, and extent from kml_joda_lessee"""
    try:
        connection = db_pool.getconn()
        cursor = connection.cursor()

        query = """
        SELECT gid, layer, ST_Extent(geom) AS extent 
        FROM kml_joda_lessee 
        GROUP BY gid, layer
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No records found")

        results = []
        for row in rows:
            gid, layer, extent = row
            extent_dict = None

            if extent:
                extent_values = extent.replace("BOX(", "").replace(")", "").split(",")
                minx, miny = map(float, extent_values[0].split())
                maxx, maxy = map(float, extent_values[1].split())
                extent_dict = {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}

            results.append({"gid": gid, "layer": layer, "extent": extent_dict})

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if connection:
            cursor.close()
            db_pool.putconn(connection)