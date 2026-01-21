"""
Example usage of UnifiedBedrockAgentCoreClient.

This example demonstrates how to use the unified client to interact with
AWS Bedrock AgentCore services without worrying about which underlying
service (control plane vs data plane) handles each operation.
"""

from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize the unified client - it will automatically route operations
# to the appropriate service (bedrock-agentcore or bedrock-agentcore-control)
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# ============================================================================
# MEMORY OPERATIONS
# ============================================================================

print("\n=== Memory Operations ===\n")

# 1. CREATE MEMORY (Control Plane)
# The client automatically routes this to bedrock-agentcore-control
memory_response = client.create_memory(
    name="customer-support-memory",
    eventExpiryDuration=90,
    memoryStrategies=[
        {
            "SEMANTIC": {
                "name": "semantic-facts",
                "namespaces": ["support/facts/{actorId}/{sessionId}"]
            }
        }
    ],
    description="Memory for customer support conversations"
)
print(f"✓ Created memory: {memory_response['memory']['id']}")
memory_id = memory_response['memory']['id']

# 2. GET MEMORY (Control Plane)
# Automatically routed to control plane
memory_details = client.get_memory(memoryId=memory_id)
print(f"✓ Retrieved memory status: {memory_details['memory']['status']}")

# 3. CREATE EVENT (Data Plane)
# The client automatically routes this to bedrock-agentcore
event_response = client.create_event(
    memoryId=memory_id,
    actorId="customer-123",
    sessionId="session-456",
    payload=[
        {
            "conversational": {
                "content": {"text": "I need help with my order"},
                "role": "USER"
            }
        },
        {
            "conversational": {
                "content": {"text": "I'd be happy to help! What's your order number?"},
                "role": "ASSISTANT"
            }
        }
    ]
)
print(f"✓ Created event: {event_response['event']['eventId']}")

# 4. LIST EVENTS (Data Plane)
# Automatically routed to data plane
events = client.list_events(
    memoryId=memory_id,
    actorId="customer-123",
    sessionId="session-456",
    maxResults=10
)
print(f"✓ Retrieved {len(events['events'])} events")

# 5. RETRIEVE MEMORY RECORDS (Data Plane)
# Automatically routed to data plane - semantic search
records = client.retrieve_memory_records(
    memoryId=memory_id,
    namespace="support/facts/customer-123/session-456",
    searchCriteria={
        "searchQuery": "order issue",
        "topK": 3
    }
)
print(f"✓ Retrieved {len(records.get('memoryRecordSummaries', []))} memory records")

# ============================================================================
# CODE INTERPRETER OPERATIONS
# ============================================================================

print("\n=== Code Interpreter Operations ===\n")

# 1. CREATE CODE INTERPRETER (Control Plane)
# Automatically routed to control plane
interpreter_response = client.create_code_interpreter(
    name="data_analysis_interpreter",
    executionRoleArn="arn:aws:iam::123456789012:role/CodeInterpreterRole",
    networkConfiguration={
        "networkMode": "PUBLIC"
    },
    description="Interpreter for data analysis tasks"
)
print(f"✓ Created code interpreter: {interpreter_response['codeInterpreterId']}")
interpreter_id = interpreter_response['codeInterpreterId']

# 2. GET CODE INTERPRETER (Control Plane)
# Automatically routed to control plane
interpreter_details = client.get_code_interpreter(codeInterpreterId=interpreter_id)
print(f"✓ Interpreter status: {interpreter_details['status']}")

# 3. START SESSION (Data Plane)
# Automatically routed to data plane
session_response = client.start_code_interpreter_session(
    codeInterpreterIdentifier="aws.codeinterpreter.v1"
)
print(f"✓ Started session: {session_response['sessionId']}")
session_id = session_response['sessionId']

# 4. INVOKE CODE INTERPRETER (Data Plane)
# Automatically routed to data plane
result = client.invoke_code_interpreter(
    codeInterpreterIdentifier="aws.codeinterpreter.v1",
    sessionId=session_id,
    method="execute",
    parameters={
        "code": "print('Hello from unified client!')"
    }
)
print(f"✓ Code execution result: {result.get('output', 'Success')}")

# 5. STOP SESSION (Data Plane)
# Automatically routed to data plane
client.stop_code_interpreter_session(
    codeInterpreterIdentifier="aws.codeinterpreter.v1",
    sessionId=session_id
)
print("✓ Stopped code interpreter session")

# ============================================================================
# BROWSER OPERATIONS
# ============================================================================

print("\n=== Browser Operations ===\n")

# 1. CREATE BROWSER (Control Plane)
# Automatically routed to control plane
browser_response = client.create_browser(
    name="web_automation_browser",
    executionRoleArn="arn:aws:iam::123456789012:role/BrowserRole",
    networkConfiguration={
        "networkMode": "PUBLIC"
    },
    recording={
        "enabled": True,
        "s3Location": {
            "bucket": "my-browser-recordings",
            "keyPrefix": "sessions/"
        }
    }
)
print(f"✓ Created browser: {browser_response['browserId']}")
browser_id = browser_response['browserId']

# 2. LIST BROWSERS (Control Plane)
# Automatically routed to control plane
browsers = client.list_browsers(maxResults=10)
print(f"✓ Retrieved {len(browsers.get('browsers', []))} browsers")

# 3. START BROWSER SESSION (Data Plane)
# Automatically routed to data plane
browser_session = client.start_browser_session(
    browserIdentifier="aws.browser.v1"
)
print(f"✓ Started browser session: {browser_session['sessionId']}")
browser_session_id = browser_session['sessionId']

# 4. INVOKE BROWSER (Data Plane)
# Automatically routed to data plane
browser_result = client.invoke_browser(
    browserIdentifier="aws.browser.v1",
    sessionId=browser_session_id,
    method="navigate",
    parameters={
        "url": "https://example.com"
    }
)
print("✓ Browser navigation successful")

# 5. STOP BROWSER SESSION (Data Plane)
# Automatically routed to data plane
client.stop_browser_session(
    browserIdentifier="aws.browser.v1",
    sessionId=browser_session_id
)
print("✓ Stopped browser session")

# ============================================================================
# CLEANUP
# ============================================================================

print("\n=== Cleanup ===\n")

# Delete resources (all control plane operations)
client.delete_browser(browserId=browser_id)
print("✓ Deleted browser")

client.delete_code_interpreter(codeInterpreterId=interpreter_id)
print("✓ Deleted code interpreter")

client.delete_memory(memoryId=memory_id)
print("✓ Deleted memory")

# ============================================================================
# ADVANCED: Check which client handles an operation
# ============================================================================

print("\n=== Advanced: Client Introspection ===\n")

# You can check which underlying client handles a specific operation
control_client = client.get_client_for_operation("create_memory")
print(f"✓ create_memory uses: {type(control_client).__name__}")

data_client = client.get_client_for_operation("create_event")
print(f"✓ create_event uses: {type(data_client).__name__}")

print("\n=== Complete! ===\n")
print("The unified client automatically routed all operations to the correct service.")
print("You didn't need to know about bedrock-agentcore vs bedrock-agentcore-control!")
