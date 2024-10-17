from datetime import datetime
import logging
from langgraph.graph import StateGraph, MessagesState, START
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition
from prompts import get_calendar_management_prompt
import requests
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.DEBUG)

# Define our state
class CalendarState(MessagesState):
    pass

# Tool definitions

@tool 
def get_today_date():
    """Returns today's date in the format MM/DD/YYYY"""
    month = datetime.now().month
    day = datetime.now().day
    year = datetime.now().year
    return f"{month}/{day}/{year}"

@tool
def get_calendar_events() -> str:
    """Retrieves calendar events for the specified month and year."""
    month = datetime.now().month
    year = datetime.now().year
    day = datetime.now().day
    response = requests.get(f'http://127.0.0.1:5000/calendar_events?month={month}&year={year}&day={day}')
    if response.status_code == 200:
        events = response.json()
        # Format the events as a string
        formatted_events = "\n".join([
            f"- {event['summary']} (Organizer: {event.get('organizer', 'N/A')}) ({event['start']} - {event['end']})"
            for event in events
        ])
        return f"Calendar events for {month}/{year}:\n{formatted_events}"
    else:
        return f"Failed to retrieve events: {response.text}"

@tool
def create_event(summary: str, start: str, end: str, description: str = "", location: str = "", time_zone: str = "UTC") -> str:
    """Creates a new calendar event."""
    payload = {
        'summary': summary,
        'start': start,
        'end': end,
        'description': description,
        'location': location,
        'timeZone': time_zone
    }
    response = requests.post('http://127.0.0.1:5000/create_event', json=payload)
    if response.status_code == 200:
        return f"Event created successfully: {response.json()['id']}"
    else:
        return f"Failed to create event: {response.text}"

@tool
def get_availabilities() -> str:
    """Retrieves available time slots for the current month."""
    response = requests.get('http://127.0.0.1:5000/availabilities')
    if response.status_code == 200:
        availabilities = response.json()
        # Format the availabilities as a string
        formatted_availabilities = "\n".join([f"- {slot}" for slot in availabilities])
        return f"Available time slots:\n{formatted_availabilities}"
    else:
        return f"Failed to retrieve availabilities: {response.text}"

# Create LLM and bind tools
llm = ChatOpenAI(model="gpt-4")
llm_with_tools = llm.bind_tools([get_calendar_events, create_event, get_availabilities, get_today_date])

# System message
system_prompt = get_calendar_management_prompt()
sys_msg = SystemMessage(content=system_prompt)

# Node definition
def assistant(state: CalendarState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# Create the graph
workflow = StateGraph(CalendarState)

# Add nodes
workflow.add_node("assistant", assistant)
workflow.add_node("tools", ToolNode([get_calendar_events, create_event, get_availabilities, get_today_date]))

# Add edges
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges(
    "assistant",
    tools_condition,
)
workflow.add_edge("tools", "assistant")

memory = MemorySaver()

# Compile the graph
calendar_manager_agent = workflow.compile(checkpointer=memory)

def run_calendar_manager(user_input: str, thread_id: str):
    if not user_input or not isinstance(user_input, str):
        raise ValueError("user_input must be a non-empty string.")
    
    config = {"configurable": {"thread_id": thread_id}}
    messages = [HumanMessage(content=user_input)]
    
    try:
        result = calendar_manager_agent.invoke({"messages": messages}, config)

        for m in result['messages']:
            m.pretty_print()

        return result.get("messages", [])
    except Exception as e:
        logging.error(f"Exception during run_calendar_manager: {str(e)}")
        raise
