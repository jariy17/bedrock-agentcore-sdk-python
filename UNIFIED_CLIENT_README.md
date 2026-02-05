# UnifiedBedrockAgentCoreClient

## What is this?

A thin wrapper that lets you call **any** AWS Bedrock AgentCore operation without worrying about which service to use.

## The Problem

AWS Bedrock AgentCore has two services:
- `bedrock-agentcore-control` - Resource management (create/delete/update resources)
- `bedrock-agentcore` - Runtime operations (sessions, events, tokens)

You used to need:
```python
import boto3

# Two clients, and you need to know which one for each operation
control = boto3.client("bedrock-agentcore-control", region_name="us-west-2")
data = boto3.client("bedrock-agentcore", region_name="us-west-2")

# Which client do I use for GetWorkloadIdentity? 🤔
identity = control.get_workload_identity(...)  # Correct!

# Which client for getting a token? 🤔
token = data.get_workload_access_token(...)  # Different client!
```

## The Solution

```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# One client for everything!
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Just call the operations - automatic routing!
identity = client.get_workload_identity(...)  # ✨ Routed to control plane
token = client.get_workload_access_token(...)  # ✨ Routed to data plane
```

## Quick Start

```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# Initialize once
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Use for any operation - the client handles routing
memory = client.create_memory(name="my-memory", ...)
event = client.create_event(memoryId="...", ...)
interpreter = client.create_code_interpreter(name="my-interp", ...)
session = client.start_code_interpreter_session(...)
identity = client.get_workload_identity(name="my-identity")
```

## Examples

### GetWorkloadIdentity Example

```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Create workload identity
identity = client.create_workload_identity(
    name="my-agent",
    allowedResourceOAuth2ReturnUrls=["https://app.example.com/callback"]
)

# Get workload identity (GetWorkloadIdentity command)
details = client.get_workload_identity(name="my-agent")
print(f"Identity: {details['name']}")
print(f"Status: {details['status']}")
print(f"ARN: {details['workloadIdentityArn']}")

# Get access token (different service, same client!)
token = client.get_workload_access_token(
    workloadName="my-agent",
    userId="user-123"
)
print(f"Token: {token['accessToken']}")
```

### Memory Operations

```python
# Create memory resource (control plane)
memory = client.create_memory(
    name="chat-memory",
    eventExpiryDuration=90,
    memoryStrategies=[{
        "SEMANTIC": {
            "name": "facts",
            "namespaces": ["app/{actorId}/{sessionId}"]
        }
    }]
)

# Create event (data plane)
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

# Search memories (data plane)
results = client.retrieve_memory_records(
    memoryId=memory['memory']['id'],
    namespace="app/user-123/session-456",
    searchCriteria={"searchQuery": "greeting", "topK": 5}
)
```

### Code Interpreter Operations

```python
# Create interpreter (control plane)
interpreter = client.create_code_interpreter(
    name="my-interpreter",
    executionRoleArn="arn:aws:iam::123456789012:role/InterpreterRole",
    networkConfiguration={"networkMode": "PUBLIC"}
)

# Start session (data plane)
session = client.start_code_interpreter_session(
    codeInterpreterIdentifier="aws.codeinterpreter.v1"
)

# Execute code (data plane)
result = client.invoke_code_interpreter(
    codeInterpreterIdentifier="aws.codeinterpreter.v1",
    sessionId=session['sessionId'],
    method="execute",
    parameters={"code": "print('Hello!')"}
)
```

## How It Works

The unified client:
1. Creates boto3 clients **only when needed** (lazy initialization)
2. Checks control plane client first when you call a method
3. Falls back to data plane client if not found on control plane
4. Raises helpful error if operation doesn't exist on either

**No hardcoded operation lists** - works automatically with any new AWS operations!

## All Supported Operations

The unified client supports **all operations** from both services:

**Control Plane (bedrock-agentcore-control):**
- Memory: `create_memory`, `get_memory`, `list_memories`, `update_memory`, `delete_memory`
- Code Interpreter: `create_code_interpreter`, `get_code_interpreter`, `list_code_interpreters`, `delete_code_interpreter`
- Browser: `create_browser`, `get_browser`, `list_browsers`, `delete_browser`
- Identity: `create_workload_identity`, `get_workload_identity`, `list_workload_identities`, `update_workload_identity`, `delete_workload_identity`
- Credentials: `create_oauth2_credential_provider`, `create_api_key_credential_provider`, `get_credential_provider`, `list_credential_providers`, `delete_credential_provider`

**Data Plane (bedrock-agentcore):**
- Memory: `create_event`, `get_event`, `list_events`, `delete_event`, `retrieve_memory_records`, `list_memory_records`
- Code Interpreter: `start_code_interpreter_session`, `stop_code_interpreter_session`, `invoke_code_interpreter`
- Browser: `start_browser_session`, `stop_browser_session`, `invoke_browser`, `update_browser_stream`
- Identity: `get_workload_access_token`, `get_api_key`

## More Examples

See the `examples/` directory:
- [`unified_client_quickstart.py`](examples/unified_client_quickstart.py) - Simplest possible example
- [`unified_client_usage.py`](examples/unified_client_usage.py) - Complete usage guide
- [`unified_client_identity_example.py`](examples/unified_client_identity_example.py) - Identity operations in detail
- [`get_workload_identity_comparison.py`](examples/get_workload_identity_comparison.py) - Before/after comparison

## Documentation

See [`docs/unified_client.md`](docs/unified_client.md) for complete documentation including:
- Architecture details
- Migration guide
- Advanced usage
- FAQ

## Benefits

✅ **Simpler code** - One client instead of two
✅ **Less to remember** - Don't need to know which service has which operation
✅ **Automatic routing** - Client figures out where to send each call
✅ **Lazy initialization** - Only creates clients when needed
✅ **Future-proof** - No hardcoded lists, works with new AWS operations automatically
✅ **Backward compatible** - Works exactly like boto3 clients

## Installation

The unified client is included in the bedrock-agentcore SDK:

```bash
pip install bedrock-agentcore
```

Then import and use:

```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
```

## Questions?

**Q: Does this add overhead?**
A: Negligible (microseconds) - just simple attribute checks. Clients are cached after creation.

**Q: Can I still use the old boto3 clients?**
A: Yes! The unified client doesn't replace them, it just makes them easier to use.

**Q: What if AWS adds new operations?**
A: They'll work automatically - no hardcoded operation lists means no updates needed.

**Q: Does this work with all boto3 features?**
A: The unified client currently focuses on direct method calls. For advanced features (paginators, waiters), access the underlying clients via `client.control_plane_client` and `client.data_plane_client`.

## Summary

**Traditional approach:**
```python
control = boto3.client("bedrock-agentcore-control", region="us-west-2")
data = boto3.client("bedrock-agentcore", region="us-west-2")

memory = control.create_memory(...)    # Which client? 🤔
event = data.create_event(...)         # Which client? 🤔
identity = control.get_workload_identity(...)  # Which client? 🤔
```

**Unified approach:**
```python
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

memory = client.create_memory(...)     # ✨ Automatic routing!
event = client.create_event(...)       # ✨ Automatic routing!
identity = client.get_workload_identity(...)  # ✨ Automatic routing!
```

**That's it! One client, automatic routing, simpler code.** 🎉
