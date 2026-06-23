# CSRF Token Fix - 403 Forbidden Error

## Error
```
POST http://localhost:8000/api/progress/save/ 403 (Forbidden)
Error saving progress: SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

## Root Cause
Django's CSRF protection was blocking the POST request because:
1. CSRF token cookie wasn't being set on page load
2. JavaScript couldn't find the CSRF token to include in the request

## Fixes Applied

### 1. Added CSRF Token to Base Template
**File**: `reader/templates/reader/base.html`

Added meta tag in `<head>`:
```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

This makes the CSRF token available to JavaScript.

### 2. Ensured CSRF Cookie is Set
**File**: `reader/views.py`

Added decorators to views:
```python
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

@ensure_csrf_cookie
def debug_audio(request):
    ...

@method_decorator(ensure_csrf_cookie, name='dispatch')
class SermonListView(ListView):
    ...
```

This ensures Django sets the `csrftoken` cookie when these pages load.

### 3. Enhanced CSRF Token Retrieval
**File**: `reader/static/reader/js/sermon_player.js`

Updated `getCookie()` method to:
1. Try to get token from cookie (normal method)
2. Fall back to meta tag if cookie not found
3. Log error if no token available

```javascript
getCookie(name) {
    // Try cookie first
    let cookieValue = getCookieFromDocument(name);
    
    // Fallback to meta tag for CSRF
    if (!cookieValue && name === 'csrftoken') {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            cookieValue = metaTag.getAttribute('content');
        }
    }
    
    return cookieValue;
}
```

### 4. Better Error Handling
**File**: `reader/static/reader/js/sermon_player.js`

Added checks before saving:
```javascript
async saveProgress(position = null) {
    const csrfToken = this.getCookie('csrftoken');
    
    if (!csrfToken) {
        console.error('CSRF token not found! Cannot save progress.');
        console.log('Available cookies:', document.cookie);
        return;
    }
    
    // ... rest of save logic
}
```

Now logs helpful error messages if token is missing.

## Testing

### 1. Clear Browser Cache
```
Ctrl + Shift + Delete
or
Ctrl + Shift + R (hard refresh)
```

### 2. Test Debug Page
```
http://localhost:8000/debug-audio/
```

Open browser console (F12) and check for:
- No CSRF errors
- Progress saves successfully
- Console shows: "Progress saved: Xs"

### 3. Check CSRF Token
In browser console:
```javascript
// Check cookie
document.cookie

// Check meta tag
document.querySelector('meta[name="csrf-token"]').content

// Test getCookie function (after scripts load)
const player = new SermonPlayer(document.querySelector('audio'));
console.log(player.getCookie('csrftoken'));
```

### 4. Test on Sermon Page
```
http://localhost:8000/sermons/
```

1. Play a sermon
2. Wait 5 seconds
3. Check console for "Progress saved: Xs"
4. No 403 errors

## Expected Behavior Now

### On Page Load:
- Django sets `csrftoken` cookie
- Meta tag contains CSRF token
- JavaScript can access token via cookie OR meta tag

### When Saving Progress:
- JavaScript gets CSRF token
- Includes it in `X-CSRFToken` header
- Django validates token
- Request succeeds (200 OK)
- Console shows: "Progress saved: 42s"

### If Token Missing:
- Console shows: "CSRF token not found!"
- Console shows: "Available cookies: ..."
- Save is skipped (doesn't attempt request)

## Verification

After clearing cache and refreshing:

✅ No 403 errors
✅ Console shows "Progress saved: Xs"
✅ Database has ListeningProgress records
✅ Audio resumes from saved position

## Files Modified

1. `reader/templates/reader/base.html` - Added CSRF meta tag
2. `reader/views.py` - Added `@ensure_csrf_cookie` decorators
3. `reader/static/reader/js/sermon_player.js` - Enhanced token retrieval and error handling

## Why This Happened

Django's CSRF protection requires:
1. A CSRF token cookie to be set
2. The token to be included in POST requests

Without `@ensure_csrf_cookie`, Django doesn't always set the cookie on GET requests. This meant JavaScript couldn't find the token to include in the POST request, causing the 403 error.

The fix ensures the token is always available via both cookie AND meta tag.
