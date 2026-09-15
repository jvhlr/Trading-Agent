---
name: debugging
description: Systematic debugging skill for diagnosing and fixing bugs, errors, and unexpected behavior in code across any language. Use this skill when the user shares broken code, an error message, unexpected output, or says their code "doesn't work", "throws an error", "crashes", "gives the wrong answer", or "won't run". Also triggers for tasks like "help me find the bug", "why is this failing?", "fix this error", "my tests are failing", or "I don't understand this stack trace". Use even for partial debugging like explaining what an error message means, or suggesting what to log to narrow down a problem.
---

# Debugging Skill

Debugging is a systematic process, not guesswork. This skill guides structured root-cause analysis and fix delivery for bugs across any language or environment.

---

## Step 1: Gather Information First

Before jumping to conclusions, collect all available evidence:

1. **What is the error?** Exact error message and stack trace (if any)
2. **What was expected?** What should the code do?
3. **What actually happened?** What does it do instead?
4. **When does it happen?** Always? Only in certain conditions? After a recent change?
5. **What has already been tried?** Avoid suggesting things already ruled out
6. **What's the environment?** Language version, OS, framework, browser?

---

## Step 2: Read the Error Message Carefully

Most bugs announce themselves. Train yourself to actually read error messages.

### Anatomy of a Stack Trace
```
TypeError: Cannot read properties of undefined (reading 'name')
    at getUserName (app.js:14:22)       ← Where it broke
    at handleRequest (app.js:8:18)      ← What called it
    at Server.<anonymous> (server.js:5) ← How we got there
```

Reading order: Start at the **top** (the actual error), then follow the stack **downward** to find your own code (ignore library internals).

### Common Error Types

| Error | Typical Cause |
|---|---|
| `TypeError: X is not a function` | Calling something that isn't a function; typo in method name |
| `TypeError: Cannot read ... of undefined/null` | Accessing property of a value that doesn't exist yet |
| `ReferenceError: X is not defined` | Typo in variable name; variable used before declaration |
| `SyntaxError` | Mismatched brackets, missing commas, bad syntax |
| `ImportError / ModuleNotFoundError` | Package not installed; wrong import path |
| `IndexError / KeyError` | Accessing list/dict with invalid index or missing key |
| `NullPointerException` (Java) | Object reference is null; not initialized |
| `SEGFAULT` (C/C++) | Memory access violation; array out of bounds; null pointer |
| `404 Not Found` (HTTP) | Wrong URL; route not defined; resource doesn't exist |
| `500 Internal Server Error` | Unhandled exception on the server — check server logs |
| `CORS error` | Missing `Access-Control-Allow-Origin` header on server |

---

## Step 3: Debugging Strategies

### 1. Rubber Duck Debugging
Explain the code out loud (or in writing) line by line. Bugs often surface when you force yourself to articulate what each line does.

### 2. Divide and Conquer
Isolate the problem. Remove half the code (or comment it out). Does the bug still happen? Narrow down until you find the exact line.

### 3. Add Logging (Strategic Print Statements)
```js
console.log('Input received:', JSON.stringify(input));
console.log('Before transform:', data);
console.log('After transform:', result);
```
Log: inputs, outputs, intermediate states, types (`typeof x`, `Array.isArray(x)`).

### 4. Check Assumptions
Ask: "What do I think this variable contains here?" Then verify:
```python
print(type(data), data)  # Python
```
```js
console.log(typeof data, data);  // JavaScript
```

### 5. Check the Obvious First
- Is the file saved?
- Is the right file/version being run?
- Did you restart the server/process after making changes?
- Is the variable actually the type you think it is?
- Is the function being called with the arguments you think?

### 6. Git Bisect (for regressions)
If something worked before and doesn't now, use `git bisect` to find the exact commit that introduced the bug.

---

## Step 4: Language-Specific Tips

### JavaScript / TypeScript
- `undefined` vs `null` are different — both are falsy
- `==` does type coercion; use `===` always
- Async bugs: Forgetting `await`; using `.then()` and `async/await` mixed incorrectly
- `this` in callbacks is often wrong — use arrow functions or `.bind(this)`
- Array methods like `.map()`, `.filter()` return new arrays — they don't mutate

```js
// Common async mistake
async function getUser(id) {
  const user = fetchUser(id); // ← forgot await! user is a Promise, not a User
  console.log(user.name);    // TypeError
}
```

### Python
- Indentation errors are syntax errors — be consistent with spaces vs tabs
- Mutable default arguments are a classic trap:
```python
# Bug: list is shared across all calls
def add_item(item, lst=[]):
    lst.append(item)
    return lst

# Fix
def add_item(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

### Java
- `NullPointerException`: Object was never initialized or a method returned `null`
- `==` compares references, not value for objects — use `.equals()`
- Off-by-one errors in loops: `i < arr.length` vs `i <= arr.length`

### CSS
- Use browser DevTools → Inspect element to see computed styles
- Check if a more specific selector is overriding your rule
- `z-index` only works on positioned elements (`position: relative/absolute/fixed`)
- Flexbox/Grid parent vs. child properties — many people apply them to the wrong element

---

## Step 5: Using Debugger Tools

### Browser DevTools (JS)
- Set **breakpoints** by clicking line numbers in Sources tab
- Use **Watch** to monitor variable values
- **Step over** (F10) executes next line; **Step into** (F11) enters function calls
- **Console**: Run expressions in the current scope while paused

### Python (pdb)
```python
import pdb; pdb.set_trace()  # Drops into interactive debugger
# Or in Python 3.7+:
breakpoint()
```

### Node.js
```bash
node --inspect app.js
# Then open chrome://inspect in Chrome
```

---

## Step 6: Fix Delivery

When providing a fix:
1. **Identify the root cause** — not just the symptom
2. **Explain why it broke** — so the pattern is understood
3. **Show the fix** — with before/after if helpful
4. **Note any related risks** — could this same bug exist elsewhere?

---

## Step 7: Prevention

- Write tests for the bug so it can't regress (`describe('when X', () => { it('should Y', ...) })`)
- Add input validation at boundaries (API, user input, file reads)
- Use TypeScript or type hints to catch type errors at compile time
- Use linters (`eslint`, `pylint`, `rubocop`) to catch common mistakes automatically
- Review code before merging — a fresh pair of eyes catches what yours misses

---

## Output Format

When debugging:
1. State what you believe the root cause is
2. Point to the exact line/expression causing the issue
3. Explain why it's wrong in plain terms
4. Provide the corrected code
5. Suggest how to test or verify the fix
