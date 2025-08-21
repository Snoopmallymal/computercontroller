import json
from computer import ComputerImporter as importer
from livedata import LiveData as live_data
from database import Database as db
import asyncio

async def main():
    computers = importer().computers
    print("Computers managed:", computers)
    for comp in computers:
        print(f"Computer ID: {comp}")
        print(f"Minutes left: {live_data(comp).get_minutes()}")
        print(f"Lock mode: {live_data(comp).get_lock_mode()}")
        print(f"Name: {computers[comp].name}")

    

asyncio.run(main())
