import logging
from langgraph.graph import StateGraph, MessagesState, START
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition
from prompts import get_email_management_prompt
from langgraph.checkpoint.memory import MemorySaver
from email_manager_agent import retrieve_emails, run_email_manager, send_email
from calendar_manager_agent import run_calendar_manager
logging.basicConfig(level=logging.DEBUG)

# Define our state
class SuperManagerState(MessagesState):
    pass

@tool
def email_manager(user_input: str, thread_id: str) -> str:
    """This tool manages emails. It can reply to an email, send a new email, or get the email summary for the day."""
    """It needs the neccessary input as the user_input string"""
    thread_id = thread_id or "default_thread_id"
    return run_email_manager(user_input, thread_id)

@tool
def calendar_manager(user_input: str, thread_id: str) -> str:
    """This tool manages calendar. It can create an event, get the calendar events for the day, or get the availabilities for the given day(s)."""
    """It needs the neccessary input as the user_input string"""
    thread_id = thread_id or "default_thread_id"
    return run_calendar_manager(user_input, thread_id)

# Create LLM and bind tools
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([email_manager, calendar_manager])

# System message
system_prompt = get_email_management_prompt()
sys_msg = SystemMessage(content=system_prompt)

# Node definition
def assistant(state: SuperManagerState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# Create the graph
workflow = StateGraph(SuperManagerState)

# Add nodes
workflow.add_node("assistant", assistant)
workflow.add_node("tools", ToolNode([email_manager, calendar_manager]))

# Add edges
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges(
    "assistant",
    tools_condition,
)
workflow.add_edge("tools", "assistant")

memory = MemorySaver()

# Compile the graph
super_manager_agent = workflow.compile(checkpointer=memory)

def run_super_manager(user_input: str, thread_id: str):
    if not user_input or not isinstance(user_input, str):
        raise ValueError("user_input must be a non-empty string.")
    
    config = {"configurable": {"thread_id": thread_id}}
    messages = [HumanMessage(content=user_input)]
    
    try:
        result = super_manager_agent.invoke({"messages": messages}, config)

        for m in result['messages']:
            m.pretty_print()
        
        return result.get("messages", [])
    except Exception as e:
        logging.error(f"Exception during run_super_manager: {str(e)}")
        raise





