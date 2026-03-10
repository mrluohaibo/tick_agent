import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Original content of news_nodes.py
import json
import time
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from bz_agent.agents.llm import get_llm_by_type
from bz_agent.graph.types import State
from utils.logger_config import logger
from utils.db_tool_init import mongo_client, mysql_client