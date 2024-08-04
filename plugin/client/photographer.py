"""References

Sending key to inactive window
    https://stackoverflow.com/questions/12996985/send-some-keys-to-inactive-window-with-python


"""
import time
import json
import time
import argparse
import datetime
import logging
import sys

import asyncio
import aiohttp
import socketio
import win32gui
import win32ui


from PIL import Image
from typing import Optional
from ctypes import windll, create_unicode_buffer
from pathlib import Path
from dataclasses import dataclass
from rich.console import Group
from rich.live import Live
from rich.console import Console
from rich.status import Status

SCREENSHOTS_DIR = Path("~/AppData/Roaming/.minecraft/screenshots").expanduser().resolve()
SIO = socketio.AsyncClient()


@dataclass
class Args:
    host: str = "localhost"
    port: int = 8234
    api_url: str = None
    api_version: str = None
    different_world_screenshot_delay: int = 15
    same_world_screenshot_delay: int = 2
    log_file = None


@dataclass
class Observation:
    id: int
    user: str
    caption: str


@dataclass
class DataStore:
    uuid: Optional[str] = None
    uuid_event = asyncio.Event()

    # The current player operating as a cameraman
    cameraman: Optional[str] = None

    observation: Optional[Observation] = None

    mc_window_id = None
    mc_window_title = None

    @property
    def is_event_in_progress(self):
        return self.observation is not None


DATA = DataStore()  # Global shared data
ARGS = Args()  # Global args

# Rich output stuff
CONSOLE = Console()
CONNECTION_LOADING = Status("[bright_red]Connecting to server")
CAMERAMAN_LOADING = Status("[bright_red]Waiting for cameraman to connect")
OBSERVATION_WAITING = Status("[bright_green]Ready for observation")


def my_excepthook(exc_type, exc_value, traceback):
    if exc_type == KeyboardInterrupt:
        log("Shutting down...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(disconnect())
        exit()
    logging.error("Logging an uncaught exception", exc_info=(exc_type, exc_value, traceback))


sys.excepthook = my_excepthook


def log(msg):
    prefix = f"[aqua]obs_id={DATA.observation.id}[/]: " if DATA.observation is not None else ""
    CONSOLE.log(f"{prefix}{msg}")
    logging.info(msg)


def get_foreground_window_title() -> Optional[str]:
    """https://stackoverflow.com/questions/10266281/obtain-active-window-using-python"""
    hWnd = windll.user32.GetForegroundWindow()
    length = windll.user32.GetWindowTextLengthW(hWnd)
    buf = create_unicode_buffer(length + 1)
    windll.user32.GetWindowTextW(hWnd, buf, length + 1)

    return buf.value


async def call_api(screenshot_path: Path, observation: Observation) -> dict:
    data = {
        "user-caption": observation.caption,
        "user": observation.user,
        "image": open(screenshot_path, "rb"),
        "version": ARGS.api_version,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(ARGS.api_url, data=data) as resp:
            raw_data = await resp.content.read()
    return json.loads(raw_data)


async def screenshot_window(window_id) -> Optional[Path]:
    windll.user32.SetProcessDPIAware()

    left, top, right, bot = win32gui.GetClientRect(window_id)

    w = right - left
    h = bot - top

    hwndDC = win32gui.GetWindowDC(window_id)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

    saveDC.SelectObject(saveBitMap)

    result = windll.user32.PrintWindow(window_id, saveDC.GetSafeHdc(), 1)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    im = Image.frombuffer(
        "RGB", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRX", 0, 1
    )

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(window_id, hwndDC)

    if result == 1:
        file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOTS_DIR / f"{file_name}.png"
        im.save(path)
        return path
    return None


async def screenshot_failed(msg, id):
    log(f"[red]{msg}[/]")
    await SIO.emit("screenshot_failed", id)


@SIO.event
async def connect_error(data):
    log(f"[bright_red]The connection failed! [{data}]")


@SIO.event
async def disconnect():
    if DATA.is_event_in_progress:
        await screenshot_failed("Screenshot in progress while shutting down!", DATA.observation.id)
        DATA.observation = None

    DATA.uuid = None
    DATA.uuid_event.clear()
    await SIO.emit("disconnect")
    await SIO.disconnect()
    log("Client disconnected")


@SIO.event
async def uuid(data):
    DATA.uuid = data
    DATA.uuid_event.set()


@SIO.event
async def cameraman_connect(player):
    log(f"New cameraman connected: {player}")
    DATA.cameraman = player


@SIO.event
async def cameraman_disconnect(player):
    log(f"Camerman ({player}) disconnected")
    DATA.cameraman = None


@SIO.event
async def message(msg):
    log(f"Message from server: {msg}")
    if msg == "screenshot":
        await screenshot_window(DATA.mc_window_id)


@SIO.event
async def screenshot(obs_id, user_name, user_caption, does_player_teleport):
    log(f"Received screenshot request: id={obs_id},caption='{user_caption}'")

    if DATA.is_event_in_progress:
        await screenshot_failed("Screenshot already in progress!", obs_id)
        return

    log("Received screenshot request")
    DATA.observation = Observation(obs_id, user_name, user_caption)

    if does_player_teleport:
        log("Player does not have to change worlds.")
        screenshot_delay = ARGS.same_world_screenshot_delay
    else:
        log("Player needs to change worlds.")
        screenshot_delay = ARGS.different_world_screenshot_delay

    # Give time for the picture to process
    log(f"Waiting {screenshot_delay}s")
    await asyncio.sleep(screenshot_delay)

    ss_path = await screenshot_window(DATA.mc_window_id)

    if ss_path is None:
        await screenshot_failed("Something went wrong when taking screenshot!", obs_id)
        DATA.observation = None
        return

    log(f"Screenshot saved to '{ss_path}'")

    log("Calling API")
    data = await call_api(ss_path, DATA.observation)
    log(f"Response from API: {data}")

    await SIO.emit(
        "screenshot_response",
        data={
            "clientUuid": DATA.uuid,
            "playerName": DATA.observation.user,
            "observationId": obs_id,
            "feedback": data["feedback"],
            "generatedCaption": data["generated caption"],
            "score": data["score"],
        },
    )
    log("[green]Response sent to server")

    DATA.observation = None


async def handle_gui():
    with Live(console=CONSOLE, refresh_per_second=10) as live_table:
        while True:
            group = [
                # Window
                f":earth_americas: Minecraft Window '{DATA.mc_window_title}' ({DATA.mc_window_id})",
                # Server connection
                f":white_check_mark:{ARGS.host}:{ARGS.port} \[{DATA.uuid}]"
                if DATA.uuid is not None
                else CONNECTION_LOADING,
                # Cameraman label
                f":white_check_mark:Cameraman: [aqua]{DATA.cameraman}[/]"
                if DATA.cameraman
                else CAMERAMAN_LOADING,
            ]

            if DATA.cameraman:
                group.append(
                    f"Processing {DATA.observation}"
                    if DATA.is_event_in_progress
                    else OBSERVATION_WAITING
                )

            await asyncio.sleep(0.1)
            live_table.update(Group(*group))


async def main():
    asyncio.create_task(handle_gui())

    url = f"ws://{ARGS.host}:{ARGS.port}"
    log(f"connecting to {url}")
    await SIO.connect(url, transports="websocket")

    # Wait for UUID to be set
    await DATA.uuid_event.wait()
    log(f"Received UUID {DATA.uuid}")

    # Free to do other stuff now
    await SIO.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        required=True,
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--api-url",
        default="",
    )
    parser.add_argument(
        "--api-version",
        choices=["1", "2"],
        default=2

    )
    parser.add_argument(
        "--same-world-screenshot-delay",
        type=int,
        help="Seconds to wait between teleporting and taking a screenshot if the player doesn't have to change worlds.",
        default=2,
    )
    parser.add_argument(
        "--different-world-screenshot-delay",
        type=int,
        help="Seconds to wait between teleporting and taking a screenshot if the player has to change worlds.",
        default=15,
    )
    parser.add_argument(
        "--log-file",
        default=Path(__file__).parent / "photographer.log",
        type=argparse.FileType("w"),
    )
    args = parser.parse_args()
    ARGS.__dict__.update(vars(args))
    logger = logging.basicConfig(
        filename=args.log_file,
        level=logging.DEBUG,
        format="[%(asctime)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log("Focus your Minecraft window!")
    time.sleep(1)

    seconds = 3
    for ind in range(seconds):
        log(seconds - ind)
        time.sleep(1)

    mc_window_title = get_foreground_window_title()
    mc_window_id = win32gui.FindWindow(None, mc_window_title)
    DATA.mc_window_id = mc_window_id
    DATA.mc_window_title = mc_window_title
    log(f"Found window '{mc_window_title}' with id: {mc_window_id}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
