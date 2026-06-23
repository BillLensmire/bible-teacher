# Quick Test Guide - Audio Progress Tracking

## Issue Reported
System not keeping track of audio playback positioning

## Fixes Applied
1. ✅ Moved static files to correct Django location
2. ✅ Fixed audio duration extraction timing
3. ✅ Created debug page for testing

## Quick Test Steps

### 1. Test Debug Page (RECOMMENDED FIRST)
```
URL: http://localhost:8000/debug-audio/
```

**What to check:**
- ✅ Fingerprint shows a hash (not "Loading...")
- ✅ Scripts status shows "✅ Loaded"
- ✅ Audio elements shows "1"
- ✅ Console log shows successful API tests

**If this works**: The system is functioning correctly

**If this fails**: See troubleshooting section below

### 2. Test on Sermon Page
```
URL: http://localhost:8000/sermons/
```

**Steps:**
1. Open browser console (F12)
2. Look for: "Sermon list page loaded"
3. Play any sermon audio
4. Wait 5-10 seconds
5. Refresh the page
6. Audio should resume from where you left off

### 3. Verify in Database
```bash
source venv/bin/activate
python manage.py shell
```

```python
from reader.models import ListeningProgress
records = ListeningProgress.objects.all()
for r in records:
    print(f"Sermon: {r.sermon.title}, Position: {r.current_position}s")
```

## Quick Troubleshooting

### Scripts Not Loading?
```bash
# Check files exist
ls -la reader/static/reader/js/

# Should show:
# fingerprint.js
# sermon_player.js
```

**Fix**: Files are in correct location now. Clear browser cache (Ctrl+Shift+Delete)

### Still Not Working?
1. **Hard refresh**: Ctrl+Shift+R
2. **Check browser console**: F12 → Console tab
3. **Check network tab**: F12 → Network tab → Look for 404 errors
4. **Restart server**: Stop and restart `python manage.py runserver`

### Common Error Messages

**"BrowserFingerprint is not defined"**
- Scripts not loading
- Clear cache and hard refresh

**"403 Forbidden" on save**
- CSRF token issue
- Check cookies are enabled

**"404 Not Found" on /api/progress/**
- URL routing issue
- Restart Django server

## Expected Behavior

### When Playing Audio:
1. Fingerprint generated on page load
2. Progress saved every 5 seconds
3. Console shows save requests (in Network tab)
4. Database records created/updated

### When Returning:
1. Fingerprint retrieved from localStorage
2. Last position loaded from database
3. Blue notification shows "Resuming from X:XX"
4. Audio starts at saved position

## Debug URLs

- **Main debug page**: http://localhost:8000/debug-audio/
- **Sermon list**: http://localhost:8000/sermons/
- **Admin**: http://localhost:8000/admin/
- **Static file test**: http://localhost:8000/static/reader/js/fingerprint.js

## Success Indicators

✅ Debug page shows all green checkmarks
✅ Console log shows "Fingerprint generated"
✅ Network tab shows POST to /api/progress/save/
✅ Database has ListeningProgress records
✅ Audio resumes on page reload

## If Still Not Working

See detailed guide: `AUDIO_PROGRESS_TROUBLESHOOTING.md`

Or check:
1. Browser console for errors
2. Django server logs
3. Network tab for failed requests
4. Database for records

## Quick Commands

```bash
# Restart server
source venv/bin/activate
python manage.py runserver

# Check database
python manage.py shell
>>> from reader.models import ListeningProgress
>>> ListeningProgress.objects.count()

# Clear all progress (for testing)
>>> ListeningProgress.objects.all().delete()
```
