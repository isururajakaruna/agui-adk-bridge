# ACTIVITY_SNAPSHOT Event Flow Analysis

## Summary

**Result**: `ACTIVITY_SNAPSHOT` events are successfully sent by the bridge AND received by Next.js, but **filtered out by CopilotKit's GraphQL layer** before reaching the browser.

---

## Event Flow Comparison

### 1️⃣ Bridge Sent (Python)

From `/agui-dojo-adk-bridge/logs/events_20251120_213949.log`:

```
✅ Thinking Start (1): thinking-98a2a718-433a-4450-9c28-19a33c86ef60-1763646224938
✅ Thinking Complete (1): thinking-98a2a718-433a-4450-9c28-19a33c86ef60-complete-1763646224941
✅ Thinking Start (2): thinking-98a2a718-433a-4450-9c28-19a33c86ef60-1763646237215
✅ Thinking Complete (2): thinking-98a2a718-433a-4450-9c28-19a33c86ef60-complete-1763646237216
✅ Session Stats: session-stats-98a2a718-433a-4450-9c28-19a33c86ef60-be7128cc-60eb-4f2f-8e56-b870d2213d7d
```

**Total ACTIVITY_SNAPSHOT events sent: 5**

---

### 2️⃣ Next.js Received (via @ag-ui/client)

From `/apps/agent_ui/logs/bridge-events-2025-11-20T13-43-38.log`:

#### Line 13-14: Thinking Start (1)
```json
{
  "type": "ACTIVITY_SNAPSHOT",
  "messageId": "thinking-98a2a718-433a-4450-9c28-19a33c86ef60-1763646224938",
  "activityType": "THINKING",
  "content": {
    "status": "in_progress",
    "thoughtsTokenCount": 183,
    "totalTokenCount": 3114,
    "candidatesTokenCount": 103,
    "promptTokenCount": 2828,
    "model": "gemini-2.5-flash"
  },
  "replace": true
}
```

#### Line 25-26: Thinking Complete (1)
```json
{
  "type": "ACTIVITY_SNAPSHOT",
  "messageId": "thinking-98a2a718-433a-4450-9c28-19a33c86ef60-complete-1763646224941",
  "activityType": "THINKING",
  "content": {"status": "completed"},
  "replace": false
}
```

#### Line 52-53: Thinking Start (2)
```json
{
  "type": "ACTIVITY_SNAPSHOT",
  "messageId": "thinking-98a2a718-433a-4450-9c28-19a33c86ef60-1763646237215",
  "activityType": "THINKING",
  "content": {
    "status": "in_progress",
    "thoughtsTokenCount": 1227,
    "totalTokenCount": 5088,
    "candidatesTokenCount": 462,
    "promptTokenCount": 3399,
    "model": "gemini-2.5-flash"
  },
  "replace": true
}
```

#### Line 64-65: Thinking Complete (2)
```json
{
  "type": "ACTIVITY_SNAPSHOT",
  "messageId": "thinking-98a2a718-433a-4450-9c28-19a33c86ef60-complete-1763646237216",
  "activityType": "THINKING",
  "content": {"status": "completed"},
  "replace": false
}
```

#### Line 67-68: Session Stats
```json
{
  "type": "ACTIVITY_SNAPSHOT",
  "messageId": "session-stats-98a2a718-433a-4450-9c28-19a33c86ef60-be7128cc-60eb-4f2f-8e56-b870d2213d7d",
  "activityType": "SESSION_STATS",
  "content": {
    "totalThinkingTokens": 1410,
    "totalToolCalls": 2,
    "durationSeconds": 18.83,
    "threadId": "98a2a718-433a-4450-9c28-19a33c86ef60",
    "runId": "be7128cc-60eb-4f2f-8e56-b870d2213d7d"
  },
  "replace": true
}
```

**Total ACTIVITY_SNAPSHOT events received by Next.js: 5** ✅

---

### 3️⃣ Browser Received (After CopilotKit GraphQL)

From previous browser network log (`/api/copilotkit` response):

```
❌ NO ACTIVITY_SNAPSHOT EVENTS FOUND
```

The browser only received:
- `TEXT_MESSAGE` events (text content)
- `ACTION_EXECUTION` events (tool calls)
- `RESULT_MESSAGE` events (tool results)

**Total ACTIVITY_SNAPSHOT events received by browser: 0** ❌

---

## Conclusion

### ✅ What Works
1. **Python Bridge → SSE**: Bridge correctly emits `ACTIVITY_SNAPSHOT` events via SSE
2. **@ag-ui/client → Next.js**: `HttpAgent` properly parses and passes through `ACTIVITY_SNAPSHOT` events
3. **Next.js Backend**: All events are successfully logged before being passed to CopilotKit

### ❌ What Doesn't Work
**CopilotKit's GraphQL Layer**: Filters out `ACTIVITY_SNAPSHOT` events before they reach the browser

### Why CopilotKit Filters These Events

CopilotKit uses an internal GraphQL schema to validate and serialize events. Only events with corresponding GraphQL type definitions are allowed through. The `ACTIVITY_SNAPSHOT` event type (while part of the AG-UI Protocol spec) **does not have a GraphQL type definition** in CopilotKit's runtime.

From CopilotKit's architecture:
```
Next.js Backend (HttpAgent.run())
  ↓ (Observable<Event>)
CopilotKit Runtime
  ↓ (GraphQL Validation)
GraphQL Schema (filters unknown types)
  ↓ (Serialized Events)
Browser
```

---

## Options to Fix

### Option 1: Use TEXT_MESSAGE Events for Thinking ⭐ RECOMMENDED
Convert thinking steps to standard `TEXT_MESSAGE` events with special formatting:

```json
{
  "type": "TEXT_MESSAGE_START",
  "messageId": "thinking-...",
  "role": "assistant"
}
{
  "type": "TEXT_MESSAGE_CONTENT",
  "messageId": "thinking-...",
  "delta": "🧠 Thinking (183 thoughts tokens)...\n\nAnalyzing client profile..."
}
{
  "type": "TEXT_MESSAGE_END",
  "messageId": "thinking-..."
}
```

**Pros:**
- Works with CopilotKit's existing GraphQL schema
- Displays as regular chat bubbles (looks nice!)
- Can be styled differently with CSS

**Cons:**
- Not semantically correct (thinking isn't a "text message")
- Can't easily collapse/expand

### Option 2: Extend CopilotKit's GraphQL Schema
Add `ACTIVITY_SNAPSHOT` type definitions to CopilotKit's runtime.

**Pros:**
- Proper semantic representation
- Structured data

**Cons:**
- Requires modifying CopilotKit's source code
- May break with CopilotKit updates
- Complex implementation

### Option 3: Separate WebSocket Connection for Metadata
Keep the current hybrid approach but improve it.

**Pros:**
- Clean separation of concerns
- Full control over metadata format

**Cons:**
- Extra HTTP requests (polling overhead)
- Complexity

---

## Recommendation

**Go with Option 1** (TEXT_MESSAGE events):
1. Simple and reliable
2. Works with existing CopilotKit infrastructure
3. Actually provides a good UX (thinking as chat bubbles)
4. Can be implemented in 5 minutes

Would you like me to implement this?

