# Immediate Test Steps - Script Loading Issue

## Current Issue
Console shows: "BrowserFingerprint class NOT loaded"

## What I Just Fixed
1. Added cache-busting parameters to script tags (`?v=timestamp`)
2. Added explicit `type="text/javascript"` to script tags
3. Added detailed console logging to track script loading
4. Added error handlers for failed script loads
5. Added fetch test to verify script content

## Test Now

### Step 1: Hard Refresh Browser
**IMPORTANT**: Clear cache first!

**Chrome/Edge/Firefox:**
- Press: `Ctrl + Shift + Delete`
- Select: "Cached images and files"
- Click: "Clear data"

OR just do a hard refresh:
- Press: `Ctrl + Shift + R` (or `Cmd + Shift + R` on Mac)

### Step 2: Open Debug Page
```
http://localhost:8000/debug-audio/
```

### Step 3: Check Browser Console
Press `F12` to open DevTools, then check Console tab.

**You should now see:**
```
Loading fingerprint.js from: /static/reader/js/fingerprint.js
Loading sermon_player.js from: /static/reader/js/sermon_player.js
Scripts loaded. BrowserFingerprint available: true
```

**If you still see `false`:**
```
BrowserFingerprint class failed to load!
Attempting to fetch script directly...
Script content length: 5006 First 100 chars: class BrowserFingerprint {...
```

This will tell us if the file is accessible but not executing.

### Step 4: Check Network Tab
In DevTools:
1. Go to "Network" tab
2. Refresh page (F5)
3. Look for `fingerprint.js` in the list
4. Check:
   - Status should be `200` (green)
   - Type should be `javascript` or `script`
   - Size should be `5.0 KB`

### Step 5: Test Direct Access
Open in new tab:
```
http://localhost:8000/static/reader/js/fingerprint.js
```

**Expected**: File should download or display in browser

## Possible Outcomes

### ✅ SUCCESS: Scripts Load
Console shows:
```
Scripts loaded. BrowserFingerprint available: true
```
**Action**: Audio progress tracking should work now!

### ❌ FAIL: 404 Not Found
Network tab shows red 404 error

**Cause**: Static files not being served
**Fix**:
```bash
# In terminal
source venv/bin/activate
python manage.py collectstatic --noinput
```

### ❌ FAIL: 200 OK but Script Not Executing
- File loads (200 status)
- But `BrowserFingerprint available: false`
- Fetch shows script content

**Cause**: JavaScript syntax error or browser compatibility
**Fix**: Check console for JavaScript errors (red text)

### ❌ FAIL: CORS or Security Error
Console shows security/CORS error

**Cause**: Browser security blocking script
**Fix**: 
1. Check if using HTTPS (should use HTTP for local dev)
2. Try different browser
3. Check browser security settings

## Quick Diagnostic Commands

### Verify File Exists
```bash
ls -la reader/static/reader/js/fingerprint.js
# Should show: -rw-rw-r-- 1 bill bill 5006 ...
```

### Check File Content
```bash
head -5 reader/static/reader/js/fingerprint.js
# Should show: class BrowserFingerprint {
```

### Test Static File Serving
```bash
curl http://localhost:8000/static/reader/js/fingerprint.js | head -5
# Should show: class BrowserFingerprint {
```

## If Still Not Working

### Try: Restart Django Server
```bash
# Stop server (Ctrl+C)
# Then restart:
source venv/bin/activate
python manage.py runserver
```

### Try: Different Browser
- Chrome
- Firefox
- Edge

### Try: Incognito/Private Mode
This bypasses all cache and extensions

### Check: Browser Console for Errors
Look for:
- Red error messages
- CSP (Content Security Policy) errors
- CORS errors
- Syntax errors

## Report Back

After testing, report:
1. What you see in console (copy/paste)
2. Network tab status for fingerprint.js
3. Can you access the file directly?
4. Any red errors in console?

This will help diagnose the exact issue!
