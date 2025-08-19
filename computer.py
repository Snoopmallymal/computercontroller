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

    async def apipost(self, endpoint, data=None):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"http://{self.hostname}/{endpoint}", json=data, headers={"Authorization": f"Bearer {self.token}"})
            return resp.json()
