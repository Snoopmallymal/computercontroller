import json
from computer import ComputerManager
import asyncio

async def main():
    with open("config.json","r") as f:
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
        await manager.apipost("unlock")

    print("Managers initialized:", list(computers.keys()))

# Run the async main function
asyncio.run(main())
