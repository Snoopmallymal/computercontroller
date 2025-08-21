# computer.py
from database import Database as DatabaseClass
from apscheduler.schedulers.background import BackgroundScheduler
import httpx
import asyncio
import json

class ComputerManager:
    def __init__(self, id, name, hostname, token, enviroment_token, managed_user):
        print(id, name, hostname, token, enviroment_token, managed_user)
        self.hostname = hostname
        self.database = DatabaseClass(f"{id}.db")
        self.token = token
        self.database.adjust_time(10, reason="Initialized computer manager")
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._removemin, 'interval', seconds=60)
        self.scheduler.start()

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
    
    async def _removemin(self):
        min =  int(self.database.get_time())
        newmin = max(0, min - 1)
        self.database.adjust_time(-1, reason="Timer countdown")
        return newmin

class ComputerImporter:
    def __init__(self, config_file="config.json"):
        with open(config_file,"r") as f:
            data = json.load(f)

        computers = {}

        for comp in data["computers"]:
            manager = ComputerManager(
                comp["id"],
                comp["name"],
                comp["hostname"],
                comp["token"],
                comp["enviroment_token"],
                comp["managed_user"]
            )
            computers[comp["id"]] = manager
            # await the async function
        print("Managers initialized:", list(computers.keys()))
        self.computers = computers.keys()

