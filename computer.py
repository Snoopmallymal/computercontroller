# computer.py
from database import Database as DatabaseClass
import httpx
import asyncio

class ComputerManager:
    def __init__(self, id, name, hostname, token, enviroment_token, managed_user):
        print(id, name, hostname, token, enviroment_token, managed_user)
        self.hostname = hostname
        self.database = DatabaseClass(f"{id}.db")
        self.token = token

    async def _apipost(self, endpoint, data=None):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"http://{self.hostname}/{endpoint}", json=data, headers={"Authorization": f"Bearer {self.token}"})
            return resp.json()
        
    async def _apiget(self, endpoint, params=None):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://{self.hostname}/{endpoint}",
                params=params,
                headers={"Authorization": f"Bearer {self.token}"}
            )

            # safer handling
            try:
                return resp.json()
            except ValueError:
                print(f"Non-JSON response from {endpoint}: {resp.text}")
                return None
    
    async def _unlock(self):
        resp = await self._apipost("unlock")
        return resp
    
    async def _lock(self):
        resp = await self._apipost("lock")
        return resp
    
    async def status(self):
        resp = await self._apiget("status")
        return resp
