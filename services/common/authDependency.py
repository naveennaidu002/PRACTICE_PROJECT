from fastapi import Header, HTTPException, Depends
from services.common.auth import validateToken, getDatasourceDetail, getUserDetail
import logging

async def Authorization(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        token = authorization.split(" ")[1]
        decoded_token = validateToken(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def DatasourceAuthorization(authorization, isresearch):
    
    if not authorization:
         raise HTTPException(status_code=401, detail="Authorization header missing")
         
    try:
        token = authorization.split(" ")[1]
        decoded_token = validateToken(token) 
        
        user_info, datasources_backend = getDatasourceDetail(decoded_token, isresearch)
        
        # We process keys here if needed, but getDatasourceDetail returns dict_keys usually.
        # Ensure it returns a list for 'in' checks if it's not already
        if not isinstance(datasources_backend, list) and not isinstance(datasources_backend, dict):
             datasources_backend = list(datasources_backend)

        return user_info, datasources_backend
    except Exception as e:
        # Log error if needed
        print(f"Auth Decision Error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed or invalid token")
