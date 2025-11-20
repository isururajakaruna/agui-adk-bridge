# Frontend Enhancement Plan

## Current Status

### ✅ What's Working
- Direct protocol translation (no errors!)
- Text messages display between tool calls
- Some tool calls show up (3 visible in UI)
- Tool call modals open with parameters and results

### ❌ What's Missing
1. **Only 3/5 tool calls visible** in frontend
   - Visible: `transfer_to_agent` (1st), `get_market_summary`
   - Missing: `transfer_to_agent` (2nd), `load_client_profile`, `match_products_to_market_view`

2. **No thinking steps displayed** in UI
   - Backend detects thinking (3 events with ~3000 tokens)
   - Events emitted: `THINKING_START`, `THINKING_END`
   - Not rendering in frontend

3. **No token counts** for thinking
   - We log `thoughts_token_count` in bridge
   - Not passed to frontend in events

4. **Empty tool results** for some tools
   - `transfer_to_agent` shows `{"result": null}` (expected, but looks empty)
   - Should show more context or message

---

## Investigation Needed

### 🔍 Why are only 3/5 tool calls visible?

**Hypothesis 1**: Frontend filtering/grouping
- Maybe CopilotKit only shows unique tool names?
- We have 2x `transfer_to_agent` calls - maybe it only shows one?

**Hypothesis 2**: Event timing issue
- Tool calls happening too fast?
- Events getting lost in stream?

**Hypothesis 3**: Frontend rendering limit
- UI only shows first N tools?

**Action**: Check `agent_ui` tool rendering logic

---

### 🧠 Why isn't thinking displayed?

**Hypothesis 1**: Missing UI component
- CopilotKit might not have built-in thinking UI
- Need custom renderer for `THINKING_START`/`THINKING_END`

**Hypothesis 2**: Event structure issue
- Maybe thinking events need additional fields?
- Check if `title` field is required

**Action**: Review CopilotKit thinking support & add custom renderer

---

### 📊 How to show token counts?

**Current**: 
```python
logger.info(f"🧠 Thinking detected (thoughts_token_count: {count})")
```

**Needed**:
```python
yield self._format_sse({
    "type": "THINKING_START",
    "title": "Reasoning",
    "tokenCount": thoughts_token_count  # Add this!
})
```

**Action**: Pass token metadata in thinking events

---

## Enhancement Plan

### Phase 1: Debug Missing Tool Calls (Priority 1)

**1.1 Verify Events Are Being Sent**
- [x] Check `events_*.log` - All 5 tool calls are logged ✅
- [ ] Check browser Network tab - Are all events received?
- [ ] Check browser Console - Any JavaScript errors?

**1.2 Check Frontend Tool Rendering**
- File: `apps/agent_ui/src/components/tools/GenericToolCard.tsx`
- Check if there's any filtering logic
- Verify `useCopilotAction` handles all tool calls

**1.3 Add Debug Logging**
- Add console.log in `GenericToolCard` to see all tools received
- Log tool call IDs and names

**Expected Fix**: 
- If events are sent but not rendered: Update frontend rendering logic
- If events are not sent: Fix protocol translator

---

### Phase 2: Display Thinking Steps (Priority 1)

**2.1 Update Protocol Translator**
```python
# In protocol_translator.py, _handle_text_message()

if has_thinking:
    thoughts_token_count = event.get('usage_metadata', {}).get('thoughts_token_count', 0)
    
    yield self._format_sse({
        "type": "THINKING_START",
        "title": "Extended Thinking",
        "metadata": {
            "tokenCount": thoughts_token_count,
            "model": event.get('model_version', 'unknown')
        }
    })
```

**2.2 Add Thinking UI in Frontend**
File: `apps/agent_ui/src/app/page.tsx` or create `components/ThinkingDisplay.tsx`

```typescript
// Add thinking state tracking
const [isThinking, setIsThinking] = useState(false);
const [thinkingTokens, setThinkingTokens] = useState(0);

// Listen for thinking events
useEffect(() => {
  // Subscribe to AG-UI Protocol events
  // On THINKING_START: setIsThinking(true), setThinkingTokens(count)
  // On THINKING_END: setIsThinking(false)
}, []);

// Render thinking indicator
{isThinking && (
  <div className="thinking-indicator">
    🧠 Thinking... ({thinkingTokens} tokens)
  </div>
)}
```

**2.3 Style Thinking Display**
- Show thinking as a distinct visual element
- Display token count
- Animate while thinking is active
- Collapse when thinking ends

---

### Phase 3: Improve Tool Result Display (Priority 2)

**3.1 Handle `transfer_to_agent` Results Better**

Currently: `{"result": null}` looks empty

Improve:
```json
{
  "agent_name": "research_agent",
  "status": "transferred",
  "message": "Successfully transferred to research_agent"
}
```

**Option A**: Update Agent Engine to return better results
**Option B**: Enhance display in `GenericToolCard` to show context

```typescript
// In GenericToolCard.tsx
if (toolName === 'transfer_to_agent') {
  const agentName = JSON.parse(args).agent_name;
  return (
    <div>
      <p>✅ Transferred to: <strong>{agentName}</strong></p>
      <p className="text-sm text-gray-500">
        Agent handoff successful
      </p>
    </div>
  );
}
```

**3.2 Add Tool Call Duration**
- Track `TOOL_CALL_START` timestamp
- Show duration on `TOOL_CALL_RESULT`
- Display in modal: "Completed in 1.2s"

---

### Phase 4: Enhanced Tool Call Visualization (Priority 3)

**4.1 Show All Tool Calls in Sequence**
- Timeline view showing all 5 tool calls
- Visual indication of agent transfers
- Collapsible details for each tool

**4.2 Add Tool Call Statistics**
- Total tool calls: 5
- Total thinking tokens: ~3000
- Total duration: 39s
- Show at end of conversation

---

## Implementation Steps

### Step 1: Verify Event Delivery (30 min)
```bash
# In browser console while chatting:
# Monitor Network tab → EventStream → Response
# Look for all TOOL_CALL_START events
# Count how many are received vs sent
```

**Expected**: See 5 TOOL_CALL_START events
**If missing**: Fix protocol translator
**If received**: Fix frontend rendering

---

### Step 2: Update Protocol Translator (1 hour)

**File**: `agui-dojo-adk-bridge/src/protocol_translator.py`

Changes:
1. Add `tokenCount` to `THINKING_START` events
2. Add `model` info to thinking metadata
3. Improve `transfer_to_agent` result formatting
4. Add event sequence logging

```python
async def _handle_text_message(self, part, event):
    """Handle text with enhanced thinking metadata."""
    if has_thinking:
        usage = event.get('usage_metadata', {})
        yield self._format_sse({
            "type": "THINKING_START",
            "title": "Extended Thinking",
            "metadata": {
                "thoughtsTokenCount": usage.get('thoughts_token_count', 0),
                "model": event.get('model_version', 'unknown'),
                "timestamp": event.get('timestamp')
            }
        })
```

---

### Step 3: Add Thinking UI (2 hours)

**File**: `apps/agent_ui/src/components/ThinkingIndicator.tsx` (new)

```typescript
import { useState, useEffect } from 'react';
import { Brain, Sparkles } from 'lucide-react';

export function ThinkingIndicator({ tokenCount, isActive }) {
  return (
    <div className={`thinking-card ${isActive ? 'active' : 'completed'}`}>
      <div className="flex items-center gap-2">
        <Brain className="animate-pulse" />
        <span>Extended Thinking</span>
        {tokenCount > 0 && (
          <span className="badge">{tokenCount} tokens</span>
        )}
      </div>
    </div>
  );
}
```

**Integration**: Add event listener in main chat component

---

### Step 4: Debug Tool Call Display (1 hour)

**File**: `apps/agent_ui/src/components/tools/GenericToolCard.tsx`

Add debug logging:
```typescript
useEffect(() => {
  console.log('[GenericToolCard] Rendered:', {
    toolName: tool.name,
    toolId: tool.id,
    status: tool.status,
    timestamp: Date.now()
  });
}, [tool]);
```

Check browser console to see if all 5 tools are rendered.

---

### Step 5: Test & Iterate (1 hour)

1. Run the same query: "Generate complete pitch deck for CLI_SG_001"
2. Check browser console for debug logs
3. Verify all 5 tool calls appear
4. Verify thinking indicators show up
5. Verify token counts are displayed

---

## Expected Outcome

### Before:
- 3/5 tool calls visible ❌
- No thinking display ❌
- No token counts ❌
- Empty tool results ❌

### After:
- 5/5 tool calls visible ✅
- Thinking indicators with animation ✅
- Token counts displayed ✅
- Better tool result formatting ✅
- Timeline view of all tool calls ✅

---

## Quick Wins (Start Here)

### 1. Add Debug Logging (5 min)
In `GenericToolCard.tsx`, add console.log to see all tools

### 2. Check Browser Network Tab (5 min)
Verify all 5 TOOL_CALL_START events are received

### 3. Add Token Count to Thinking (15 min)
Update `protocol_translator.py` to include metadata

### 4. Create Thinking Component (30 min)
Build basic `ThinkingIndicator.tsx`

---

## Open Questions

1. **Does CopilotKit support thinking events natively?**
   - Check CopilotKit docs for `THINKING_START` handling
   - May need custom event handlers

2. **Why are tool calls missing?**
   - Events sent but not rendered?
   - Frontend filtering?
   - CopilotKit limitation?

3. **How to display thinking best?**
   - Inline with messages?
   - Separate panel?
   - Collapsible cards?

4. **Should we show thinking content?**
   - Currently only showing token count
   - `thought_signature` is binary (not human-readable)
   - Maybe show "Reasoning for X seconds" instead?

---

## Next Action

**Let's start with Quick Win #2**: Check browser Network tab to see if all 5 tool call events are being received. This will tell us if the issue is:
- Backend (missing events) → Fix protocol translator
- Frontend (events received but not displayed) → Fix GenericToolCard

Then we can proceed with the appropriate fix!

