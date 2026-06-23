# Audio Progress Tracking Troubleshooting Guide

## Issue: System not keeping track of audio playback positioning

## Fixes Applied

### 1. Static Files Path Issue (FIXED)
**Problem**: JavaScript files were in wrong directory structure
- Files were in: `reader/static/js/`
- Should be in: `reader/static/reader/js/`

**Solution**: Moved files to correct location
```bash
mkdir -p reader/static/reader/js
mv reader/static/js/* reader/static/reader/js/
```

**Template Updated**: `sermon_list.html` now uses:
```django
{% static 'reader/js/fingerprint.js' %}
{% static 'reader/js/sermon_player.js' %}
```

### 2. Audio Duration Extraction Issue (FIXED)
**Problem**: Audio file might not exist on disk when save() is called
- Original code tried to read file before it was saved

**Solution**: Save file first, then extract duration
```python
def save(self, *args, **kwargs):
    super().save(*args, **kwargs)  # Save first
    
    if self.audio_file and not self.audio_duration:
        # Now file exists on disk
        audio = MutagenFile(self.audio_file.path)
        # Extract and save duration
```

### 3. Debug Page Created
**URL**: http://localhost:8000/debug-audio/

**Purpose**: Test and diagnose audio progress tracking
- Shows fingerprint generation status
- Displays script loading status
- Tests API endpoints
- Provides console log

## Testing Steps

### 1. Verify Static Files
```bash
# Check files are in correct location
ls -la reader/static/reader/js/

# Should show:
# fingerprint.js
# sermon_player.js
```

### 2. Test Debug Page
1. Navigate to: http://localhost:8000/debug-audio/
2. Check the status indicators:
   - ✅ Fingerprint should show a hash
   - ✅ Scripts should show "Loaded"
   - ✅ Audio elements should show "1"
3. Review console log for any errors

### 3. Test on Sermon Page
1. Go to: http://localhost:8000/sermons/
2. Open browser console (F12)
3. Look for these messages:
   ```
   Sermon list page loaded
   Audio elements: [number]
   ```
4. Play a sermon
5. Check console for:
   ```
   Extracted audio duration: ...
   ```

### 4. Verify Database
```bash
# Activate venv
source venv/bin/activate

# Check listening progress records
python manage.py shell
```

```python
from reader.models import ListeningProgress
ListeningProgress.objects.all()
# Should show records with fingerprint, sermon, and position
```

## Common Issues & Solutions

### Issue: Scripts Not Loading
**Symptoms**: Console shows "BrowserFingerprint is not defined"

**Solutions**:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh page (Ctrl+Shift+R)
3. Check static files are served:
   - Visit: http://localhost:8000/static/reader/js/fingerprint.js
   - Should download the file
4. Run collectstatic if needed:
   ```bash
   python manage.py collectstatic --noinput
   ```

### Issue: CSRF Token Error
**Symptoms**: Console shows "403 Forbidden" on save

**Solutions**:
1. Check CSRF middleware is enabled in settings.py
2. Verify cookie is being sent:
   ```javascript
   console.log(document.cookie);
   ```
3. Check CSRF_COOKIE_HTTPONLY setting

### Issue: API Endpoints Not Working
**Symptoms**: 404 errors on /api/progress/

**Solutions**:
1. Verify URLs are configured:
   ```bash
   python manage.py show_urls | grep progress
   ```
2. Check URL patterns in reader/urls.py
3. Restart development server

### Issue: Fingerprint Not Generating
**Symptoms**: Fingerprint shows "Loading..." forever

**Solutions**:
1. Check browser console for errors
2. Verify crypto.subtle is available (requires HTTPS or localhost)
3. Test in different browser
4. Check browser permissions (canvas, WebGL)

### Issue: Progress Not Saving
**Symptoms**: Position always starts at 0

**Solutions**:
1. Check database has ListeningProgress records:
   ```python
   from reader.models import ListeningProgress
   print(ListeningProgress.objects.count())
   ```
2. Verify fingerprint is consistent:
   - Open debug page
   - Note fingerprint
   - Refresh page
   - Fingerprint should be same
3. Check browser localStorage:
   ```javascript
   console.log(localStorage.getItem('browserFingerprint'));
   ```

### Issue: Audio Duration Not Extracted
**Symptoms**: Duration shows as empty in admin

**Solutions**:
1. Check mutagen is installed:
   ```bash
   pip list | grep mutagen
   ```
2. Verify audio file format is supported (MP3, WAV, OGG, M4A)
3. Check Django logs for warnings:
   ```bash
   tail -f logs/django.log
   ```
4. Manually trigger extraction:
   ```python
   from reader.models import Sermon
   sermon = Sermon.objects.get(id=1)
   sermon.save()  # Will re-extract duration
   ```

## Verification Checklist

- [ ] Static files in correct directory: `reader/static/reader/js/`
- [ ] Template uses correct path: `{% static 'reader/js/...' %}`
- [ ] Debug page loads without errors
- [ ] Fingerprint generates successfully
- [ ] Scripts show as "Loaded" on debug page
- [ ] API endpoints return success
- [ ] Browser console shows no errors
- [ ] Audio plays correctly
- [ ] Progress saves to database
- [ ] Position resumes on page reload
- [ ] Speed control works
- [ ] Time display updates

## Debug Commands

### Check Static Files Configuration
```python
from django.conf import settings
print(settings.STATIC_URL)
print(settings.STATIC_ROOT)
print(settings.STATICFILES_DIRS)
```

### Check Installed Apps
```python
from django.conf import settings
print('reader' in settings.INSTALLED_APPS)
```

### Test Fingerprint Generation
```javascript
// In browser console
BrowserFingerprint.get().then(fp => console.log(fp));
```

### Test API Manually
```bash
# Get CSRF token first
curl -c cookies.txt http://localhost:8000/sermons/

# Save progress
curl -b cookies.txt -X POST http://localhost:8000/api/progress/save/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: [token]" \
  -d '{"fingerprint":"test123","sermon_id":1,"position":42}'

# Get progress
curl http://localhost:8000/api/progress/1/?fingerprint=test123
```

## Next Steps if Still Not Working

1. **Enable Debug Logging**
   ```python
   # In settings.py
   LOGGING = {
       'version': 1,
       'handlers': {
           'console': {
               'class': 'logging.StreamHandler',
           },
       },
       'loggers': {
           'reader': {
               'handlers': ['console'],
               'level': 'DEBUG',
           },
       },
   }
   ```

2. **Add More Console Logging**
   Edit `sermon_player.js` and add:
   ```javascript
   console.log('SermonPlayer initialized for sermon:', this.sermonId);
   console.log('Fingerprint:', this.fingerprint);
   ```

3. **Check Network Tab**
   - Open browser DevTools (F12)
   - Go to Network tab
   - Play audio
   - Look for requests to `/api/progress/save/`
   - Check request/response details

4. **Test with Simple Audio**
   - Use the debug page test audio
   - It uses a public MP3 file
   - Should work without any sermon data

## Contact Information

If issue persists after trying all solutions:
1. Check browser console for errors
2. Check Django server logs
3. Review database for ListeningProgress records
4. Test with debug page first
5. Verify all files are in correct locations
