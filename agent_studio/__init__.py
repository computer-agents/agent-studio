import logging
import os
from datetime import datetime

logging.getLogger('twisted').setLevel(logging.WARNING)
logger = logging.getLogger("agent_studio")
format = "%(asctime)s\t%(levelname)s %(filename)s:%(lineno)s -- %(message)s"
formatter = logging.Formatter(format)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler(
    filename=os.path.join("logs", f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"),
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logging.basicConfig(level=logging.DEBUG, handlers=[handler, file_handler])
logger.propagate = False
