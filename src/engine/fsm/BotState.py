import time
import logging
from config.config_loader import config
from typing import Optional
from src.engine.game_state import GameState
import time
import random
from pathlib import Path
import yaml
import time
from enum import Enum, auto


class BotState(Enum):
    IDLE = auto()
    MOVING = auto()
    HUNTING = auto()
    FIGHTING = auto()