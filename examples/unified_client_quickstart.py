"""
Quick start example for UnifiedBedrockAgentCoreClient.

This example shows the simplest way to get started with the unified client.
"""

from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# Step 1: Create the unified client
# This is all you need - no need to create multiple clients!
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Step 2: Use any operation - the client automatically routes to the right service
# You don't need to know or care about control plane vs data plane

# Create a memory (control plane operation)
memory = client.create_memory(
    name="my-first-memory",
    eventExpiryDuration=90,
    memoryStrategies=[{
        "SEMANTIC": {
            "name": "facts",
            "namespaces": ["app/{actorId}/{sessionId}"]
        }
    }]
)
print(f"✓ Created memory: {memory['memory']['id']}")

# Save a conversation (data plane operation)
event = client.create_event(
    memoryId=memory['memory']['id'],
    actorId="user-123",
    sessionId="session-456",
    payload=[
        {
            "conversational": {
                "content": {"text": "What's the weather today?"},
                "role": "USER"
            }
        },
        {
            "conversational": {
                "content": {"text": "It's sunny and 75°F!"},
                "role": "ASSISTANT"
            }
        }
    ]
)
print(f"✓ Saved conversation: {event['event']['eventId']}")

# Search memories (data plane operation)
results = client.retrieve_memory_records(
    memoryId=memory['memory']['id'],
    namespace="app/user-123/session-456",
    searchCriteria={
        "searchQuery": "weather",
        "topK": 5
    }
)
print(f"✓ Found {len(results.get('memoryRecordSummaries', []))} relevant memories")

# That's it! The unified client handled routing everything automatically.
print("\n✨ Success! You used control and data plane operations without thinking about it.")
