# CUSTOM Events Implementation

## 🎯 Goal
Send thinking steps and token counts to the frontend using AG-UI Protocol CUSTOM events to see if CopilotKit passes them through (unlike THINKING_START/END which got filtered).

## ✅ What We Changed

### Updated: `src/protocol_translator.py`

#### 1. Added Session Tracking
```python
class AGUIProtocolTranslator:
    def __init__(self):
        # ... existing fields
        
        # NEW: Track session statistics
        self.total_thinking_tokens = 0
        self.total_tool_calls = 0
        self.session_start_time: Optional[float] = None
```

#### 2. Thinking Events as CUSTOM
**Before:**
```python
yield {
    "type": "THINKING_START",
    "title": "Reasoning"
}
```

**After:**
```python
yield {
    "type": "CUSTOM",
    "name": "thinking",
    "value": {
        "status": "start",
        "thoughtsTokenCount": 132,
        "totalTokenCount": 4074,
        "candidatesTokenCount": 44,
        "promptTokenCount": 4030,
        "model": "gemini-2.5-flash"
    }
}
```

#### 3. Tool Call Tracking
```python
async def _handle_function_call(self, part):
    # NEW: Track tool calls
    self.total_tool_calls += 1
    
    # ... rest of function
```

#### 4. Session Statistics at End
**NEW event sent before RUN_FINISHED:**
```python
yield {
    "type": "CUSTOM",
    "name": "session_stats",
    "value": {
        "totalThinkingTokens": 3000,
        "totalToolCalls": 5,
        "durationSeconds": 38.5,
        "threadId": "...",
        "runId": "..."
    }
}
```

---

## 🧪 Testing Plan

### Step 1: Restart Bridge
```bash
cd agui-dojo-adk-bridge
./run_direct.sh
```

### Step 2: Send Same Query
```
"Generate complete pitch deck for CLI_SG_001 singapore conservative fund"
```

### Step 3: Check Browser Network Tab
Look for in the GraphQL response:
- `__typename: "CustomMessageOutput"` or similar
- Event with `name: "thinking"`
- Event with `name: "session_stats"`

### Step 4: Check Browser Console
Add this to `apps/agent_ui/src/app/page.tsx`:
```typescript
useEffect(() => {
  console.log('[Messages]', messages.map(m => ({
    type: m.__typename,
    ...m
  })));
}, [messages]);
```

---

## 📊 Expected Results

### If CopilotKit Passes CUSTOM Events:
✅ Browser network log will show:
```json
{
  "__typename": "CustomMessageOutput",
  "name": "thinking",
  "value": {
    "status": "start",
    "thoughtsTokenCount": 132,
    ...
  }
}
```

### If CopilotKit Filters CUSTOM Events:
❌ No custom events in browser
❌ Back to square one
❌ Need Option B (direct SSE connection)

---

## 🔍 What to Look For

### In Browser Network Tab:
1. **Search for**: `"CUSTOM"` or `"thinking"` or `"session_stats"`
2. **Count**: Should see 3 thinking events + 1 session_stats
3. **Structure**: Check if `value` field contains our data

### In Bridge Logs:
```bash
tail -f logs/events_*.log | grep "CUSTOM\|session_stats\|Thinking detected"
```

Should see:
- `🧠 Thinking detected (thoughts_token_count: 132)`
- `📊 Session stats - Thinking tokens: 3000, Tool calls: 5, Duration: 38s`

---

## 📋 CUSTOM Events Being Sent

| Event Name | Status | Data Included |
|------------|--------|---------------|
| `thinking` | start | thoughtsTokenCount, totalTokenCount, candidatesTokenCount, promptTokenCount, model |
| `thinking` | end | (just status) |
| `session_stats` | end of run | totalThinkingTokens, totalToolCalls, durationSeconds |

---

## 🎯 Next Steps

### If CUSTOM Events Work ✅
1. Update `apps/agent_ui` to listen for CUSTOM events
2. Create `ThinkingIndicator` component
3. Display session stats at end
4. Show real-time token counts

### If CUSTOM Events Don't Work ❌
**Plan B**: Direct SSE Connection
- Add second EventSource connection to `/chat`
- Bypass CopilotKit's GraphQL layer
- Listen directly to AG-UI Protocol SSE stream
- Extract thinking and token data

---

## 🚀 Frontend Integration (If CUSTOM Events Work)

### 1. Listen for CUSTOM Events
```typescript
// apps/agent_ui/src/hooks/useCustomEvents.ts
export function useCustomEvents() {
  const [thinkingEvents, setThinkingEvents] = useState([]);
  const [sessionStats, setSessionStats] = useState(null);
  
  // Subscribe to CopilotKit messages
  useEffect(() => {
    // Check if messages contain CustomMessageOutput
    const customMessages = messages.filter(
      m => m.__typename === 'CustomMessageOutput'
    );
    
    customMessages.forEach(msg => {
      if (msg.name === 'thinking') {
        if (msg.value.status === 'start') {
          setThinkingEvents(prev => [...prev, msg.value]);
        }
      }
      
      if (msg.name === 'session_stats') {
        setSessionStats(msg.value);
      }
    });
  }, [messages]);
  
  return { thinkingEvents, sessionStats };
}
```

### 2. Display Thinking
```typescript
{thinkingEvents.map((thinking, i) => (
  <div key={i} className="thinking-badge">
    🧠 Extended Thinking ({thinking.thoughtsTokenCount} tokens)
  </div>
))}
```

### 3. Display Session Stats
```typescript
{sessionStats && (
  <div className="session-stats">
    <p>💡 Total Thinking: {sessionStats.totalThinkingTokens} tokens</p>
    <p>🔧 Tool Calls: {sessionStats.totalToolCalls}</p>
    <p>⏱️ Duration: {sessionStats.durationSeconds}s</p>
  </div>
)}
```

---

## 📝 Test Script

Run this after starting the bridge:

```bash
# Terminal 1: Bridge logs
cd agui-dojo-adk-bridge
./run_direct.sh

# Terminal 2: Watch for CUSTOM events
cd agui-dojo-adk-bridge
tail -f logs/events_*.log | grep -E "CUSTOM|thinking|session_stats|📊"

# Terminal 3: Agent UI
cd apps/agent_ui
npm run dev

# Browser: Open DevTools → Network → Filter: copilotkit
# Send query and check for CUSTOM events
```

---

## ✅ Success Criteria

1. ✅ Bridge sends CUSTOM events (check logs)
2. ✅ Browser receives CUSTOM events (check network)
3. ✅ Frontend can access CUSTOM events (check console)
4. ✅ UI displays thinking indicators
5. ✅ UI shows session statistics

If all 5 pass: **Mission accomplished!** 🎉
If any fail: **Implement Plan B** (direct SSE)

