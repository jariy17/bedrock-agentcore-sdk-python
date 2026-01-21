# Unified Bedrock AgentCore Client

## Overview

The `UnifiedBedrockAgentCoreClient` is a thin wrapper that provides a single, unified interface for all AWS Bedrock AgentCore operations. It automatically routes API calls to the appropriate underlying service without requiring you to know which service handles which operation.

## The Problem It Solves

AWS Bedrock AgentCore has two separate services:

1. **bedrock-agentcore-control** (Control Plane): Handles resource management operations like creating, updating, and deleting resources
2. **bedrock-agentcore** (Data Plane): Handles runtime and data operations like creating events, starting sessions, and executing code

Traditionally, you would need to:
- Know which service handles each operation
- Create and manage separate boto3 clients for each service
- Remember which client to use for each API call

**Example of the traditional approach:**
```python
import boto3

# Need to create two clients
control_client = boto3.client("bedrock-agentcore-control", region_name="us-west-2")
data_client = boto3.client("bedrock-agentcore", region_name="us-west-2")

# Need to remember which client to use
memory = control_client.create_memory(...)  # Control plane
event = data_client.create_event(...)       # Data plane
```

## The Solution

The unified client simplifies this:

```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# Single client for everything
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Automatically routed to the correct service
memory = client.create_memory(...)  # Automatically uses control plane
event = client.create_event(...)    # Automatically uses data plane
```

## Key Features

### 1. Automatic Routing
The client automatically determines which underlying service (control plane or data plane) handles each operation and routes calls appropriately.

### 2. Lazy Initialization
Boto3 clients are only created when first needed, minimizing resource usage:
```python
# No boto3 clients created yet
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Control plane client created on first control operation
client.create_memory(...)

# Data plane client created on first data operation
client.create_event(...)
```

### 3. No Hardcoded Operations
The client uses dynamic routing with no hardcoded operation lists, ensuring it always works with the latest AWS API updates.

### 4. Full boto3 Compatibility
All boto3 client methods are available through the unified client with identical signatures.

## Usage Examples

### Memory Operations

```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Control plane: Create memory resource
memory = client.create_memory(
    name="my-memory",
    eventExpiryDuration=90,
    memoryStrategies=[{
        "SEMANTIC": {
            "name": "facts",
            "namespaces": ["app/{actorId}/{sessionId}"]
        }
    }]
)

# Data plane: Create events (conversation turns)
event = client.create_event(
    memoryId=memory['memory']['id'],
    actorId="user-123",
    sessionId="session-456",
    payload=[{
        "conversational": {
            "content": {"text": "Hello!"},
            "role": "USER"
        }
    }]
)

# Data plane: Retrieve memory records
records = client.retrieve_memory_records(
    memoryId=memory['memory']['id'],
    namespace="app/user-123/session-456",
    searchCriteria={"searchQuery": "greeting", "topK": 3}
)

# Control plane: Clean up
client.delete_memory(memoryId=memory['memory']['id'])
```

### Code Interpreter Operations

```python
# Control plane: Create code interpreter resource
interpreter = client.create_code_interpreter(
    name="my-interpreter",
    executionRoleArn="arn:aws:iam::123456789012:role/InterpreterRole",
    networkConfiguration={"networkMode": "PUBLIC"}
)

# Data plane: Start session
session = client.start_code_interpreter_session(
    codeInterpreterIdentifier="aws.codeinterpreter.v1"
)

# Data plane: Execute code
result = client.invoke_code_interpreter(
    codeInterpreterIdentifier="aws.codeinterpreter.v1",
    sessionId=session['sessionId'],
    method="execute",
    parameters={"code": "print('Hello, World!')"}
)

# Data plane: Stop session
client.stop_code_interpreter_session(
    codeInterpreterIdentifier="aws.codeinterpreter.v1",
    sessionId=session['sessionId']
)

# Control plane: Clean up
client.delete_code_interpreter(
    codeInterpreterId=interpreter['codeInterpreterId']
)
```

### Browser Operations

```python
# Control plane: Create browser resource
browser = client.create_browser(
    name="my-browser",
    executionRoleArn="arn:aws:iam::123456789012:role/BrowserRole",
    networkConfiguration={"networkMode": "PUBLIC"},
    recording={
        "enabled": True,
        "s3Location": {
            "bucket": "my-recordings",
            "keyPrefix": "sessions/"
        }
    }
)

# Data plane: Start browser session
session = client.start_browser_session(
    browserIdentifier="aws.browser.v1"
)

# Data plane: Automate browser
result = client.invoke_browser(
    browserIdentifier="aws.browser.v1",
    sessionId=session['sessionId'],
    method="navigate",
    parameters={"url": "https://example.com"}
)

# Data plane: Stop session
client.stop_browser_session(
    browserIdentifier="aws.browser.v1",
    sessionId=session['sessionId']
)

# Control plane: Clean up
client.delete_browser(browserId=browser['browserId'])
```

## Advanced Usage

### Checking Which Client Handles an Operation

If you need to know which underlying client handles a specific operation (useful for debugging):

```python
# Get the underlying boto3 client for an operation
control_client = client.get_client_for_operation("create_memory")
print(type(control_client))  # <class 'botocore.client.BedrockAgentCoreControl'>

data_client = client.get_client_for_operation("create_event")
print(type(data_client))  # <class 'botocore.client.BedrockAgentCore'>
```

### Direct Access to Underlying Clients

If you need direct access to the underlying boto3 clients:

```python
# Access control plane client directly
control_plane = client.control_plane_client

# Access data plane client directly
data_plane = client.data_plane_client
```

## Migration from Multiple Clients

If you're currently using separate boto3 clients, migration is simple:

**Before:**
```python
import boto3

control_client = boto3.client("bedrock-agentcore-control", region_name="us-west-2")
data_client = boto3.client("bedrock-agentcore", region_name="us-west-2")

memory = control_client.create_memory(...)
event = data_client.create_event(...)
```

**After:**
```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

memory = client.create_memory(...)  # Same method, no need to pick client
event = client.create_event(...)    # Same method, no need to pick client
```

## Error Handling

The unified client provides helpful error messages when operations are not found:

```python
try:
    client.non_existent_operation()
except AttributeError as e:
    print(e)
    # AttributeError: 'UnifiedBedrockAgentCoreClient' object has no attribute 'non_existent_operation'.
    # Operation 'non_existent_operation' was not found on either the control plane
    # (bedrock-agentcore-control) or data plane (bedrock-agentcore) client.
```

## Performance Considerations

### Lazy Initialization
The unified client uses lazy initialization for boto3 clients:
- Control plane client is only created when you first call a control plane operation
- Data plane client is only created when you first call a data plane operation
- Once created, clients are cached and reused

This means there's **zero performance overhead** if you only use one type of operation.

### Routing Overhead
The routing mechanism uses simple `hasattr` checks:
- First checks control plane client
- If not found, checks data plane client
- The overhead is negligible (microseconds)

## Complete Example

See [examples/unified_client_usage.py](../examples/unified_client_usage.py) for a complete working example demonstrating all features.

## API Reference

### UnifiedBedrockAgentCoreClient

```python
class UnifiedBedrockAgentCoreClient:
    def __init__(self, region_name: Optional[str] = None)
```

#### Parameters
- `region_name` (str, optional): AWS region to use. If not provided, uses the default boto3 session region or falls back to `us-west-2`.

#### Properties
- `region_name` (str): The AWS region being used
- `control_plane_client`: The underlying boto3 client for control plane operations (lazy initialized)
- `data_plane_client`: The underlying boto3 client for data plane operations (lazy initialized)

#### Methods

All boto3 client methods for both `bedrock-agentcore-control` and `bedrock-agentcore` are available as direct methods on the unified client.

**Special method:**
```python
def get_client_for_operation(self, operation_name: str) -> boto3.Client
```
Returns the underlying boto3 client that handles the specified operation.

## Operation Reference

### Control Plane Operations (bedrock-agentcore-control)

**Memory:**
- `create_memory`
- `get_memory`
- `list_memories`
- `update_memory`
- `delete_memory`
- `list_memory_strategies`

**Code Interpreter:**
- `create_code_interpreter`
- `delete_code_interpreter`
- `get_code_interpreter`
- `list_code_interpreters`

**Browser:**
- `create_browser`
- `delete_browser`
- `get_browser`
- `list_browsers`

**Identity:**
- `create_oauth2_credential_provider`
- `create_api_key_credential_provider`
- `delete_credential_provider`
- `get_credential_provider`
- `list_credential_providers`
- `update_credential_provider`
- `create_workload_identity`
- `update_workload_identity`
- `get_workload_identity`
- `delete_workload_identity`
- `list_workload_identities`

### Data Plane Operations (bedrock-agentcore)

**Memory:**
- `create_event`
- `get_event`
- `delete_event`
- `list_events`
- `retrieve_memory_records`
- `get_memory_record`
- `delete_memory_record`
- `list_memory_records`

**Code Interpreter:**
- `start_code_interpreter_session`
- `stop_code_interpreter_session`
- `get_code_interpreter_session`
- `list_code_interpreter_sessions`
- `invoke_code_interpreter`

**Browser:**
- `start_browser_session`
- `stop_browser_session`
- `get_browser_session`
- `list_browser_sessions`
- `update_browser_stream`
- `invoke_browser`

**Runtime:**
- `generate_ws_connection`
- `generate_presigned_url`

**Identity:**
- `get_workload_access_token`
- `get_api_key`

## Frequently Asked Questions

### Q: Does this add any overhead?
**A:** The overhead is negligible (microseconds per call) due to simple attribute checks. Boto3 clients are cached after first use.

### Q: What happens if AWS adds new operations?
**A:** The unified client uses dynamic routing with no hardcoded operation lists, so it automatically supports new operations without any updates.

### Q: Can I still use the underlying boto3 clients directly?
**A:** Yes! You can access them via `client.control_plane_client` and `client.data_plane_client`.

### Q: Does this work with all boto3 features (paginators, waiters, etc.)?
**A:** The unified client currently focuses on direct method calls. For advanced boto3 features, access the underlying clients directly.

### Q: Is this thread-safe?
**A:** Yes, the client uses boto3 clients which are thread-safe for making requests.

## See Also

- [AWS Bedrock AgentCore Control Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html)
- [AWS Bedrock AgentCore Data Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore.html)
- [Complete Usage Example](../examples/unified_client_usage.py)
