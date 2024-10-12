from typing import Optional, TypedDict
from langgraph.graph import StateGraph, END, START

# Define the state for the graph
class CalendarState(TypedDict):
    user_input: str
    event_details: Optional[dict] = None

# Define the logic for each node
def create_event(state: CalendarState) -> CalendarState:
    # Logic to create a calendar event
    return {"event_details": {"status": "created"}}

def update_event(state: CalendarState) -> CalendarState:
    # Logic to update a calendar event
    return {"event_details": {"status": "updated"}}

def delete_event(state: CalendarState) -> CalendarState:
    # Logic to delete a calendar event
    return {"event_details": {"status": "deleted"}}

def send_reminders(state: CalendarState) -> CalendarState:
    # Logic to send reminders for events
    return {"event_details": {"status": "reminder sent"}}

def accept_invitation(start: CalendarState) -> CalendarState:
    return {"event_details": {"status": "invitation accepted"}}

def retrieve_availability(state: CalendarState) -> CalendarState:
    # Logic to retrieve availability
    return {"event_details": {"status": "availability retrieved"}}

def decide_next_action(state: CalendarState) -> CalendarState:
    # Return the user_input as part of the state
    return {"user_input": state["user_input"]}

# Create the graph
graph = StateGraph(CalendarState)

# Add nodes
graph.add_node("decide_next_action", decide_next_action)
graph.add_node("create_event", create_event)
graph.add_node("update_event", update_event)
graph.add_node("delete_event", delete_event)
graph.add_node("send_reminders", send_reminders)
graph.add_node("retrieve_availability", retrieve_availability)
graph.add_node("accept_invitation", accept_invitation)

# Set entry point
# graph.set_entry_point("decide_next_action")
graph.add_edge(START, "decide_next_action")

# Add edges
graph.add_conditional_edges(
    "decide_next_action",
    lambda x: x["user_input"],
    {
        "create": "create_event",
        "update": "update_event",
        "delete": "delete_event",
        "send_reminders": "send_reminders",
        "retrieve_availability": "retrieve_availability",
        "accept_invitation": "accept_invitation",
        "end": END
    },
)


# Add edges from action nodes to END
for action in ["create_event", "update_event", "delete_event", "send_reminders", "retrieve_availability", "accept_invitation"]:
    graph.add_edge(action, END)

# Compile the graph
calendar_manager = graph.compile()

if __name__ == "__main__":
    while True:
        user_input = input("Enter action (create/update/delete/send_reminders/retrieve_availability/end): ").strip().lower()
        result = calendar_manager.invoke({"user_input": user_input})
        print(f"Result: {result}")
        if user_input == "end":
            break
