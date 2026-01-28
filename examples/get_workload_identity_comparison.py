"""
Comparison: GetWorkloadIdentity with and without UnifiedClient

This example shows the difference between using separate boto3 clients
vs using the unified client for identity operations.
"""

import boto3
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# ============================================================================
# BEFORE: Traditional approach with separate boto3 clients
# ============================================================================

print("=" * 70)
print("BEFORE: Using separate boto3 clients (the hard way)")
print("=" * 70)
print()

# Problem 1: You need to know which service to use
# GetWorkloadIdentity is on the CONTROL plane, but how would you know that?
print("Step 1: Create the correct client")
print("  → You need to know GetWorkloadIdentity is on bedrock-agentcore-control")
control_client = boto3.client("bedrock-agentcore-control", region_name="us-west-2")
print("  ✓ Created: bedrock-agentcore-control client")
print()

# Step 2: Call the operation
print("Step 2: Call GetWorkloadIdentity")
try:
    response = control_client.get_workload_identity(name="my-agent-identity")
    print(f"  ✓ Retrieved identity: {response['name']}")
    print(f"    Status: {response['status']}")
    print(f"    ARN: {response['workloadIdentityArn']}")
except Exception as e:
    print(f"  ⚠ Error (expected if identity doesn't exist): {type(e).__name__}")
print()

# Problem 2: If you need data plane operations, you need ANOTHER client
print("Step 3: Need a token? Create ANOTHER client!")
print("  → GetWorkloadAccessToken is on the DATA plane (bedrock-agentcore)")
data_client = boto3.client("bedrock-agentcore", region_name="us-west-2")
print("  ✓ Created: bedrock-agentcore client")
print()

try:
    token_response = data_client.get_workload_access_token(
        workloadName="my-agent-identity"
    )
    print(f"  ✓ Got access token: {token_response['accessToken'][:20]}...")
except Exception as e:
    print(f"  ⚠ Error (expected): {type(e).__name__}")
print()

print("❌ Problems with this approach:")
print("  • You need to know which service has which operation")
print("  • You need to create and manage multiple boto3 clients")
print("  • Easy to use the wrong client and get confusing errors")
print()

# ============================================================================
# AFTER: Using UnifiedBedrockAgentCoreClient
# ============================================================================

print("=" * 70)
print("AFTER: Using UnifiedBedrockAgentCoreClient (the easy way)")
print("=" * 70)
print()

# Solution: One client for everything!
print("Step 1: Create ONE unified client")
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
print("  ✓ Created: UnifiedBedrockAgentCoreClient")
print()

# Step 2: Just call the operation - routing is automatic
print("Step 2: Call GetWorkloadIdentity (automatically routed)")
try:
    response = client.get_workload_identity(name="my-agent-identity")
    print(f"  ✓ Retrieved identity: {response['name']}")
    print(f"    Status: {response['status']}")
    print(f"    ARN: {response['workloadIdentityArn']}")
    print("  → Automatically routed to control plane ✨")
except Exception as e:
    print(f"  ⚠ Error (expected if identity doesn't exist): {type(e).__name__}")
    print("  → Still automatically routed to the correct service ✨")
print()

# Step 3: Need a token? Use the SAME client!
print("Step 3: Need a token? Use the SAME client!")
try:
    token_response = client.get_workload_access_token(
        workloadName="my-agent-identity"
    )
    print(f"  ✓ Got access token: {token_response['accessToken'][:20]}...")
    print("  → Automatically routed to data plane ✨")
except Exception as e:
    print(f"  ⚠ Error (expected): {type(e).__name__}")
    print("  → Still automatically routed to the correct service ✨")
print()

print("✅ Benefits of unified client:")
print("  • No need to know which service has which operation")
print("  • Single client for ALL operations")
print("  • Automatic routing - just call the method you need!")
print()

# ============================================================================
# COMPLETE WORKFLOW COMPARISON
# ============================================================================

print("=" * 70)
print("COMPLETE WORKFLOW COMPARISON")
print("=" * 70)
print()

print("Traditional Approach (with separate clients):")
print("-" * 70)
print("""
import boto3

# Need to know which service for each operation!
control_client = boto3.client("bedrock-agentcore-control", region="us-west-2")
data_client = boto3.client("bedrock-agentcore", region="us-west-2")

# Create workload identity - use control client
identity = control_client.create_workload_identity(name="my-identity", ...)

# Get workload identity - use control client
details = control_client.get_workload_identity(name="my-identity")

# Get access token - use data client (different client!)
token = data_client.get_workload_access_token(workloadName="my-identity")

# Update identity - back to control client
updated = control_client.update_workload_identity(name="my-identity", ...)
""")
print()

print("Unified Client Approach:")
print("-" * 70)
print("""
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# One client for everything!
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# All operations use the same client - automatic routing!
identity = client.create_workload_identity(name="my-identity", ...)
details = client.get_workload_identity(name="my-identity")
token = client.get_workload_access_token(workloadName="my-identity")
updated = client.update_workload_identity(name="my-identity", ...)

# No need to remember which client to use - just call the method!
""")
print()

# ============================================================================
# REAL-WORLD EXAMPLE
# ============================================================================

print("=" * 70)
print("REAL-WORLD EXAMPLE: Complete Identity Setup")
print("=" * 70)
print()

print("Using UnifiedBedrockAgentCoreClient:")
print()

# Create unified client
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

print("1. Create workload identity")
try:
    identity = client.create_workload_identity(
        name="production-agent",
        allowedResourceOAuth2ReturnUrls=["https://app.example.com/callback"]
    )
    print(f"   ✓ Created: {identity['name']}")
except Exception as e:
    print(f"   ⚠ {type(e).__name__}: Identity may already exist")
print()

print("2. Get workload identity details (GetWorkloadIdentity)")
try:
    details = client.get_workload_identity(name="production-agent")
    print(f"   ✓ Name: {details['name']}")
    print(f"   ✓ Status: {details['status']}")
    print(f"   ✓ ARN: {details['workloadIdentityArn']}")
except Exception as e:
    print(f"   ⚠ {type(e).__name__}")
print()

print("3. List all workload identities")
try:
    all_identities = client.list_workload_identities()
    count = len(all_identities.get('workloadIdentities', []))
    print(f"   ✓ Found {count} workload identities")
except Exception as e:
    print(f"   ⚠ {type(e).__name__}")
print()

print("4. Get access token for agent")
try:
    token = client.get_workload_access_token(
        workloadName="production-agent",
        userId="user-12345"
    )
    print(f"   ✓ Got access token: {token['accessToken'][:15]}...")
except Exception as e:
    print(f"   ⚠ {type(e).__name__}")
print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()
print("✨ With UnifiedBedrockAgentCoreClient:")
print()
print("  • Write cleaner, simpler code")
print("  • Don't worry about control vs data plane")
print("  • Use ONE client for ALL operations")
print("  • Let the client handle the routing automatically")
print()
print("  Traditional:  5+ lines to set up clients")
print("  Unified:      1 line to set up client")
print()
print("  Traditional:  Need to remember which client for each operation")
print("  Unified:      Just call client.<operation_name>(...)")
print()
print("=" * 70)
